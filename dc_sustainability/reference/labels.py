"""O02 certified development labels attached to Q07 feature rows.

This module is the missing training-data stage: it consumes the already-merged
visible-state collection (``training.collect``) and feature rows
(``training.features``), runs the O01 reference solver, and produces a deterministic,
auditable label for every feasible candidate.

A label is one of:

* ``True``  – the reference solver selected this candidate in a ``certified_optimal`` result.
* ``False`` – the candidate was feasible (has a Q07 feature row) but was not selected.
* ``None``  – the candidate cannot be labeled because the solver did not certify an optimal
  schedule (infeasible, unresolved, insufficient evidence). These rows are excluded from
  training data.

The label record carries enough provenance to reconstruct the decision: solver result id,
state hash, candidate key, and the solver status. This keeps the leakage boundary intact:
labels are computed from the *same* visible state that produced the feature rows, never
from held-out episodes or future arrivals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from dc_sustainability import schemas as s
from dc_sustainability.reference.solver import solve_visible
from dc_sustainability.training.collect import CollectedDecision
from dc_sustainability.training.features import FeatureRow, candidate_features


@dataclass(frozen=True)
class CandidateLabel:
    """One certified label for one feasible (job_id, start_slot) candidate."""

    episode_id: str
    slot: int
    state_version: int
    job_id: str
    start_slot: int
    label: Optional[bool]
    source_solver_result_id: str
    state_hash: str
    candidate_hash: str

    @property
    def candidate_key(self) -> tuple[str, int]:
        return (self.job_id, self.start_slot)

    def is_training_row(self) -> bool:
        """Return True only when the label is a definite positive or negative."""
        return self.label is not None


@dataclass(frozen=True)
class LabeledDecision:
    """One collected decision with certified labels attached to its feature rows."""

    collected: CollectedDecision
    solver_result: s.SolverResult
    labels: tuple[CandidateLabel, ...]

    @property
    def episode_id(self) -> str:
        return self.collected.episode_id

    @property
    def slot(self) -> int:
        return self.collected.slot

    def training_rows(self) -> tuple[tuple[CandidateLabel, FeatureRow], ...]:
        """Return (label, feature_row) pairs that are safe to use for training."""
        row_by_key = {(row.job_id, row.start_slot): row for row in self.collected.rows}
        return tuple(
            (label, row_by_key[label.candidate_key])
            for label in self.labels
            if label.is_training_row() and label.candidate_key in row_by_key
        )


def _candidate_hash(state_hash: str, job_id: str, start_slot: int) -> str:
    """Stable identifier for one candidate under one state."""
    from dc_sustainability.schemas import sha256_hex

    return sha256_hex(
        {
            "state_hash": state_hash,
            "job_id": job_id,
            "start_slot": start_slot,
        }
    )


def label_decision(
    collected: CollectedDecision,
    *,
    time_limit_s: float = 30.0,
    tolerance: float = 1e-6,
) -> LabeledDecision:
    """Run the O01 reference solver on one collected decision and attach labels."""
    result = solve_visible(
        collected.state,
        collected.context,
        decision_time_utc=collected.decision_time_utc,
        time_limit_s=time_limit_s,
        tolerance=tolerance,
    )
    state_hash = collected.context.content_hash
    labels: list[CandidateLabel] = []

    if result.status == "certified_optimal":
        selected = {(ps.job_id, ps.start_slot) for ps in (result.schedule or ())}
        for row in collected.rows:
            key = (row.job_id, row.start_slot)
            labels.append(
                CandidateLabel(
                    episode_id=collected.episode_id,
                    slot=collected.slot,
                    state_version=collected.state_version,
                    job_id=row.job_id,
                    start_slot=row.start_slot,
                    label=key in selected,
                    source_solver_result_id=result.solver_result_id,
                    state_hash=state_hash,
                    candidate_hash=_candidate_hash(state_hash, row.job_id, row.start_slot),
                )
            )
    else:
        # Infeasible, unresolved, or insufficient_evidence: every feasible candidate is
        # marked None so downstream training excludes the whole decision.
        for row in collected.rows:
            labels.append(
                CandidateLabel(
                    episode_id=collected.episode_id,
                    slot=collected.slot,
                    state_version=collected.state_version,
                    job_id=row.job_id,
                    start_slot=row.start_slot,
                    label=None,
                    source_solver_result_id=result.solver_result_id,
                    state_hash=state_hash,
                    candidate_hash=_candidate_hash(state_hash, row.job_id, row.start_slot),
                )
            )

    return LabeledDecision(
        collected=collected,
        solver_result=result,
        labels=tuple(labels),
    )


def label_episode(
    decisions: tuple[CollectedDecision, ...],
    *,
    time_limit_s: float = 30.0,
    tolerance: float = 1e-6,
) -> tuple[LabeledDecision, ...]:
    """Label every collected decision in an episode."""
    return tuple(
        label_decision(decision, time_limit_s=time_limit_s, tolerance=tolerance)
        for decision in decisions
    )


def labels_from_solver_result(
    state: s.VisibleState,
    context: s.Context,
    result: s.SolverResult,
    *,
    decision_time_utc: datetime,
) -> tuple[CandidateLabel, ...]:
    """Attach labels to the Q07 feature rows of a state using an existing SolverResult.

    This is useful for replay/audit: the solver result may have been cached or produced by
    a different backend, but the label semantics stay identical.
    """
    rows = candidate_features(state, context, decision_time_utc=decision_time_utc)
    state_hash = context.content_hash
    labels: list[CandidateLabel] = []
    if result.status == "certified_optimal":
        selected = {(ps.job_id, ps.start_slot) for ps in (result.schedule or ())}
        for row in rows:
            key = (row.job_id, row.start_slot)
            labels.append(
                CandidateLabel(
                    episode_id=state.episode_id,
                    slot=state.current_slot,
                    state_version=state.state_version,
                    job_id=row.job_id,
                    start_slot=row.start_slot,
                    label=key in selected,
                    source_solver_result_id=result.solver_result_id,
                    state_hash=state_hash,
                    candidate_hash=_candidate_hash(state_hash, row.job_id, row.start_slot),
                )
            )
    else:
        for row in rows:
            labels.append(
                CandidateLabel(
                    episode_id=state.episode_id,
                    slot=state.current_slot,
                    state_version=state.state_version,
                    job_id=row.job_id,
                    start_slot=row.start_slot,
                    label=None,
                    source_solver_result_id=result.solver_result_id,
                    state_hash=state_hash,
                    candidate_hash=_candidate_hash(state_hash, row.job_id, row.start_slot),
                )
            )
    return tuple(labels)
