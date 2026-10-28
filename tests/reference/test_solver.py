"""Regression tests for the deterministic visible-state MILP solver."""

from dc_sustainability import schemas as s
from dc_sustainability.reference.solver import solve_visible
from tests.contracts import fixtures as f


def _context(state: s.VisibleState) -> s.Context:
    snap = f.snapshot()
    return s.Context.build(state, snap, representation="flat")


def test_hand_example_is_certified_optimal():
    snap = f.snapshot()
    state = f.visible_state(snap)
    result = solve_visible(state, _context(state), time_limit_s=5.0)
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


def test_infeasible_job_is_certified_infeasible():
    snap = f.snapshot()
    state = f.visible_state(
        snap,
        current_slot=4,
        waiting_job_ids=("J3",),
        completed_job_ids=("J1", "J2"),
    )
    result = solve_visible(state, _context(state), time_limit_s=5.0)
    assert result.status == "certified_infeasible"
    assert result.schedule is None
    assert result.objective_kg is None
    assert result.certification_basis


def test_missing_capacity_is_insufficient_evidence():
    snap = f.snapshot(include_capacity=False)
    state = f.visible_state(snap)
    result = solve_visible(state, _context(state), time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    assert result.schedule is None
    assert result.objective_kg is None
    assert "capacity" in result.unresolved_reason.lower()


def test_solver_result_schema_validates():
    snap = f.snapshot()
    state = f.visible_state(snap)
    result = solve_visible(state, _context(state), time_limit_s=5.0)
    # Round-trip through JSON to ensure strict schema compliance.
    s.SolverResult.from_json(result.to_json())


def test_solver_is_deterministic():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = _context(state)
    first = solve_visible(state, ctx, time_limit_s=5.0)
    second = solve_visible(state, ctx, time_limit_s=5.0)
    assert first.schedule == second.schedule
    assert first.objective_kg == second.objective_kg
    assert first.input_hash == second.input_hash
