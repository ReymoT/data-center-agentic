"""Earliest feasible starts for greedy_a; lowest-emission starts for greedy_b."""

import re
from datetime import datetime, timedelta

from dc_sustainability import schemas as s
from dc_sustainability.verification.rules import assess_forecasts

_LAST_START_SLOT = s.PROPOSED_DECISION_SLOTS - 1
_JOB_NUMBER = re.compile(r"\d+")

_COVERAGE_REASONS = (
    ("beyond-horizon", lambda a, _: bool(a.beyond_horizon_slots)),
    ("future", lambda a, _: bool(a.future_issued_slots)),
    ("stale", lambda a, _: bool(a.stale_slots)),
    (
        "partial",
        lambda a, facts: bool(a.missing_slots) and bool(set(a.required_slots) & facts),
    ),
    ("missing", lambda a, _: bool(a.missing_slots)),
)


def propose(
    visible_state: s.VisibleState,
    context: s.Context,
    *,
    system: s.SystemId = "greedy_a",
    decision_time_utc: datetime | None = None,
) -> s.PolicyOutput:
    """Propose starts for the requested greedy policy."""
    if system == "greedy_a":
        return _propose_greedy_a(visible_state, context)
    if system == "greedy_b":
        return _propose_greedy_b(visible_state, context, decision_time_utc)
    raise ValueError(f"unsupported policy system: {system}")


def _propose_greedy_a(visible_state: s.VisibleState, context: s.Context) -> s.PolicyOutput:
    """Propose the earliest IT-feasible start for each waiting job."""
    capacity = _capacity_kw(context)
    occupancy = _running_load(visible_state)
    starts: list[s.PlannedStart] = []
    abstentions: list[s.Abstention] = []
    for job in sorted(visible_state.waiting_jobs, key=_priority):
        start = _earliest_start(job, visible_state, capacity, occupancy)
        if start is None:
            abstentions.append(
                s.Abstention(
                    job_id=job.job_id,
                    reason=_abstain_reason(job, visible_state, capacity),
                )
            )
            continue
        starts.append(s.PlannedStart(job_id=job.job_id, start_slot=start))
        _reserve(occupancy, start, job)
    plan = s.Plan(
        episode_id=visible_state.episode_id,
        slot=visible_state.current_slot,
        state_version=visible_state.state_version,
        starts=tuple(starts),
        abstentions=tuple(abstentions),
        status="proposed",
    )
    return s.PolicyOutput(system="greedy_a", output_status="ok", plan=plan)


def _propose_greedy_b(
    visible_state: s.VisibleState,
    context: s.Context,
    decision_time_utc: datetime | None,
) -> s.PolicyOutput:
    if not isinstance(decision_time_utc, datetime) or decision_time_utc.utcoffset() != timedelta(0):
        raise ValueError("an explicit trusted UTC decision time is required")
    content = context.content
    snapshot = s.ConstraintSnapshot(
        snapshot_id=content.snapshot_id,
        site=content.site,
        constraints=content.constraints,
        sources=content.sources,
    )
    assessment = assess_forecasts(visible_state, snapshot, decision_time_utc=decision_time_utc)
    fact_slots = {fact.valid_slot for fact in visible_state.carbon_facts}
    reason = next(
        (label for label, matches in _COVERAGE_REASONS if matches(assessment, fact_slots)),
        None,
    )
    if reason is not None:
        base = _propose_greedy_a(visible_state, context)
        return base.model_copy(
            update={
                "explanation": s.Explanation(source="template", summary=reason),
            }
        )

    capacity = _capacity_kw(context)
    occupancy = _running_load(visible_state)
    carbon = {fact.valid_slot: fact.value for fact in visible_state.carbon_facts}
    site = visible_state.site
    slot_energy_kwh = site.pue * site.slot_hours / 1000
    starts: list[s.PlannedStart] = []
    abstentions: list[s.Abstention] = []
    for job in sorted(visible_state.waiting_jobs, key=_priority):
        start = _lowest_emissions_start(
            job, visible_state, capacity, occupancy, carbon, slot_energy_kwh
        )
        if start is None:
            abstentions.append(
                s.Abstention(
                    job_id=job.job_id,
                    reason=_abstain_reason(job, visible_state, capacity),
                )
            )
            continue
        starts.append(s.PlannedStart(job_id=job.job_id, start_slot=start))
        _reserve(occupancy, start, job)
    plan = s.Plan(
        episode_id=visible_state.episode_id,
        slot=visible_state.current_slot,
        state_version=visible_state.state_version,
        starts=tuple(starts),
        abstentions=tuple(abstentions),
        status="proposed",
    )
    return s.PolicyOutput(system="greedy_b", output_status="ok", plan=plan)


def _lowest_emissions_start(
    job: s.Job,
    state: s.VisibleState,
    capacity: float | None,
    occupancy: dict[int, float],
    carbon: dict[int, float],
    slot_energy_kwh: float,
) -> int | None:
    if capacity is None:
        return None
    best: tuple[float, int] | None = None
    best_start: int | None = None
    for start in _window(job, state.current_slot):
        if not _fits(occupancy, start, job, capacity):
            continue
        emissions = sum(
            slot_energy_kwh * job.power_kw * carbon[slot]
            for slot in range(start, start + job.duration_slots)
        )
        key = (emissions, start)
        if best is None or key < best:
            best = key
            best_start = start
    return best_start


def _capacity_kw(context: s.Context) -> float | None:
    limits = [
        constraint.limit_value
        for constraint in context.content.constraints
        if constraint.constraint_type == "capacity"
    ]
    if len(limits) != 1:
        return None
    return limits[0]


def _priority(job: s.Job) -> tuple[bool, int, int, int, str]:
    return (
        job.flexible,
        job.deadline_slot - job.duration_slots,
        job.deadline_slot,
        _job_number(job.job_id),
        job.job_id,
    )


def _job_number(job_id: str) -> int:
    digits = _JOB_NUMBER.search(job_id)
    return int(digits.group()) if digits else 0


def _window(job: s.Job, current_slot: int) -> tuple[int, ...]:
    if not job.flexible:
        arrival = job.arrival_slot
        if arrival < current_slot or arrival > _LAST_START_SLOT:
            return ()
        if arrival + job.duration_slots > min(job.deadline_slot, 30):
            return ()
        return (arrival,)
    first = max(current_slot, job.arrival_slot)
    last = min(_LAST_START_SLOT, job.deadline_slot - job.duration_slots, 30 - job.duration_slots)
    if first > last:
        return ()
    return tuple(range(first, last + 1))


def _earliest_start(
    job: s.Job,
    state: s.VisibleState,
    capacity: float | None,
    occupancy: dict[int, float],
) -> int | None:
    if capacity is None:
        return None
    for start in _window(job, state.current_slot):
        if _fits(occupancy, start, job, capacity):
            return start
    return None


def _fits(
    occupancy: dict[int, float],
    start: int,
    job: s.Job,
    capacity: float,
) -> bool:
    return all(
        occupancy.get(slot, 0.0) + job.power_kw <= capacity
        for slot in range(start, start + job.duration_slots)
    )


def _reserve(occupancy: dict[int, float], start: int, job: s.Job) -> None:
    for slot in range(start, start + job.duration_slots):
        occupancy[slot] = occupancy.get(slot, 0.0) + job.power_kw


def _running_load(state: s.VisibleState) -> dict[int, float]:
    # The authoritative IT limit includes background, running and proposed work.
    # PUE scales facility energy, not this capacity constraint.
    horizon = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS
    load: dict[int, float] = {
        slot: state.site.background_kw for slot in range(state.current_slot, horizon)
    }
    for running in state.running_jobs:
        for slot in range(running.start_slot, running.end_slot):
            load[slot] = load.get(slot, 0.0) + running.job.power_kw
    return load


def _abstain_reason(job: s.Job, state: s.VisibleState, capacity: float | None) -> str:
    if capacity is None:
        return "missing_evidence"
    if _window(job, state.current_slot):
        return "constraint_violation"
    return "infeasible_deadline"
