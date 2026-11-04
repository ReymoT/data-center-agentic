"""Regression tests for the deterministic visible-state MILP solver."""

from datetime import timedelta
from itertools import product
from typing import Optional

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.reference.solver import _BACKEND_VERSION, solve_visible
from tests.contracts import fixtures as f


def _context(state: s.VisibleState) -> s.Context:
    return s.Context.build(state, f.snapshot(), representation="flat")


def _decision_time(state: s.VisibleState) -> s.UtcTime:
    return f.SLOT0_UTC + timedelta(hours=state.current_slot)


# ---------------------------------------------------------------------------
# Independent exhaustive oracle for tiny scheduling instances.
#
# The oracle below deliberately does NOT call solve_visible, reuse the production
# MILP builder, or copy its results. It independently enumerates allowed start
# combinations, checks feasibility from first principles, and computes emissions
# using job power, duration, slot length, PUE, and the visible carbon forecasts.
# It is intentionally limited to tiny cases (a handful of jobs and slots) so the
# test layer can compare the production solver against a transparent brute-force
# reference.
# ---------------------------------------------------------------------------


def _visible_end(state: s.VisibleState) -> int:
    """Return the exclusive end of the visible decision/completion horizon."""
    return min(
        state.current_slot + s.PROPOSED_DECISION_SLOTS,
        s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS,
    )


def _freshness_limit_seconds(state: s.VisibleState, context: s.Context) -> Optional[float]:
    """Return the smallest freshness limit in seconds, or None if missing."""
    limits = [
        c.limit_value for c in context.content.constraints if c.constraint_type == "freshness"
    ]
    if not limits:
        return None
    return min(2, *limits) * state.site.slot_hours * 3600


def _carbon_for_slot(
    state: s.VisibleState,
    context: s.Context,
    slot: int,
    decision_time_utc: s.UtcTime,
) -> Optional[float]:
    """Return the fresh forecast value for a slot, or None if missing/stale."""
    max_age = _freshness_limit_seconds(state, context)
    if max_age is None:
        return None
    visible_end = _visible_end(state)
    if not state.current_slot <= slot < visible_end:
        return None
    fact = next((f for f in state.carbon_facts if f.valid_slot == slot), None)
    if fact is None:
        return None
    age = (decision_time_utc - fact.issued_at_utc).total_seconds()
    if age < 0 or age > max_age:
        return None
    return fact.value


def _job_energy_kwh(job: s.Job, site: s.SiteConfig) -> float:
    """Independent energy calculation: power * duration * slot_hours * PUE."""
    return job.power_kw * job.duration_slots * site.slot_hours * site.pue


def _allowed_starts(
    job: s.Job,
    current_slot: int,
    horizon: int,
    capacity: float,
    occupancy: dict[int, float],
) -> tuple[int, ...]:
    """Return start slots that satisfy arrival, deadline, non-flexible, and running-capacity rules."""
    if not job.flexible:
        arrival = job.arrival_slot
        if arrival < current_slot or arrival > s.PROPOSED_DECISION_SLOTS - 1:
            return ()
        if arrival + job.duration_slots > min(job.deadline_slot, horizon):
            return ()
        candidates = (arrival,)
    else:
        first = max(current_slot, job.arrival_slot)
        last = min(
            s.PROPOSED_DECISION_SLOTS - 1,
            job.deadline_slot - job.duration_slots,
            horizon - job.duration_slots,
        )
        if first > last:
            return ()
        candidates = tuple(range(first, last + 1))

    feasible: list[int] = []
    for start in candidates:
        if all(
            occupancy.get(slot, 0.0) + job.power_kw <= capacity
            for slot in range(start, start + job.duration_slots)
        ):
            feasible.append(start)
    return tuple(feasible)


def _schedule_load(
    schedule: dict[str, int],
    jobs: dict[str, s.Job],
    base_occupancy: dict[int, float],
) -> dict[int, float]:
    """Return per-slot total load including background/running occupancy and scheduled jobs."""
    load = dict(base_occupancy)
    for job_id, start in schedule.items():
        job = jobs[job_id]
        for slot in range(start, start + job.duration_slots):
            load[slot] = load.get(slot, 0.0) + job.power_kw
    return load


def _schedule_emissions_kg(
    schedule: dict[str, int],
    jobs: dict[str, s.Job],
    state: s.VisibleState,
    context: s.Context,
    decision_time_utc: s.UtcTime,
) -> Optional[float]:
    """Return total emissions for a schedule, or None if any occupied slot lacks fresh carbon."""
    total = 0.0
    for job_id, start in schedule.items():
        job = jobs[job_id]
        energy_per_slot = _job_energy_kwh(job, state.site) / job.duration_slots
        for slot in range(start, start + job.duration_slots):
            carbon = _carbon_for_slot(state, context, slot, decision_time_utc)
            if carbon is None:
                return None
            total += energy_per_slot * carbon / 1000.0
    return total


def exhaustive_oracle(
    state: s.VisibleState,
    context: s.Context,
    *,
    decision_time_utc: s.UtcTime,
) -> dict:
    """Brute-force optimum/infeasibility for tiny visible-state instances.

    Returns a dict with keys:
      - feasible: bool
      - objective_kg: float or None
      - optimal_schedules: tuple[dict[str, int], ...] (set of optimal start maps)
      - reason: "optimal" | "infeasible" | "insufficient_evidence"
    """
    capacity_limits = [
        c.limit_value for c in context.content.constraints if c.constraint_type == "capacity"
    ]
    if len(capacity_limits) != 1:
        return {
            "feasible": False,
            "objective_kg": None,
            "optimal_schedules": (),
            "reason": "insufficient_evidence",
        }
    capacity = capacity_limits[0]

    horizon = _visible_end(state)
    base_occupancy = {slot: state.site.background_kw for slot in range(state.current_slot, horizon)}
    for running in state.running_jobs:
        for slot in range(running.start_slot, running.end_slot):
            base_occupancy[slot] = base_occupancy.get(slot, 0.0) + running.job.power_kw

    jobs = {job.job_id: job for job in state.waiting_jobs if job.arrival_slot <= state.current_slot}
    job_ids = sorted(jobs)

    # Per-job allowed starts (capacity/deadline/arrival/nonflexible already applied).
    allowed = {
        job_id: _allowed_starts(jobs[job_id], state.current_slot, horizon, capacity, base_occupancy)
        for job_id in job_ids
    }

    # Any arrived job with no allowed start is physically infeasible.
    for job_id in job_ids:
        if not allowed[job_id]:
            return {
                "feasible": False,
                "objective_kg": None,
                "optimal_schedules": (),
                "reason": "infeasible",
            }

    # Physical feasibility and evidence availability are different questions.
    # Enumerate only candidate starts whose complete occupied window has fresh
    # forecasts, while keeping the physical-start check above independent.
    for job_id in job_ids:
        job = jobs[job_id]
        allowed[job_id] = tuple(
            start
            for start in allowed[job_id]
            if all(
                _carbon_for_slot(state, context, slot, decision_time_utc) is not None
                for slot in range(start, start + job.duration_slots)
            )
        )
        if not allowed[job_id]:
            return {
                "feasible": False,
                "objective_kg": None,
                "optimal_schedules": (),
                "reason": "insufficient_evidence",
            }

    # Enumerate all combinations of one start per job.
    best_objective: Optional[float] = None
    best_schedules: list[dict[str, int]] = []
    for combo in product(*[allowed[job_id] for job_id in job_ids]):
        schedule = dict(zip(job_ids, combo))
        load = _schedule_load(schedule, jobs, base_occupancy)
        if any(load.get(slot, 0.0) > capacity for slot in range(state.current_slot, horizon)):
            continue
        emissions = _schedule_emissions_kg(schedule, jobs, state, context, decision_time_utc)
        assert emissions is not None  # all enumerated windows have complete evidence
        if best_objective is None or emissions < best_objective - 1e-9:
            best_objective = emissions
            best_schedules = [schedule]
        elif abs(emissions - best_objective) <= 1e-9:
            best_schedules.append(schedule)

    if best_objective is None:
        return {
            "feasible": False,
            "objective_kg": None,
            "optimal_schedules": (),
            "reason": "infeasible",
        }

    optimal = tuple(
        dict(sorted(s.items())) for s in sorted(best_schedules, key=lambda d: sorted(d.items()))
    )
    return {
        "feasible": True,
        "objective_kg": best_objective,
        "optimal_schedules": optimal,
        "reason": "optimal",
    }


def test_hand_example_is_certified_optimal():
    snap = f.snapshot()
    state = f.visible_state(snap)
    result = solve_visible(
        state, _context(state), decision_time_utc=_decision_time(state), time_limit_s=5.0
    )
    assert result.status == "certified_optimal"
    assert result.kind == "visible"
    assert result.uses_future_arrivals is False
    assert result.schedule is not None
    scheduled = {(ps.job_id, ps.start_slot) for ps in result.schedule}
    assert scheduled == {("J1", 2), ("J2", 4)}
    assert result.objective_kg == 48.4
    assert result.matching_work_job_ids == ("J1", "J2")
    assert result.certification_basis
    assert result.backend == "scipy.optimize.milp"
    assert result.backend_version == _BACKEND_VERSION
    assert result.time_limit_s == 5.0
    assert result.elapsed_s >= 0.0
    assert result.gap is not None
    assert result.bound_kg is not None


def test_infeasible_job_is_certified_infeasible():
    snap = f.snapshot()
    state = f.visible_state(
        snap,
        current_slot=4,
        waiting_job_ids=("J3",),
        completed_job_ids=("J1", "J2"),
    )
    result = solve_visible(
        state, _context(state), decision_time_utc=_decision_time(state), time_limit_s=5.0
    )
    assert result.status == "certified_infeasible"
    assert result.schedule is None
    assert result.objective_kg is None
    assert result.certification_basis
    assert "J3" in result.termination


def test_missing_capacity_is_insufficient_evidence():
    snap = f.snapshot(include_capacity=False)
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    assert result.schedule is None
    assert result.objective_kg is None
    assert "capacity" in result.unresolved_reason.lower()


def test_solver_result_schema_validates():
    snap = f.snapshot()
    state = f.visible_state(snap)
    result = solve_visible(
        state, _context(state), decision_time_utc=_decision_time(state), time_limit_s=5.0
    )
    # Round-trip through JSON to ensure strict schema compliance.
    s.SolverResult.from_json(result.to_json())


def test_solver_is_deterministic():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = _context(state)
    first = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    second = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert first.schedule == second.schedule
    assert first.objective_kg == second.objective_kg
    assert first.input_hash == second.input_hash


def test_solver_requires_decision_time_utc():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = _context(state)
    with pytest.raises((ValueError, TypeError)):
        solve_visible(state, ctx, time_limit_s=5.0)


def test_solver_rejects_naive_decision_time():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = _context(state)
    with pytest.raises(ValueError):
        solve_visible(
            state, ctx, decision_time_utc=f.SLOT0_UTC.replace(tzinfo=None), time_limit_s=5.0
        )


def test_stale_forecast_is_insufficient_evidence():
    """A feasible physical start with stale carbon forecast must be insufficient evidence."""
    snap = f.snapshot()
    state = f.visible_state(snap)
    _context(state)
    # Issue forecasts far in the past so they exceed the 2-slot freshness limit.
    stale_facts = tuple(
        fact.model_copy(update={"issued_at_utc": f.SLOT0_UTC - timedelta(hours=10)})
        for fact in state.carbon_facts
    )
    stale_state = state.model_copy(update={"carbon_facts": stale_facts})
    stale_ctx = s.Context.build(stale_state, snap, representation="flat")
    result = solve_visible(
        stale_state, stale_ctx, decision_time_utc=_decision_time(stale_state), time_limit_s=5.0
    )
    assert result.status == "insufficient_evidence"
    assert (
        "stale" in result.unresolved_reason.lower()
        or "forecast" in result.unresolved_reason.lower()
    )


def test_missing_forecast_is_insufficient_evidence():
    """A job whose only feasible start needs a missing forecast is insufficient evidence."""
    snap = f.snapshot()
    # J2 duration=2, deadline=6, so feasible starts are 0..4. With current_slot=0,
    # keep only the slot-0 forecast so every feasible start needs at least one missing forecast.
    state = f.visible_state(snap, waiting_job_ids=("J2",))
    limited_facts = tuple(fact for fact in state.carbon_facts if fact.valid_slot < 1)
    limited_state = state.model_copy(update={"carbon_facts": limited_facts})
    limited_ctx = s.Context.build(limited_state, snap, representation="flat")
    result = solve_visible(
        limited_state,
        limited_ctx,
        decision_time_utc=_decision_time(limited_state),
        time_limit_s=5.0,
    )
    assert result.status == "insufficient_evidence"
    assert (
        "missing" in result.unresolved_reason.lower()
        or "forecast" in result.unresolved_reason.lower()
    )


def test_missing_freshness_constraint_is_insufficient_evidence():
    """A forecast cannot be treated as fresh without an authoritative freshness limit."""
    snap = f.snapshot()
    constraints = tuple(
        constraint for constraint in snap.constraints if constraint.constraint_type != "freshness"
    )
    no_freshness = snap.model_copy(update={"constraints": constraints})
    state = f.visible_state(no_freshness)
    ctx = s.Context.build(state, no_freshness, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    assert "missing or stale carbon forecasts" in result.unresolved_reason


def test_physical_capacity_infeasibility_is_certified():
    """A job that cannot fit under capacity is certified_infeasible, not insufficient_evidence."""
    snap = f.snapshot(capacity_kw=10.0)
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert result.status == "certified_infeasible"
    assert "capacity" in result.termination.lower() or "feasible" in result.termination.lower()


def test_empty_waiting_jobs_is_optimal():
    """No waiting jobs yields a trivial certified_optimal empty schedule."""
    snap = f.snapshot()
    state = f.visible_state(snap, waiting_job_ids=())
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert result.status == "certified_optimal"
    assert result.schedule == ()
    assert result.objective_kg == 0.0


def test_nonflexible_job_requires_arrival_start():
    """A non-flexible job that cannot start at its arrival slot is infeasible."""
    snap = f.snapshot()
    jobs = f.jobs()
    # Make J1 non-flexible with arrival_slot=0. At current_slot=2 its only allowed start
    # is 0, which is before the current slot, so it has no feasible candidate.
    nonflex = jobs["J1"].model_copy(update={"flexible": False, "arrival_slot": 0})
    state = f.visible_state(snap, current_slot=2, waiting_job_ids=("J1", "J2"))
    state = state.model_copy(
        update={
            "waiting_jobs": tuple(
                nonflex if job.job_id == "J1" else job for job in state.waiting_jobs
            )
        }
    )
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert result.status == "certified_infeasible"
    assert "non-flexible" in result.termination.lower() or "feasible" in result.termination.lower()


def test_solver_populates_gap_and_bound():
    snap = f.snapshot()
    state = f.visible_state(snap)
    result = solve_visible(
        state, _context(state), decision_time_utc=_decision_time(state), time_limit_s=5.0
    )
    assert result.status == "certified_optimal"
    assert result.gap is not None
    assert result.bound_kg is not None
    assert result.gap >= 0.0


def test_solver_timeout_is_unresolved():
    """A tiny time limit on a non-trivial problem should report unresolved."""
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = _context(state)
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=1e-6)
    assert result.status == "unresolved"
    assert result.unresolved_reason
    assert result.elapsed_s >= 0.0


def test_tie_break_is_deterministic():
    """Two equal-cost schedules must resolve to the same deterministic choice."""
    snap = f.snapshot()
    # J1 and J2 have identical power/duration; with uniform carbon all feasible starts tie.
    uniform_facts = tuple(fact.model_copy(update={"value": 100.0}) for fact in f.forecasts())
    state = f.visible_state(snap)
    state = state.model_copy(update={"carbon_facts": uniform_facts})
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert result.status == "certified_optimal"
    first = result.schedule
    for _ in range(3):
        rerun = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
        assert rerun.schedule == first


def test_solver_input_hash_matches_context():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = _context(state)
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert result.input_hash == ctx.content_hash


# ---------------------------------------------------------------------------
# Independent exhaustive-oracle comparison tests (O01 acceptance evidence).
# ---------------------------------------------------------------------------


def _assert_oracle_matches_production(
    state: s.VisibleState,
    context: s.Context,
    decision_time_utc: s.UtcTime,
) -> dict:
    """Run the oracle, compare with solve_visible, and return the oracle result."""
    oracle = exhaustive_oracle(state, context, decision_time_utc=decision_time_utc)
    result = solve_visible(state, context, decision_time_utc=decision_time_utc, time_limit_s=5.0)

    if oracle["reason"] == "insufficient_evidence":
        assert result.status == "insufficient_evidence"
        assert result.schedule is None
        assert result.objective_kg is None
        return oracle

    if not oracle["feasible"]:
        assert result.status == "certified_infeasible"
        assert result.schedule is None
        assert result.objective_kg is None
        return oracle

    assert result.status == "certified_optimal"
    assert result.schedule is not None
    assert result.objective_kg is not None
    scheduled = {ps.job_id: ps.start_slot for ps in result.schedule}
    assert scheduled in oracle["optimal_schedules"]
    assert result.objective_kg == pytest.approx(oracle["objective_kg"], abs=1e-6)
    return oracle


def test_oracle_finds_hand_example_optimum():
    """A. Small feasible optimum: oracle minimum matches production solver."""
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = _context(state)
    oracle = _assert_oracle_matches_production(state, ctx, _decision_time(state))
    assert oracle["feasible"]
    assert oracle["objective_kg"] == pytest.approx(48.4, abs=1e-6)
    assert frozenset({("J1", 2), ("J2", 4)}) in {
        frozenset(schedule.items()) for schedule in oracle["optimal_schedules"]
    }


def _make_state_with_jobs(
    snap: s.ConstraintSnapshot,
    current_slot: int,
    jobs: tuple[s.Job, ...],
    running_jobs: tuple[s.RunningJobView, ...] = (),
    completed_job_ids: tuple[str, ...] = (),
    carbon_facts: tuple[s.CarbonForecast, ...] | None = None,
) -> s.VisibleState:
    """Build a VisibleState using the supplied job records directly."""
    visible_end = min(
        current_slot + s.PROPOSED_DECISION_SLOTS,
        s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS,
    )
    visible_forecasts = (
        carbon_facts
        if carbon_facts is not None
        else tuple(fact for fact in f.forecasts() if current_slot <= fact.valid_slot < visible_end)
    )
    return s.VisibleState.from_snapshot(
        snap,
        episode_id=f.EPISODE_ID,
        current_slot=current_slot,
        state_version=current_slot,
        waiting_jobs=jobs,
        running_jobs=running_jobs,
        completed_jobs=tuple(
            s.CompletedJobView(
                job_id=job_id,
                start_slot=0 if job_id == "J1" else 2,
                end_slot=2 if job_id == "J1" else 4,
            )
            for job_id in completed_job_ids
        ),
        carbon_facts=visible_forecasts,
    )


def test_oracle_rejects_overlapping_capacity():
    """B. Overlapping jobs and capacity: oracle independently rejects invalid overlaps."""
    snap = f.snapshot(capacity_kw=100.0)
    jobs = f.jobs()
    # Each 40 kW job fits individually above the 40 kW background, but both
    # require the same two slots and jointly exceed the 100 kW capacity.
    big_a = jobs["J1"].model_copy(
        update={
            "job_id": "JA",
            "power_kw": 40,
            "duration_slots": 2,
            "arrival_slot": 0,
            "deadline_slot": 2,
        }
    )
    big_b = jobs["J2"].model_copy(
        update={
            "job_id": "JB",
            "power_kw": 40,
            "duration_slots": 2,
            "arrival_slot": 0,
            "deadline_slot": 2,
        }
    )
    state = _make_state_with_jobs(snap, current_slot=0, jobs=(big_a, big_b))
    ctx = s.Context.build(state, snap, representation="flat")
    for job in (big_a, big_b):
        assert _allowed_starts(job, 0, _visible_end(state), 100.0, {0: 40.0, 1: 40.0}) == (0,)
    oracle = _assert_oracle_matches_production(state, ctx, _decision_time(state))
    assert not oracle["feasible"]


def test_oracle_accounts_for_running_and_background_occupancy():
    """C. Running/background occupancy: oracle accounts for existing load before new starts."""
    snap = f.snapshot(capacity_kw=120.0)
    jobs = f.jobs()
    # Background 40 kW + running 30 kW occupies slots 0-1. A 70 kW one-slot job is
    # feasible only when background+running load leaves at least 70 kW headroom:
    # slots 0-1 have 30 kW free (insufficient), slot 2+ has 80 kW free (sufficient).
    big_job = jobs["J1"].model_copy(update={"job_id": "JBIG", "power_kw": 70, "duration_slots": 1})
    running_job = jobs["J2"].model_copy(
        update={"job_id": "JRUN", "power_kw": 30, "duration_slots": 2}
    )
    running = s.RunningJobView(job=running_job, start_slot=0)
    state = _make_state_with_jobs(
        snap,
        current_slot=0,
        jobs=(big_job,),
        running_jobs=(running,),
    )
    ctx = s.Context.build(state, snap, representation="flat")
    oracle = _assert_oracle_matches_production(state, ctx, _decision_time(state))
    assert oracle["feasible"]
    assert all(schedule["JBIG"] >= 2 for schedule in oracle["optimal_schedules"])


def test_oracle_enforces_arrival_deadline_and_nonflexible():
    """D. Arrival, deadline, and non-flexible restrictions."""
    snap = f.snapshot(capacity_kw=120.0)
    jobs = f.jobs()
    # Non-flexible job must start exactly at arrival; here arrival=1 and current=1.
    nonflex = jobs["J1"].model_copy(
        update={
            "job_id": "JNF",
            "flexible": False,
            "arrival_slot": 1,
            "duration_slots": 2,
            "deadline_slot": 4,
        }
    )
    # Flexible job with a tight deadline: only starts 1 or 2 are feasible at current_slot=1.
    flex = jobs["J2"].model_copy(
        update={"job_id": "JF", "arrival_slot": 0, "duration_slots": 2, "deadline_slot": 4}
    )
    state = _make_state_with_jobs(
        snap,
        current_slot=1,
        jobs=(nonflex, flex),
    )
    ctx = s.Context.build(state, snap, representation="flat")
    oracle = _assert_oracle_matches_production(state, ctx, _decision_time(state))
    assert oracle["feasible"]
    for schedule in oracle["optimal_schedules"]:
        assert schedule["JNF"] == 1  # non-flexible must start at arrival
        assert schedule["JF"] >= 1  # cannot start before current slot / arrival
        assert schedule["JF"] + 2 <= 4  # deadline respected


def test_oracle_confirms_physical_infeasibility():
    """E. Physical infeasibility: oracle finds no feasible schedule and production agrees."""
    snap = f.snapshot()
    jobs = f.jobs()
    # A job whose deadline is before it can finish.
    impossible = jobs["J3"].model_copy(
        update={"job_id": "JIMP", "arrival_slot": 2, "duration_slots": 5, "deadline_slot": 6}
    )
    state = _make_state_with_jobs(snap, current_slot=2, jobs=(impossible,))
    ctx = s.Context.build(state, snap, representation="flat")
    oracle = _assert_oracle_matches_production(state, ctx, _decision_time(state))
    assert not oracle["feasible"]


def test_oracle_equal_cost_optima_without_imposing_tie_break():
    """F. Equal-cost optima: feasible schedules share the same objective; no lexicographic rule."""
    snap = f.snapshot()
    jobs = f.jobs()
    # Two identical jobs with uniform carbon: many schedules have the same emissions.
    uniform_facts = tuple(fact.model_copy(update={"value": 100.0}) for fact in f.forecasts())
    twin_a = jobs["J1"].model_copy(update={"job_id": "JA", "power_kw": 30, "duration_slots": 1})
    twin_b = jobs["J2"].model_copy(update={"job_id": "JB", "power_kw": 30, "duration_slots": 1})
    state = _make_state_with_jobs(
        snap,
        current_slot=0,
        jobs=(twin_a, twin_b),
        carbon_facts=uniform_facts,
    )
    ctx = s.Context.build(state, snap, representation="flat")
    oracle = _assert_oracle_matches_production(state, ctx, _decision_time(state))
    assert oracle["feasible"]
    assert len(oracle["optimal_schedules"]) > 1
    objectives = {
        _schedule_emissions_kg(
            schedule, {j.job_id: j for j in state.waiting_jobs}, state, ctx, _decision_time(state)
        )
        for schedule in oracle["optimal_schedules"]
    }
    assert len(objectives) == 1
    # Production solver must pick one of the optimal schedules, not a particular one.
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert result.status == "certified_optimal"
    scheduled = {ps.job_id: ps.start_slot for ps in result.schedule}
    assert scheduled in oracle["optimal_schedules"]


def test_oracle_independence_from_production_solver(monkeypatch):
    """Validate the oracle: its expected objective does not come from solve_visible."""
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = _context(state)

    def forbidden(*args, **kwargs):
        raise AssertionError("the exhaustive oracle must not call the production solver")

    monkeypatch.setattr("tests.reference.test_solver.solve_visible", forbidden)
    monkeypatch.setattr("dc_sustainability.reference.solver.solve_visible", forbidden)
    oracle = exhaustive_oracle(state, ctx, decision_time_utc=_decision_time(state))
    assert oracle["objective_kg"] == pytest.approx(48.4, abs=1e-6)


def test_oracle_can_use_a_later_start_when_first_start_lacks_carbon():
    snap = f.snapshot()
    job = f.jobs()["J1"].model_copy(
        update={"job_id": "JONE", "duration_slots": 1, "arrival_slot": 0, "deadline_slot": 3}
    )
    facts = tuple(fact for fact in f.forecasts() if fact.valid_slot != 0)
    state = _make_state_with_jobs(snap, 0, (job,), carbon_facts=facts)
    oracle = _assert_oracle_matches_production(
        state, s.Context.build(state, snap, representation="flat"), _decision_time(state)
    )
    assert oracle["feasible"]
    assert all(schedule["JONE"] > 0 for schedule in oracle["optimal_schedules"])


def test_oracle_missing_all_carbon_is_evidence_failure():
    snap = f.snapshot()
    state = _make_state_with_jobs(snap, 0, (f.jobs()["J1"],), carbon_facts=())
    oracle = _assert_oracle_matches_production(
        state, s.Context.build(state, snap, representation="flat"), _decision_time(state)
    )
    assert oracle["reason"] == "insufficient_evidence"
