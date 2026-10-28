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
    result = solve_visible(state, ctx, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result)
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
    result = solve_visible(state, ctx, time_limit_s=5.0)
    assert result.status == "certified_infeasible"
    labels = labels_from_solver_result(state, ctx, result)
    assert all(label.label is None for label in labels)
    assert not any(label.is_training_row() for label in labels)


def test_missing_capacity_labels_are_none():
    snap = f.snapshot(include_capacity=False)
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    labels = labels_from_solver_result(state, ctx, result)
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


def test_candidate_label_hash_is_stable():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result)
    hashes = {label.candidate_hash for label in labels}
    assert len(hashes) == len(labels)
    # Recompute and verify stability.
    recomputed = labels_from_solver_result(state, ctx, result)
    assert {label.candidate_hash for label in recomputed} == hashes


def test_labels_preserve_feature_row_order():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result)
    label_keys = [(label.job_id, label.start_slot) for label in labels]
    row_keys = [(row.job_id, row.start_slot) for row in rows]
    assert label_keys == row_keys
