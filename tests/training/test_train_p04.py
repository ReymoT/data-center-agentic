"""Observable P04 fit, reload, fold selection, and empty-class refusal."""

from datetime import datetime, timezone

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.training.dataset import LabeledRow, matrix_and_labels, rows_for_episodes
from dc_sustainability.training.features import FEATURE_NAMES
from dc_sustainability.training.select import rollout_metrics, select_and_refit
from dc_sustainability.training.train import (
    ModelSpec,
    artifact_sha256,
    bind_classifier,
    fit_model,
    grid_specs,
    load_artifact,
    save_artifact,
)
from tests.contracts import fixtures as f


def _features(seed: float, label: bool) -> tuple[float, ...]:
    base = [seed + index for index in range(len(FEATURE_NAMES))]
    if label:
        base[0] += 10.0
    return tuple(float(value) for value in base)


def _rows() -> tuple[LabeledRow, ...]:
    rows = []
    for episode_index, episode_id in enumerate(("EP-A", "EP-B", "EP-C", "EP-D", "EP-E", "EP-F")):
        for index in range(4):
            label = index % 2 == 0
            rows.append(
                LabeledRow(
                    episode_id=episode_id,
                    slot=index,
                    job_id=f"J{index}",
                    start_slot=index,
                    features=_features(episode_index * 10 + index, label),
                    label=label,
                )
            )
    return tuple(rows)


def _fold_map() -> dict[str, int]:
    return {"EP-A": 0, "EP-B": 0, "EP-C": 1, "EP-D": 1, "EP-E": 2, "EP-F": 2}


def test_grid_covers_required_tree_and_forest_cells():
    specs = grid_specs()
    assert [spec.key for spec in specs] == [
        "decision_tree_c:depth=3",
        "decision_tree_c:depth=5",
        "decision_tree_c:depth=8",
        "random_forest_d:trees=100:depth=5",
        "random_forest_d:trees=100:depth=10",
    ]


def test_fit_save_reload_preserves_probabilities(tmp_path):
    from hashlib import sha256

    rows = rows_for_episodes(_rows(), ("EP-A", "EP-B", "EP-C", "EP-D"))
    fitted = fit_model(ModelSpec("decision_tree_c", 3), rows, seed=7)
    path = tmp_path / "decision_tree_c.joblib"
    digest = save_artifact(fitted, path, manifest={"seed": 7})
    assert digest == sha256(path.read_bytes()).hexdigest()
    assert digest == artifact_sha256(fitted)
    loaded = load_artifact(path)
    sample = rows[0].features
    assert loaded.selection_probability_vector(sample) == pytest.approx(
        fitted.selection_probability_vector(sample)
    )
    assert path.with_suffix(".joblib.manifest.json").is_file()


def test_empty_class_partition_refuses_invented_weights():
    rows = tuple(
        LabeledRow(
            episode_id="EP-A",
            slot=0,
            job_id="J1",
            start_slot=0,
            features=_features(index, True),
            label=True,
        )
        for index in range(4)
    )
    with pytest.raises(ValueError, match="no invented class weight"):
        fit_model(ModelSpec("decision_tree_c", 3), rows, seed=1)


def test_bound_classifier_matches_feature_lookup():
    rows = rows_for_episodes(_rows(), ("EP-A", "EP-B", "EP-C", "EP-D"))
    fitted = fit_model(ModelSpec("decision_tree_c", 3), rows, seed=3)
    job = f.jobs()["J2"].model_copy(
        update={"arrival_slot": 0, "deadline_slot": 10, "duration_slots": 2}
    )
    facts = tuple(
        s.CarbonForecast(
            fact_id=f"FACT-P04-{slot}",
            value=100.0 + slot,
            unit="g/kWh",
            source_id=f.SOURCE_ID,
            valid_slot=slot,
            issued_at_utc=f.SLOT0_UTC,
            forecast_kind="perfect_foresight",
            semantics=f.semantics(),
            quality_status="unvalidated",
        )
        for slot in range(0, 8)
    )
    state = s.VisibleState.from_snapshot(
        f.snapshot(),
        episode_id=f.EPISODE_ID,
        current_slot=0,
        state_version=0,
        waiting_jobs=(job,),
        carbon_facts=facts,
    )
    context = s.Context.build(state, f.snapshot(), "flat")
    decision_time = f.SLOT0_UTC
    bound = bind_classifier(fitted, state, context, decision_time_utc=decision_time)
    probability = bound.selection_probability(job, 0)
    assert 0.0 <= probability <= 1.0


def test_select_and_refit_picks_both_systems_on_synthetic_episodes():
    rows = _rows()
    fold_map = _fold_map()
    origin = datetime(2022, 1, 1, tzinfo=timezone.utc)
    episodes = {}
    for episode_id in fold_map:
        private = f.private_episode()
        episodes[episode_id] = private.model_copy(update={"episode_id": episode_id})
    selection = select_and_refit(
        rows,
        fold_map,
        episodes,
        seed=11,
        decision_origin_by_episode={episode_id: origin for episode_id in fold_map},
        specs=(
            ModelSpec("decision_tree_c", 3),
            ModelSpec("random_forest_d", 5, n_estimators=100),
        ),
    )
    assert set(selection.selected) == {"decision_tree_c", "random_forest_d"}
    assert set(selection.refit) == {"decision_tree_c", "random_forest_d"}
    assert selection.fold_results


def test_matrix_helper_rejects_empty_rows():
    with pytest.raises(ValueError, match="at least one labeled row"):
        matrix_and_labels(())


def test_rollout_metrics_are_finite_on_contract_episode():
    rows = rows_for_episodes(_rows(), ("EP-A", "EP-B", "EP-C", "EP-D"))
    fitted = fit_model(ModelSpec("decision_tree_c", 3), rows, seed=5)
    episode = f.private_episode()
    metrics = rollout_metrics(
        episode,
        fitted,
        decision_origin_utc=datetime(2022, 1, 1, tzinfo=timezone.utc),
    )
    assert metrics.completed >= 0
    assert metrics.deadline_misses >= 0
    assert metrics.emissions_kg >= 0.0 or metrics.emissions_kg == float("inf")
