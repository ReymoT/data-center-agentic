"""E03 paired statistics: episode-level differences with resampled intervals.

The episode is the unit. An LLM's trials are averaged inside their episode first, so
resampling keeps them together and three trials never count as three independent results.
An episode enters a paired sample only when every expected trial of both systems has a
value. Anything else is excluded and counted with its reason: nothing is filled in, and an
interval over too few units is None, never a width of zero.

Scenarios on one date share carbon and history, so resampling episodes can overstate
precision. ``interval(..., by="date")`` resamples whole dates as a sensitivity check; with
six dates it is coarse, and it qualifies the episode interval rather than replacing it.

These are descriptive summaries of saved values. Nothing here reads a run or a policy, and
the settings must be frozen before any held-out value is seen.
"""

import math
import random
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from dc_sustainability.evaluation.comparison import SavingsComparison

ExcludedReason = Literal[
    "run_missing",  # an expected trial has no observation
    "value_unavailable",  # the run exists but this metric has no value
    "comparison_blocked",  # E03 equal-work rule blocked a trial's savings
]


@dataclass(frozen=True)
class Resampling:
    """Proposed settings; frozen with the I02 manifest, never tuned on held-out results."""

    resamples: int = 10_000
    confidence: float = 0.95
    seed: int = 20261113

    def __post_init__(self):
        if type(self.resamples) is not int or self.resamples < 1:
            raise ValueError("resamples must be a positive integer")
        if not 0 < self.confidence < 1:
            raise ValueError("confidence must be between 0 and 1")
        if type(self.seed) is not int:
            raise ValueError("seed must be an integer")


@dataclass(frozen=True)
class Observation:
    """One metric value from one run; None means the metric is unavailable for that run."""

    system: str
    episode_id: str
    trial: int | None
    scenario: str
    date: str
    value: float | None

    def __post_init__(self):
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("an observation value must be finite or None")


@dataclass(frozen=True)
class EpisodeDifference:
    episode_id: str
    scenario: str
    date: str
    difference: float


@dataclass(frozen=True)
class PairedSample:
    baseline: str
    candidate: str
    differences: tuple[EpisodeDifference, ...]  # sorted by episode ID
    excluded: Mapping[str, ExcludedReason]  # episode ID -> first reason

    @property
    def excluded_by_reason(self) -> dict[str, int]:
        return dict(Counter(self.excluded.values()))


@dataclass(frozen=True)
class Interval:
    estimate: float | None  # mean episode difference; None with no episodes
    lower: float | None  # None with fewer than two resampling units
    upper: float | None
    episodes: int
    excluded: int
    units: int  # episodes, or dates when by="date"
    by: Literal["episode", "date"]
    confidence: float
    resamples: int


@dataclass(frozen=True)
class ScenarioRow:
    """Run-level description: an LLM's trials count as separate runs here, not in intervals."""

    system: str
    scenario: str
    runs: int
    missing: int
    mean: float | None
    std: float | None  # sample standard deviation; None with fewer than two values
    minimum: float | None
    maximum: float | None


def _index(observations: Iterable[Observation]) -> dict[tuple, Observation]:
    runs: dict[tuple, Observation] = {}
    labels: dict[str, tuple[str, str]] = {}
    for item in observations:
        key = (item.system, item.episode_id, item.trial)
        if key in runs:
            raise ValueError(f"more than one observation for {key}")
        runs[key] = item
        if labels.setdefault(item.episode_id, (item.scenario, item.date)) != (
            item.scenario,
            item.date,
        ):
            raise ValueError(f"{item.episode_id} has conflicting scenario or date labels")
    return runs


def _episode_mean(
    runs: Mapping[tuple, Observation], system: str, episode_id: str, trials: tuple
) -> float | ExcludedReason:
    found = [runs.get((system, episode_id, trial)) for trial in trials]
    if any(item is None for item in found):
        return "run_missing"
    if any(item.value is None for item in found):
        return "value_unavailable"
    return math.fsum(item.value for item in found) / len(found)


def paired_sample(
    observations: Iterable[Observation],
    baseline: str,
    candidate: str,
    trials: Mapping[str, tuple[int | None, ...]],
    labels: Mapping[str, tuple[str, str]],
) -> PairedSample:
    """Candidate minus baseline for each planned episode.

    ``trials`` and ``labels`` state what was planned: the expected trials of each system,
    and every episode's scenario and date. A run or episode that never happened is then
    counted as missing rather than silently narrowing the average or the denominator.
    """
    if baseline == candidate:
        raise ValueError("a paired comparison needs two systems")
    if not trials.get(baseline) or not trials.get(candidate):
        raise ValueError("expected trials are required for both systems")
    runs = _index(observations)
    for (system, episode_id, trial), item in runs.items():
        if system not in (baseline, candidate):
            continue
        if trial not in trials[system]:
            raise ValueError(f"{system} has unexpected trial {trial!r}")
        if labels.get(episode_id) != (item.scenario, item.date):
            raise ValueError(f"{episode_id} is not a planned episode with these labels")
    differences: list[EpisodeDifference] = []
    excluded: dict[str, ExcludedReason] = {}
    for episode_id in sorted(labels):
        first = _episode_mean(runs, baseline, episode_id, trials[baseline])
        second = _episode_mean(runs, candidate, episode_id, trials[candidate])
        problem = next((value for value in (first, second) if isinstance(value, str)), None)
        if problem is not None:
            excluded[episode_id] = problem
            continue
        differences.append(EpisodeDifference(episode_id, *labels[episode_id], second - first))
    return PairedSample(baseline, candidate, tuple(differences), excluded)


def savings_sample(
    comparisons: Iterable[SavingsComparison],
    labels: Mapping[str, tuple[str, str]],
    trials: tuple[int | None, ...],
) -> PairedSample:
    """Savings per episode under the equal-work rule, from E03 comparisons.

    ``labels`` maps every planned episode to its scenario and date. An episode counts only
    when all its trials are comparable, because averaging only the comparable trials would
    keep the runs that did the same work and hide the ones that did not. Positive
    differences mean the candidate emitted less, the opposite sign to ``paired_sample``.
    """
    if not trials:
        raise ValueError("expected trials are required")
    by_episode: dict[str, dict] = defaultdict(dict)
    pair = None
    for item in comparisons:
        if item.episode_id not in labels:
            raise ValueError(f"{item.episode_id} has no scenario and date label")
        if pair not in (None, (item.baseline, item.candidate)):
            raise ValueError("comparisons mix system pairs")
        pair = (item.baseline, item.candidate)
        if item.trial not in trials:
            raise ValueError(f"unexpected trial {item.trial!r}")
        if item.trial in by_episode[item.episode_id]:
            raise ValueError(f"more than one comparison for {item.episode_id}")
        by_episode[item.episode_id][item.trial] = item
    if pair is None:
        raise ValueError("at least one comparison is required")
    differences: list[EpisodeDifference] = []
    excluded: dict[str, ExcludedReason] = {}
    for episode_id in sorted(labels):
        found = by_episode.get(episode_id, {})
        if set(found) != set(trials):
            excluded[episode_id] = "run_missing"
        elif any(item.status != "comparable" for item in found.values()):
            excluded[episode_id] = "comparison_blocked"
        else:
            mean = math.fsum(item.savings_kg for item in found.values()) / len(found)
            differences.append(EpisodeDifference(episode_id, *labels[episode_id], mean))
    return PairedSample(*pair, tuple(differences), excluded)


def _percentile(ordered: list[float], fraction: float) -> float:
    """Linear interpolation between order statistics."""
    position = fraction * (len(ordered) - 1)
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def interval(
    sample: PairedSample,
    settings: Resampling = Resampling(),
    by: Literal["episode", "date"] = "episode",
) -> Interval:
    """Percentile interval for the mean episode difference, resampling whole units."""
    if by not in ("episode", "date"):
        raise ValueError("resample by episode or date")
    groups: dict[str, list[float]] = defaultdict(list)
    for item in sample.differences:
        groups[item.episode_id if by == "episode" else item.date].append(item.difference)
    units = [groups[key] for key in sorted(groups)]  # input order cannot change the result
    values = [item.difference for item in sample.differences]
    estimate = math.fsum(values) / len(values) if values else None
    lower = upper = None
    if len(units) >= 2:
        rng = random.Random(settings.seed)
        means = []
        for _ in range(settings.resamples):
            drawn = rng.choices(units, k=len(units))
            # Dates hold unequal episode counts, so this is a mean over episodes.
            means.append(
                math.fsum(math.fsum(unit) for unit in drawn) / sum(len(unit) for unit in drawn)
            )
        means.sort()
        tail = (1 - settings.confidence) / 2
        lower, upper = _percentile(means, tail), _percentile(means, 1 - tail)
    return Interval(
        estimate=estimate,
        lower=lower,
        upper=upper,
        episodes=len(values),
        excluded=len(sample.excluded),
        units=len(units),
        by=by,
        confidence=settings.confidence,
        resamples=settings.resamples,
    )


def scenario_summary(observations: Iterable[Observation]) -> tuple[ScenarioRow, ...]:
    """Mean, standard deviation, minimum and maximum per system and scenario."""
    groups: dict[tuple[str, str], list[Observation]] = defaultdict(list)
    for item in _index(observations).values():
        groups[(item.system, item.scenario)].append(item)
    rows = []
    for (system, scenario), items in sorted(groups.items()):
        values = [item.value for item in items if item.value is not None]
        rows.append(
            ScenarioRow(
                system=system,
                scenario=scenario,
                runs=len(items),
                missing=len(items) - len(values),
                mean=math.fsum(values) / len(values) if values else None,
                std=statistics.stdev(values) if len(values) > 1 else None,
                minimum=min(values, default=None),
                maximum=max(values, default=None),
            )
        )
    return tuple(rows)
