"""Regression tests for the deterministic visible-state MILP solver."""

from datetime import timedelta
from typing import Optional

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.reference.solver import _BACKEND_VERSION, solve_visible
from tests.contracts import fixtures as f


def _context(state: s.VisibleState) -> s.Context:
    return s.Context.build(state, f.snapshot(), representation="flat")


def _decision_time(state: s.VisibleState) -> s.UtcTime:
    return f.SLOT0_UTC + timedelta(hours=state.current_slot)


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


def _emissions_kg(state: s.VisibleState, start_by_job: dict[str, int]) -> float:
    """Independent oracle: compute total emissions for a feasible schedule."""
    total = 0.0
    site = state.site
    facts = {fact.valid_slot: fact.value for fact in state.carbon_facts}
    for job in state.waiting_jobs:
        if job.job_id not in start_by_job:
            continue
        start = start_by_job[job.job_id]
        energy = job.power_kw * job.duration_slots * site.slot_hours * site.pue
        mean_carbon = sum(facts[start + k] for k in range(job.duration_slots)) / job.duration_slots
        total += energy * mean_carbon / 1000.0
    return total


def _feasible_schedules(
    state: s.VisibleState, context: s.Context
) -> list[tuple[dict[str, int], float]]:
    """Brute-force enumerate all feasible schedules and their emissions.

    Does not use the MILP model or any solver helper except the public
    ``_window`` and ``_running_load`` utilities for feasibility checks.
    """
    from dc_sustainability.training.features import _running_load, _window

    capacity = next(
        (c.limit_value for c in context.content.constraints if c.constraint_type == "capacity"),
        None,
    )
    if capacity is None:
        return []
    occupancy = _running_load(state)
    current = state.current_slot
    horizon = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS
    visible_end = min(current + s.PROPOSED_DECISION_SLOTS, horizon)
    arrived = [job for job in state.waiting_jobs if job.arrival_slot <= current]
    if not arrived:
        return [({}, 0.0)]

    # Build per-job feasible starts.
    job_starts: dict[str, tuple[int, ...]] = {}
    for job in arrived:
        if not job.flexible:
            arrival = job.arrival_slot
            if arrival < current or arrival + job.duration_slots > min(job.deadline_slot, horizon):
                return []
            if any(
                occupancy.get(slot, 0.0) + job.power_kw > capacity
                for slot in range(arrival, arrival + job.duration_slots)
            ):
                return []
            job_starts[job.job_id] = (arrival,)
        else:
            feasible = []
            for start in _window(job, current):
                if start + job.duration_slots > visible_end:
                    continue
                if all(
                    occupancy.get(slot, 0.0) + job.power_kw <= capacity
                    for slot in range(start, start + job.duration_slots)
                ):
                    feasible.append(start)
            if not feasible:
                return []
            job_starts[job.job_id] = tuple(feasible)

    # Enumerate all combinations and enforce per-slot capacity.
    schedules: list[tuple[dict[str, int], float]] = []
    jobs = arrived

    def backtrack(idx: int, current_starts: dict[str, int], slot_load: dict[int, float]) -> None:
        if idx == len(jobs):
            emissions = _emissions_kg(state, current_starts)
            schedules.append((dict(current_starts), emissions))
            return
        job = jobs[idx]
        for start in job_starts[job.job_id]:
            # Check capacity for this start.
            ok = True
            new_load = dict(slot_load)
            for slot in range(start, start + job.duration_slots):
                new_load[slot] = new_load.get(slot, 0.0) + job.power_kw
                if new_load[slot] > capacity:
                    ok = False
                    break
            if not ok:
                continue
            current_starts[job.job_id] = start
            backtrack(idx + 1, current_starts, new_load)
            del current_starts[job.job_id]

    backtrack(0, {}, dict(occupancy))
    return schedules


def _oracle_result(
    state: s.VisibleState, context: s.Context
) -> tuple[str, Optional[float], Optional[tuple[s.PlannedStart, ...]]]:
    """Return (status, objective_kg, schedule) from brute-force enumeration."""
    schedules = _feasible_schedules(state, context)
    if not schedules:
        return ("certified_infeasible", None, None)
    best = min(schedules, key=lambda item: (item[1], sorted(item[0].items())))
    schedule = tuple(
        s.PlannedStart(job_id=job_id, start_slot=start_slot)
        for job_id, start_slot in sorted(best[0].items())
    )
    return ("certified_optimal", best[1], schedule)


def _build_state(
    snap: s.ConstraintSnapshot,
    *,
    current_slot: int = 0,
    waiting_job_ids: tuple[str, ...] = ("J1", "J2"),
    completed_job_ids: tuple[str, ...] = (),
    carbon_facts: tuple[s.CarbonForecast, ...] | None = None,
) -> s.VisibleState:
    state = f.visible_state(
        snap,
        current_slot=current_slot,
        waiting_job_ids=waiting_job_ids,
        completed_job_ids=completed_job_ids,
    )
    if carbon_facts is not None:
        state = state.model_copy(update={"carbon_facts": carbon_facts})
    return state


def test_hand_example_matches_brute_force_oracle():
    """The MILP result must match an independent brute-force enumeration."""
    snap = f.snapshot()
    state = _build_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    oracle_status, oracle_objective, oracle_schedule = _oracle_result(state, ctx)
    assert result.status == oracle_status
    assert result.schedule == oracle_schedule
    assert result.objective_kg == pytest.approx(oracle_objective, abs=1e-6)


def test_capacity_infeasibility_matches_oracle():
    """A job that cannot fit under capacity is certified_infeasible by both solver and oracle."""
    snap = f.snapshot(capacity_kw=10.0)
    state = _build_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    oracle_status, _, _ = _oracle_result(state, ctx)
    assert result.status == oracle_status == "certified_infeasible"


def test_nonflexible_job_matches_oracle():
    """A non-flexible job that cannot start at its arrival slot is infeasible per both."""
    snap = f.snapshot()
    jobs = f.jobs()
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
    oracle_status, _, _ = _oracle_result(state, ctx)
    assert result.status == oracle_status == "certified_infeasible"


def test_empty_waiting_jobs_matches_oracle():
    snap = f.snapshot()
    state = _build_state(snap, waiting_job_ids=())
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    oracle_status, oracle_objective, oracle_schedule = _oracle_result(state, ctx)
    assert result.status == oracle_status == "certified_optimal"
    assert result.schedule == oracle_schedule
    assert result.objective_kg == pytest.approx(oracle_objective, abs=1e-6)


def test_tie_break_prefers_lower_job_id_start_slot():
    """When primary carbon costs are equal, lexicographic (job_id, start_slot) wins."""
    snap = f.snapshot()
    uniform_facts = tuple(fact.model_copy(update={"value": 100.0}) for fact in f.forecasts())
    state = _build_state(snap, carbon_facts=uniform_facts)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    oracle_status, oracle_objective, oracle_schedule = _oracle_result(state, ctx)
    assert result.status == oracle_status == "certified_optimal"
    assert result.schedule == oracle_schedule
    assert result.objective_kg == pytest.approx(oracle_objective, abs=1e-6)


def test_near_tie_prefers_lower_carbon():
    """Schedules whose carbon costs differ by less than the old epsilon still resolve correctly."""
    snap = f.snapshot()
    # Construct a near-tie where the two cheapest feasible schedules differ by < 1e-7 kg.
    # J1 duration=2, J2 duration=2. We make J1@2 + J2@4 and J1@4 + J2@2 nearly identical,
    # with J1@2 slightly cheaper, and verify the solver picks the cheaper one.
    carbon = list(f.HAND_CARBON)
    # Candidate schedules:
    #   J1@2 uses slots 2,3; J2@4 uses slots 4,5.
    #   J1@4 uses slots 4,5; J2@2 uses slots 2,3.
    # Original values: 300, 250, 400, 480.
    # J1@2+J2@4 = (300+250)*80 + (400+480)*60 = 44000 + 52800 = 96800 g = 96.8 kg.
    # J1@4+J2@2 = (400+480)*80 + (300+250)*60 = 70400 + 33000 = 103400 g = 103.4 kg.
    # We want J1@2+J2@4 to be cheaper by a tiny amount, so lower slots 4,5 slightly.
    # Difference to overcome: 103400 - 96800 = 6600 g. Shared slots 4,5 total kWh = 80+60 = 140.
    # Mean carbon reduction needed: 6600/140 = 47.1429 g/kWh.
    # Set slot 4 = 352.8571, slot 5 = 432.8571 -> J1@4+J2@2 = 96800.004 g, just above 96800 g.
    carbon[4] = 352.8571
    carbon[5] = 432.8571
    facts = tuple(
        fact.model_copy(update={"value": carbon[fact.valid_slot]}) for fact in f.forecasts()
    )
    state = _build_state(snap, carbon_facts=facts)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    oracle_status, oracle_objective, oracle_schedule = _oracle_result(state, ctx)
    assert result.status == oracle_status == "certified_optimal"
    assert result.schedule == oracle_schedule
    assert result.objective_kg == pytest.approx(oracle_objective, abs=1e-9)
    # The lower-carbon schedule is J1 starting at slot 2.
    assert {ps for ps in result.schedule if ps.job_id == "J1"} == {
        s.PlannedStart(job_id="J1", start_slot=2)
    }
    # Sanity check: the oracle objective must be strictly less than the next-best feasible schedule.
    schedules = _feasible_schedules(state, ctx)
    sorted_objs = sorted({obj for _, obj in schedules})
    assert sorted_objs[0] < sorted_objs[1]


def test_missing_freshness_constraint_is_insufficient_evidence():
    """A context with no freshness constraint must not certify a schedule."""
    snap = f.snapshot()
    # Remove the freshness constraint.
    constraints = tuple(c for c in snap.constraints if c.constraint_type != "freshness")
    snap_no_fresh = snap.model_copy(update={"constraints": constraints})
    state = _build_state(snap_no_fresh)
    ctx = s.Context.build(state, snap_no_fresh, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    assert "freshness" in result.unresolved_reason.lower()


def test_stale_forecast_is_insufficient_evidence_oracle():
    """A feasible physical start with stale carbon forecast is insufficient evidence."""
    snap = f.snapshot()
    state = _build_state(snap)
    stale_facts = tuple(
        fact.model_copy(update={"issued_at_utc": f.SLOT0_UTC - timedelta(hours=10)})
        for fact in state.carbon_facts
    )
    state = state.model_copy(update={"carbon_facts": stale_facts})
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    assert (
        "stale" in result.unresolved_reason.lower()
        or "forecast" in result.unresolved_reason.lower()
    )


def test_missing_forecast_is_insufficient_evidence_oracle():
    """A job whose only feasible start needs a missing forecast is insufficient evidence."""
    snap = f.snapshot()
    state = _build_state(snap, waiting_job_ids=("J2",))
    limited_facts = tuple(fact for fact in state.carbon_facts if fact.valid_slot < 1)
    state = state.model_copy(update={"carbon_facts": limited_facts})
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=_decision_time(state), time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    assert (
        "missing" in result.unresolved_reason.lower()
        or "forecast" in result.unresolved_reason.lower()
    )
