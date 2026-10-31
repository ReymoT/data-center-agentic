"""Tests for O02 deterministic reference-label cache."""

from datetime import timedelta

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data.scenarios import hand_jobs
from dc_sustainability.reference.cache import LabelCache, make_cache_key
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


def _slot0_key():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    return make_cache_key(
        state,
        ctx,
        rows,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )


def test_cache_key_is_deterministic():
    key1 = _slot0_key()
    key2 = _slot0_key()
    assert key1.digest() == key2.digest()


def test_cache_key_changes_with_state():
    base_key = _slot0_key()

    snap = f.snapshot()
    state = f.visible_state(snap, current_slot=1)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=_decision_time(1))
    later_key = make_cache_key(
        state,
        ctx,
        rows,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    assert later_key.digest() != base_key.digest()


def test_cache_key_changes_with_solver_config():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    base_key = make_cache_key(
        state,
        ctx,
        rows,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    different_tol = make_cache_key(
        state,
        ctx,
        rows,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-5,
        time_limit_s=5.0,
    )
    assert different_tol.digest() != base_key.digest()


def test_cache_key_changes_with_candidate_set():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    base_key = make_cache_key(
        state,
        ctx,
        rows,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    # Drop one candidate from the key's candidate set.
    fewer_rows = rows[:-1]
    fewer_key = make_cache_key(
        state,
        ctx,
        fewer_rows,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    assert fewer_key.digest() != base_key.digest()


def test_cache_miss_then_hit(tmp_path):
    cache = LabelCache(tmp_path)
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        backend=result.backend,
        backend_version=result.backend_version,
        tolerance=result.tolerance,
        time_limit_s=5.0,
    )

    assert cache.get(key) is None
    cache.put(key, result, labels)
    hit = cache.get(key)
    assert hit is not None
    assert hit.status == "certified_optimal"
    assert hit.schedule == result.schedule
    assert cache.labels_for(key) == labels


def test_cache_ignores_non_optimal_results(tmp_path):
    cache = LabelCache(tmp_path)
    snap = f.snapshot(include_capacity=False)
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        backend=result.backend,
        backend_version=result.backend_version,
        tolerance=result.tolerance,
        time_limit_s=5.0,
    )
    cache.put(key, result, labels)
    assert cache.get(key) is None


def test_cache_invalidates_on_corrupted_entry(tmp_path):
    cache = LabelCache(tmp_path)
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        backend=result.backend,
        backend_version=result.backend_version,
        tolerance=result.tolerance,
        time_limit_s=5.0,
    )
    cache.put(key, result, labels)

    # Corrupt the entry file but leave the result file intact.
    entry_path = cache._entry_path(key)
    entry_path.write_text("not json", encoding="utf-8")
    assert cache.get(key) is None
    assert cache.labels_for(key) is None


def test_cache_idempotent_put(tmp_path):
    cache = LabelCache(tmp_path)
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        backend=result.backend,
        backend_version=result.backend_version,
        tolerance=result.tolerance,
        time_limit_s=5.0,
    )
    cache.put(key, result, labels)
    cache.put(key, result, labels)  # identical content is allowed
    assert cache.get(key) is not None


def test_cache_put_rejects_collision(tmp_path):
    cache = LabelCache(tmp_path)
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        backend=result.backend,
        backend_version=result.backend_version,
        tolerance=result.tolerance,
        time_limit_s=5.0,
    )
    cache.put(key, result, labels)

    different_result = result.model_copy(update={"objective_kg": result.objective_kg + 1.0})
    with pytest.raises(FileExistsError):
        cache.put(key, different_result, labels)


def test_label_decision_uses_cache(tmp_path):
    cache = LabelCache(tmp_path)
    samples = collect_decisions(
        episode(hand_jobs()),
        decision_time_utc=_decision_time,
        approve=_empty_approve,
        forecasts_by_slot=_forecast_map(),
    )
    sample = samples[0]
    labeled = label_decision(sample, time_limit_s=5.0, cache=cache)
    assert labeled.solver_result.status == "certified_optimal"
    assert labeled.training_rows()

    # Second call with the same collected decision must hit the cache.
    cached = label_decision(sample, time_limit_s=5.0, cache=cache)
    assert cached.solver_result.solver_result_id == labeled.solver_result.solver_result_id


def test_label_episode_excludes_unresolved_states(tmp_path):
    cache = LabelCache(tmp_path)
    samples = collect_decisions(
        episode(hand_jobs()),
        decision_time_utc=_decision_time,
        approve=_empty_approve,
        forecasts_by_slot=_forecast_map(),
    )
    labeled = label_episode(tuple(samples), time_limit_s=5.0, cache=cache)
    training_rows = [
        (ld.slot, label.candidate_key)
        for ld in labeled
        for label in ld.labels
        if label.is_training_row()
    ]
    assert training_rows
    for ld in labeled:
        for label in ld.labels:
            assert label.episode_id == ld.episode_id
            assert label.slot == ld.slot
            assert label.state_hash == ld.collected.context.content_hash


def test_only_certified_optimal_produces_training_rows():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, time_limit_s=5.0)
    assert result.status == "certified_optimal"
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    assert any(label.label is True for label in labels)
    assert any(label.label is False for label in labels)
    assert all(label.is_training_row() for label in labels)


def test_infeasible_state_excludes_training_rows():
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
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=_decision_time(4))
    assert all(label.label is None for label in labels)
    assert not any(label.is_training_row() for label in labels)


def test_missing_capacity_excludes_training_rows():
    snap = f.snapshot(include_capacity=False)
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    assert all(label.label is None for label in labels)
    assert not any(label.is_training_row() for label in labels)


def test_labels_use_authoritative_decision_time():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, time_limit_s=5.0)
    # Explicit decision time must be used; default anchor is also deterministic.
    labels_explicit = labels_from_solver_result(
        state, ctx, result, decision_time_utc=f.SLOT0_UTC
    )
    labels_default = labels_from_solver_result(state, ctx, result)
    assert labels_explicit == labels_default
