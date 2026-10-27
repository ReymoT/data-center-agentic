"""E03 equal-work savings comparison between two paired runs of one episode.

Implements the rule agreed in issue #61 (Nisha's proposal; agreed by Reimo, Ved and
Edison). A savings or exact-gap value is given only when both runs did exactly the same
work under the same inputs, as replayed independently by E01. Anything else is blocked
with every failed reason recorded, and a blocked comparison has no savings value: it is
never reported as zero savings.

Emissions come from E01's own arithmetic (``claims``) on private realized carbon and the
replayed starts. Neither the S02 savings helper nor P01 is imported or used as truth;
the strict S02 guard stays as it is.
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal, get_args

from dc_sustainability.evaluation import claims
from dc_sustainability.evaluation.replay import Replay

BlockedReason = Literal[
    "completed_set_differs",
    "unfinished_set_differs",  # unfinished or deadline-missed job IDs differ
    "inputs_differ",  # episode, site, capacity, horizon, realized carbon, protocol or trial
    "unfinished_job_occupied",  # an unfinished job has executed occupancy in either run
    "carbon_missing",  # a realized carbon value the comparison needs is absent
]
REASON_ORDER: tuple[BlockedReason, ...] = get_args(BlockedReason)


@dataclass(frozen=True)
class Run:
    """One system's run of an episode, as replayed by E01 from its executed starts."""

    system: str
    trial: int | None
    replay: Replay


@dataclass(frozen=True)
class WorkCounts:
    completed: int
    unfinished: int  # missed jobs included
    missed: int


@dataclass(frozen=True)
class SavingsComparison:
    episode_id: str
    baseline: str
    candidate: str
    trial: int | None
    status: Literal["comparable", "blocked"]
    reasons: tuple[BlockedReason, ...]  # every failed condition, in REASON_ORDER
    baseline_kg: float | None
    candidate_kg: float | None
    savings_kg: float | None  # baseline minus candidate; None whenever blocked
    counts: Mapping[str, WorkCounts]  # "baseline" / "candidate" -> counts


def _counts(replay: Replay) -> WorkCounts:
    return WorkCounts(
        len(replay.completed_job_ids), len(replay.unfinished_job_ids), len(replay.missed_job_ids)
    )


def _starts(replay: Replay) -> dict[str, int]:
    return {job_id: slot.slot for slot in replay.slots for job_id in slot.started}


def _occupied_unfinished(replay: Replay) -> set[str]:
    occupied = {job_id for slot in replay.slots for job_id in slot.running}
    return occupied & set(replay.unfinished_job_ids)


def _emissions_kg(replay: Replay, carbon: Mapping[int, float]) -> float:
    """Job emissions of the completed jobs at their replayed starts; background excluded."""
    jobs = {p.job.job_id: p.job for p in replay.episode.jobs}
    starts = _starts(replay)
    return claims.schedule_emissions_kg(
        {j: starts[j] for j in replay.completed_job_ids}, jobs, replay.episode.snapshot.site, carbon
    )


def compare_savings(baseline: Run, candidate: Run) -> SavingsComparison:
    """Savings of ``candidate`` against the named ``baseline``, or the reasons it is blocked."""
    a, b = baseline.replay, candidate.replay
    reasons: set[BlockedReason] = set()
    if set(a.completed_job_ids) != set(b.completed_job_ids):
        reasons.add("completed_set_differs")
    if (set(a.unfinished_job_ids), set(a.missed_job_ids)) != (
        set(b.unfinished_job_ids),
        set(b.missed_job_ids),
    ):
        reasons.add("unfinished_set_differs")
    # The private episode holds the site, capacity, jobs, horizon and realized carbon.
    if (
        a.episode.canonical_hash() != b.episode.canonical_hash()
        or a.protocol != b.protocol
        or len(a.slots) != len(b.slots)
        or baseline.trial != candidate.trial
    ):
        reasons.add("inputs_differ")
    if _occupied_unfinished(a) or _occupied_unfinished(b):
        reasons.add("unfinished_job_occupied")

    baseline_kg = candidate_kg = None
    try:
        baseline_kg = _emissions_kg(a, claims.carbon_series(a.episode.realized_carbon))
        candidate_kg = _emissions_kg(b, claims.carbon_series(b.episode.realized_carbon))
    except claims.CarbonUnavailable:
        reasons.add("carbon_missing")
        baseline_kg = candidate_kg = None

    ordered = tuple(r for r in REASON_ORDER if r in reasons)
    return SavingsComparison(
        episode_id=a.episode.episode_id,
        baseline=baseline.system,
        candidate=candidate.system,
        trial=candidate.trial,
        status="blocked" if ordered else "comparable",
        reasons=ordered,
        baseline_kg=baseline_kg,
        candidate_kg=candidate_kg,
        savings_kg=None if ordered else baseline_kg - candidate_kg,
        counts={"baseline": _counts(a), "candidate": _counts(b)},
    )


@dataclass(frozen=True)
class ComparisonSummary:
    """Table counts: comparable and blocked comparisons, and each blocked reason."""

    total: int
    comparable: int
    blocked: int
    by_reason: Mapping[str, int]  # a comparison blocked for two reasons counts in both


def summarize(comparisons: Iterable[SavingsComparison]) -> ComparisonSummary:
    comparisons = list(comparisons)
    reasons = Counter(r for c in comparisons for r in c.reasons)
    blocked = sum(c.status == "blocked" for c in comparisons)
    return ComparisonSummary(
        total=len(comparisons),
        comparable=len(comparisons) - blocked,
        blocked=blocked,
        by_reason={r: reasons[r] for r in REASON_ORDER if reasons[r]},
    )
