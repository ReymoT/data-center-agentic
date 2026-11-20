"""RULE-03 trace mode: independent reader and replay of rule-study adapter records (#241).

Reads ``rule_study_decision_v1`` and ``rule_study_result_v1`` records as agreed in
ADAPTER_RECORD_PROPOSAL.md proposal-1 (accepted by Nisha and Ved in #239) and replays them
with the independent predicates in ``rule_study_verifier``. Standard library only: no
production checker, simulator, schema or scheduler import, and no field the system reports
about its own success (check results, passed flags, status) is used as a verdict.

Fail closed: an unknown record kind, adapter version, study, policy or field, a missing
or malformed binding, a hash mismatch, a nonzero model-call count or a broken decision
sequence refuses the whole trace. A refused trace is counted and makes the properties it
would have informed INCOMPLETE; it is never scored as PASS.

What is checked per trace (method ``trace_replay``):

- S1-S3 on the executed current starts, against a reconstruction from the case input.
- S4: no stage whose current-slot starts are invalid is executed; executed starts come only
  from the selected stage; with no selected stage nothing executes.
- S5: one decision per slot 0..29 in order, state_version == slot, state_after.slot ==
  slot + 1, state hash continuity, no new starts in slots 24-29, consistent execution
  status. An ``indeterminate`` execution stops the replay (partial trace).
- P1 on oracle-eligible inputs, P2 against the result record's job sets.
- Arithmetic consistency (not a safety property): each capacity arithmetic entry's
  total, limit and signed excess against an independent recomputation for that stage's
  plan.

Field names of ``rule_study_result_v1`` beyond the proposal's prose (``decision_sha256s``,
``completed_job_ids``, ``missed_job_ids``, ``unfinished_job_ids``, ``accounting``,
``status``) are this reader's assumption until Ved's adapter publishes them.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from dc_sustainability.evaluation import rule_study_verifier as v

DECISION_KIND = "rule_study_decision_v1"
RESULT_KIND = "rule_study_result_v1"
ACCEPTED_ADAPTER_VERSIONS = frozenset({"proposal-1"})
STUDY_ID = "rule-study-20261119-v1"
POLICY_IDS = frozenset({"rules-v1", "greedy_a", "greedy_b"})
STAGE_ORIGINS = frozenset(
    {"rules-v1", "greedy_a", "greedy_b", "greedy_a_fallback", "fault_injection"}
)
EXECUTION_STATUSES = frozenset({"executed", "abstained", "blocked", "indeterminate"})
RESULT_STATUSES = frozenset({"complete", "partial", "failed"})
DECISION_FIELDS = frozenset(
    {
        "record_kind",
        "adapter_version",
        "study_id",
        "policy_id",
        "case_id",
        "decision_index",
        "bindings",
        "state_before",
        "proposal_stages",
        "selected_stage_id",
        "execution",
        "errors",
        "model_call_count",
    }
)
BINDING_FIELDS = frozenset(
    {
        "spec_sha256",
        "adapter_source_sha256",
        "generator_source_sha256",
        "case_sha256",
        "environment_lock_sha256",
        "code_commit",
    }
)
STATE_BEFORE_FIELDS = frozenset(
    {"slot", "state_version", "visible_state_sha256", "constraint_snapshot_sha256"}
)
STAGE_FIELDS = frozenset(
    {"stage_id", "origin", "plan", "rule_ids", "arithmetic", "check_result", "errors"}
)
EXECUTION_FIELDS = frozenset(
    {
        "status",
        "current_starts",
        "transition_ref",
        "transition_sha256",
        "simulator_rejection",
        "state_after",
    }
)
STATE_AFTER_FIELDS = frozenset({"slot", "state_version", "state_sha256"})
RESULT_FIELDS = frozenset(
    {
        "record_kind",
        "adapter_version",
        "study_id",
        "policy_id",
        "case_id",
        "bindings",
        "decision_sha256s",
        "completed_job_ids",
        "missed_job_ids",
        "unfinished_job_ids",
        "accounting",
        "status",
        "errors",
    }
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


class TraceRefused(ValueError):
    """The trace cannot be read under the agreed contract; nothing in it is scored."""


# --- Case input -----------------------------------------------------------------------------


def case_from_dict(data: Mapping) -> v.Case:
    """Build a case from its JSON input; scores as a full 30-slot list or first+remaining."""
    if "scores" in data:
        scores = None if data["scores"] is None else tuple(data["scores"])
    elif "first_scores" in data:
        first = list(data["first_scores"])
        scores = tuple(first + [data["remaining_score"]] * (v.HORIZON - len(first)))
    else:
        raise TraceRefused("case has no scores field (use null for a missing forecast)")
    jobs = tuple(
        v.Job(
            j["job_id"],
            j["power_kw"],
            j["duration_slots"],
            j["arrival_slot"],
            j["deadline_slot"],
            j["flexible"],
        )
        for j in data["jobs"]
    )
    return v.Case(
        data.get("case_id") or data.get("id"),
        data["capacity_kw"],
        data["background_kw"],
        jobs,
        scores,
        tuple(data.get("fault_starts", ())),
    )


# --- Strict readers -------------------------------------------------------------------------


def _fields(obj, allowed: frozenset, where: str, required: frozenset | None = None) -> Mapping:
    if not isinstance(obj, Mapping):
        raise TraceRefused(f"{where}: expected an object")
    unknown = set(obj) - allowed
    if unknown:
        raise TraceRefused(f"{where}: unknown fields {sorted(unknown)}")
    missing = (required if required is not None else allowed) - set(obj)
    if missing:
        raise TraceRefused(f"{where}: missing fields {sorted(missing)}")
    return obj


def _int(value, where: str, lo: int, hi: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not lo <= value <= hi:
        raise TraceRefused(f"{where}: expected integer {lo}-{hi}")
    return value


def _sha(value, where: str) -> str:
    if not isinstance(value, str) or not SHA256.match(value):
        raise TraceRefused(f"{where}: expected lowercase sha256 hex")
    return value


def _bindings(obj, where: str) -> Mapping:
    b = _fields(obj, BINDING_FIELDS, f"{where}.bindings")
    for key in BINDING_FIELDS - {"code_commit"}:
        _sha(b[key], f"{where}.bindings.{key}")
    if not isinstance(b["code_commit"], str) or not COMMIT.match(b["code_commit"]):
        raise TraceRefused(f"{where}.bindings.code_commit: expected full 40-hex commit")
    return b


def _plan_starts(plan, where: str) -> tuple[tuple[str, int], ...]:
    if not isinstance(plan, Mapping) or not isinstance(plan.get("starts", []), list):
        raise TraceRefused(f"{where}.plan: expected an F02 Plan object with a starts list")
    _fields(
        plan,
        frozenset(
            {
                "schema_version",
                "record_type",
                "episode_id",
                "slot",
                "state_version",
                "starts",
                "deferrals",
                "abstentions",
                "evidence_ids",
                "status",
            }
        ),
        f"{where}.plan",
        required=frozenset({"starts"}),
    )
    out = []
    for i, s in enumerate(plan.get("starts", [])):
        if not isinstance(s, Mapping) or not isinstance(s.get("job_id"), str):
            raise TraceRefused(f"{where}.plan.starts[{i}]: expected job_id/start_slot")
        _fields(s, frozenset({"job_id", "start_slot"}), f"{where}.plan.starts[{i}]")
        if not s["job_id"]:
            raise TraceRefused(f"{where}: empty job ID")
        out.append((s["job_id"], _int(s.get("start_slot"), f"{where}.plan.starts[{i}]", 0, 29)))
    return tuple(out)


@dataclass(frozen=True)
class Stage:
    stage_id: str
    origin: str
    starts: tuple[tuple[str, int], ...]  # all planned starts, including future ones
    arithmetic: tuple[Mapping, ...]

    def current(self, slot: int) -> tuple[str, ...]:
        return tuple(job for job, start in self.starts if start == slot)


@dataclass(frozen=True)
class Decision:
    index: int
    slot: int
    state_version: int
    visible_state_sha256: str
    stages: tuple[Stage, ...]
    selected_stage_id: str | None
    status: str
    current_starts: tuple[str, ...]
    after_slot: int | None
    after_sha256: str | None
    raw_sha256: str


def read_decision(rec, *, case_id: str, policy_id: str, bindings: Mapping) -> Decision:
    where = f"decision[{rec.get('decision_index') if isinstance(rec, Mapping) else '?'}]"
    _fields(rec, DECISION_FIELDS, where)
    if rec["record_kind"] != DECISION_KIND:
        raise TraceRefused(f"{where}: record_kind {rec['record_kind']!r} is not {DECISION_KIND}")
    if rec["adapter_version"] not in ACCEPTED_ADAPTER_VERSIONS:
        raise TraceRefused(f"{where}: adapter_version {rec['adapter_version']!r} not accepted")
    if rec["study_id"] != STUDY_ID:
        raise TraceRefused(f"{where}: study_id {rec['study_id']!r}")
    if rec["policy_id"] != policy_id or rec["case_id"] != case_id:
        raise TraceRefused(f"{where}: policy/case identity differs within the trace")
    if dict(_bindings(rec["bindings"], where)) != dict(bindings):
        raise TraceRefused(f"{where}: bindings differ within the trace")
    if type(rec["model_call_count"]) is not int or rec["model_call_count"] != 0:
        raise TraceRefused(f"{where}: model_call_count must be exactly 0")
    index = _int(rec["decision_index"], f"{where}.decision_index", 0, 29)
    sb = _fields(rec["state_before"], STATE_BEFORE_FIELDS, f"{where}.state_before")
    slot = _int(sb["slot"], f"{where}.state_before.slot", 0, 29)
    version = _int(sb["state_version"], f"{where}.state_before.state_version", 0, 10**9)
    vis = _sha(sb["visible_state_sha256"], f"{where}.state_before.visible_state_sha256")
    _sha(sb["constraint_snapshot_sha256"], f"{where}.state_before.constraint_snapshot_sha256")
    if not isinstance(rec["proposal_stages"], list) or not isinstance(rec["errors"], list):
        raise TraceRefused(f"{where}: proposal_stages and errors must be lists")
    stages = []
    for i, st in enumerate(rec["proposal_stages"]):
        sw = f"{where}.proposal_stages[{i}]"
        _fields(st, STAGE_FIELDS, sw, required=frozenset({"stage_id", "origin", "plan"}))
        if st["origin"] not in STAGE_ORIGINS:
            raise TraceRefused(f"{sw}: origin {st['origin']!r}")
        if not isinstance(st["stage_id"], str) or not st["stage_id"]:
            raise TraceRefused(f"{sw}: stage_id")
        arithmetic = st.get("arithmetic", [])
        if not isinstance(arithmetic, list):
            raise TraceRefused(f"{sw}.arithmetic: expected a list")
        for entry in arithmetic:
            if not isinstance(entry, Mapping):
                raise TraceRefused(f"{sw}.arithmetic: expected object entries")
            if entry.get("rule_id") != "R04":
                continue
            _int(entry.get("slot"), f"{sw}.arithmetic.slot", 0, 29)
            for key in ("total", "limit", "signed_excess"):
                value = entry.get(key)
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise TraceRefused(f"{sw}.arithmetic.{key}: expected finite number")
            terms = entry.get("terms")
            if not isinstance(terms, list) or any(
                not isinstance(term, Mapping)
                or type(term.get("value")) not in (int, float)
                or not math.isfinite(term["value"])
                for term in terms
            ):
                raise TraceRefused(f"{sw}.arithmetic.terms: expected finite numeric terms")
        starts = _plan_starts(st["plan"], sw)
        plan = st["plan"]
        if "record_type" in plan and plan["record_type"] != "Plan":
            raise TraceRefused(f"{sw}.plan: unknown record_type")
        if "slot" in plan and _int(plan["slot"], f"{sw}.plan.slot", 0, 29) != slot:
            raise TraceRefused(f"{sw}.plan.slot: does not match decision state")
        if (
            "state_version" in plan
            and _int(plan["state_version"], f"{sw}.plan.state_version", 0, 10**9) != version
        ):
            raise TraceRefused(f"{sw}.plan.state_version: stale or mismatched state")
        stages.append(Stage(st["stage_id"], st["origin"], starts, tuple(arithmetic)))
    ids = [s.stage_id for s in stages]
    if len(set(ids)) != len(ids):
        raise TraceRefused(f"{where}: duplicate stage_id")
    selected = rec["selected_stage_id"]
    if selected is not None and selected not in ids:
        raise TraceRefused(f"{where}: selected_stage_id {selected!r} names no stage")
    ex = _fields(
        rec["execution"],
        EXECUTION_FIELDS,
        f"{where}.execution",
        required=frozenset({"status", "current_starts", "state_after"}),
    )
    if ex["status"] not in EXECUTION_STATUSES:
        raise TraceRefused(f"{where}.execution.status {ex['status']!r}")
    starts = ex["current_starts"]
    if not isinstance(starts, list) or not all(isinstance(j, str) for j in starts):
        raise TraceRefused(f"{where}.execution.current_starts: expected job ID strings")
    after_slot = after_sha = None
    if ex["state_after"] is not None:
        sa = _fields(ex["state_after"], STATE_AFTER_FIELDS, f"{where}.execution.state_after")
        after_slot = _int(sa["slot"], f"{where}.execution.state_after.slot", 1, 30)
        after_sha = _sha(sa["state_sha256"], f"{where}.execution.state_after.state_sha256")
        after_version = _int(
            sa["state_version"], f"{where}.execution.state_after.state_version", 1, 10**9
        )
        if after_version != after_slot:
            raise TraceRefused(f"{where}: state_after.state_version must match its boundary slot")
    elif ex["status"] != "indeterminate":
        raise TraceRefused(f"{where}: state_after is required unless execution is indeterminate")
    return Decision(
        index,
        slot,
        version,
        vis,
        tuple(stages),
        selected,
        ex["status"],
        tuple(starts),
        after_slot,
        after_sha,
        v.canonical_sha256(rec),
    )


@dataclass(frozen=True)
class Trace:
    case: v.Case
    policy_id: str
    decisions: tuple[Decision, ...]
    result: Mapping


def read_trace(
    case_data: Mapping,
    decisions: Sequence[Mapping],
    result: Mapping,
    *,
    expected_spec_sha256: str | None = None,
) -> Trace:
    """Strictly read one case/policy trace; raises TraceRefused on any contract breach."""
    case = case_from_dict(case_data)
    _fields(result, RESULT_FIELDS, "result", required=RESULT_FIELDS - {"errors"})
    if result["record_kind"] != RESULT_KIND:
        raise TraceRefused(f"result: record_kind {result['record_kind']!r}")
    if result["adapter_version"] not in ACCEPTED_ADAPTER_VERSIONS:
        raise TraceRefused(f"result: adapter_version {result['adapter_version']!r} not accepted")
    if result["study_id"] != STUDY_ID or result["policy_id"] not in POLICY_IDS:
        raise TraceRefused("result: study/policy identity")
    if result["case_id"] != case.case_id:
        raise TraceRefused("result: case_id does not match the case input")
    if result["status"] not in RESULT_STATUSES:
        raise TraceRefused(f"result: status {result['status']!r}")
    bindings = _bindings(result["bindings"], "result")
    if bindings["case_sha256"] != v.canonical_sha256(case_data):
        raise TraceRefused("result: case_sha256 does not match the supplied case input")
    if expected_spec_sha256 is not None and bindings["spec_sha256"] != expected_spec_sha256:
        raise TraceRefused("result: spec_sha256 does not match the expected specification")
    for key in ("completed_job_ids", "missed_job_ids", "unfinished_job_ids", "decision_sha256s"):
        if not isinstance(result[key], list) or not all(isinstance(x, str) for x in result[key]):
            raise TraceRefused(f"result.{key}: expected a list of strings")
    read = [
        read_decision(d, case_id=case.case_id, policy_id=result["policy_id"], bindings=bindings)
        for d in decisions
    ]
    read.sort(key=lambda d: d.index)
    if [d.index for d in read] != list(range(len(read))):
        raise TraceRefused("decision_index values must be 0..n-1 without gaps or repeats")
    if result["decision_sha256s"] != [d.raw_sha256 for d in read]:
        raise TraceRefused("result.decision_sha256s does not bind the supplied decisions")
    return Trace(case, result["policy_id"], tuple(read), result)


# --- Replay ---------------------------------------------------------------------------------


@dataclass
class _TraceTally:
    tally: v._Tally = field(default_factory=v._Tally)
    arithmetic_checked: int = 0
    arithmetic_mismatches: list[dict] = field(default_factory=list)
    continuity_checked: int = 0
    continuity_mismatches: list[dict] = field(default_factory=list)


def _record(t: _TraceTally, case, state, prop, code, detail, decision=None, extra=None):
    item = {"decision_index": decision.index} if decision is not None else {}
    if extra:
        item.update(extra)
    t.tally.record(case, state, v.Violation(prop, code, detail), item)


def _plan_load(case: v.Case, state: v.State, starts, slot: int) -> int:
    load = case.background_kw
    for job_id, start, end in state.running:
        if start <= slot < end:
            load += case.job(job_id).power_kw
    for job_id, start in starts:
        job = case.job(job_id)
        if job is not None and start <= slot < start + job.duration_slots:
            load += job.power_kw
    return load


def _check_arithmetic(t: _TraceTally, case, state, decision: Decision, stage: Stage):
    """Compare capacity arithmetic entries with an independent recomputation (R04 entries)."""
    for entry in stage.arithmetic:
        if not isinstance(entry, Mapping) or entry.get("rule_id") != "R04":
            continue
        t.arithmetic_checked += 1
        slot = entry.get("slot")
        if not isinstance(slot, int) or not state.slot <= slot < v.HORIZON:
            t.arithmetic_mismatches.append(
                {
                    "decision_index": decision.index,
                    "stage_id": stage.stage_id,
                    "reason": f"slot {slot!r} outside the remaining horizon",
                }
            )
            continue
        total = _plan_load(case, state, stage.starts, slot)
        expected = {
            "total": total,
            "limit": case.capacity_kw,
            "signed_excess": total - case.capacity_kw,
        }
        reported = {k: entry.get(k) for k in expected}
        terms = entry.get("terms")
        term_sum = (
            sum(x.get("value", 0) for x in terms)
            if isinstance(terms, list) and all(isinstance(x, Mapping) for x in terms)
            else None
        )
        expected_terms = [(None, case.background_kw, "kW")]
        for jid, start, end in state.running:
            if start <= slot < end:
                expected_terms.append((jid, case.job(jid).power_kw, "kW"))
        for jid, start in stage.starts:
            job = case.job(jid)
            if job is not None and start <= slot < start + job.duration_slots:
                expected_terms.append((jid, job.power_kw, "kW"))
        reported_terms = [(x.get("job_id"), x.get("value"), x.get("unit")) for x in terms]
        terms_match = sorted(expected_terms, key=repr) == sorted(reported_terms, key=repr)
        if reported != expected or term_sum != entry.get("total") or not terms_match:
            t.arithmetic_mismatches.append(
                {
                    "decision_index": decision.index,
                    "stage_id": stage.stage_id,
                    "slot": slot,
                    "reported": reported,
                    "independent": expected,
                    "reported_term_sum": term_sum,
                    "terms_match_input_jobs_and_units": terms_match,
                }
            )


def _valid_plan(case: v.Case, state: v.State, stage: Stage) -> bool:
    seen = set()
    waiting = {j.job_id for j in state.waiting(case)}
    for job_id, start in stage.starts:
        job = case.job(job_id)
        if job is None or job_id not in waiting or job_id in seen:
            return False
        seen.add(job_id)
        if start not in job.legal_starts(state.slot):
            return False
    return all(
        _plan_load(case, state, stage.starts, slot) <= case.capacity_kw
        for slot in range(state.slot, v.HORIZON)
    )


def replay_trace(trace: Trace, t: _TraceTally, budget: v.Budget | None = None) -> dict:
    """Replay one read trace; returns per-trace facts used for P1/P2 and aggregation."""
    case = trace.case
    state = v.initial_state()
    prev_after_sha = None
    stopped = None
    for d in trace.decisions:
        if budget is not None and not budget.take_state("trace_replay"):
            stopped = "budget"
            break
        tally = t.tally
        if d.slot != state.slot or d.index != state.slot:
            _record(
                t,
                case,
                state,
                "S5",
                "clock",
                f"decision {d.index} at slot {d.slot}; reconstruction at {state.slot}",
                d,
            )
            stopped = "clock"
            break
        if d.state_version != d.slot:
            _record(t, case, state, "S5", "state_version", f"version {d.state_version}", d)
        if prev_after_sha is not None:
            # Informational until the runner confirms state_after.state_sha256 and the next
            # visible_state_sha256 hash the same object; never a safety verdict on its own.
            t.continuity_checked += 1
            if d.visible_state_sha256 != prev_after_sha:
                t.continuity_mismatches.append({"decision_index": d.index})
        for stage in d.stages:
            _check_arithmetic(t, case, state, d, stage)
        executed = d.current_starts
        if d.status == "indeterminate":
            stopped = "indeterminate"
            break
        if d.status in ("abstained", "blocked") and executed:
            _record(
                t,
                case,
                state,
                "S4",
                "starts_without_execution_status",
                f"status {d.status} with starts {list(executed)}",
                d,
            )
        selected = next((s for s in d.stages if s.stage_id == d.selected_stage_id), None)
        if (executed or d.status == "executed") and selected is None:
            _record(
                t,
                case,
                state,
                "S4",
                "execution_without_selected_stage",
                f"starts {list(executed)}",
                d,
            )
        if (
            selected is not None
            and d.status == "executed"
            and (sorted(executed) != sorted(selected.current(d.slot)))
        ):
            _record(
                t,
                case,
                state,
                "S4",
                "execution_differs_from_selected_stage",
                f"executed {list(executed)}; selected {list(selected.current(d.slot))}",
                d,
            )
        for stage in d.stages:
            if _valid_plan(case, state, stage):
                continue
            tally.checked["S4"] += 1
            if selected is stage and (executed or d.status == "executed"):
                _record(
                    t,
                    case,
                    state,
                    "S4",
                    "invalid_selected_plan_executed",
                    f"selected stage {stage.stage_id} has invalid current/future placements",
                    d,
                )
        stages = [v.ProposalStage(s.origin, s.current(d.slot)) for s in d.stages]
        valid = v._check_decision(case, state, v.SystemDecision(executed, tuple(stages)), tally)
        if not valid:
            stopped = "invalid_execution"
            break
        if budget is not None and not budget.take_transition("trace_replay"):
            stopped = "budget"
            break
        state = v.advance(case, state, executed)
        if d.after_slot != state.slot:
            _record(
                t,
                case,
                state,
                "S5",
                "state_after_slot",
                f"reported {d.after_slot}; reconstruction {state.slot}",
                d,
            )
        prev_after_sha = d.after_sha256
    complete = stopped is None and state.slot == v.HORIZON
    return {"state": state, "complete": complete, "stopped": stopped}


def verify_traces(
    traces: Sequence[tuple[Mapping, Sequence[Mapping], Mapping]],
    *,
    expected_spec_sha256: str | None = None,
    is_rules_v1_run: bool = False,
    budget: v.Budget | None = None,
) -> dict:
    """Read and replay (case, decisions, result) triples; one report per policy_id."""
    budget = budget or v.Budget()
    per_policy: dict[str, dict] = {}
    refused: list[dict] = []
    for n, (case_data, decisions, result) in enumerate(traces):
        try:
            trace = read_trace(
                case_data, decisions, result, expected_spec_sha256=expected_spec_sha256
            )
        except (TraceRefused, KeyError, TypeError, ValueError) as exc:
            refused.append({"trace_index": n, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        bucket = per_policy.setdefault(
            trace.policy_id,
            {
                "t": _TraceTally(),
                "traces": 0,
                "complete": 0,
                "p1_eligible": 0,
                "p1_outside": {},
                "p2_checked": 0,
                "partial": 0,
                "bindings": set(),
            },
        )
        bucket["traces"] += 1
        bucket["bindings"].add(json.dumps(dict(trace.result["bindings"]), sort_keys=True))
        t = bucket["t"]
        facts = replay_trace(trace, t, budget)
        final = facts["state"]
        try:
            witness, _ = v.completion_witness(trace.case, v.initial_state(), budget=budget)
        except v.BudgetStopped:
            bucket["partial"] += 1
            continue
        outside = v._p1_scope(trace.case, witness)
        if not facts["complete"] or trace.result["status"] != "complete":
            bucket["partial"] += 1
            continue
        bucket["complete"] += 1
        if outside:
            bucket["p1_outside"][outside] = bucket["p1_outside"].get(outside, 0) + 1
        else:
            bucket["p1_eligible"] += 1
            t.tally.checked["P1"] += 1
            if len(final.completed) != len(trace.case.jobs):
                _record(
                    t,
                    trace.case,
                    final,
                    "P1",
                    "feasible_work_not_completed",
                    f"witness {witness}; completed {[c[0] for c in final.completed]}",
                )
        _check_p2(t, trace, final)
        bucket["p2_checked"] += 1

    results = {}
    for policy, b in sorted(per_policy.items()):
        tally = b["t"].tally
        props = {}
        for prop in v.PROPERTY_IDS:
            entry = {
                "meaning": v.PROPERTY_MEANING[prop],
                "checked": tally.checked[prop],
                "violations": tally.violations[prop],
            }
            if tally.violations[prop]:
                props[prop] = {**entry, "status": "FAIL"}
            elif refused or b["partial"]:
                props[prop] = {
                    **entry,
                    "status": "INCOMPLETE",
                    "reason": f"{len(refused)} refused, {b['partial']} partial traces",
                }
            elif not tally.checked[prop]:
                reason = {"S4": "no invalid proposal occurred", "P1": "no P1 inputs"}.get(
                    prop, "not exercised"
                )
                props[prop] = {**entry, "status": "NOT_RUN", "reason": reason}
            else:
                props[prop] = {**entry, "status": "PASS"}
        results[policy] = {
            "counts": {
                "traces": b["traces"],
                "complete_traces": b["complete"],
                "partial_traces": b["partial"],
                "p1_eligible_traces": b["p1_eligible"],
                "p1_outside_scope": dict(sorted(b["p1_outside"].items())),
                "p2_checked_traces": b["p2_checked"],
                "distinct_binding_sets": len(b["bindings"]),
            },
            "properties": props,
            "state_hash_continuity": {
                "checked": b["t"].continuity_checked,
                "mismatches": len(b["t"].continuity_mismatches),
                "examples": b["t"].continuity_mismatches[:10],
                "note": "informational: assumes state_after and the next state_before hash "
                "the same object, pending the runner's convention",
            },
            "arithmetic_consistency": {
                "status": "FAIL"
                if b["t"].arithmetic_mismatches
                else ("PASS" if b["t"].arithmetic_checked else "NOT_RUN"),
                "checked": b["t"].arithmetic_checked,
                "mismatches": len(b["t"].arithmetic_mismatches),
                "examples": b["t"].arithmetic_mismatches[:10],
                "note": "R04 capacity arithmetic only; not a human faithfulness judgment",
            },
            "counterexample_total": tally.counterexample_total,
            "counterexamples": tally.counterexamples,
        }
    report = {
        "record_kind": v.RECORD_KIND,
        "verifier_version": v.VERIFIER_VERSION,
        "verifier_source_sha256": v.source_sha256(),
        "trace_reader_source_sha256": _own_sha256(),
        "methods": ["trace_replay"],
        "budget": budget.summary(),
        "accepted_adapter_versions": sorted(ACCEPTED_ADAPTER_VERSIONS),
        "spec_sha256_expected": expected_spec_sha256,
        "refused_traces": refused,
        "results": results,
        "binding_validation": {
            "status": "INCOMPLETE",
            "verified": "case content, specification when supplied, decision-list hashes and within-trace consistency",
            "not_authenticated": "external adapter/generator/environment/code artifacts and raw state/transition bytes are not supplied",
        },
        "exclusions": v.EXCLUSIONS
        + ["Trace replay checks only the supplied records; it is not bounded exploration."],
    }
    if not is_rules_v1_run:
        report["status_note"] = (
            "Not a rules-v1 result: these traces are constructed test records or a fixture."
        )
    return report


def _check_p2(t: _TraceTally, trace: Trace, final: v.State):
    """Reported job sets must match the reconstruction; every job ends completed or missed."""
    tally = t.tally
    tally.checked["P2"] += 1
    completed = {c[0] for c in final.completed}
    missed = set(final.missed)
    all_ids = {j.job_id for j in trace.case.jobs}
    unresolved = all_ids - completed - missed
    if unresolved:
        _record(t, trace.case, final, "P2", "unresolved_jobs", f"{sorted(unresolved)}")
    expected = {
        "completed_job_ids": sorted(completed),
        "missed_job_ids": sorted(missed),
        "unfinished_job_ids": sorted(all_ids - completed),
    }
    for key, want in expected.items():
        got = sorted(trace.result[key])
        if got != want:
            _record(
                t,
                trace.case,
                final,
                "P2",
                f"result_{key}_mismatch",
                f"reported {got}; reconstruction {want}",
            )


def _own_sha256() -> str:
    import hashlib

    return hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_trace_dir(path: Path) -> tuple[Mapping, list[Mapping], Mapping]:
    """Read one trace folder: case.json, result.json and decisions/*.json (any order).

    This layout is the reader's assumption until the RULE-02 runner publishes its own.
    """
    case = json.loads((path / "case.json").read_text(encoding="utf-8"))
    result = json.loads((path / "result.json").read_text(encoding="utf-8"))
    decisions = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((path / "decisions").glob("*.json"))
    ]
    return case, decisions, result
