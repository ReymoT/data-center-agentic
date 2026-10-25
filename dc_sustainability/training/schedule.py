"""Probability-ranked feasible starts for training policies."""

import re

from dc_sustainability import schemas as s

_LAST_START_SLOT = s.PROPOSED_DECISION_SLOTS - 1
_JOB_NUMBER = re.compile(r"\d+")


def schedule_from_probabilities(
    visible_state: s.VisibleState,
    context: s.Context,
    classifier,
    *,
    system: s.SystemId,
) -> s.PolicyOutput:
    """Propose starts by walking classifier-scored feasible (job, start) candidates."""
    capacity = _capacity_kw(context)
    occupancy = _running_load(visible_state)
    current = visible_state.current_slot
    candidates: list[tuple[tuple, s.Job, int, float]] = []
    for job in visible_state.waiting_jobs:
        if job.arrival_slot > current:
            continue
        for start in _window(job, current):
            probability = classifier.selection_probability(job, start)
            candidates.append((_candidate_key(job, start, probability), job, start, probability))
    candidates.sort(key=lambda item: item[0])

    scheduled: set[str] = set()
    starts: list[s.PlannedStart] = []
    for _key, job, start, _probability in candidates:
        if job.job_id in scheduled:
            continue
        if capacity is None or not _fits(occupancy, start, job, capacity):
            continue
        starts.append(s.PlannedStart(job_id=job.job_id, start_slot=start))
        scheduled.add(job.job_id)
        _reserve(occupancy, start, job)

    plan = s.Plan(
        episode_id=visible_state.episode_id,
        slot=visible_state.current_slot,
        state_version=visible_state.state_version,
        starts=tuple(starts),
        status="proposed",
    )
    return s.PolicyOutput(system=system, output_status="ok", plan=plan)


def _candidate_key(job: s.Job, start_slot: int, probability: float) -> tuple:
    return (
        job.flexible,
        job.deadline_slot - job.duration_slots,
        -probability,
        start_slot,
        _job_number(job.job_id),
    )


def _job_number(job_id: str) -> int:
    digits = _JOB_NUMBER.search(job_id)
    return int(digits.group()) if digits else 0


def _capacity_kw(context: s.Context) -> float | None:
    limits = [
        constraint.limit_value
        for constraint in context.content.constraints
        if constraint.constraint_type == "capacity"
    ]
    if len(limits) != 1:
        return None
    return limits[0]


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
    horizon = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS
    load: dict[int, float] = {
        slot: state.site.background_kw for slot in range(state.current_slot, horizon)
    }
    for running in state.running_jobs:
        for slot in range(running.start_slot, running.end_slot):
            load[slot] = load.get(slot, 0.0) + running.job.power_kw
    return load
