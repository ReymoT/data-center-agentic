"""Assemble D04 materialization + O02 labels into a P04 selection run."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from dc_sustainability import schemas as s
from dc_sustainability.data import materialize_development as materialize
from dc_sustainability.reference.labels import label_episode
from dc_sustainability.training.collect import collect_decisions
from dc_sustainability.training.dataset import LabeledRow, rows_from_labeled_decisions
from dc_sustainability.training.select import SelectionResult, select_and_refit
from dc_sustainability.training.train import save_artifact


def _empty_approve(state: s.VisibleState, _context: s.Context) -> s.ApprovedActions:
    return s.ApprovedActions(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        plan_hash="a" * 64,
        check_id="CHK-P04-COLLECT",
        starts=(),
    )


@dataclass(frozen=True)
class LabeledCorpus:
    """Development episodes with definite O02 training rows."""

    episodes: tuple[s.PrivateEpisode, ...]
    fold_of_episode: Mapping[str, int]
    rows: tuple[LabeledRow, ...]
    decision_origin_by_episode: Mapping[str, datetime]


def build_labeled_corpus(
    source: Path,
    *,
    label_time_limit_s: float = 5.0,
    approve: Callable[[s.VisibleState, s.Context], s.ApprovedActions] = _empty_approve,
) -> LabeledCorpus:
    """Materialize the published allocation, collect features, and attach O02 labels."""
    manifest, fold_of_episode = materialize.allocation()
    corpus = materialize.episodes(source)
    origins: dict[str, datetime] = {}
    labeled_rows: list[LabeledRow] = []
    for episode in corpus:
        origin = episode.realized_carbon[0].observed_at_utc
        origins[episode.episode_id] = origin
        forecasts = materialize.persistence_forecasts(source, episode.episode_id)
        decisions = collect_decisions(
            episode,
            decision_time_utc=lambda slot, start=origin: start + timedelta(hours=slot),
            approve=approve,
            forecasts_by_slot=forecasts,
        )
        # Label decision slots that produced candidates; skip empty completion drain.
        candidate_decisions = tuple(decision for decision in decisions if decision.rows)
        if not candidate_decisions:
            continue
        labeled = label_episode(candidate_decisions, time_limit_s=label_time_limit_s)
        labeled_rows.extend(rows_from_labeled_decisions(labeled))
    if not labeled_rows:
        raise ValueError("O02 produced no definite training rows on the development corpus")
    return LabeledCorpus(
        episodes=corpus,
        fold_of_episode=fold_of_episode,
        rows=tuple(labeled_rows),
        decision_origin_by_episode=origins,
    )


def run_selection(
    corpus: LabeledCorpus,
    *,
    seed: int,
    source: Path | None = None,
) -> SelectionResult:
    """Select C/D by blocked-fold rollouts and refit on all eligible rows."""
    episodes = {episode.episode_id: episode for episode in corpus.episodes}

    def forecasts_for(episode_id: str):
        if source is None:
            return None
        return materialize.persistence_forecasts(source, episode_id)

    return select_and_refit(
        corpus.rows,
        corpus.fold_of_episode,
        episodes,
        seed=seed,
        decision_origin_by_episode=corpus.decision_origin_by_episode,
        forecasts_for=forecasts_for if source is not None else None,
    )


def freeze_selection(
    selection: SelectionResult,
    output_dir: Path,
    *,
    extra_manifest: Mapping[str, object] | None = None,
) -> dict[str, str]:
    """Write C/D artifacts under output_dir and return system -> sha256."""
    output_dir.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}
    shared = {
        "seed": selection.seed,
        "fold_of_episode": dict(selection.fold_of_episode),
        "selected": {
            system: {
                "system": spec.system,
                "max_depth": spec.max_depth,
                "n_estimators": spec.n_estimators,
                "key": spec.key,
            }
            for system, spec in selection.selected.items()
        },
        "fold_results": [
            {
                "fold": result.fold,
                "spec": result.spec.key,
                "completed": result.metrics.completed,
                "deadline_misses": result.metrics.deadline_misses,
                "emissions_kg": result.metrics.emissions_kg,
            }
            for result in selection.fold_results
        ],
        **dict(extra_manifest or {}),
    }
    for system, fitted in selection.refit.items():
        path = output_dir / f"{system}.joblib"
        digests[system] = save_artifact(fitted, path, manifest=shared)
    (output_dir / "selection.json").write_text(
        json.dumps({"artifacts": digests, **shared}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return digests
