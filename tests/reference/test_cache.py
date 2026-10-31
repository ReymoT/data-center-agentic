"""Tests for O02 deterministic reference-label cache."""

import json
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
from dc_sustainability.training.collect import CollectedDecision, collect_decisions
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
        decision_time_utc=f.SLOT0_UTC,
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
        decision_time_utc=_decision_time(1),
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
        decision_time_utc=f.SLOT0_UTC,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    different_tol = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
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
        decision_time_utc=f.SLOT0_UTC,
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
        decision_time_utc=f.SLOT0_UTC,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    assert fewer_key.digest() != base_key.digest()


def test_cache_key_changes_with_decision_time():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    base_key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    later_time = f.SLOT0_UTC + timedelta(hours=1)
    later_key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=later_time,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    assert later_key.digest() != base_key.digest()


def test_cache_key_changes_with_forecast_values():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    base_key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    # Different forecast values change the context hash and therefore the key.
    uniform_facts = tuple(
        fact.model_copy(update={"value": 100.0}) for fact in state.carbon_facts
    )
    different_state = state.model_copy(update={"carbon_facts": uniform_facts})
    different_ctx = s.Context.build(different_state, snap, representation="flat")
    different_rows = candidate_features(different_state, different_ctx, decision_time_utc=f.SLOT0_UTC)
    different_key = make_cache_key(
        different_state,
        different_ctx,
        different_rows,
        decision_time_utc=f.SLOT0_UTC,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    assert different_key.digest() != base_key.digest()


def test_cache_key_changes_with_forecast_metadata():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    base_key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    # Same values but different issued_at_utc / fact_id change the context hash.
    shifted_facts = tuple(
        fact.model_copy(
            update={
                "fact_id": f"FACT-SHIFT-s{fact.valid_slot:02d}",
                "issued_at_utc": f.SLOT0_UTC + timedelta(hours=fact.valid_slot + 1),
            }
        )
        for fact in state.carbon_facts
    )
    shifted_state = state.model_copy(update={"carbon_facts": shifted_facts})
    shifted_ctx = s.Context.build(shifted_state, snap, representation="flat")
    shifted_rows = candidate_features(shifted_state, shifted_ctx, decision_time_utc=f.SLOT0_UTC)
    shifted_key = make_cache_key(
        shifted_state,
        shifted_ctx,
        shifted_rows,
        decision_time_utc=f.SLOT0_UTC,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    assert shifted_key.digest() != base_key.digest()


def test_cache_key_changes_with_solver_version():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
        backend="scipy.optimize.milp",
        backend_version="scipy",
        tolerance=1e-6,
        time_limit_s=5.0,
    )
    assert key.reference_solver_version == "1.0.0"
    assert key.label_schema_version == s.SCHEMA_VERSION


def test_cache_miss_then_hit(tmp_path):
    cache = LabelCache(tmp_path)
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
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
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
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
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
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
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
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
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
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
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
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
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    assert result.status == "certified_infeasible"
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=_decision_time(4))
    assert all(label.label is None for label in labels)
    assert not any(label.is_training_row() for label in labels)


def test_missing_capacity_excludes_training_rows():
    snap = f.snapshot(include_capacity=False)
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    assert result.status == "insufficient_evidence"
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    assert all(label.label is None for label in labels)
    assert not any(label.is_training_row() for label in labels)


def test_labels_require_authoritative_decision_time():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    # Explicit decision time must be used; O02 must not invent a timestamp.
    labels_explicit = labels_from_solver_result(
        state, ctx, result, decision_time_utc=f.SLOT0_UTC
    )
    with pytest.raises(ValueError, match="explicit trusted UTC decision_time_utc"):
        labels_from_solver_result(state, ctx, result)
    assert labels_explicit == labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)


def test_label_decision_rejects_missing_decision_time():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    sample = CollectedDecision(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        state=state,
        context=ctx,
        decision_time_utc=None,  # type: ignore[arg-type]
        rows=rows,
    )
    with pytest.raises(ValueError, match="explicit trusted UTC decision_time_utc"):
        label_decision(sample, time_limit_s=5.0)


def test_cache_invalidates_on_outdated_schema_version(tmp_path):
    cache = LabelCache(tmp_path)
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
        backend=result.backend,
        backend_version=result.backend_version,
        tolerance=result.tolerance,
        time_limit_s=5.0,
    )
    cache.put(key, result, labels)

    entry_path = cache._entry_path(key)
    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    entry["cache_schema_version"] = "0.0.0"
    entry_path.write_text(json.dumps(entry), encoding="utf-8")
    assert cache.get(key) is None
    assert cache.labels_for(key) is None


def test_cache_invalidates_on_solver_version_change(tmp_path):
    cache = LabelCache(tmp_path)
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
        backend=result.backend,
        backend_version=result.backend_version,
        tolerance=result.tolerance,
        time_limit_s=5.0,
    )
    cache.put(key, result, labels)

    entry_path = cache._entry_path(key)
    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    entry["reference_solver_version"] = "0.0.0"
    entry_path.write_text(json.dumps(entry), encoding="utf-8")
    assert cache.get(key) is None
    assert cache.labels_for(key) is None


def test_cache_invalidates_on_key_mismatch(tmp_path):
    cache = LabelCache(tmp_path)
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    rows = candidate_features(state, ctx, decision_time_utc=f.SLOT0_UTC)
    result = solve_visible(state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    labels = labels_from_solver_result(state, ctx, result, decision_time_utc=f.SLOT0_UTC)
    key = make_cache_key(
        state,
        ctx,
        rows,
        decision_time_utc=f.SLOT0_UTC,
        backend=result.backend,
        backend_version=result.backend_version,
        tolerance=result.tolerance,
        time_limit_s=5.0,
    )
    cache.put(key, result, labels)

    entry_path = cache._entry_path(key)
    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    entry["key"]["time_limit_s"] = 999.0
    entry_path.write_text(json.dumps(entry), encoding="utf-8")
    assert cache.get(key) is None
    assert cache.labels_for(key) is None


def test_solver_rejects_stale_forecasts():
    snap = f.snapshot()
    state = f.visible_state(snap)
    ctx = s.Context.build(state, snap, representation="flat")
    # decision_time_utc is one freshness window after the forecasts were issued.
    stale_time = f.SLOT0_UTC + timedelta(hours=3)
    result = solve_visible(state, ctx, decision_time_utc=stale_time, time_limit_s=5.0)
    # With stale forecasts no feasible candidate can be built, so the solver reports
    # certified_infeasible (no schedule satisfies capacity/carbon freshness).
    assert result.status in ("insufficient_evidence", "certified_infeasible")
    assert result.schedule is None


def test_solver_rejects_future_issued_forecasts():
    snap = f.snapshot()
    state = f.visible_state(snap)
    # Issue forecasts in the future relative to the decision time.
    future_facts = tuple(
        fact.model_copy(update={"issued_at_utc": f.SLOT0_UTC + timedelta(hours=2)})
        for fact in state.carbon_facts
    )
    future_state = state.model_copy(update={"carbon_facts": future_facts})
    ctx = s.Context.build(future_state, snap, representation="flat")
    result = solve_visible(future_state, ctx, decision_time_utc=f.SLOT0_UTC, time_limit_s=5.0)
    assert result.status in ("insufficient_evidence", "certified_infeasible")
    assert result.schedule is None


def test_end_to_end_collect_label_cache_hit(tmp_path):
    """Collect decisions, label them, persist to cache, and hit cache on identical inputs."""
    cache = LabelCache(tmp_path)
    samples = collect_decisions(
        episode(hand_jobs()),
        decision_time_utc=_decision_time,
        approve=_empty_approve,
        forecasts_by_slot=_forecast_map(),
    )
    # Use the first sample that produces an optimal label set.
    sample = next(sample for sample in samples if sample.rows)
    first = label_decision(sample, time_limit_s=5.0, cache=cache)
    assert first.solver_result.status == "certified_optimal"
    assert first.training_rows()

    # Re-labeling the same collected decision must hit the cache.
    second = label_decision(sample, time_limit_s=5.0, cache=cache)
    assert second.solver_result.solver_result_id == first.solver_result.solver_result_id
    assert second.labels == first.labels

    # Verify the persistent entry exists and is schema-current.
    from dc_sustainability.reference.cache import _REFERENCE_SOLVER_VERSION, _CACHE_SCHEMA_VERSION

    rows = candidate_features(sample.state, sample.context, decision_time_utc=sample.decision_time_utc)
    key = make_cache_key(
        sample.state,
        sample.context,
        rows,
        decision_time_utc=sample.decision_time_utc,
        backend=first.solver_result.backend,
        backend_version=first.solver_result.backend_version,
        tolerance=first.solver_result.tolerance,
        time_limit_s=5.0,
    )
    entry_path = cache._entry_path(key)
    assert entry_path.exists()
    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    assert entry["cache_schema_version"] == _CACHE_SCHEMA_VERSION
    assert entry["reference_solver_version"] == _REFERENCE_SOLVER_VERSION
    assert entry["key"] == key.canonical_dict()

    # A different decision timestamp must miss the cache.
    different_time = sample.decision_time_utc + timedelta(hours=1)
    different_key = make_cache_key(
        sample.state,
        sample.context,
        rows,
        decision_time_utc=different_time,
        backend=first.solver_result.backend,
        backend_version=first.solver_result.backend_version,
        tolerance=first.solver_result.tolerance,
        time_limit_s=5.0,
    )
    assert cache.get(different_key) is None
