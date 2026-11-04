"""E03 forecast-tie rate: how often a forecast cannot separate a job's feasible starts.

A flat forecast gives every start of a job the same forecast emissions, so a policy that
ranks starts by emissions has no reason to prefer one hour. This counts those decisions
from a run's E01 replay and the forecasts its policy saw, so the report can describe
whether forecasts distinguish individual-job starts. Read Greedy B's run for the reported
rate. Nothing here calls a policy, the simulator or the production checker.

One job decision is one waiting job at one decision slot, so a job that waits three slots
counts three times. Feasibility uses background and running work only, as a job alone:
contention between waiting jobs depends on policy order and is not settled here. Forecast
freshness is not judged; the forecasts supplied are taken to be those the policy saw.
"""

import math
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from dc_sustainability import schemas as s
from dc_sustainability.evaluation.replay import Replay
from dc_sustainability.evaluation.validator import (
    Protocol,
    _fits_alone,
    _legal_starts,
    facts_from_state,
)

Status = Literal[
    "tied",  # two or more feasible starts, all with equal forecast emissions
    "distinct",  # two or more feasible starts, not all equal
    "no_choice",  # fewer than two feasible starts, so a forecast cannot matter
    "uncovered",  # a feasible start occupies a slot with no forecast
    "unverifiable",  # capacity evidence is missing, so feasibility is unknown
]


@dataclass(frozen=True)
class JobDecision:
    slot: int
    job_id: str
    status: Status
    feasible_starts: tuple[int, ...]


@dataclass(frozen=True)
class TieSummary:
    """Explicit counts; the rate's denominator is the comparable decisions only."""

    job_decisions: int
    tied: int
    distinct: int
    no_choice: int
    uncovered: int
    unverifiable: int

    @property
    def comparable(self) -> int:
        return self.tied + self.distinct

    @property
    def tie_rate(self) -> float | None:
        """Tied share of comparable decisions; None when there are none, never 0."""
        return self.tied / self.comparable if self.comparable else None


def _classify(job: s.Job, starts: tuple[int, ...], carbon: Mapping[int, float]) -> Status:
    if len(starts) < 2:
        return "no_choice"
    occupied = [range(start, start + job.duration_slots) for start in starts]
    if any(slot not in carbon for slots in occupied for slot in slots):
        return "uncovered"
    # Power and energy per slot are fixed for one job, so summed carbon ranks its starts.
    sums = [math.fsum(carbon[slot] for slot in slots) for slots in occupied]
    first = sums[0]
    # Do not turn a small but real forecast difference into an all-starts tie.
    # fsum gives stable sums; this diagnostic uses exact equality, not a near-tie threshold.
    same = all(value == first for value in sums)
    return "tied" if same else "distinct"


def job_decisions(
    replay: Replay,
    forecasts_by_slot: Mapping[int, Iterable[s.CarbonForecast]],
    protocol: Protocol,
) -> tuple[JobDecision, ...]:
    """Classify every waiting job at every decision slot of one replayed run."""
    if replay.protocol != protocol.name:
        raise ValueError("forecast-tie protocol must match the replay protocol")
    decisions: list[JobDecision] = []
    for slot in range(s.PROPOSED_DECISION_SLOTS):
        visible = tuple(forecasts_by_slot.get(slot, ()))
        carbon = {fact.valid_slot: fact.value for fact in visible}
        if len(carbon) != len(visible):
            raise ValueError(f"slot {slot} has more than one forecast for a valid slot")
        facts = facts_from_state(replay.state_at(slot, visible), replay.episode.snapshot)
        for job_id, job in sorted(facts.waiting.items()):
            legal = tuple(_legal_starts(job, slot, protocol))
            if facts.capacity_kw is None:
                decisions.append(JobDecision(slot, job_id, "unverifiable", legal))
                continue
            starts = tuple(start for start in legal if _fits_alone(job, start, facts))
            decisions.append(JobDecision(slot, job_id, _classify(job, starts, carbon), starts))
    return tuple(decisions)


def summarize(decisions: Iterable[JobDecision]) -> TieSummary:
    """Pool decisions by summing counts, so a rate is never an average of rates."""
    counts = Counter(decision.status for decision in decisions)
    return TieSummary(
        job_decisions=sum(counts.values()),
        tied=counts["tied"],
        distinct=counts["distinct"],
        no_choice=counts["no_choice"],
        uncovered=counts["uncovered"],
        unverifiable=counts["unverifiable"],
    )
