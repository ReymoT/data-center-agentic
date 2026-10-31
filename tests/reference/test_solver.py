"""Regression tests for the deterministic visible-state MILP solver."""

from datetime import timedelta

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
