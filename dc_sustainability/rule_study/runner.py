"""Study-local common checked execution for rules-v1, greedy_a and greedy_b (adapter proposal-1).

One trusted runner serializes simulator mutations and gives all three policies identical
gate/clock/accounting semantics, using the UNCHANGED production ``check_schedule`` and
``recheck_schedule``. It does not use the F02 ``ExecutionController``/``TraceStore`` (those are
bound to the legacy ``SystemId``) and it never forges ``ApprovedActions`` or a passing check.

Per decision, in order: lock; read actual state and snapshot; bind identity/hashes; persist
an intention marker; compute candidates (no future arrivals or private weights are visible);
check every stage with the production gate; re-read state/snapshot and run the production
recheck; re-read again and refuse on any difference; mint ``ApprovedActions`` only from an
actually passing check; step the simulator once (``None`` invokes the simulator's own
refusal-and-drain: no starts, clock and running work advance); derive executed starts and the
state after from that real transition; publish one immutable decision record.

Deliberate stop conditions (never retried): rules-v1 R01/scope rejection and a changed live
state record the decision but do NOT step the simulator; an unexpected failure after the
intention marker leaves it reserved, and a later replay reports ``IndeterminateExecution``.
"""

import hashlib
import json
import os
import re
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from uuid import uuid4

from dc_sustainability import schemas as s
from dc_sustainability.policies import greedy
from dc_sustainability.rule_study import records as r
from dc_sustainability.rule_study import scheduler as sch
from dc_sustainability.runtime.traces import IndeterminateExecution
from dc_sustainability.simulator import SchedulingSimulator
from dc_sustainability.verification.checker import check_schedule, recheck_schedule

__all__ = [
    "CaseRun",
    "DecisionOutcome",
    "IndeterminateExecution",
    "RuleStudyRunner",
    "make_bindings",
    "replay_case",
    "run_case",
]

HORIZON = r.HORIZON_SLOTS
FaultInjection = Callable[[s.VisibleState], Optional[s.Plan]]


def _publish(path: Path, text: str) -> None:
    """Publish fully written bytes exclusively; never replace an existing artifact."""
    temp = path.parent / f".{uuid4().hex}.tmp"
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _publish_immutable(path: Path, text: str) -> None:
    """Publish once; an identical re-publish is fine, a different one is a hard error."""
    try:
        _publish(path, text)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != text:
            raise ValueError(f"a different immutable file already exists at {path.name}") from None


def _lf_sha256(path: Path) -> str:
    """SHA-256 of a source/lock file with CRLF normalized to LF (the repository convention)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


class BindingError(ValueError):
    """A required artifact binding cannot be established from actual artifacts."""


def make_bindings(case, repo_root, *, code_commit: Optional[str] = None) -> r.Bindings:
    """Bind every field the merged reader requires to a real, existing artifact.

    - ``spec_sha256``: canonical-JSON hash of ``docs/rule_study/specification.json`` (the same
      value the verifier derives and expects).
    - ``adapter_source_sha256``: canonical-JSON hash of ``{path: LF-normalized sha256}`` over
      every ``dc_sustainability/rule_study/*.py`` source file.
    - ``generator_source_sha256``: LF-normalized hash of the merged RULE-04 generator source
      (identical to the generator's own ``source_sha256()``).
    - ``environment_lock_sha256``: LF-normalized hash of
      ``requirements/requirements-windows-py312.lock.txt``.
    - ``case_sha256``: hash of the canonical ``case.json`` object.
    - ``code_commit``: the full ``git rev-parse HEAD``, and only from a completely clean
      working tree, so the committed sources are exactly the ones that ran. An explicit
      ``code_commit`` argument is for unit tests only and is not a real frozen binding.
    """
    root = Path(repo_root)
    spec_path = root / "docs" / "rule_study" / "specification.json"
    package = root / "dc_sustainability" / "rule_study"
    generator = root / "dc_sustainability" / "evaluation" / "rule_study_generator.py"
    lock = root / "requirements" / "requirements-windows-py312.lock.txt"
    for path in (spec_path, generator, lock):
        if not path.is_file():
            raise BindingError(f"required binding artifact is missing: {path.name}")
    sources = sorted(package.glob("*.py"))
    if not sources:
        raise BindingError("no adapter source files found")
    if code_commit is None:
        try:
            dirty = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            if dirty:
                raise BindingError("a clean committed checkout is required to bind code_commit")
            code_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise BindingError("cannot read the git commit") from exc
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    return r.Bindings(
        spec_sha256=r.study_sha256(r.study_json(spec)),
        adapter_source_sha256=r.study_sha256(
            r.study_json({p.name: _lf_sha256(p) for p in sources})
        ),
        generator_source_sha256=_lf_sha256(generator),
        case_sha256=case.case_sha256(),
        environment_lock_sha256=_lf_sha256(lock),
        code_commit=code_commit,
    )


@dataclass(frozen=True)
class DecisionOutcome:
    record: r.RuleStudyDecision
    decision_ref: str
    decision_sha256: str
    transition: object
    replayed: bool

    @property
    def stopped(self) -> bool:
        """True when the run must not continue (fail-closed input or changed live state)."""
        return any(error.code.startswith("STOP_") for error in self.record.errors)


def _identity(state: s.VisibleState) -> tuple:
    return (state.episode_id, state.current_slot, state.state_version)


def _violation_text(check: s.CheckResult) -> str:
    detail = [v.message for v in check.violations] + list(check.errors)
    return f"production check status {check.status}: " + "; ".join(detail)


class RuleStudyRunner:
    """Serialized common runner for one (policy, case). The caller owns the simulator."""

    def __init__(
        self,
        simulator: SchedulingSimulator,
        snapshot_reader: Callable[[], s.ConstraintSnapshot],
        directory,
        *,
        policy_id: str,
        case_id: str,
        decision_time_utc: Callable[[int], datetime],
        bindings: r.Bindings,
        score_convention: Optional[sch.ScoreConvention] = None,
        fault_injection: Optional[FaultInjection] = None,
        case_json: Optional[dict] = None,
        read_only: bool = False,
    ):
        if policy_id not in r.POLICY_IDS:
            raise ValueError(f"policy_id must be one of {r.POLICY_IDS}")
        if (
            not isinstance(case_id, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", case_id) is None
        ):
            raise ValueError("case_id must be a safe single path component")
        if policy_id == "rules-v1" and score_convention is None:
            raise ValueError("rules-v1 needs an explicit ScoreConvention")
        if fault_injection is not None and policy_id != "rules-v1":
            raise ValueError("fault injection is a rules-v1 demonstration only")
        if not isinstance(bindings, r.Bindings):
            raise TypeError("bindings must be Bindings")
        if type(read_only) is not bool:
            raise TypeError("read_only must be boolean")
        if (
            case_json is not None
            and r.study_sha256(r.study_json(case_json)) != bindings.case_sha256
        ):
            raise ValueError("case body and bindings identify a different immutable file")
        self._sim = simulator
        self._reader = snapshot_reader
        self._policy_id = policy_id
        self._case_id = case_id
        self._time = decision_time_utc
        self._bindings = bindings
        self._case_expected = case_json is not None
        self._convention = score_convention
        self._fault = fault_injection
        self._lock = threading.Lock()
        self._read_only = read_only
        self.root = Path(directory) / policy_id / f"{case_id}-{policy_id}"
        if read_only and any(
            p.is_symlink() or p.is_junction() for p in (self.root, *self.root.parents)
        ):
            raise ValueError("read-only replay refuses linked roots")
        for name in ("decisions", "states", "snapshots", "transitions", ".intents", ".completed"):
            path = self.root / name
            if read_only:
                if not path.is_dir() or path.is_symlink() or path.is_junction():
                    raise ValueError(
                        "read-only replay requires existing unlinked evidence directories"
                    )
            else:
                path.mkdir(parents=True, exist_ok=True)
        self._reasons: dict[str, str] = {}
        if case_json is not None:
            if read_only:
                if (self.root / "case.json").read_bytes() != r.study_json(case_json).encode(
                    "utf-8"
                ):
                    raise ValueError("read-only case differs from supplied evidence")
            else:
                _publish_immutable(self.root / "case.json", r.study_json(case_json))

    # ------------------------------------------------------------------ identity / replay
    def _fingerprint(self, index: int) -> str:
        probe = None
        if self._fault is not None:
            probe = "fault_injection_configured"
        return r.study_sha256(
            r.study_json(
                {
                    "adapter_version": r.ADAPTER_VERSION,
                    "study_id": r.STUDY_ID,
                    "policy_id": self._policy_id,
                    "case_id": self._case_id,
                    "decision_index": index,
                    "bindings": self._bindings.to_jsonable(),
                    "score_convention": None
                    if self._convention is None
                    else {
                        "id": self._convention.convention_id,
                        "status": self._convention.status,
                        "unit": self._convention.unit,
                    },
                    "fault": probe,
                }
            )
        )

    def _paths(self, index: int):
        name = f"decision-{index:02d}.json"
        return self.root / "decisions" / name, self.root / ".intents" / name

    def _outcome(self, index: int, record, text, transition, replayed) -> DecisionOutcome:
        return DecisionOutcome(
            record=record,
            decision_ref=f"decisions/decision-{index:02d}.json",
            decision_sha256=r.study_sha256(text),
            transition=transition,
            replayed=replayed,
        )

    def _replay(self, index: int) -> Optional[DecisionOutcome]:
        decision_path, intent_path = self._paths(index)
        if intent_path.exists():
            saved = json.loads(intent_path.read_text(encoding="utf-8"))
            if saved["fingerprint"] != self._fingerprint(index):
                raise ValueError("this decision is already reserved for a different request")
            if not decision_path.exists():
                raise IndeterminateExecution(
                    "reserved decision has no final record; reconcile actual state, do not retry"
                )
            text = decision_path.read_bytes().decode("utf-8")
            record = r.RuleStudyDecision.from_json(text)
            completion = self.root / ".completed" / decision_path.name
            if not completion.exists():
                raise IndeterminateExecution("record has no completion commitment; do not retry")
            if completion.read_bytes() != (r.study_sha256(text) + "\n").encode("utf-8"):
                raise ValueError("saved decision differs from its completion commitment")
            if (
                record.policy_id != self._policy_id
                or record.case_id != self._case_id
                or record.decision_index != index
                or record.bindings != self._bindings
                or record.state_before.to_jsonable() != saved["state_before"]
            ):
                raise ValueError("saved decision identity differs from its reservation")
            evidence = [
                (
                    self.root / "states" / f"{record.state_before.visible_state_sha256}.json",
                    record.state_before.visible_state_sha256,
                ),
                (
                    self.root
                    / "snapshots"
                    / f"{record.state_before.constraint_snapshot_sha256}.json",
                    record.state_before.constraint_snapshot_sha256,
                ),
            ]
            if record.execution.state_after is not None:
                digest = record.execution.state_after.state_sha256
                evidence.append((self.root / "states" / f"{digest}.json", digest))
            if record.execution.transition_ref is not None:
                expected_ref = f"transitions/transition-{index:02d}.json"
                if record.execution.transition_ref != expected_ref:
                    raise ValueError("unexpected transition reference")
                evidence.append((self.root / expected_ref, record.execution.transition_sha256))
            if self._case_expected or (self.root / "case.json").exists():
                evidence.append((self.root / "case.json", self._bindings.case_sha256))
            for path, digest in evidence:
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError(f"saved evidence hash mismatch: {path.name}")
            return self._outcome(index, record, text, None, True)
        if decision_path.exists():
            raise ValueError("a decision record exists outside this reservation")
        return None

    # ------------------------------------------------------------------ persistence
    def _persist_state(self, state: s.VisibleState) -> str:
        """Save the exact serialized state as ``states/<sha256>.json``; return that hash."""
        text = r.study_json(state.to_jsonable())
        digest = r.study_sha256(text)
        _publish_immutable(self.root / "states" / f"{digest}.json", text)
        return digest

    def _persist_snapshot(self, snapshot: s.ConstraintSnapshot) -> str:
        text = r.study_json(snapshot.to_jsonable())
        digest = r.study_sha256(text)
        _publish_immutable(self.root / "snapshots" / f"{digest}.json", text)
        return digest

    # ------------------------------------------------------------------ main transition
    def decide(self, decision_index: int) -> DecisionOutcome:
        """Check and execute one decision; replay saved evidence without another transition."""
        if type(decision_index) is not int or not 0 <= decision_index < HORIZON:
            raise ValueError("decision_index must be an integer 0-29")
        with self._lock:
            replay = self._replay(decision_index)
            if replay is not None:
                return replay
            if self._read_only:
                raise ValueError("read-only replay cannot execute a missing decision")
            state = self._sim.state()
            snapshot = self._reader()
            if state.current_slot != decision_index:
                raise ValueError("stale/different slot; no additional advancement")
            state_hash = self._persist_state(state)
            snap_hash = self._persist_snapshot(snapshot)
            before = r.StateBefore(
                slot=state.current_slot,
                state_version=state.state_version,
                visible_state_sha256=state_hash,
                constraint_snapshot_sha256=snap_hash,
            )
            decision_path, intent_path = self._paths(decision_index)
            _publish(
                intent_path,
                r.study_json(
                    {
                        "fingerprint": self._fingerprint(decision_index),
                        "state_before": before.to_jsonable(),
                    }
                ),
            )
            self._reasons = {}
            stages, errors, stop = self._candidates(state, snapshot)
            selected = next(
                (st for st in stages if st.check_result and st.check_result.status == "pass"),
                None,
            )
            recheck, approved = None, None
            if stop:
                pass
            elif selected is None:
                errors.append(
                    r.RecordError(
                        stage=None,
                        code="NO_APPROVED_CANDIDATE",
                        message="no proposal stage passed the production check; "
                        "refusal-and-drain with no new starts",
                    )
                )
            else:
                latest, latest_snapshot = self._sim.state(), self._reader()
                recheck = recheck_schedule(selected.plan, latest, latest_snapshot)
                final, final_snapshot = self._sim.state(), self._reader()
                if latest != state or final != state:
                    stop = True
                    errors.append(
                        r.RecordError(
                            stage=selected.stage_id,
                            code="STOP_STATE_CHANGED",
                            message="live state changed during the check; no approval minted "
                            "and the simulator was not stepped",
                        )
                    )
                elif latest_snapshot != snapshot or final_snapshot != snapshot:
                    errors.append(
                        r.RecordError(
                            stage=selected.stage_id,
                            code="CONSTRAINTS_CHANGED",
                            message="constraint snapshot changed during the check; refused",
                        )
                    )
                elif recheck.status != "pass":
                    errors.append(
                        r.RecordError(
                            stage=selected.stage_id,
                            code="RECHECK_REFUSED",
                            message="latest-state production recheck refused execution: "
                            + _violation_text(recheck),
                        )
                    )
                else:
                    approved = s.ApprovedActions.from_checked_plan(
                        selected.plan, recheck, final.state_version
                    )
            if stop:
                record = self._record(
                    decision_index,
                    before,
                    stages,
                    selected,
                    errors,
                    r.Execution(
                        # The merged reader requires state_after for every status except
                        # "indeterminate"; a stop without a step has none, so it is recorded as
                        # a stop that needs reconciliation. STOP_* errors say why.
                        status="indeterminate",
                        current_starts=(),
                        transition_ref=None,
                        transition_sha256=None,
                        simulator_rejection=None,
                        state_after=None,
                    ),
                )
                return self._publish_record(decision_index, decision_path, record, None)
            return self._step_and_record(
                decision_index,
                decision_path,
                state,
                before,
                stages,
                selected,
                recheck,
                approved,
                errors,
            )

    def _step_and_record(
        self, index, decision_path, state, before, stages, selected, recheck, approved, errors
    ):
        try:
            transition = self._sim.step(approved)  # None => the simulator's real refusal-and-drain
            if transition.rejection:
                errors.append(
                    r.RecordError(
                        stage=None,
                        code="SIMULATOR_REFUSAL",
                        message=f"simulator refusal: {transition.rejection}",
                    )
                )
            executed = tuple(transition.slot.started_job_ids)
            if approved is None and executed:
                raise RuntimeError("simulator executed starts without approval")
            if (
                approved is not None
                and not transition.rejection
                and set(executed) != {start.job_id for start in approved.starts}
            ):
                raise RuntimeError("executed starts differ from approved current starts")
            status = "executed" if approved is not None and not transition.rejection else "blocked"
            if (
                status == "executed"
                and selected.plan.abstentions
                and not selected.plan.starts
                and not selected.plan.deferrals
            ):
                status = "abstained"
            transition_text = r.study_json(
                {
                    "slot_record": transition.slot.to_jsonable(),
                    "rejection": transition.rejection,
                    "missed_job_ids": list(transition.missed_job_ids),
                    "nonflexible_violation_ids": list(transition.nonflexible_violation_ids),
                    # Evidence that the reader's decision record has no field for; hashed by
                    # transition_sha256 so it cannot be silently changed.
                    "latest_state_recheck": recheck.to_jsonable() if recheck is not None else None,
                    "fallback_reasons": dict(sorted(self._reasons.items())),
                }
            )
            transition_ref = f"transitions/transition-{index:02d}.json"
            _publish_immutable(self.root / transition_ref, transition_text)
            after = self._sim.state()
            after_hash = self._persist_state(after)
            record = self._record(
                index,
                before,
                stages,
                selected,
                errors,
                r.Execution(
                    status=status,
                    current_starts=executed,
                    transition_ref=transition_ref,
                    transition_sha256=r.study_sha256(transition_text),
                    simulator_rejection=transition.rejection,
                    state_after=r.StateAfter(
                        slot=after.current_slot,
                        state_version=after.state_version,
                        state_sha256=after_hash,
                    ),
                ),
            )
            return self._publish_record(index, decision_path, record, transition)
        except Exception as exc:
            raise IndeterminateExecution(
                "effect or record completion failed; do not retry automatically"
            ) from exc

    def _record(self, index, before, stages, selected, errors, execution):
        return r.RuleStudyDecision(
            record_kind=r.DECISION_KIND,
            adapter_version=r.ADAPTER_VERSION,
            study_id=r.STUDY_ID,
            policy_id=self._policy_id,
            case_id=self._case_id,
            decision_index=index,
            bindings=self._bindings,
            state_before=before,
            proposal_stages=tuple(stages),
            selected_stage_id=selected.stage_id if selected is not None else None,
            execution=execution,
            errors=tuple(errors),
            model_call_count=0,
        )

    def _publish_record(self, index, decision_path, record, transition) -> DecisionOutcome:
        text = record.to_json()
        _publish(decision_path, text)
        _publish(self.root / ".completed" / decision_path.name, r.study_sha256(text) + "\n")
        return self._outcome(index, record, text, transition, False)

    # ------------------------------------------------------------------ candidate stages
    def _stage(
        self,
        stages,
        origin,
        plan,
        state,
        snapshot,
        *,
        rule_ids=(),
        arithmetic=(),
        errors=(),
        fallback_reason=None,
    ):
        check = check_schedule(plan, state, snapshot)
        stage_id = f"STG-{len(stages)}"
        stage_errors = list(errors)
        if check.status != "pass":
            stage_errors.append(
                r.RecordError(
                    stage=stage_id,
                    code=f"CHECK_{check.status.upper()}",
                    message=_violation_text(check),
                )
            )
        stage = r.ProposalStage(
            stage_id=stage_id,
            origin=origin,
            plan=plan,
            rule_ids=tuple(rule_ids),
            arithmetic=tuple(arithmetic),
            check_result=check,
            errors=tuple(stage_errors),
        )
        if fallback_reason is not None:
            self._reasons[stage_id] = fallback_reason
        stages.append(stage)
        return stage

    def _candidates(self, state, snapshot):
        """Return (stages, record errors, stop). Greedy A/B reuse their actual PolicyOutput.plan."""
        stages: list[r.ProposalStage] = []
        errors: list[r.RecordError] = []
        decision_time = self._time(state.current_slot)
        try:
            context = s.Context.build(state, snapshot, representation="flat")
        except ValueError as exc:
            errors.append(r.RecordError(stage=None, code="CONTEXT_INVALID", message=str(exc)))
            if self._policy_id != "rules-v1":
                return stages, errors, False
            context = None

        if self._policy_id in ("greedy_a", "greedy_b"):
            try:
                output = greedy.propose(
                    state, context, system=self._policy_id, decision_time_utc=decision_time
                )
            except ValueError as exc:
                errors.append(r.RecordError(stage=None, code="POLICY_ERROR", message=str(exc)))
                return stages, errors, False
            if output.output_status != "ok":
                errors.append(
                    r.RecordError(
                        stage=None,
                        code="POLICY_OUTPUT",
                        message=f"policy output status: {output.output_status}",
                    )
                )
                return stages, errors, False
            policy_fallback = output.system == "greedy_a" and self._policy_id == "greedy_b"
            self._stage(
                stages,
                "greedy_a_fallback" if policy_fallback else self._policy_id,
                output.plan,
                state,
                snapshot,
                fallback_reason=output.explanation.summary
                if policy_fallback and output.explanation
                else None,
            )
            return stages, errors, False

        # rules-v1
        injected = self._fault(state) if self._fault is not None else None
        trigger: tuple = ()
        reason = None
        if injected is not None:
            stage = self._stage(
                stages,
                "fault_injection",
                injected,
                state,
                snapshot,
                rule_ids=("R04", "R09"),
                arithmetic=sch.explain_plan_capacity(state, snapshot, injected),
            )
            if stage.check_result.status == "pass":
                return stages, errors, False
            reason = "invalid_proposal"
        else:
            decision = sch.propose_rules_v1(
                state, snapshot, decision_time_utc=decision_time, score_convention=self._convention
            )
            if decision.status == "rejected":
                errors.extend(decision.errors)
                errors.append(
                    r.RecordError(
                        stage=None,
                        code="STOP_RULES_V1_REJECTED_INPUT",
                        message="rules-v1 failed closed on R01/scope input; no candidate, "
                        "no fallback, simulator not stepped",
                    )
                )
                return stages, errors, True
            if decision.status == "fallback_required":
                reason, trigger = decision.fallback_reason, decision.arithmetic
                errors.extend(decision.errors)
            else:
                stage = self._stage(
                    stages,
                    "rules-v1",
                    decision.plan,
                    state,
                    snapshot,
                    rule_ids=decision.rule_ids,
                    arithmetic=decision.arithmetic,
                )
                if stage.check_result.status == "pass":
                    return stages, errors, False
                reason = "invalid_proposal"
        if reason == "invalid_proposal":
            check = stages[-1].check_result
            trigger = (
                r.ArithmeticEntry(
                    rule_id="R08",
                    constraint_id=None,
                    slot=state.current_slot,
                    terms=(
                        r.ArithmeticTerm(
                            label="proposal_check_failed", job_id=None, value=1, unit="flag"
                        ),
                        r.ArithmeticTerm(
                            label="violations",
                            job_id=None,
                            value=len(check.violations),
                            unit="count",
                        ),
                    ),
                    total=1,
                    limit=0,
                    signed_excess=1,
                    outcome="fail",
                    unit="flag",
                    formula="a proposal failing the production check routes to checked Greedy A",
                ),
            )
        if context is None:
            errors.append(
                r.RecordError(
                    stage=None,
                    code="FALLBACK_UNAVAILABLE",
                    message="no valid context for the Greedy A fallback",
                )
            )
            return stages, errors, False
        fallback = greedy.propose(state, context, system="greedy_a")
        self._stage(
            stages,
            "greedy_a_fallback",
            fallback.plan,
            state,
            snapshot,
            rule_ids=("R08",),
            arithmetic=trigger,
            fallback_reason=reason,
        )
        return stages, errors, False


# ----------------------------------------------------------------------------- case driver
@dataclass(frozen=True)
class CaseRun:
    result: r.RuleStudyResult
    result_ref: str
    result_sha256: str
    outcomes: tuple[DecisionOutcome, ...]
    root: Path


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_result(
    root: Path, case, policy_id, bindings, convention, *, indeterminate=False
) -> r.RuleStudyResult:
    """Derive the result purely from persisted decision/transition evidence (replay-safe)."""
    decision_files = sorted((root / "decisions").glob("decision-*.json"))
    hashes, started, errors, transitions = [], {}, [], []
    stopped = False
    for path in decision_files:
        text = path.read_bytes().decode("utf-8")
        record = r.RuleStudyDecision.from_json(text)
        commitment = root / ".completed" / path.name
        if not commitment.is_file() or commitment.read_bytes() != (
            r.study_sha256(text) + "\n"
        ).encode("utf-8"):
            raise ValueError("result cannot use an uncommitted or modified decision")
        if (
            record.bindings != bindings
            or record.policy_id != policy_id
            or record.case_id != case.case_id
            or record.decision_index != len(hashes)
        ):
            raise ValueError("result decision identity or sequence mismatch")
        hashes.append(r.study_sha256(text))
        for job_id in record.execution.current_starts:
            started[job_id] = record.decision_index
        if record.execution.transition_ref:
            expected_ref = f"transitions/transition-{record.decision_index:02d}.json"
            if record.execution.transition_ref != expected_ref:
                raise ValueError("unexpected result transition reference")
            transition_path = root / expected_ref
            if (
                hashlib.sha256(transition_path.read_bytes()).hexdigest()
                != record.execution.transition_sha256
            ):
                raise ValueError("result transition hash mismatch")
            transitions.append(_load_json(transition_path))
        stop_errors = [e for e in record.errors if e.code.startswith("STOP_")]
        stopped = stopped or bool(stop_errors) or record.execution.status == "indeterminate"
        errors.extend(stop_errors)
    universe = {job.job_id: job for job in case.jobs}
    completed = sorted({j for t in transitions for j in t["slot_record"]["completed_job_ids"]})
    missed = sorted({j for t in transitions for j in t["missed_job_ids"]})
    # P2 definition in the merged reader: unfinished is every job that did not complete.
    unfinished = sorted(set(universe) - set(completed))
    unscheduled = sorted(set(universe) - set(started))
    started_not_completed = sorted(set(started) - set(completed))
    complete = len(hashes) == HORIZON and not stopped and not indeterminate
    status = "failed" if indeterminate else "complete" if complete else "partial"
    accounting = None
    if status != "failed":
        weights = {o.valid_slot: int(o.value) for o in case.episode().realized_carbon}
        per_job, total = [], 0
        for job_id in completed:
            job = universe[job_id]
            score = convention.job_score(
                power_kw=int(job.power_kw),
                start=started[job_id],
                duration_slots=job.duration_slots,
                weights=weights,
            )
            total += score.total
            per_job.append(
                r.JobAccounting(
                    job_id=job_id,
                    power_kw=int(job.power_kw),
                    start_slot=started[job_id],
                    end_slot=started[job_id] + job.duration_slots,
                    synthetic_impact=score.total,
                )
            )
        slot_hours = 1.0
        job_kwh = sum(t["slot_record"]["job_load_kw"] for t in transitions) * slot_hours
        background_kwh = (
            sum(t["slot_record"]["background_load_kw"] for t in transitions) * slot_hours
        )
        accounting = r.Accounting(
            slots_recorded=len(transitions),
            slot_hours=slot_hours,
            pue=float(case.pue),
            background_kw=case.background_kw,
            capacity_kw=case.capacity_kw,
            score_convention_id=convention.convention_id,
            score_convention_status=convention.status,
            synthetic_impact_unit=convention.unit,
            synthetic_impact_total=total,
            per_job=tuple(per_job),
            job_outcomes=r.JobOutcomes(
                completed=tuple(completed),
                missed=tuple(missed),
                unscheduled=tuple(unscheduled),
                started_not_completed=tuple(started_not_completed),
                unfinished=tuple(unfinished),
            ),
            job_it_energy_kwh=job_kwh,
            job_facility_energy_kwh=job_kwh * case.pue,
            background_facility_energy_kwh=background_kwh * case.pue,
            site_facility_energy_kwh=(job_kwh + background_kwh) * case.pue,
            energy_unit="kWh",
        )
    if indeterminate:
        errors.append(
            r.RecordError(
                stage=None,
                code="INDETERMINATE_EXECUTION",
                message="effect/record completion failed; stopped, not retried",
            )
        )
    return r.RuleStudyResult(
        record_kind=r.RESULT_KIND,
        adapter_version=r.ADAPTER_VERSION,
        study_id=r.STUDY_ID,
        policy_id=policy_id,
        case_id=case.case_id,
        bindings=bindings,
        decision_sha256s=tuple(hashes),
        completed_job_ids=tuple(completed),
        missed_job_ids=tuple(missed),
        unfinished_job_ids=tuple(unfinished),
        accounting=accounting,
        status=status,
        errors=tuple(errors),
    )


def run_case(
    directory,
    case,
    policy_id: str,
    *,
    bindings: r.Bindings,
    score_convention: sch.ScoreConvention,
    fault_injection: Optional[FaultInjection] = None,
    simulator: Optional[SchedulingSimulator] = None,
    snapshot_reader: Optional[Callable[[], s.ConstraintSnapshot]] = None,
) -> tuple[CaseRun, SchedulingSimulator, RuleStudyRunner]:
    """Run all 30 decisions of an authored case through the common runner and write the result."""
    if type(case.pue) not in (int, float) or case.pue != 1:
        raise ValueError("the accepted rule-study case envelope fixes PUE to 1")
    sim = simulator or SchedulingSimulator(allow_completion_starts=False)
    if simulator is None:
        sim.reset(case.episode(), forecasts_by_slot=case.forecasts_by_slot())
    snapshot = case.snapshot()
    runner = RuleStudyRunner(
        sim,
        snapshot_reader or (lambda: snapshot),
        directory,
        policy_id=policy_id,
        case_id=case.case_id,
        decision_time_utc=case.decision_time_utc,
        bindings=bindings,
        score_convention=score_convention,
        fault_injection=fault_injection,
        case_json=case.case_json(),
    )
    outcomes, indeterminate = [], False
    for index in range(HORIZON):
        try:
            outcome = runner.decide(index)
        except IndeterminateExecution:
            indeterminate = True
            break
        outcomes.append(outcome)
        if outcome.stopped:
            break
    result = build_result(
        runner.root, case, policy_id, bindings, score_convention, indeterminate=indeterminate
    )
    text = result.to_json()
    _publish_immutable(runner.root / "result.json", text)
    return (
        CaseRun(result, "result.json", r.study_sha256(text), tuple(outcomes), runner.root),
        sim,
        runner,
    )


def replay_case(runner: RuleStudyRunner, n: int = HORIZON) -> tuple[DecisionOutcome, ...]:
    """Return the saved evidence for the first n decisions without another simulator step."""
    return tuple(runner.decide(index) for index in range(n))
