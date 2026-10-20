"""E01 independent reference validator for one scheduling decision.

Re-derives schedule validity from raw F02 job, site and constraint records and the
project rules. It deliberately does not import or call the production checker
(``dc_sustainability.verification``), the simulator or shared impact code, and it never
treats a CheckResult as truth: ``compare_with_check`` only reports disagreements.

Rules follow the Q01-Q03 drafts in issue #7 (Q01/Q02/Q04 agreed by Reimo and Ved; Q03
confirmed by Nisha and agreed by Ved and Matty; Edison pending). They live in an explicit
``Protocol`` so nothing here is a silent default. Cases the drafts do not settle are
reported as ``pending`` findings, never as passes or failures.
"""

from dataclasses import dataclass
from typing import Literal

from dc_sustainability import schemas as s


@dataclass(frozen=True)
class Protocol:
    """The decision rules the validator applies, named so results record their source."""

    name: str
    status: str
    last_start_slot: int  # Q01: last decision slot in which a new job may start

    def __post_init__(self):
        if type(self.last_start_slot) is not int or self.last_start_slot < 0:
            raise ValueError("last_start_slot must be a non-negative integer")
        if not self.name.strip() or not self.status.strip():
            raise ValueError("a protocol must be named and carry its agreement status")


Q03_DRAFT = Protocol(
    name="Q01-Q03-draft-2026-10-20",
    status="Q03 confirmed by Nisha, agreed by Ved and Matty; Edison pending (issue #7)",
    last_start_slot=23,
)

Code = Literal[
    "no_plan",
    "plan_identity",
    "empty_queue_not_noop",
    "omitted_job",
    "duplicate_job",
    "not_waiting_job",
    "start_before_current",
    "start_before_arrival",
    "start_after_last_start",
    "deadline",
    "episode_horizon",
    "nonflexible_start",
    "capacity",
    "capacity_unverifiable",
    "invalid_deferral",
    "unjustified_abstention",
    # Pending: the drafts do not settle these, so they neither pass nor fail a decision.
    "joint_infeasibility_not_assessed",
    # Note only: recorded for E04 citation review, does not change validity.
    "unknown_evidence_id",
]
PENDING_CODES = frozenset({"joint_infeasibility_not_assessed"})
NOTE_CODES = frozenset({"unknown_evidence_id"})


@dataclass(frozen=True)
class Finding:
    code: Code
    job_id: str | None = None
    slot: int | None = None
    detail: str = ""


@dataclass(frozen=True)
class DecisionFacts:
    """Authoritative facts at one decision, read directly from F02 records."""

    episode_id: str
    slot: int
    state_version: int
    waiting: dict[str, s.Job]
    running: dict[str, tuple[s.Job, int]]  # job and its start slot
    unavailable_ids: frozenset[str]  # completed or missed
    background_kw: float
    capacity_kw: float | None  # None means capacity evidence is missing
    evidence_ids: frozenset[str]


def facts_from_state(state: s.VisibleState, snapshot: s.ConstraintSnapshot) -> DecisionFacts:
    """Collect decision facts from a visible state and its authoritative snapshot.

    Capacity is read from the snapshot's constraint records here, not via schema helpers,
    and constraints that contradict a visible job are refused. F02 validates record
    structure only; visibility and job/constraint consistency are derived here.
    """
    state = s.VisibleState.model_validate(
        state.model_dump(mode="python", warnings="none"), strict=True
    )
    snapshot = s.ConstraintSnapshot.model_validate(
        snapshot.model_dump(mode="python", warnings="none"), strict=True
    )
    if state.constraint_snapshot_id != snapshot.snapshot_id or state.site != snapshot.site:
        raise ValueError("state and snapshot describe different sites or snapshots")
    if state.current_slot >= s.PROPOSED_DECISION_SLOTS:
        raise ValueError("completion slots have no decision to validate")
    site_id = state.site.site_id
    capacities = [
        c
        for c in snapshot.constraints
        if c.constraint_type == "capacity" and c.applies_to_site == site_id
    ]
    waiting = {job.job_id: job for job in state.waiting_jobs}
    running = {view.job.job_id: (view.job, view.start_slot) for view in state.running_jobs}
    jobs = {**waiting, **{job_id: job for job_id, (job, _) in running.items()}}
    known = set(jobs) | {view.job_id for view in state.completed_jobs} | set(state.missed_job_ids)
    visible_ids = {
        c.constraint_id
        for c in snapshot.constraints
        if c.applies_to_site == site_id or (c.applies_to_jobs and set(c.applies_to_jobs) <= known)
    }
    if set(state.constraint_ids) != visible_ids:
        raise ValueError("visible constraint IDs do not match the authoritative snapshot")
    for constraint in snapshot.constraints:
        for job_id in constraint.applies_to_jobs:
            job = jobs.get(job_id)
            if job is None:
                continue
            values = {
                "arrival": job.arrival_slot,
                "deadline": job.deadline_slot,
                "nonflexible": job.arrival_slot,
            }
            kind = constraint.constraint_type
            if kind in values and (
                constraint.limit_value != values[kind] or (kind == "nonflexible" and job.flexible)
            ):
                raise ValueError(f"{constraint.constraint_id} contradicts job {job_id}")
    evidence = {"FACT-SITE-BG", "FACT-SITE-PUE", "FACT-SITE-SLOTH"}
    evidence |= {f"FACT-JOB-{job_id}" for job_id in jobs}
    evidence |= {f"FACT-JOB-{view.job_id}" for view in state.completed_jobs}
    evidence |= {f"FACT-JOB-{job_id}" for job_id in state.missed_job_ids}
    evidence |= {fact.fact_id for fact in state.carbon_facts}
    evidence |= set(state.constraint_ids)
    return DecisionFacts(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        waiting=waiting,
        running=running,
        unavailable_ids=frozenset(
            {view.job_id for view in state.completed_jobs} | set(state.missed_job_ids)
        ),
        background_kw=state.site.background_kw,
        capacity_kw=capacities[0].limit_value if len(capacities) == 1 else None,
        evidence_ids=frozenset(evidence),
    )


@dataclass(frozen=True)
class ValidationResult:
    """``status`` is "pending" only when nothing failed but a pending rule applies."""

    status: Literal["valid", "invalid", "pending"]
    findings: tuple[Finding, ...]
    notes: tuple[Finding, ...]
    empty_queue: bool
    justified_abstentions: tuple[str, ...]
    protocol: str
    # Internal comparison metadata, not an F02 schema or an independent truth source.
    # An unbound legacy/manual result cannot be compared to a production check.
    decision_key: tuple[str, int, int, str] | None = None

    @property
    def valid(self) -> bool:
        return self.status == "valid"


def _legal_starts(job: s.Job, earliest: int, protocol: Protocol) -> range:
    """Start slots allowed by arrival, Q01 and the completion deadline, ignoring capacity."""
    first = max(earliest, job.arrival_slot)
    end = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS
    last = min(protocol.last_start_slot, min(job.deadline_slot, end) - job.duration_slots)
    if not job.flexible:
        return (
            range(job.arrival_slot, job.arrival_slot + 1)
            if first <= job.arrival_slot <= last
            else range(0)
        )
    return range(first, last + 1)


def _fits_alone(job: s.Job, start: int, facts: DecisionFacts) -> bool:
    """Whether the job fits with background and running work only, in every occupied slot."""
    for t in range(start, start + job.duration_slots):
        load = facts.background_kw + job.power_kw
        load += sum(
            j.power_kw for j, st in facts.running.values() if st <= t < st + j.duration_slots
        )
        if load > facts.capacity_kw:
            return False
    return True


def _assess_abstention(job: s.Job, facts: DecisionFacts, protocol: Protocol) -> Code | None:
    """None when justified; otherwise the finding code for this abstention."""
    if facts.capacity_kw is None:
        return None  # required feasibility evidence is missing
    if not any(_fits_alone(job, t, facts) for t in _legal_starts(job, facts.slot, protocol)):
        return None  # physically infeasible even with no other new work
    # Feasible alone; whether contention with other waiting jobs justifies it is unsettled.
    return "joint_infeasibility_not_assessed"


def validate_plan(plan: s.Plan, facts: DecisionFacts, protocol: Protocol) -> ValidationResult:
    """Validate one proposed plan against the decision facts and protocol."""
    plan = s.Plan.model_validate(plan.model_dump(mode="python", warnings="none"), strict=True)
    findings: list[Finding] = []
    justified: list[str] = []
    if (plan.episode_id, plan.slot, plan.state_version) != (
        facts.episode_id,
        facts.slot,
        facts.state_version,
    ):
        findings.append(Finding("plan_identity", detail="plan is for a different decision"))

    whole = [a for a in plan.abstentions if a.job_id is None]
    per_job = [a.job_id for a in plan.abstentions if a.job_id is not None]
    mentioned = [p.job_id for p in plan.starts] + [d.job_id for d in plan.deferrals] + per_job
    empty_queue = not facts.waiting

    if empty_queue:
        if mentioned or whole:
            findings.append(Finding("empty_queue_not_noop"))
    else:
        for job_id in sorted(set(mentioned)):
            if job_id not in facts.waiting:
                findings.append(Finding("not_waiting_job", job_id))
            elif mentioned.count(job_id) > 1:
                findings.append(Finding("duplicate_job", job_id))
        if whole and (mentioned or len(whole) > 1):
            findings.append(
                Finding("duplicate_job", detail="whole-decision abstention plus entries")
            )
        if not whole:
            for job_id in sorted(set(facts.waiting) - set(mentioned)):
                findings.append(Finding("omitted_job", job_id))

    starts = [p for p in plan.starts if p.job_id in facts.waiting]
    for p in starts:
        job = facts.waiting[p.job_id]
        if p.start_slot < facts.slot:
            findings.append(Finding("start_before_current", p.job_id, p.start_slot))
        if p.start_slot < job.arrival_slot:
            findings.append(Finding("start_before_arrival", p.job_id, p.start_slot))
        if p.start_slot > protocol.last_start_slot:
            findings.append(Finding("start_after_last_start", p.job_id, p.start_slot))
        if p.start_slot + job.duration_slots > job.deadline_slot:
            findings.append(Finding("deadline", p.job_id, p.start_slot))
        if (
            p.start_slot + job.duration_slots
            > s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS
        ):
            findings.append(Finding("episode_horizon", p.job_id, p.start_slot))
        if not job.flexible and p.start_slot != job.arrival_slot:
            findings.append(Finding("nonflexible_start", p.job_id, p.start_slot))

    if starts and facts.capacity_kw is None:
        findings.append(Finding("capacity_unverifiable", detail="no capacity constraint"))
    elif starts:
        # Every planned start counts, including future intentions: the plan as a whole
        # must be feasible, not only its current-slot part.
        occupied = [(facts.waiting[p.job_id], p.start_slot) for p in starts]
        occupied += list(facts.running.values())
        horizon = max(st + j.duration_slots for j, st in occupied)
        for t in range(facts.slot, horizon):
            load = facts.background_kw + sum(
                j.power_kw for j, st in occupied if st <= t < st + j.duration_slots
            )
            if load > facts.capacity_kw:
                findings.append(Finding("capacity", slot=t, detail=f"{load:g} kW"))

    for d in plan.deferrals:
        job = facts.waiting.get(d.job_id)
        if job is not None and not _legal_starts(job, facts.slot + 1, protocol):
            findings.append(Finding("invalid_deferral", d.job_id))

    abstained = sorted(facts.waiting) if whole else sorted(set(per_job) & set(facts.waiting))
    if empty_queue:
        abstained = []
    for job_id in abstained:
        code = _assess_abstention(facts.waiting[job_id], facts, protocol)
        if code is None:
            justified.append(job_id)
        else:
            findings.append(Finding(code, job_id))

    cited = set(plan.evidence_ids)
    for item in (*plan.deferrals, *plan.abstentions):
        cited |= set(item.evidence_ids)
    for a in plan.abstentions:
        cited |= set(a.constraint_ids)
    notes = tuple(
        Finding("unknown_evidence_id", detail=e) for e in sorted(cited - facts.evidence_ids)
    )

    if any(f.code not in PENDING_CODES for f in findings):
        status = "invalid"
    elif findings:
        status = "pending"
    else:
        status = "valid"
    return ValidationResult(
        status=status,
        findings=tuple(findings),
        notes=notes,
        empty_queue=empty_queue,
        justified_abstentions=tuple(justified),
        protocol=protocol.name,
        decision_key=(facts.episode_id, facts.slot, facts.state_version, plan.plan_hash),
    )


def validate_output(
    output: s.PolicyOutput | None, facts: DecisionFacts, protocol: Protocol
) -> ValidationResult:
    """Validate a policy's output; missing, malformed and error outputs are invalid."""
    if output is not None:
        output = s.PolicyOutput.model_validate(
            output.model_dump(mode="python", warnings="none"), strict=True
        )
    if output is None or output.output_status != "ok" or output.plan is None:
        status = "missing" if output is None else output.output_status
        return ValidationResult(
            status="invalid",
            findings=(Finding("no_plan", detail=status),),
            notes=(),
            empty_queue=not facts.waiting,
            justified_abstentions=(),
            protocol=protocol.name,
        )
    return validate_plan(output.plan, facts, protocol)


Disagreement = Literal["agree", "checker_passed_invalid", "checker_failed_valid", "not_comparable"]


def compare_with_check(result: ValidationResult, check: s.CheckResult) -> Disagreement:
    """Report how the production verdict relates to this one; neither is changed.

    Unbound/different decisions, checker errors and pending results are not
    comparable. A check from a different proposal must never count as agreement.
    """
    check = s.CheckResult.model_validate(
        check.model_dump(mode="python", warnings="none"), strict=True
    )
    if (
        result.decision_key != (check.episode_id, check.slot, check.state_version, check.plan_hash)
        or check.status == "error"
        or result.status == "pending"
    ):
        return "not_comparable"
    if check.status == "pass":
        return "agree" if result.valid else "checker_passed_invalid"
    return "checker_failed_valid" if result.valid else "agree"
