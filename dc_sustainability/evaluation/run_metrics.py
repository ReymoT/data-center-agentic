"""E03 run-level metrics from one saved run, judged by E01 rather than by the run's checks.

Every recorded plan is re-validated against the state E01 replays from the executed starts,
so a production check is compared with that verdict and never taken as truth. A stage that
was not used is not a safe output: it is left out of its stage's denominator.

A recommendation is a decision slot with waiting work, or with a plan that claims some. An
empty-queue no-op is counted apart, because counting it would raise accuracy for doing
nothing. Decision accuracy is valid / all recommendations, so a pending decision stays in
the denominator and is not credited, and a recommendation with no plan is invalid.

An invalid plan that only omits waiting jobs breaks the coverage rule but asks for nothing
dangerous, so ``omission_only`` keeps it apart from plans that would break a physical or
timing rule. ``unsafe_rate`` follows the current "proposal the checker would refuse"
definition and ``unsafe_rate_without_omissions`` is the narrower reading.

Rates are None when their denominator is 0, never 0. A cost total is None rather than a
partial sum. These are draft definitions until they are frozen with I02.
"""

import math
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import claims
from dc_sustainability.evaluation.comparison import INVALIDATING_FINDINGS
from dc_sustainability.evaluation.replay import Replay, executed_starts, replay_episode
from dc_sustainability.evaluation.validator import (
    Protocol,
    ValidationResult,
    compare_with_check,
    facts_from_state,
    validate_output,
    validate_plan,
)

StageName = Literal["initial", "repaired", "fallback", "final"]
RECORDED_STAGES: tuple[s.Stage, ...] = ("initial", "repaired", "fallback")


def _rate(part: int, whole: int) -> float | None:
    return part / whole if whole else None


@dataclass(frozen=True)
class StageMetrics:
    """E01's verdicts on one stage's plans, over recommendations that used the stage."""

    proposals: int
    valid: int
    invalid: int
    pending: int
    omission_only: int  # invalid plans whose only finding is an omitted waiting job
    violation_types: Mapping[str, int]  # E01 finding code -> count
    checker_passed_invalid: int  # production check passed what E01 found invalid
    checker_failed_valid: int

    @property
    def unsafe_rate(self) -> float | None:
        return _rate(self.invalid, self.proposals)

    @property
    def unsafe_rate_without_omissions(self) -> float | None:
        return _rate(self.invalid - self.omission_only, self.proposals)


@dataclass(frozen=True)
class CostMetrics:
    """A total is None when any record that made model calls lacks it: no partial sums."""

    model_calls: int
    latency_ms: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_usd: float | None


@dataclass(frozen=True)
class RunMetrics:
    system: str
    run_id: str
    episode_id: str
    trial: int | None
    recommendations: int
    empty_queue_noops: int
    no_plan: int
    stages: Mapping[StageName, StageMetrics]
    repairs: int
    repair_opportunities: int  # recommendations where a repaired stage is applicable
    fallbacks: int
    fallback_opportunities: int
    abstained_jobs: int
    justified_abstentions: int  # verified infeasible or required evidence unavailable
    executed_starts: int
    executed_invalid_findings: Mapping[str, int]  # E01 replay finding code -> count
    capacity_unverifiable_findings: int
    jobs: int
    completed_jobs: int
    missed_jobs: int
    unfinished_jobs: int  # missed jobs included, so these two overlap
    completed_it_energy_kwh: float
    completed_facility_energy_kwh: float
    completed_job_emissions_kg: float | None  # None when realized carbon is missing
    cost: CostMetrics

    @property
    def decision_accuracy(self) -> float | None:
        return _rate(self.stages["final"].valid, self.recommendations)

    @property
    def repair_rate(self) -> float | None:
        return _rate(self.repairs, self.repair_opportunities)

    @property
    def fallback_rate(self) -> float | None:
        return _rate(self.fallbacks, self.fallback_opportunities)


def _final_stage(record: s.DecisionRecord) -> s.StageRecord | None:
    """The stage the execution gate checked, otherwise the last recorded stage."""
    present = [
        stage for stage in (getattr(record, n) for n in RECORDED_STAGES) if stage is not None
    ]
    gate = record.execution_check
    if gate is not None:
        for stage in present:
            if stage.plan.plan_hash == gate.plan_hash:
                return stage
    return present[-1] if present else None


class _StageTally:
    def __init__(self):
        self.statuses = Counter()
        self.omission_only = 0
        self.findings = Counter()
        self.disagreements = Counter()

    def add(self, result: ValidationResult, stage: s.StageRecord | None) -> None:
        self.statuses[result.status] += 1
        codes = {finding.code for finding in result.findings}
        self.omission_only += result.status == "invalid" and codes == {"omitted_job"}
        self.findings.update(finding.code for finding in result.findings)
        if stage is not None and stage.check is not None:
            self.disagreements[compare_with_check(result, stage.check)] += 1

    def metrics(self) -> StageMetrics:
        return StageMetrics(
            proposals=sum(self.statuses.values()),
            valid=self.statuses["valid"],
            invalid=self.statuses["invalid"],
            pending=self.statuses["pending"],
            omission_only=self.omission_only,
            violation_types=dict(sorted(self.findings.items())),
            checker_passed_invalid=self.disagreements["checker_passed_invalid"],
            checker_failed_valid=self.disagreements["checker_failed_valid"],
        )


def _total(records: Iterable[s.DecisionRecord], field: str) -> float | None:
    called = [record for record in records if record.model_call_count > 0]
    values = [getattr(record, field) for record in called]
    return None if any(value is None for value in values) else sum(values)


def _cost(records: tuple[s.DecisionRecord, ...]) -> CostMetrics:
    return CostMetrics(
        model_calls=sum(record.model_call_count for record in records),
        latency_ms=_total(records, "latency_ms"),
        prompt_tokens=_total(records, "prompt_tokens"),
        completion_tokens=_total(records, "completion_tokens"),
        cost_usd=_total(records, "cost_usd"),
    )


def _emissions_kg(replay: Replay) -> float | None:
    episode = replay.episode
    jobs = {p.job.job_id: p.job for p in episode.jobs}
    starts = {job_id: start for slot in replay.boundaries for job_id, start, _ in slot.completed}
    try:
        return claims.schedule_emissions_kg(
            starts,
            jobs,
            episode.snapshot.site,
            claims.carbon_series(episode.realized_carbon),
        )
    except claims.CarbonUnavailable:
        return None


def run_metrics(
    episode: s.PrivateEpisode,
    records: Iterable[s.DecisionRecord],
    protocol: Protocol,
) -> RunMetrics:
    """Score one saved run: its decision records for one system, episode and trial."""
    records = tuple(sorted(records, key=lambda record: record.slot))
    if [record.slot for record in records] != list(
        range(s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS)
    ):
        raise ValueError("a run needs exactly one decision record for each slot")
    replay = replay_episode(episode, executed_starts(records, episode.episode_id), protocol)

    tallies = {name: _StageTally() for name in (*RECORDED_STAGES, "final")}
    recommendations = noops = no_plan = 0
    repairs = repair_opportunities = fallbacks = fallback_opportunities = 0
    abstained = justified = 0
    for record in records[: s.PROPOSED_DECISION_SLOTS]:
        state = replay.state_at(record.slot)
        facts = facts_from_state(state, episode.snapshot)
        final = _final_stage(record)
        stage_results = {
            name: validate_plan(stage.plan, facts, protocol)
            for name in RECORDED_STAGES
            if (stage := getattr(record, name)) is not None
        }
        if final is None:
            result = validate_output(None, facts, protocol)
            if result.empty_queue:
                noops += 1
                continue
            no_plan += 1
        else:
            result = validate_plan(final.plan, facts, protocol)
            if (
                result.empty_queue
                and result.valid
                and all(verdict.empty_queue and verdict.valid for verdict in stage_results.values())
            ):
                noops += 1
                continue
            whole = any(item.job_id is None for item in final.plan.abstentions)
            named = {item.job_id for item in final.plan.abstentions if item.job_id is not None}
            abstained += len(facts.waiting) if whole else len(named & set(facts.waiting))
            justified += len(result.justified_abstentions)
        recommendations += 1
        tallies["final"].add(result, final)
        for name in RECORDED_STAGES:
            stage = getattr(record, name)
            if stage is not None:
                tallies[name].add(stage_results[name], stage)
        repair_opportunities += "repaired" not in record.not_applicable_stages
        fallback_opportunities += "fallback" not in record.not_applicable_stages
        repairs += record.repaired is not None
        fallbacks += record.fallback is not None

    findings = Counter(finding.code for finding in replay.findings)
    first = records[0]
    return RunMetrics(
        system=first.system,
        run_id=first.run_id,
        episode_id=episode.episode_id,
        trial=first.trial,
        recommendations=recommendations,
        empty_queue_noops=noops,
        no_plan=no_plan,
        stages={name: tally.metrics() for name, tally in tallies.items()},
        repairs=repairs,
        repair_opportunities=repair_opportunities,
        fallbacks=fallbacks,
        fallback_opportunities=fallback_opportunities,
        abstained_jobs=abstained,
        justified_abstentions=justified,
        executed_starts=sum(len(record.executed_starts) for record in records),
        executed_invalid_findings={
            code: count for code, count in sorted(findings.items()) if code in INVALIDATING_FINDINGS
        },
        capacity_unverifiable_findings=findings["capacity_unverifiable"],
        jobs=len(episode.jobs),
        completed_jobs=replay.completed_job_count,
        missed_jobs=len(replay.missed_job_ids),
        unfinished_jobs=len(replay.unfinished_job_ids),
        completed_it_energy_kwh=replay.completed_it_energy_kwh,
        completed_facility_energy_kwh=math.fsum(
            claims.job_energy_kwh(p.job, episode.snapshot.site)
            for p in episode.jobs
            if p.job.job_id in replay.completed_job_ids
        ),
        completed_job_emissions_kg=_emissions_kg(replay),
        cost=_cost(records),
    )
