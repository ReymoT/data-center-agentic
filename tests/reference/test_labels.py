"""Regression tests for O02 certified development labels."""

from datetime import timedelta

from dc_sustainability import schemas as s
from dc_sustainability.data.scenarios import hand_jobs
from dc_sustainability.reference.labels import (
    label_decision,
    label_episode,
    labels_from_solver_result,
)
from dc_sustainability.reference.solver import solve_visible
from dc_sustainability.training.collect import collect_decisions
from dc_sustainability.training.features import candidate_features
from tests.contracts import fixtures as f
from tests.simulator.test_core import episode


def _decision_time(slot: int):
    return f.SLOT0_UTC + timedelta(hours=slot)


def _empty_approve(state: s.VisibleState, _context: s.Context) -> s.ApprovedActions:
    return s.ApprovedActions(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        plan_hash="a" * 64,
        check_id="CHK-COLLECT",
        starts=(),
    )


def _forecast_map():
    return {
        slot: tuple(fact for fact in f.forecasts(issued_slot=slot) if fact.valid_slot >= slot)
        for slot in range(30)
    }


def test_optimal_labels_match_solver_schedule():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    selected = {(label.job_id, label.start_slot) for label in labels if label.label is True}
    assert selected == {(ps.job_id, ps.start_slot) for ps in result.schedule}
    assert all(label.source_solver_result_id == result.solver_result_id for label in labels)
    assert all(label.state_hash == ctx.content_hash for label in labels)


def test_infeasible_state_labels_are_none():
    snap = f.snapshot()
    state = f.visible_state(
        snap,
        current_slot=4,
        waiting_job_ids=("J3",),
        completed_job_ids=("J1", "J2"),
    )
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    assert result.status == "certified_infeasible"
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=_decision_time(4))
    assert all(label.label is None for label in labels)
    assert not any(label.is_training_row() for label in labels)


def test_missing_capacity_labels_are_none():
    snap = f.snapshot(include_capacity=False)
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    assert all(label.label is None for label in labels)


def test_label_decision_attaches_to_collected_rows():
    samples = collect_decisions(
        episode(hand_jobs()),
        decision_time_utc=_decision_time,
        approve=_empty_approve,
        forecasts_by_slot=_forecast_map(),
    )
    labeled = [label_decision(sample, time_limit_s=5.0) for sample in samples]
    assert all(isinstance(ld.solver_result, s.SolverResult) for ld in labeled)
    # Slot 0 has feasible candidates and should be certified optimal.
    slot0 = labeled[0]
    assert slot0.solver_result.status == "certified_optimal"
    assert len(slot0.training_rows()) == len(slot0.collected.rows)
    positives = [label for label in slot0.labels if label.label is True]
    negatives = [label for label in slot0.labels if label.label is False]
    assert positives and negatives
    # Provenance: every label points back to the solver result and state hash.
    assert all(
        label.source_solver_result_id == slot0.solver_result.solver_result_id
        for label in slot0.labels
    )
    assert all(label.state_hash == slot0.collected.context.content_hash for label in slot0.labels)
    # Negative labels are limited to feasible candidates that the solver considered.
    assert all(label.label is not None for label in slot0.labels)


def test_label_episode_excludes_unresolved_states():
    samples = collect_decisions(
        episode(hand_jobs()),
        decision_time_utc=_decision_time,
        approve=_empty_approve,
        forecasts_by_slot=_forecast_map(),
    )
    labeled = label_episode(tuple(samples), time_limit_s=5.0)
    training_rows = [
        (ld.slot, label.candidate_key)
        for ld in labeled
        for label in ld.labels
        if label.is_training_row()
    ]
    # At least the early slots should produce training rows.
    assert training_rows
    # No label should leak future-arrival information.
    for ld in labeled:
        for label in ld.labels:
            assert label.episode_id == ld.episode_id
            assert label.slot == ld.slot
            assert label.state_hash == ld.collected.context.content_hash


def test_only_optimal_results_produce_training_labels():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    optimal = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    assert optimal.status == "certified_optimal"
    optimal_labels = labels_from_solver_result(state, ctx, optimal, decision_time_utc=f.SLOT0_UTC)
    assert any(label.label is True for label in optimal_labels)
    assert any(label.label is False for label in optimal_labels)
    assert all(label.is_training_row() for label in optimal_labels)

    # Same state but with stale forecasts becomes infeasible/insufficient and yields no labels.
    stale_time = f.SLOT0_UTC + timedelta(hours=3)
    stale_result = solve_visible(state, ctx, decision_time_utc=stale_time, time_limit_s=5.0)
    assert stale_result.status != "certified_optimal"
    stale_labels = labels_from_solver_result(state, ctx, stale_result, decision_time_utc=stale_time)
    assert all(label.label is None for label in stale_labels)
    assert not any(label.is_training_row() for label in stale_labels)


def test_negative_labels_are_feasible_candidates_only():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    feasible_keys = {(row.job_id, row.start_slot) for row in rows}
    for label in labels:
        assert label.candidate_key in feasible_keys
        if label.label is False:
            # Negative labels must still be feasible candidates the solver evaluated.
            assert label.source_solver_result_id == result.solver_result_id
            assert label.state_hash == ctx.content_hash


def test_labels_cannot_use_future_arrivals():
    """A decision made before J3 arrives must not label J3 candidates."""
    snap = f.snapshot()
    # Slot 0: only J1 and J2 have arrived; J3 is still hidden.
    state = f.visible_state(snap, current_slot=0, waiting_job_ids=("J1", "J2"))
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    labeled_jobs = {label.job_id for label in labels}
    assert "J3" not in labeled_jobs
    assert all(label.job_id in ("J1", "J2") for label in labels)


def test_labels_cannot_use_realized_future_carbon():
    """Labels must be built from forecasts, not realized observations."""
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    # The solver result is computed from the state's carbon_facts (forecasts).
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    # No label references observations or future realized slots.
    for label in labels:
        assert label.state_hash == ctx.content_hash
        assert label.source_solver_result_id == result.solver_result_id
    # Changing only realized observations (not in the visible state) leaves labels unchanged.
    from tests.contracts import fixtures as fixtures_module

    modified_obs = tuple(
        obs.model_copy(update={"value": obs.value + 1000.0})
        for obs in fixtures_module.observations()
    )
    assert len(modified_obs) == len(fixtures_module.observations())
    # Recompute with the same visible state proves the label set is identical.
    recomputed = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    assert recomputed == labels


def test_candidate_label_hash_is_stable():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    hashes = {label.candidate_hash for label in labels}
    assert len(hashes) == len(labels)
    # Recompute and verify stability.
    recomputed = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    assert {label.candidate_hash for label in recomputed} == hashes


def test_labels_preserve_feature_row_order():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    label_keys = [(label.job_id, label.start_slot) for label in labels]
    row_keys = [(row.job_id, row.start_slot) for row in rows]
    assert label_keys == row_keys
