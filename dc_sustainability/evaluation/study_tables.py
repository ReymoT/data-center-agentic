"""E06 study tables: saved runs scored by E03, then paired and summarized.

This joins ``run_metrics``, ``paired``, ``comparison`` and ``forecast_ties`` under the
analysis decisions recorded on November 4: the broad ``unsafe_rate`` is primary with the
narrower measure beside it, the 24 core episodes are the main comparison, and withheld
forecast episodes are reported apart. Those decisions await affected-owner confirmation.

Nothing is dropped quietly. A planned run that is absent stays missing in the paired
counts, and a saved run that cannot be scored is listed with its reason. Every episode must
share one split, and the report states it, so development tables cannot pass as held-out
findings. Reading a table does not freeze the analysis or authorize a run.
"""

from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Literal

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import forecast_ties, paired
from dc_sustainability.evaluation.comparison import Run, compare_savings
from dc_sustainability.evaluation.replay import executed_starts, replay_episode
from dc_sustainability.evaluation.run_metrics import RunMetrics, run_metrics
from dc_sustainability.evaluation.validator import Protocol

Cohort = Literal["core", "withheld"]
COHORTS: tuple[Cohort, ...] = ("core", "withheld")
PHOENIX = timedelta(hours=-7)  # slot 0 is Phoenix midnight (no daylight saving)
RunKey = tuple[str, str, int | None]  # system, episode ID, trial


@dataclass(frozen=True)
class PlannedEpisode:
    """One planned episode and the forecasts its policies saw."""

    episode: s.PrivateEpisode
    date: str
    forecasts_by_slot: Mapping[int, tuple[s.CarbonForecast, ...]]

    @property
    def cohort(self) -> Cohort:
        return "withheld" if self.episode.forecast_visibility == "withheld" else "core"


def planned_episode(
    episode: s.PrivateEpisode,
    slot0_utc: datetime,
    forecasts_by_slot: Mapping[int, tuple[s.CarbonForecast, ...]],
) -> PlannedEpisode:
    return PlannedEpisode(episode, (slot0_utc + PHOENIX).date().isoformat(), forecasts_by_slot)


def _stage_rate(stage: str, field: str) -> Callable[[RunMetrics], float | None]:
    return lambda metrics: getattr(metrics.stages[stage], field)


METRICS: dict[str, Callable[[RunMetrics], float | None]] = {
    "decision_accuracy": lambda m: m.decision_accuracy,
    **{
        f"{name}_{stage}": _stage_rate(stage, name)
        for name in ("unsafe_rate", "unsafe_rate_without_omissions")
        for stage in ("initial", "repaired", "fallback", "final")
    },
    "repair_rate": lambda m: m.repair_rate,
    "fallback_rate": lambda m: m.fallback_rate,
    "completed_jobs": lambda m: m.completed_jobs,
    "missed_jobs": lambda m: m.missed_jobs,
    "unfinished_jobs": lambda m: m.unfinished_jobs,
    "completed_it_energy_kwh": lambda m: m.completed_it_energy_kwh,
    "completed_job_emissions_kg": lambda m: m.completed_job_emissions_kg,
    "model_calls": lambda m: m.cost.model_calls,
    "latency_ms": lambda m: m.cost.latency_ms,
    "prompt_tokens": lambda m: m.cost.prompt_tokens,
    "completion_tokens": lambda m: m.cost.completion_tokens,
}


# A raw emissions difference would compare runs that did different work. Paired emissions
# only come from the equal-work savings rows; the scenario summaries still describe them.
PAIRED_METRICS = tuple(name for name in METRICS if name != "completed_job_emissions_kg")


@dataclass(frozen=True)
class ScoredRuns:
    runs: Mapping[RunKey, RunMetrics]
    records: Mapping[RunKey, tuple[s.DecisionRecord, ...]]
    unscored: Mapping[RunKey, str]  # a saved run E03 refused, with the reason


def _split(planned: Mapping[str, PlannedEpisode]) -> str:
    splits = {item.episode.split for item in planned.values()}
    if len(splits) != 1:
        raise ValueError("a report covers one split; these episodes mix them")
    return splits.pop()


def score_runs(
    runs: Iterable[Iterable[s.DecisionRecord]],
    planned: Mapping[str, PlannedEpisode],
    protocol: Protocol,
) -> ScoredRuns:
    """Score each saved run; a run E03 refuses is listed, never silently dropped."""
    scored: dict[RunKey, RunMetrics] = {}
    kept: dict[RunKey, tuple[s.DecisionRecord, ...]] = {}
    unscored: dict[RunKey, str] = {}
    for run in runs:
        records = tuple(run)
        if not records:
            raise ValueError("a saved run has no decision records")
        first = records[0]
        key = (first.system, first.episode_id, first.trial)
        if key in kept or key in unscored:
            raise ValueError(f"more than one saved run for {key}")
        if first.episode_id not in planned:
            raise ValueError(f"{first.episode_id} is not a planned episode")
        try:
            scored[key] = run_metrics(planned[first.episode_id].episode, records, protocol)
            kept[key] = records
        except ValueError as error:
            unscored[key] = str(error)
    return ScoredRuns(scored, kept, unscored)


def _labels(planned: Mapping[str, PlannedEpisode], cohort: Cohort) -> dict[str, tuple[str, str]]:
    return {
        episode_id: (item.episode.scenario_id, item.date)
        for episode_id, item in planned.items()
        if item.cohort == cohort
    }


def observations(
    scored: ScoredRuns,
    planned: Mapping[str, PlannedEpisode],
    metric: str,
    cohort: Cohort,
) -> tuple[paired.Observation, ...]:
    """One metric's values for one cohort, ready for ``paired``."""
    read = METRICS[metric]
    labels = _labels(planned, cohort)
    return tuple(
        paired.Observation(system, episode_id, trial, *labels[episode_id], read(metrics))
        for (system, episode_id, trial), metrics in scored.runs.items()
        if episode_id in labels
    )


def _comparison_row(
    sample: paired.PairedSample, metric: str, cohort: Cohort, settings: paired.Resampling
) -> dict:
    return {
        "metric": metric,
        "cohort": cohort,
        "baseline": sample.baseline,
        "candidate": sample.candidate,
        "by_episode": asdict(paired.interval(sample, settings)),
        "by_date": asdict(paired.interval(sample, settings, by="date")),
        "excluded_by_reason": sample.excluded_by_reason,
    }


def paired_rows(
    scored: ScoredRuns,
    planned: Mapping[str, PlannedEpisode],
    baseline: str,
    candidate: str,
    trials: Mapping[str, tuple[int | None, ...]],
    settings: paired.Resampling,
) -> list[dict]:
    """Candidate minus baseline for every metric, core and withheld kept apart."""
    rows = []
    for cohort in COHORTS:
        labels = _labels(planned, cohort)
        if not labels:
            continue
        for metric in PAIRED_METRICS:
            sample = paired.paired_sample(
                observations(scored, planned, metric, cohort),
                baseline,
                candidate,
                trials,
                labels,
            )
            rows.append(_comparison_row(sample, metric, cohort, settings))
    return rows


def savings_rows(
    scored: ScoredRuns,
    planned: Mapping[str, PlannedEpisode],
    baseline: str,
    candidate: str,
    trials: Mapping[str, tuple[int | None, ...]],
    protocol: Protocol,
    settings: paired.Resampling,
) -> list[dict]:
    """Equal-work savings by cohort; positive means the candidate emitted less.

    Only systems with the same trials can be compared, because the rule for pairing a
    single classical run with three LLM trials has not been agreed.
    """
    if tuple(trials[baseline]) != tuple(trials[candidate]):
        raise ValueError("savings need matching trials; the unequal-trial rule is not agreed")

    def run(system, episode, trial, records):
        replay = replay_episode(episode, executed_starts(records, episode.episode_id), protocol)
        return Run(system, trial, replay)

    rows = []
    for cohort in COHORTS:
        labels = _labels(planned, cohort)
        if not labels:
            continue
        comparisons = []
        for episode_id in labels:
            episode = planned[episode_id].episode
            for trial in trials[candidate]:
                first = scored.records.get((baseline, episode_id, trial))
                second = scored.records.get((candidate, episode_id, trial))
                if first is not None and second is not None:
                    comparisons.append(
                        compare_savings(
                            run(baseline, episode, trial, first),
                            run(candidate, episode, trial, second),
                        )
                    )
        if not comparisons:
            rows.append(
                {
                    "metric": "savings_kg",
                    "cohort": cohort,
                    "baseline": baseline,
                    "candidate": candidate,
                    "by_episode": None,
                    "by_date": None,
                    "excluded_by_reason": {"run_missing": len(labels)},
                }
            )
            continue
        sample = paired.savings_sample(comparisons, labels, tuple(trials[candidate]))
        rows.append(_comparison_row(sample, "savings_kg", cohort, settings))
    return rows


def scenario_rows(
    scored: ScoredRuns,
    planned: Mapping[str, PlannedEpisode],
    trials: Mapping[str, tuple[int | None, ...]] | None = None,
) -> list[dict]:
    rows = []
    for cohort in COHORTS:
        for metric in METRICS:
            values = list(observations(scored, planned, metric, cohort))
            if trials is not None:
                present = {(o.system, o.episode_id, o.trial) for o in values}
                for episode_id, labels in _labels(planned, cohort).items():
                    for system, expected in trials.items():
                        for trial in expected:
                            if (system, episode_id, trial) not in present:
                                values.append(
                                    paired.Observation(system, episode_id, trial, *labels, None)
                                )
            for row in paired.scenario_summary(values):
                rows.append({"metric": metric, "cohort": cohort, **asdict(row)})
    return rows


def tie_rows(
    scored: ScoredRuns,
    planned: Mapping[str, PlannedEpisode],
    protocol: Protocol,
    system: str = "greedy_b",
) -> list[dict]:
    """Pooled forecast-tie counts from one system's runs, by cohort."""
    rows = []
    for cohort in COHORTS:
        decisions: list[forecast_ties.JobDecision] = []
        runs = 0
        for (run_system, episode_id, _), records in scored.records.items():
            item = planned[episode_id]
            if run_system != system or item.cohort != cohort:
                continue
            runs += 1
            replay = replay_episode(item.episode, executed_starts(records, episode_id), protocol)
            decisions += forecast_ties.job_decisions(replay, item.forecasts_by_slot, protocol)
        if runs:
            summary = forecast_ties.summarize(decisions)
            rows.append(
                {
                    "system": system,
                    "cohort": cohort,
                    "runs": runs,
                    **asdict(summary),
                    "comparable": summary.comparable,
                    "tie_rate": summary.tie_rate,
                }
            )
    return rows


def study_report(
    runs: Iterable[Iterable[s.DecisionRecord]],
    planned: Mapping[str, PlannedEpisode],
    trials: Mapping[str, tuple[int | None, ...]],
    protocol: Protocol,
    comparisons: Iterable[tuple[str, str]] = (("plain_llm", "agent"),),
    settings: paired.Resampling = paired.Resampling(),
) -> dict:
    """Every table for one set of saved runs, as plain JSON-ready data."""
    split = _split(planned)
    scored = score_runs(runs, planned, protocol)
    for system, episode_id, trial in (*scored.runs, *scored.unscored):
        if system not in trials or trial not in trials[system]:
            raise ValueError(f"unplanned system/trial: {(system, episode_id, trial)}")
    comparison_rows = []
    savings = []
    for baseline, candidate in comparisons:
        comparison_rows += paired_rows(scored, planned, baseline, candidate, trials, settings)
        if tuple(trials[baseline]) == tuple(trials[candidate]):
            savings += savings_rows(
                scored, planned, baseline, candidate, trials, protocol, settings
            )
        else:
            savings.append(
                {
                    "metric": "savings_kg",
                    "baseline": baseline,
                    "candidate": candidate,
                    "status": "blocked",
                    "reason": "unequal_trial_rule_not_agreed",
                    "by_episode": None,
                    "by_date": None,
                }
            )
    cohorts = Counter(item.cohort for item in planned.values())
    return {
        "split": split,
        "status": "not_a_frozen_result",
        "protocol": protocol.name,
        "resampling": asdict(settings),
        "planned_episodes": dict(sorted(cohorts.items())),
        "scored_runs": len(scored.runs),
        "unscored_runs": [
            {"system": key[0], "episode_id": key[1], "trial": key[2], "reason": reason}
            for key, reason in sorted(scored.unscored.items(), key=str)
        ],
        "comparisons": comparison_rows,
        "savings": savings,
        "scenario_summaries": scenario_rows(scored, planned, trials),
        "forecast_ties": tie_rows(scored, planned, protocol),
    }
