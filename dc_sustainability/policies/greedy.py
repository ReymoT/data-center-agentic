"""Earliest feasible starts for system greedy_a."""

import re

from dc_sustainability import schemas as s

_LAST_START_SLOT = s.PROPOSED_DECISION_SLOTS - 1
_JOB_NUMBER = re.compile(r"\d+")


def propose(visible_state: s.VisibleState, context: s.Context) -> s.PolicyOutput:
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
        if arrival + job.duration_slots > job.deadline_slot:
            return ()
        return (arrival,)
    first = max(current_slot, job.arrival_slot)
    last = min(_LAST_START_SLOT, job.deadline_slot - job.duration_slots)
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
    load: dict[int, float] = {}
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
