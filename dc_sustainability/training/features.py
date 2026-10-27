"""Candidate feature rows for one visible decision.

Each row is one arrived waiting job and one start that fits the same window and
IT capacity as the probability constructor. Carbon must be fresh on every
occupied slot. Rows do not reserve one another, because a proposal is not an
input to these features.
"""

import re
from datetime import datetime, timedelta

from dc_sustainability import schemas as s

_LAST_START_SLOT = s.PROPOSED_DECISION_SLOTS - 1
_JOB_NUMBER = re.compile(r"\d+")

FEATURE_NAMES = (
    "delay_slots",
    "deadline_margin_slots",
    "duration_slots",
    "power_kw",
    "available_capacity_kw",
    "queue_load_count",
    "carbon_mean_g_per_kwh",
    "carbon_min_g_per_kwh",
)


class FeatureRow:
    """One feasible candidate and its eight features, in FEATURE_NAMES order."""

    def __init__(
        self,
        job_id: str,
        start_slot: int,
        delay_slots: int,
        deadline_margin_slots: int,
        duration_slots: int,
        power_kw: float,
        available_capacity_kw: float,
        queue_load_count: int,
        carbon_mean_g_per_kwh: float,
        carbon_min_g_per_kwh: float,
    ) -> None:
        self.job_id = job_id
        self.start_slot = start_slot
        self.delay_slots = delay_slots
        self.deadline_margin_slots = deadline_margin_slots
        self.duration_slots = duration_slots
        self.power_kw = power_kw
        self.available_capacity_kw = available_capacity_kw
        self.queue_load_count = queue_load_count
        self.carbon_mean_g_per_kwh = carbon_mean_g_per_kwh
        self.carbon_min_g_per_kwh = carbon_min_g_per_kwh

    def values(self) -> tuple[float, ...]:
        return tuple(float(getattr(self, name)) for name in FEATURE_NAMES)


def candidate_features(
    visible_state: s.VisibleState,
    context: s.Context,
    *,
    decision_time_utc: datetime,
) -> tuple[FeatureRow, ...]:
    """Return feature rows for feasible starts with fresh carbon on every occupied slot."""
    if not isinstance(decision_time_utc, datetime) or decision_time_utc.utcoffset() != timedelta(0):
        raise ValueError("an explicit trusted UTC decision time is required")
    capacity = _capacity_kw(context)
    if capacity is None:
        return ()
    max_age = _max_age_seconds(visible_state, context)
    current = visible_state.current_slot
    visible_end = min(current + s.PROPOSED_DECISION_SLOTS, 30)
    facts = {fact.valid_slot: fact for fact in visible_state.carbon_facts}
    occupancy = _running_load(visible_state)
    queue_load = sum(1 for job in visible_state.waiting_jobs if job.arrival_slot <= current)
    rows: list[tuple[tuple, FeatureRow]] = []
    for job in visible_state.waiting_jobs:
        if job.arrival_slot > current:
            continue
        for start in _window(job, current):
            if not _fits(occupancy, start, job, capacity):
                continue
            carbon = _fresh_carbon(
                start,
                job.duration_slots,
                facts,
                decision_time_utc,
                max_age,
                current,
                visible_end,
            )
            if carbon is None:
                continue
            row = FeatureRow(
                job_id=job.job_id,
                start_slot=start,
                delay_slots=current - job.arrival_slot,
                deadline_margin_slots=job.deadline_slot - start - job.duration_slots,
                duration_slots=job.duration_slots,
                power_kw=job.power_kw,
                available_capacity_kw=_available_kw(occupancy, start, job, capacity),
                queue_load_count=queue_load,
                carbon_mean_g_per_kwh=sum(carbon) / len(carbon),
                carbon_min_g_per_kwh=min(carbon),
            )
            rows.append((_row_key(job, start), row))
    rows.sort(key=lambda item: item[0])
    return tuple(row for _key, row in rows)


def _row_key(job: s.Job, start_slot: int) -> tuple:
    return (
        job.flexible,
        job.deadline_slot - job.duration_slots,
        start_slot,
        _job_number(job.job_id),
        job.job_id,
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


def _max_age_seconds(state: s.VisibleState, context: s.Context) -> float:
    limits = [
        constraint.limit_value
        for constraint in context.content.constraints
        if constraint.constraint_type == "freshness"
    ]
    if not limits:
        raise s.MissingEvidenceError("authoritative freshness constraint is missing")
    return min(2, *limits) * state.site.slot_hours * 3600


def _fresh_carbon(
    start: int,
    duration: int,
    facts: dict[int, s.CarbonForecast],
    decision_time_utc: datetime,
    max_age: float,
    current: int,
    visible_end: int,
) -> tuple[float, ...] | None:
    values: list[float] = []
    for slot in range(start, start + duration):
        fact = facts.get(slot)
        if fact is None or not current <= slot < visible_end:
            return None
        age = (decision_time_utc - fact.issued_at_utc).total_seconds()
        if age < 0 or age > max_age:
            return None
        values.append(fact.value)
    return tuple(values)


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


def _fits(occupancy: dict[int, float], start: int, job: s.Job, capacity: float) -> bool:
    return all(
        occupancy.get(slot, 0.0) + job.power_kw <= capacity
        for slot in range(start, start + job.duration_slots)
    )


def _available_kw(occupancy: dict[int, float], start: int, job: s.Job, capacity: float) -> float:
    return min(
        capacity - occupancy.get(slot, 0.0) for slot in range(start, start + job.duration_slots)
    )


def _running_load(state: s.VisibleState) -> dict[int, float]:
    horizon = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS
    load = {slot: state.site.background_kw for slot in range(state.current_slot, horizon)}
    for running in state.running_jobs:
        for slot in range(running.start_slot, running.end_slot):
            load[slot] = load.get(slot, 0.0) + running.job.power_kw
    return load
