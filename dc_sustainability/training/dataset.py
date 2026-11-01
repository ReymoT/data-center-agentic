"""Labeled training rows from O02-certified visible-state decisions."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from dc_sustainability.reference.labels import LabeledDecision
from dc_sustainability.training.features import FEATURE_NAMES


@dataclass(frozen=True)
class LabeledRow:
    """One definite training example bound to a development episode."""

    episode_id: str
    slot: int
    job_id: str
    start_slot: int
    features: tuple[float, ...]
    label: bool

    def __post_init__(self) -> None:
        if len(self.features) != len(FEATURE_NAMES):
            raise ValueError("features must match FEATURE_NAMES width")


def rows_from_labeled_decisions(decisions: Iterable[LabeledDecision]) -> tuple[LabeledRow, ...]:
    """Keep only certified True/False labels; drop unresolved None labels."""
    rows: list[LabeledRow] = []
    for decision in decisions:
        for label, feature_row in decision.training_rows():
            if label.label is None:
                continue
            rows.append(
                LabeledRow(
                    episode_id=decision.episode_id,
                    slot=decision.slot,
                    job_id=feature_row.job_id,
                    start_slot=feature_row.start_slot,
                    features=feature_row.values(),
                    label=bool(label.label),
                )
            )
    return tuple(rows)


def matrix_and_labels(
    rows: Sequence[LabeledRow],
) -> tuple[tuple[tuple[float, ...], ...], tuple[bool, ...]]:
    """Split labeled rows into a feature matrix and label vector."""
    if not rows:
        raise ValueError("training requires at least one labeled row")
    return tuple(row.features for row in rows), tuple(row.label for row in rows)


def rows_for_episodes(
    rows: Sequence[LabeledRow], episode_ids: Iterable[str]
) -> tuple[LabeledRow, ...]:
    allowed = frozenset(episode_ids)
    return tuple(row for row in rows if row.episode_id in allowed)
