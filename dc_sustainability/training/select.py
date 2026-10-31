"""Blocked-fold selection by development rollout metrics, then full refit."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import claims
from dc_sustainability.simulator import SchedulingSimulator
from dc_sustainability.training.dataset import LabeledRow, rows_for_episodes
from dc_sustainability.training.folds import FoldSplit, blocked_fold_splits
from dc_sustainability.training.schedule import schedule_from_probabilities
from dc_sustainability.training.train import (
    FittedModel,
    ModelSpec,
    bind_classifier,
    fit_model,
    grid_specs,
)
from dc_sustainability.verification.checker import check_schedule


@dataclass(frozen=True)
class RolloutMetrics:
    """Lexicographic selection key: more completed, fewer misses, lower emissions."""

    completed: int
    deadline_misses: int
    emissions_kg: float

    def key(self) -> tuple[int, int, float]:
        return (-self.completed, self.deadline_misses, self.emissions_kg)


@dataclass(frozen=True)
class FoldConfigResult:
    fold: int
    spec: ModelSpec
    metrics: RolloutMetrics
    fitted: FittedModel


@dataclass(frozen=True)
class SelectionResult:
    """Per-system winners across folds, then models refit on all eligible rows."""

    fold_of_episode: Mapping[str, int]
    fold_results: tuple[FoldConfigResult, ...]
    selected: Mapping[str, ModelSpec]
    refit: Mapping[str, FittedModel]
    seed: int


def _empty_approve(state: s.VisibleState) -> s.ApprovedActions:
    return s.ApprovedActions(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        plan_hash="a" * 64,
        check_id="CHK-P04-EMPTY",
        starts=(),
    )


def _current_plan(output: s.PolicyOutput, state: s.VisibleState) -> s.Plan:
    current = state.current_slot
    starts = tuple(start for start in output.plan.starts if start.start_slot == current)
    started = {start.job_id for start in starts}
    abstentions = tuple(
        s.Abstention(job_id=job.job_id, reason="other")
        for job in state.waiting_jobs
        if job.arrival_slot <= current and job.job_id not in started
    )
    return s.Plan(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        starts=starts,
        abstentions=abstentions,
        status="proposed",
    )


def rollout_metrics(
    episode: s.PrivateEpisode,
    fitted: FittedModel,
    *,
    decision_origin_utc: datetime,
    forecasts_by_slot: Mapping[int, tuple[s.CarbonForecast, ...]] | None = None,
    system: str | None = None,
) -> RolloutMetrics:
    """Execute one development episode under the fitted classifier and score it."""
    system_id = system or fitted.spec.system
    simulator = SchedulingSimulator(allow_completion_starts=False)
    simulator.reset(episode, forecasts_by_slot=forecasts_by_slot)
    executed: dict[str, int] = {}
    for _ in range(30):
        state = simulator.state()
        context = s.Context.build(state, episode.snapshot, representation="flat")
        if state.current_slot >= 24 or not state.waiting_jobs:
            simulator.step(_empty_approve(state))
            continue
        decision_time = decision_origin_utc + timedelta(hours=state.current_slot)
        classifier = bind_classifier(fitted, state, context, decision_time_utc=decision_time)
        output = schedule_from_probabilities(
            state,
            context,
            classifier,
            system=system_id,  # type: ignore[arg-type]
        )
        plan = _current_plan(output, state)
        check = check_schedule(plan, state, episode.snapshot)
        if check.status != "pass":
            simulator.step(_empty_approve(state))
            continue
        action = s.ApprovedActions.from_checked_plan(plan, check, state.current_slot)
        for start in action.starts:
            executed[start.job_id] = start.start_slot
        simulator.step(action)
    result = simulator.result(run_id="p04-rollout", system=system_id)
    carbon = claims.carbon_series(episode.realized_carbon)
    jobs = {private.job.job_id: private.job for private in episode.jobs}
    completed_starts = {
        job_id: executed[job_id] for job_id in result.completed_job_ids if job_id in executed
    }
    try:
        emissions = claims.schedule_emissions_kg(
            completed_starts, jobs, episode.snapshot.site, carbon
        )
    except claims.CarbonUnavailable:
        emissions = float("inf")
    return RolloutMetrics(
        completed=len(result.completed_job_ids),
        deadline_misses=len(result.deadline_missed_job_ids),
        emissions_kg=float(emissions),
    )


def _sum_metrics(parts: Sequence[RolloutMetrics]) -> RolloutMetrics:
    return RolloutMetrics(
        completed=sum(part.completed for part in parts),
        deadline_misses=sum(part.deadline_misses for part in parts),
        emissions_kg=sum(part.emissions_kg for part in parts),
    )


def select_and_refit(
    rows: Sequence[LabeledRow],
    fold_of_episode: Mapping[str, int],
    episodes: Mapping[str, s.PrivateEpisode],
    *,
    seed: int,
    decision_origin_by_episode: Mapping[str, datetime],
    forecasts_for: Callable[[str], Mapping[int, tuple[s.CarbonForecast, ...]] | None] | None = None,
    specs: Sequence[ModelSpec] | None = None,
) -> SelectionResult:
    """Blocked-fold select by rollout, then refit winners on all eligible rows."""
    splits = blocked_fold_splits(fold_of_episode)
    candidates = tuple(specs) if specs is not None else grid_specs()
    fold_results: list[FoldConfigResult] = []
    best_by_system: dict[str, tuple[tuple[int, int, float], ModelSpec]] = {}

    for split in splits:
        train_rows = rows_for_episodes(rows, split.train_episode_ids)
        eval_ids = sorted(split.eval_episode_ids)
        for spec in candidates:
            try:
                fitted = fit_model(spec, train_rows, seed=seed)
            except ValueError:
                continue
            metrics = _sum_metrics(
                tuple(
                    rollout_metrics(
                        episodes[episode_id],
                        fitted,
                        decision_origin_utc=decision_origin_by_episode[episode_id],
                        forecasts_by_slot=None
                        if forecasts_for is None
                        else forecasts_for(episode_id),
                    )
                    for episode_id in eval_ids
                    if episode_id in episodes
                )
            )
            fold_results.append(
                FoldConfigResult(fold=split.fold, spec=spec, metrics=metrics, fitted=fitted)
            )
            key = metrics.key()
            current = best_by_system.get(spec.system)
            if (
                current is None
                or key < current[0]
                or (key == current[0] and spec.key < current[1].key)
            ):
                best_by_system[spec.system] = (key, spec)

    if set(best_by_system) != {"decision_tree_c", "random_forest_d"}:
        raise ValueError("selection requires winners for both decision_tree_c and random_forest_d")
    selected = {system: winner[1] for system, winner in best_by_system.items()}
    refit = {system: fit_model(spec, rows, seed=seed) for system, spec in selected.items()}
    return SelectionResult(
        fold_of_episode=dict(fold_of_episode),
        fold_results=tuple(fold_results),
        selected=selected,
        refit=refit,
        seed=seed,
    )


def fold_splits(fold_of_episode: Mapping[str, int]) -> tuple[FoldSplit, ...]:
    return blocked_fold_splits(fold_of_episode)
