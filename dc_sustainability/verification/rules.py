"""Agreed Q01-Q04 predicates on validated policy-visible inputs only.

These functions establish individual opportunities, not a joint Q08 certificate.
Forecast assessment requires an explicit trusted UTC decision time; it never
guesses an episode date from a forecast, private observation or wall clock.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from dc_sustainability import schemas as s


def legal_starts(job, state, capacity, *, after=None, reservations=()):
    """Enumerate a job's opportunities under known running reservations and Q01."""
    first = max(state.current_slot, job.arrival_slot)
    if after is not None:
        first = max(first, after + 1)
    last = min(23, job.deadline_slot - job.duration_slots, 30 - job.duration_slots)
    return tuple(
        start
        for start in range(first, last + 1)
        if (job.flexible or start == job.arrival_slot)
        and (
            capacity is None
            or all(
                state.site.background_kw
                + state.running_job_load_kw(t)
                + sum(kw for start, end, kw in reservations if start <= t < end)
                + job.power_kw
                <= capacity
                for t in range(start, start + job.duration_slots)
            )
        )
    )


@dataclass(frozen=True)
class ForecastAssessment:
    """Local routing evidence, not an F02 record or scientific source approval."""

    required_slots: tuple[int, ...]
    missing_slots: tuple[int, ...]
    stale_slots: tuple[int, ...]
    future_issued_slots: tuple[int, ...]
    beyond_horizon_slots: tuple[int, ...]

    @property
    def reasons(self):
        return tuple(
            name
            for name, values in (
                ("missing", self.missing_slots),
                ("stale", self.stale_slots),
                ("future_issued", self.future_issued_slots),
                ("beyond_horizon", self.beyond_horizon_slots),
            )
            if values
        )

    @property
    def usable(self):
        return not self.reasons


def assess_forecasts(state, snapshot, *, decision_time_utc):
    """Q04 union across all individually legal candidates, without shortening it.

    The caller owns the trusted slot-to-UTC mapping. Missing physical constraints
    are errors; they are not evidence for a usable forecast or infeasibility.
    """
    state = s.VisibleState.model_validate(state.model_dump(mode="python"), strict=True)
    snapshot = s.ConstraintSnapshot.model_validate(snapshot.model_dump(mode="python"), strict=True)
    s.Context.build(state, snapshot, representation="flat")
    if not isinstance(decision_time_utc, datetime) or decision_time_utc.utcoffset() != timedelta(0):
        raise ValueError("an explicit trusted UTC decision time is required")
    capacity = snapshot.capacity_kw
    limits = snapshot.constraints_of("freshness")
    if not limits:
        raise s.MissingEvidenceError("authoritative freshness constraint is missing")
    max_age = min(2, *(c.limit_value for c in limits)) * state.site.slot_hours * 3600
    required = {
        t
        for job in state.waiting_jobs
        for start in legal_starts(job, state, capacity)
        for t in range(start, start + job.duration_slots)
    }
    visible_end = min(state.current_slot + 24, 30)
    beyond = required - set(range(state.current_slot, visible_end))
    facts = {f.valid_slot: f for f in state.carbon_facts}
    missing = required - facts.keys() - beyond
    stale, future = set(), set()
    for slot in required & facts.keys():
        age = (decision_time_utc - facts[slot].issued_at_utc).total_seconds()
        if age < 0:
            future.add(slot)
        elif age > max_age:
            stale.add(slot)
    return ForecastAssessment(
        *(tuple(sorted(values)) for values in (required, missing, stale, future, beyond))
    )
