"""Fit, freeze, and reload Q07 probability classifiers for C and D."""

from __future__ import annotations

import io
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

from dc_sustainability import schemas as s
from dc_sustainability.training.dataset import LabeledRow, matrix_and_labels
from dc_sustainability.training.features import FEATURE_NAMES, candidate_features
from dc_sustainability.training.folds import TrainOnlyScaler, balanced_class_weights

SystemKind = Literal["decision_tree_c", "random_forest_d"]
TREE_DEPTHS = (3, 5, 8)
FOREST_DEPTHS = (5, 10)
FOREST_TREES = 100
ARTIFACT_SCHEMA = "p04-artifact-v1"


@dataclass(frozen=True)
class ModelSpec:
    """One grid cell for C or D."""

    system: SystemKind
    max_depth: int
    n_estimators: int | None = None

    def __post_init__(self) -> None:
        if self.system == "decision_tree_c":
            if self.max_depth not in TREE_DEPTHS or self.n_estimators is not None:
                raise ValueError("decision_tree_c uses depths 3/5/8 and no n_estimators")
        elif self.system == "random_forest_d":
            if self.max_depth not in FOREST_DEPTHS or self.n_estimators != FOREST_TREES:
                raise ValueError("random_forest_d uses 100 trees at depths 5/10")
        else:
            raise ValueError(f"unsupported system: {self.system}")

    @property
    def key(self) -> str:
        if self.system == "decision_tree_c":
            return f"{self.system}:depth={self.max_depth}"
        return f"{self.system}:trees={self.n_estimators}:depth={self.max_depth}"


def grid_specs() -> tuple[ModelSpec, ...]:
    """Return the required C/D hyperparameter grid."""
    trees = tuple(ModelSpec("decision_tree_c", depth) for depth in TREE_DEPTHS)
    forests = tuple(
        ModelSpec("random_forest_d", depth, n_estimators=FOREST_TREES) for depth in FOREST_DEPTHS
    )
    return trees + forests


@dataclass(frozen=True)
class FittedModel:
    """Scaler + sklearn classifier fitted on one training partition."""

    spec: ModelSpec
    scaler: TrainOnlyScaler
    estimator: Any
    seed: int
    class_weights: tuple[float, float]
    n_rows: int
    n_positives: int
    n_negatives: int

    def selection_probability_vector(self, features: Sequence[float]) -> float:
        scaled = self.scaler.transform((tuple(float(v) for v in features),))[0]
        proba = self.estimator.predict_proba((scaled,))[0]
        classes = list(self.estimator.classes_)
        if True in classes:
            return float(proba[classes.index(True)])
        if 1 in classes:
            return float(proba[classes.index(1)])
        raise ValueError("fitted classifier has no positive class")


@dataclass(frozen=True)
class BoundClassifier:
    """P03 classifier bound to one visible state/context for probability lookup."""

    fitted: FittedModel
    by_key: Mapping[tuple[str, int], tuple[float, ...]]

    def selection_probability(self, job: s.Job, start_slot: int) -> float:
        features = self.by_key.get((job.job_id, start_slot))
        if features is None:
            return 0.0
        return self.fitted.selection_probability_vector(features)


def bind_classifier(
    fitted: FittedModel,
    state: s.VisibleState,
    context: s.Context,
    *,
    decision_time_utc: datetime,
) -> BoundClassifier:
    """Build a P03 classifier for one decision from a fitted model."""
    rows = candidate_features(state, context, decision_time_utc=decision_time_utc)
    return BoundClassifier(
        fitted=fitted,
        by_key={(row.job_id, row.start_slot): row.values() for row in rows},
    )


def fit_model(spec: ModelSpec, rows: Sequence[LabeledRow], *, seed: int) -> FittedModel:
    """Fit scaler and classifier on training rows; refuse empty-class weights."""
    matrix, labels = matrix_and_labels(rows)
    weights = balanced_class_weights(labels)
    scaler = TrainOnlyScaler.fit(matrix)
    scaled = scaler.transform(matrix)
    sample_weight = tuple(weights[1] if label else weights[0] for label in labels)
    if spec.system == "decision_tree_c":
        estimator = DecisionTreeClassifier(max_depth=spec.max_depth, random_state=seed)
    else:
        estimator = RandomForestClassifier(
            n_estimators=spec.n_estimators,
            max_depth=spec.max_depth,
            random_state=seed,
        )
    estimator.fit(scaled, labels, sample_weight=sample_weight)
    positives = sum(1 for label in labels if label)
    return FittedModel(
        spec=spec,
        scaler=scaler,
        estimator=estimator,
        seed=seed,
        class_weights=weights,
        n_rows=len(labels),
        n_positives=positives,
        n_negatives=len(labels) - positives,
    )


def artifact_bytes(fitted: FittedModel) -> bytes:
    """Serialize a fitted model for hashing and reload."""
    buffer = io.BytesIO()
    joblib.dump(
        {
            "schema": ARTIFACT_SCHEMA,
            "feature_names": FEATURE_NAMES,
            "spec": {
                "system": fitted.spec.system,
                "max_depth": fitted.spec.max_depth,
                "n_estimators": fitted.spec.n_estimators,
            },
            "scaler": {"means": fitted.scaler.means, "scales": fitted.scaler.scales},
            "estimator": fitted.estimator,
            "seed": fitted.seed,
            "class_weights": fitted.class_weights,
            "n_rows": fitted.n_rows,
            "n_positives": fitted.n_positives,
            "n_negatives": fitted.n_negatives,
        },
        buffer,
    )
    return buffer.getvalue()


def artifact_sha256(fitted: FittedModel) -> str:
    return sha256(artifact_bytes(fitted)).hexdigest()


def save_artifact(fitted: FittedModel, path: Path, *, manifest: Mapping[str, Any]) -> str:
    """Write ignored binary under path and a JSON manifest beside it; return SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = artifact_bytes(fitted)
    digest = sha256(payload).hexdigest()
    path.write_bytes(payload)
    record = {
        "schema": ARTIFACT_SCHEMA,
        "artifact_sha256": digest,
        "feature_names": list(FEATURE_NAMES),
        "system": fitted.spec.system,
        "max_depth": fitted.spec.max_depth,
        "n_estimators": fitted.spec.n_estimators,
        "seed": fitted.seed,
        "class_weights": list(fitted.class_weights),
        "n_rows": fitted.n_rows,
        "n_positives": fitted.n_positives,
        "n_negatives": fitted.n_negatives,
        **dict(manifest),
    }
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return digest


def load_artifact(path: Path) -> FittedModel:
    """Reload a frozen artifact and check feature order."""
    payload = joblib.load(io.BytesIO(path.read_bytes()))
    if payload.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError("unsupported P04 artifact schema")
    if tuple(payload["feature_names"]) != FEATURE_NAMES:
        raise ValueError("artifact feature order does not match FEATURE_NAMES")
    spec = ModelSpec(
        payload["spec"]["system"],
        payload["spec"]["max_depth"],
        payload["spec"]["n_estimators"],
    )
    scaler = TrainOnlyScaler(
        means=tuple(payload["scaler"]["means"]),
        scales=tuple(payload["scaler"]["scales"]),
    )
    return FittedModel(
        spec=spec,
        scaler=scaler,
        estimator=payload["estimator"],
        seed=int(payload["seed"]),
        class_weights=tuple(payload["class_weights"]),
        n_rows=int(payload["n_rows"]),
        n_positives=int(payload["n_positives"]),
        n_negatives=int(payload["n_negatives"]),
    )


def classifier_for_factory(fitted: FittedModel, *, decision_origin_utc: datetime):
    """Return a TrainedPolicy-compatible classifier_for(state, context) factory."""

    def classifier_for(state: s.VisibleState, context: s.Context) -> BoundClassifier:
        decision_time = decision_origin_utc + timedelta(hours=state.current_slot)
        return bind_classifier(fitted, state, context, decision_time_utc=decision_time)

    return classifier_for
