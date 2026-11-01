"""P04 receiving uses real collection, labels, cache and classifier fit on fixtures."""

from pathlib import Path

import pytest

from dc_sustainability.data import materialize_development as materialize
from dc_sustainability.data.scenarios import hand_jobs
from dc_sustainability.reference import labels
from dc_sustainability.reference.cache import LabelCache
from dc_sustainability.training.pipeline import build_labeled_corpus
from dc_sustainability.training.train import ModelSpec, fit_model
from tests.reference.test_cache import _forecast_map
from tests.simulator.test_core import episode


def fixture_source(monkeypatch):
    ep = episode(hand_jobs())
    monkeypatch.setattr(materialize, "allocation", lambda: ({}, {ep.episode_id: 0}))
    monkeypatch.setattr(materialize, "episodes", lambda source: (ep,))
    monkeypatch.setattr(materialize, "persistence_forecasts", lambda source, eid: _forecast_map())
    return Path("labeled-synthetic-fixture-only.csv")


def test_p04_cached_and_uncached_rows_and_predictions_match(tmp_path, monkeypatch):
    source = fixture_source(monkeypatch)
    uncached = build_labeled_corpus(source)
    cache = LabelCache(tmp_path / "cache")
    solve = labels.solve_visible
    certified_slots = set()

    def observe(state, *args, **kwargs):
        result = solve(state, *args, **kwargs)
        if result.status == "certified_optimal":
            certified_slots.add(state.current_slot)
        return result

    monkeypatch.setattr(labels, "solve_visible", observe)
    first = build_labeled_corpus(source, cache=cache)
    assert first.rows == uncached.rows
    assert {row.label for row in first.rows} == {False, True}
    assert list(cache.directory.glob("*.entry.json"))

    def no_solver(state, *args, **kwargs):
        assert state.current_slot not in certified_slots, "cache hit must not invoke solver"
        return solve(state, *args, **kwargs)  # uncertified decisions are deliberately not cached

    monkeypatch.setattr(labels, "solve_visible", no_solver)
    second = build_labeled_corpus(source, cache=cache)
    assert second.rows == first.rows
    for spec in (ModelSpec("decision_tree_c", 3), ModelSpec("random_forest_d", 5, 100)):
        a = fit_model(spec, uncached.rows, seed=101)
        b = fit_model(spec, second.rows, seed=101)
        assert [a.selection_probability_vector(r.features) for r in uncached.rows] == [
            b.selection_probability_vector(r.features) for r in second.rows
        ]


def test_p04_refuses_hindsight_result_before_training(monkeypatch):
    source = fixture_source(monkeypatch)
    solve = labels.solve_visible

    def poisoned(*args, **kwargs):
        result = solve(*args, **kwargs)
        return result.model_copy(update={"kind": "hindsight", "uses_future_arrivals": True})

    monkeypatch.setattr(labels, "solve_visible", poisoned)
    with pytest.raises(ValueError, match="hindsight"):
        build_labeled_corpus(source)
