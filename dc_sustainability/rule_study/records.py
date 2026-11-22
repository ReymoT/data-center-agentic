"""Study-local ``rule_study_*`` records for adapter proposal-1 (RULE-02, issue #240).

This is a separate study envelope. It does NOT touch F02 ``SystemId``, ``DecisionRecord``,
``PolicyOutput``, any schema or the six-system registry, and it never carries a legacy
``system``/``record_type`` field. Existing F02 ``Plan``, ``CheckResult`` and ``ApprovedStart``
are reused only for their existing meanings.

Hash convention (study-local, pinned Python 3.12 serialization, NOT RFC 8785):
``json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)``
followed by exactly one LF, encoded as UTF-8. Hashes are SHA-256 of the exact bytes of the
referenced immutable file. A missing hash stays an explicit ``null``; it is never filled in.

Schema authority: these models mirror, field for field, the strict merged reader
``dc_sustainability/evaluation/rule_study_trace.py`` (RULE-03, PR #250/#252): no field outside
its accepted set is emitted, and every binding is a real value (the reader refuses ``null``).
Raw VisibleState/ConstraintSnapshot bytes are kept in sibling immutable files named by their
SHA-256 (``states/<sha>.json``, ``snapshots/<sha>.json``) so the records stay reader-exact.
"""

import hashlib
import json
from typing import Annotated, Any, Literal, Optional

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    Strict,
    StringConstraints,
    model_validator,
)

from dc_sustainability import schemas as s

ADAPTER_VERSION = "proposal-1"
STUDY_ID = "rule-study-20261119-v1"
DECISION_KIND = "rule_study_decision_v1"
RESULT_KIND = "rule_study_result_v1"
POLICY_IDS = ("rules-v1", "greedy_a", "greedy_b")
RULE_IDS = ("R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09")
HORIZON_SLOTS = 30

RuleId = Literal["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09"]
PolicyId = Literal["rules-v1", "greedy_a", "greedy_b"]
StageOrigin = Literal["rules-v1", "greedy_a", "greedy_b", "greedy_a_fallback", "fault_injection"]
Text = s.Text
Int = Annotated[int, Strict()]
NonNegInt = Annotated[int, Strict(), Field(ge=0)]


# --------------------------------------------------------------------------- serialization
def study_json(data: Any) -> str:
    """Serialize with the study-local convention: canonical compact JSON plus one final LF."""
    return (
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        + "\n"
    )


def study_sha256(text: str) -> str:
    """SHA-256 of the exact UTF-8 bytes of an already serialized study file."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _not_placeholder(value: Optional[str]) -> Optional[str]:
    """Reject degenerate digests (all one character) that look like invented placeholders."""
    if value is not None and len(set(value)) == 1:
        raise ValueError("a placeholder-looking digest is not an actual hash; use null")
    return value


Sha256 = Annotated[s.Hex64, AfterValidator(_not_placeholder)]
GitCommit = Annotated[
    str, Strict(), StringConstraints(pattern=r"^[0-9a-f]{40}$"), AfterValidator(_not_placeholder)
]


class _Strict(BaseModel):
    """Strict immutable base: unknown fields, coercion and mutation are all refused."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)

    def to_jsonable(self) -> dict:
        return self.model_dump(mode="json")

    def to_json(self) -> str:
        """Study-local serialization (see module docstring); this exact text is hashed."""
        return study_json(self.to_jsonable())

    def sha256(self) -> str:
        return study_sha256(self.to_json())

    @classmethod
    def from_json(cls, text: str):
        return cls.model_validate_json(text)


# --------------------------------------------------------------------------- shared pieces
class Bindings(_Strict):
    """Actual digests/commit. The merged reader refuses null, so none is optional here."""

    spec_sha256: Sha256
    adapter_source_sha256: Sha256
    generator_source_sha256: Sha256
    case_sha256: Sha256
    environment_lock_sha256: Sha256
    code_commit: GitCommit


class StateBefore(_Strict):
    slot: s.Slot
    state_version: NonNegInt
    visible_state_sha256: Sha256
    constraint_snapshot_sha256: Sha256


class StateAfter(_Strict):
    slot: Annotated[int, Strict(), Field(ge=1, le=30)]
    state_version: Annotated[int, Strict(), Field(ge=1)]
    state_sha256: Sha256

    @model_validator(mode="after")
    def _check(self):
        if self.state_version != self.slot:
            raise ValueError("state_after.state_version must match its boundary slot")
        return self


class RecordError(_Strict):
    """Structured stage/code/message; failures are preserved, never erased by a fallback."""

    stage: Optional[Text]
    code: Text
    message: Text


class ArithmeticTerm(_Strict):
    label: Text
    job_id: Optional[s.JobId]
    value: Int
    unit: Text


class ArithmeticEntry(_Strict):
    """Deterministic evidence linked to exact inputs. It is not an independent verdict.

    ``signed_excess`` is ``total - limit`` when both are present. ``computed`` marks
    arithmetic with no predicate (for example score sums or an advisory future start).
    """

    rule_id: RuleId
    constraint_id: Optional[s.ConstraintId]
    slot: Optional[s.Slot]
    terms: tuple[ArithmeticTerm, ...]
    total: Optional[Int]
    limit: Optional[Int]
    signed_excess: Optional[Int]
    outcome: Literal["pass", "fail", "computed"]
    unit: Text
    formula: Text

    @model_validator(mode="after")
    def _check(self):
        if (self.total is None or self.limit is None) != (self.signed_excess is None):
            raise ValueError("signed_excess requires both total and limit")
        if self.signed_excess is not None and self.signed_excess != self.total - self.limit:
            raise ValueError("signed_excess must equal total - limit")
        if self.outcome != "computed" and self.signed_excess is None:
            raise ValueError("a predicate outcome requires total, limit and signed_excess")
        return self


class ProposalStage(_Strict):
    stage_id: Text
    origin: StageOrigin
    plan: s.Plan
    rule_ids: tuple[RuleId, ...]
    arithmetic: tuple[ArithmeticEntry, ...]
    check_result: Optional[s.CheckResult]
    errors: tuple[RecordError, ...]


class Execution(_Strict):
    status: Literal["executed", "abstained", "blocked", "indeterminate"]
    current_starts: tuple[s.JobId, ...]
    transition_ref: Optional[Text]
    transition_sha256: Optional[Sha256]
    simulator_rejection: Optional[Text]
    state_after: Optional[StateAfter]

    @model_validator(mode="after")
    def _check(self):
        if self.status == "indeterminate":
            if self.state_after is not None or self.transition_sha256 is not None:
                raise ValueError("an indeterminate effect has no verified transition/state-after")
            if self.current_starts:
                raise ValueError("an indeterminate decision records no executed starts")
        elif self.state_after is None:
            raise ValueError("state_after is required unless the execution is indeterminate")
        if (self.transition_ref is None) != (self.transition_sha256 is None):
            raise ValueError("transition reference and hash are given together")
        if len(set(self.current_starts)) != len(self.current_starts):
            raise ValueError("duplicate executed start")
        return self


# --------------------------------------------------------------------------- decision record
class RuleStudyDecision(_Strict):
    record_kind: Literal["rule_study_decision_v1"]
    adapter_version: Literal["proposal-1"]
    study_id: Literal["rule-study-20261119-v1"]
    policy_id: PolicyId
    case_id: Text
    decision_index: Annotated[int, Strict(), Field(ge=0, le=29)]
    bindings: Bindings
    state_before: StateBefore
    proposal_stages: tuple[ProposalStage, ...]
    selected_stage_id: Optional[Text]
    execution: Execution
    errors: tuple[RecordError, ...]
    # Actual integer zero: any other count fails the no-model boundary at validation.
    model_call_count: Annotated[int, Strict(), Field(ge=0, le=0)]

    @model_validator(mode="after")
    def _check(self):
        ids = [stage.stage_id for stage in self.proposal_stages]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate proposal stage IDs")
        if self.state_before.slot != self.decision_index:
            raise ValueError("decision_index must equal the state-before slot")
        if self.selected_stage_id is None:
            if self.execution.status in ("executed", "abstained"):
                raise ValueError("executed/abstained requires a selected passing stage")
            if self.execution.current_starts:
                raise ValueError("no selected stage cannot start work")
        else:
            chosen = [
                stage for stage in self.proposal_stages if stage.stage_id == self.selected_stage_id
            ]
            if len(chosen) != 1:
                raise ValueError("selected_stage_id does not reference a proposal stage")
            check = chosen[0].check_result
            if check is None or check.status != "pass":
                raise ValueError("selected stage must reference an actually passing check")
        return self


# --------------------------------------------------------------------------- result record
class JobAccounting(_Strict):
    job_id: s.JobId
    power_kw: Int
    start_slot: NonNegInt
    end_slot: NonNegInt
    synthetic_impact: Int


class JobOutcomes(_Strict):
    """completed / missed / unscheduled / unfinished distinctions (R09), derived from evidence.

    ``unfinished`` is every job that did not complete (the reader's P2 definition), so it
    contains the missed jobs; ``unscheduled`` is the subset that never received a start.
    """

    completed: tuple[s.JobId, ...]
    missed: tuple[s.JobId, ...]
    unscheduled: tuple[s.JobId, ...]
    started_not_completed: tuple[s.JobId, ...]
    unfinished: tuple[s.JobId, ...]


class Accounting(_Strict):
    """Accounting inputs and totals with units. Synthetic weights are NOT g/kWh or kg CO2e.

    Totals cover only the ``slots_recorded`` actual simulator transitions; missing slots are
    never zero-filled. ``score_convention_status`` carries the source of the convention and
    what receiving is still pending.
    """

    slots_recorded: NonNegInt
    slot_hours: float
    pue: float
    background_kw: Int
    capacity_kw: Int
    score_convention_id: Text
    score_convention_status: Text
    synthetic_impact_unit: Text
    synthetic_impact_total: Int
    per_job: tuple[JobAccounting, ...]
    job_outcomes: JobOutcomes
    job_it_energy_kwh: float
    job_facility_energy_kwh: float
    background_facility_energy_kwh: float
    site_facility_energy_kwh: float
    energy_unit: Literal["kWh"]


class RuleStudyResult(_Strict):
    record_kind: Literal["rule_study_result_v1"]
    adapter_version: Literal["proposal-1"]
    study_id: Literal["rule-study-20261119-v1"]
    policy_id: PolicyId
    case_id: Text
    bindings: Bindings
    decision_sha256s: tuple[Sha256, ...]
    completed_job_ids: tuple[s.JobId, ...]
    missed_job_ids: tuple[s.JobId, ...]
    unfinished_job_ids: tuple[s.JobId, ...]
    accounting: Optional[Accounting]
    status: Literal["complete", "partial", "failed"]
    errors: tuple[RecordError, ...]

    @model_validator(mode="after")
    def _check(self):
        if self.status == "complete" and len(self.decision_sha256s) != HORIZON_SLOTS:
            raise ValueError("a complete result binds all 30 decisions")
        if len(self.decision_sha256s) > HORIZON_SLOTS:
            raise ValueError("more than 30 decision hashes")
        if self.status == "failed" and self.accounting is not None:
            raise ValueError("a failed result has no totals; none are invented")
        if set(self.completed_job_ids) & set(self.unfinished_job_ids):
            raise ValueError("a job cannot be both completed and unfinished")
        if not set(self.missed_job_ids) <= set(self.unfinished_job_ids):
            raise ValueError("every missed job is unfinished")
        return self
