"""Q07 candidate precision, recall, and F1.

Rates are properties of confusion counts. An undefined denominator is None.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

from dc_sustainability.training.dataset import LabeledRow
from dc_sustainability.training.features import FEATURE_NAMES
from dc_sustainability.training.train import (
    ARTIFACT_SCHEMA,
    DEVELOPMENT_SEED,
    FittedModel,
    ModelSpec,
    SystemKind,
)

POSITIVE_THRESHOLD = 0.5

CALLER_ROWS_NOTE = (
    "Scores describe the supplied rows only. "
    "They are not published development-fold precision, recall, or F1."
)

_UNPUBLISHED_METRICS = (
    "Validation-fold precision, recall, and F1 are unpublished because "
    "the fifteen fold models were not serialized and the frozen joblib "
    "is the full-data refit."
)

# Transcribed from docs/handoffs/P04_REAL_DEVELOPMENT_ARTIFACTS.md.
_DEFINITE_POSITIVE = 1411
_DEFINITE_NEGATIVE = 4635
_FOLD_TRAINING: tuple[tuple[int, int], ...] = (
    (840, 2765),
    (1009, 3363),
    (973, 3142),
)
_TOTAL_TIME_SECONDS = 101.375
_CONTENT_RECEIPT = "d04-development-content-112-v2"
_CUSTODY_LABEL = "P04_Private_2026-11-02"
_SELECTED: tuple[tuple[SystemKind, int, int | None], ...] = (
    ("decision_tree_c", 8, None),
    ("random_forest_d", 10, 100),
)


@dataclass(frozen=True)
class CandidateScore:
    """Confusion cells for one scoring call. Support and rates are derived."""

    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    excluded: int

    def __post_init__(self) -> None:
        for name in (
            "true_positive",
            "false_positive",
            "true_negative",
            "false_negative",
            "excluded",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative int")

    @property
    def basis(self) -> str:
        return "caller_rows"

    @property
    def support_positive(self) -> int:
        return self.true_positive + self.false_negative

    @property
    def support_negative(self) -> int:
        return self.true_negative + self.false_positive

    @property
    def predicted_positive(self) -> int:
        return self.true_positive + self.false_positive

    @property
    def predicted_negative(self) -> int:
        return self.true_negative + self.false_negative

    @property
    def scored(self) -> int:
        return self.support_positive + self.support_negative

    @property
    def precision(self) -> float | None:
        """tp / predicted positives. None when no row was predicted positive."""
        if self.predicted_positive == 0:
            return None
        return self.true_positive / self.predicted_positive

    @property
    def recall(self) -> float | None:
        """tp / actual positives. None when support_positive is 0; else 0.0 when no positives are predicted."""
        if self.support_positive == 0:
            return None
        return self.true_positive / self.support_positive

    @property
    def f1(self) -> float | None:
        """Harmonic mean when both rates exist. None when either rate is None. Both defined zeros yield 0.0."""
        precision = self.precision
        recall = self.recall
        if precision is None or recall is None:
            return None
        if precision + recall == 0.0:
            return 0.0
        return 2.0 * precision * recall / (precision + recall)


def score_candidates(
    labels: Sequence[bool | None],
    probabilities: Sequence[float | None],
) -> CandidateScore:
    """Score aligned pairs at POSITIVE_THRESHOLD.

    A scored pair is a bool label and a probability in [0, 1]. An excluded
    pair is (None, None) and increments excluded. Any other missing side,
    a non-bool label, a NaN, or a probability outside [0, 1] raises
    ValueError. Equal-length empty input returns all-zero cells and None rates.
    """
    if len(labels) != len(probabilities):
        raise ValueError("labels and probabilities must have the same length")
    true_positive = 0
    false_positive = 0
    true_negative = 0
    false_negative = 0
    excluded = 0
    for label, probability in zip(labels, probabilities, strict=True):
        if label is None and probability is None:
            excluded += 1
            continue
        if label is None or probability is None:
            raise ValueError("a scored row needs both a label and a probability")
        # bool is an int, so isinstance(probability, int) would accept True.
        if (
            type(label) is not bool
            or isinstance(probability, bool)
            or not isinstance(probability, (int, float))
        ):
            raise ValueError("label must be bool and probability must be a real number")
        value = float(probability)
        if value != value or value < 0.0 or value > 1.0:
            raise ValueError("probability must be between 0 and 1")
        predicted = value >= POSITIVE_THRESHOLD
        if label and predicted:
            true_positive += 1
        elif label:
            false_negative += 1
        elif predicted:
            false_positive += 1
        else:
            true_negative += 1
    return CandidateScore(
        true_positive,
        false_positive,
        true_negative,
        false_negative,
        excluded,
    )


def score_fitted_rows(
    fitted: FittedModel,
    rows: Sequence[LabeledRow],
    *,
    excluded: int = 0,
) -> CandidateScore:
    """Probability per definite row, then the same Q07 function.

    `excluded` is the count of candidate rows that never became a LabeledRow.
    They are prefixed as (None, None) pairs. Negative excluded raises.
    Probabilities come from FittedModel.selection_probability_vector.
    """
    if type(excluded) is not int or excluded < 0:
        raise ValueError("excluded must be a nonnegative int")
    labels: list[bool | None] = [None] * excluded
    probabilities: list[float | None] = [None] * excluded
    labels.extend(row.label for row in rows)
    probabilities.extend(fitted.selection_probability_vector(row.features) for row in rows)
    return score_candidates(labels, probabilities)


def sum_candidate_scores(scores: Sequence[CandidateScore]) -> CandidateScore:
    """Add cells and excluded counts. Rates come back from the sums."""
    if not scores:
        return CandidateScore(0, 0, 0, 0, 0)
    return CandidateScore(
        true_positive=sum(score.true_positive for score in scores),
        false_positive=sum(score.false_positive for score in scores),
        true_negative=sum(score.true_negative for score in scores),
        false_negative=sum(score.false_negative for score in scores),
        excluded=sum(score.excluded for score in scores),
    )


@dataclass(frozen=True)
class FoldSupport:
    """One blocked development fold."""

    fold: int
    training_positive: int
    training_negative: int
    held_out_positive: int
    held_out_negative: int


@dataclass(frozen=True)
class PublishedSelection:
    """One selected full-data refit."""

    system: SystemKind
    max_depth: int
    n_estimators: int | None
    artifact_sha256: str


@dataclass(frozen=True)
class DevelopmentCardFacts:
    """Public card payload. Held-out fold counts are definite totals minus published training counts."""

    definite_positive: int
    definite_negative: int
    folds: tuple[FoldSupport, ...]
    selection: tuple[PublishedSelection, ...]
    seed: int
    total_time_seconds: float
    content_receipt: str
    custody_label: str
    carbon_sha256: str
    feature_names: tuple[str, ...]
    artifact_schema: str
    threshold: float


def development_card_facts() -> DevelopmentCardFacts:
    """Assemble the public card from the handoff count table plus existing constants.

    Each selection must construct a legal ModelSpec. Every PUBLISHED_DEVELOPMENT_SHA256
    key must appear once.
    """
    from dc_sustainability.data.carbon_source import SHA256 as carbon_sha256
    from dc_sustainability.policies.learned import PUBLISHED_DEVELOPMENT_SHA256

    published = tuple(PUBLISHED_DEVELOPMENT_SHA256)
    selected_systems = tuple(system for system, _depth, _trees in _SELECTED)
    if selected_systems != published or len(set(selected_systems)) != len(published):
        raise ValueError("selection must list each published development system once")
    selection: list[PublishedSelection] = []
    for system, depth, trees in _SELECTED:
        spec = ModelSpec(system, depth, n_estimators=trees)
        selection.append(
            PublishedSelection(
                system=spec.system,
                max_depth=spec.max_depth,
                n_estimators=spec.n_estimators,
                artifact_sha256=PUBLISHED_DEVELOPMENT_SHA256[spec.system],
            )
        )
    folds: list[FoldSupport] = []
    for fold_id, (training_positive, training_negative) in enumerate(_FOLD_TRAINING):
        held_out_positive = _DEFINITE_POSITIVE - training_positive
        held_out_negative = _DEFINITE_NEGATIVE - training_negative
        if held_out_positive < 0 or held_out_negative < 0:
            raise ValueError("training support exceeds the definite total")
        folds.append(
            FoldSupport(
                fold=fold_id,
                training_positive=training_positive,
                training_negative=training_negative,
                held_out_positive=held_out_positive,
                held_out_negative=held_out_negative,
            )
        )
    if sum(fold.held_out_positive for fold in folds) != _DEFINITE_POSITIVE:
        raise ValueError("held-out positives must sum to the definite total")
    if sum(fold.held_out_negative for fold in folds) != _DEFINITE_NEGATIVE:
        raise ValueError("held-out negatives must sum to the definite total")
    return DevelopmentCardFacts(
        definite_positive=_DEFINITE_POSITIVE,
        definite_negative=_DEFINITE_NEGATIVE,
        folds=tuple(folds),
        selection=tuple(selection),
        seed=DEVELOPMENT_SEED,
        total_time_seconds=_TOTAL_TIME_SECONDS,
        content_receipt=_CONTENT_RECEIPT,
        custody_label=_CUSTODY_LABEL,
        carbon_sha256=carbon_sha256,
        feature_names=FEATURE_NAMES,
        artifact_schema=ARTIFACT_SCHEMA,
        threshold=POSITIVE_THRESHOLD,
    )


def render_development_card() -> str:
    """Markdown for models/development_candidate_card.md."""
    facts = development_card_facts()
    definite = facts.definite_positive + facts.definite_negative
    support_rows = [
        "| Fold | Training positive | Training negative | Held-out positive | Held-out negative |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for fold in facts.folds:
        support_rows.append(
            f"| {fold.fold} | {fold.training_positive} | {fold.training_negative} "
            f"| {fold.held_out_positive} | {fold.held_out_negative} |"
        )
    selection_rows = [
        "| System | max_depth | n_estimators | Artifact SHA-256 |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in facts.selection:
        estimators = "none" if row.n_estimators is None else str(row.n_estimators)
        selection_rows.append(
            f"| {row.system} | {row.max_depth} | {estimators} | {row.artifact_sha256} |"
        )
    feature_lines = "\n".join(f"- `{name}`" for name in facts.feature_names)
    lines = [
        "# Development candidate card",
        "",
        "Public facts for the development decision-tree and random-forest refits. "
        "Counts, hashes, and the recorded time come from "
        "[Real development C/D artifacts and receiving]"
        "(docs/handoffs/P04_REAL_DEVELOPMENT_ARTIFACTS.md). "
        "The positive rule comes from "
        "[Q07 training decision](docs/decisions/Q07_TRAINING_OCT27.md).",
        "",
        "## Support",
        "",
        f"There are {definite} definite rows. "
        f"{facts.definite_positive} are positive and {facts.definite_negative} are negative.",
        "",
        "Held-out support subtracts each fold's published training count from those "
        "definite totals. Those counts are not a measured confusion table.",
        "",
        "\n".join(support_rows),
        "",
        "## Selection",
        "",
        "\n".join(selection_rows),
        "",
        f"The development script seed is {facts.seed}. "
        "Total materialization, labeling, selection, refit, and reload time is "
        f"{facts.total_time_seconds} seconds.",
        "",
        "## Features and custody",
        "",
        f"Artifact schema `{facts.artifact_schema}`. Positive threshold {facts.threshold}.",
        "",
        "Feature names, in model order:",
        "",
        feature_lines,
        "",
        f"Carbon source SHA-256 `{facts.carbon_sha256}`.",
        "",
        f"Content receipt `{facts.content_receipt}`.",
        "",
        f"Manager-local custody label `{facts.custody_label}`. "
        "The label names storage outside this repository.",
        "",
        "## Candidate metrics",
        "",
        _UNPUBLISHED_METRICS,
        "",
    ]
    return "\n".join(lines)


def development_card_json() -> str:
    """Serialize the public card facts for a machine reader."""
    facts = development_card_facts()
    payload = {
        "artifact_schema": facts.artifact_schema,
        "binary_in_checkout": False,
        "carbon_sha256": facts.carbon_sha256,
        "content_receipt": facts.content_receipt,
        "custody_label": facts.custody_label,
        "definite_negative": facts.definite_negative,
        "definite_positive": facts.definite_positive,
        "feature_names": list(facts.feature_names),
        "folds": [
            {
                "fold": fold.fold,
                "held_out_negative": fold.held_out_negative,
                "held_out_positive": fold.held_out_positive,
                "training_negative": fold.training_negative,
                "training_positive": fold.training_positive,
            }
            for fold in facts.folds
        ],
        "measured_state": "public_only",
        "record_type": "p06-development-card",
        "schema_version": "1",
        "seed": facts.seed,
        "selection": [
            {
                "artifact_sha256": row.artifact_sha256,
                "max_depth": row.max_depth,
                "measured": None,
                "n_estimators": row.n_estimators,
                "system": row.system,
            }
            for row in facts.selection
        ],
        "threshold": facts.threshold,
        "total_time_seconds": facts.total_time_seconds,
        "unpublished_reason": _UNPUBLISHED_METRICS,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
