"""Blocked development folds and train-only preprocessing for Q07.

Fold membership is an injected map from Reimo's D04 artifacts. This module does
not invent episode lists, held-out assignments, or class weights for empty classes.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from math import sqrt

FOLD_COUNT = 3
_FOLD_IDS = frozenset(range(FOLD_COUNT))


@dataclass(frozen=True)
class FoldSplit:
    """One blocked fold: evaluate on ``fold``, fit only on the other development folds."""

    fold: int
    train_episode_ids: frozenset[str]
    eval_episode_ids: frozenset[str]


@dataclass(frozen=True)
class TrainOnlyScaler:
    """Per-feature mean and scale fitted on a training partition only."""

    means: tuple[float, ...]
    scales: tuple[float, ...]

    @classmethod
    def fit(cls, matrix: Sequence[Sequence[float]]) -> "TrainOnlyScaler":
        if not matrix:
            raise ValueError("training matrix must contain at least one row")
        width = len(matrix[0])
        if width == 0:
            raise ValueError("training matrix rows must contain at least one feature")
        if any(len(row) != width for row in matrix):
            raise ValueError("training matrix rows must share one feature width")
        count = len(matrix)
        means = []
        scales = []
        for index in range(width):
            values = [float(row[index]) for row in matrix]
            mean = sum(values) / count
            variance = sum((value - mean) ** 2 for value in values) / count
            scale = sqrt(variance)
            means.append(mean)
            scales.append(1.0 if scale == 0.0 else scale)
        return cls(means=tuple(means), scales=tuple(scales))

    def transform(self, matrix: Sequence[Sequence[float]]) -> tuple[tuple[float, ...], ...]:
        width = len(self.means)
        rows = []
        for row in matrix:
            if len(row) != width:
                raise ValueError("row width does not match the fitted scaler")
            rows.append(
                tuple(
                    (float(value) - mean) / scale
                    for value, mean, scale in zip(row, self.means, self.scales)
                )
            )
        return tuple(rows)


def blocked_fold_splits(fold_of_episode: Mapping[str, int]) -> tuple[FoldSplit, ...]:
    """Build the three development folds from an injected episode-to-fold map."""
    assignments = _validated_assignments(fold_of_episode)
    splits = []
    for fold in range(FOLD_COUNT):
        eval_ids = frozenset(
            episode_id for episode_id, value in assignments.items() if value == fold
        )
        train_ids = frozenset(
            episode_id for episode_id, value in assignments.items() if value != fold
        )
        splits.append(FoldSplit(fold=fold, train_episode_ids=train_ids, eval_episode_ids=eval_ids))
    return tuple(splits)


def refuse_held_out_episodes(
    fold_of_episode: Mapping[str, int],
    held_out_episode_ids: Collection[str],
) -> None:
    """Refuse any held-out episode that appears in the development fold map."""
    overlap = sorted(set(fold_of_episode) & set(held_out_episode_ids))
    if overlap:
        raise ValueError(f"held-out episodes cannot enter development folds: {overlap}")


def balanced_class_weights(labels: Sequence[bool | int]) -> tuple[float, float]:
    """Return (negative_weight, positive_weight) = n / (2 * class_count).

    Raises when either class is absent. Silence is not a license to invent a weight.
    """
    if not labels:
        raise ValueError("class weights require at least one training label")
    positives = sum(1 for label in labels if label)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        raise ValueError(
            "a training partition with zero examples for either class gets no invented class weight"
        )
    total = float(len(labels))
    return (total / (2.0 * negatives), total / (2.0 * positives))


def _validated_assignments(fold_of_episode: Mapping[str, int]) -> dict[str, int]:
    if not fold_of_episode:
        raise ValueError("fold map must assign at least one development episode")
    assignments: dict[str, int] = {}
    for episode_id, fold in fold_of_episode.items():
        if not isinstance(episode_id, str) or not episode_id:
            raise ValueError("fold map keys must be non-empty episode ids")
        if type(fold) is not int or fold not in _FOLD_IDS:
            raise ValueError(f"fold id must be one of {sorted(_FOLD_IDS)}")
        if episode_id in assignments:
            raise ValueError(f"episode appears more than once in the fold map: {episode_id}")
        assignments[episode_id] = fold
    missing = _FOLD_IDS - set(assignments.values())
    if missing:
        raise ValueError(
            f"fold map must use all three development folds; missing {sorted(missing)}"
        )
    return assignments
