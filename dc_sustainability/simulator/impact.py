"""S02 development adapter. Receiving agreement/review remains tracked in Issue #36."""

import math
from dataclasses import asdict, dataclass

from dc_sustainability.metrics.impact import (
    Blocked,
    Comparison,
    Horizon,
    Impact,
    Placement,
    Site,
    Work,
    calculate_impact,
    compare,
)
from dc_sustainability.schemas import EpisodeResult, EpisodeTotals, PrivateEpisode


@dataclass(frozen=True)
class RealizedAccounting:
    """Trusted outcome only; facility totals and completed IT work are distinct.

    Never expose this record as policy context or use it as a forecast estimate.
    Savings comparisons use P01 compare on the impact records, never energy differences.
    """

    result: EpisodeResult
    impact: Impact
    completed_it_energy_kwh: float


def compare_realized(baseline: RealizedAccounting, candidate: RealizedAccounting) -> Comparison:
    """Keep unstarted/missed jobs in the savings guard as well as P01 leftovers."""
    comparison = compare(baseline.impact, candidate.impact)
    if isinstance(comparison, Blocked):
        return comparison
    if baseline.result.unfinished_job_ids or candidate.result.unfinished_job_ids:
        return Blocked(
            kind="blocked",
            reason="unfinished_work",
            detail="an episode has uncompleted jobs, including jobs never started",
            baseline_schedule_id=baseline.impact.schedule_id,
            candidate_schedule_id=candidate.impact.schedule_id,
            baseline_input_id=baseline.impact.input_id,
            candidate_input_id=candidate.impact.input_id,
            baseline_horizon=baseline.impact.horizon,
            candidate_horizon=candidate.impact.horizon,
            baseline_completed_job_ids=baseline.impact.completed_job_ids,
            candidate_completed_job_ids=candidate.impact.completed_job_ids,
        )
    return comparison


def account_realized(episode: PrivateEpisode, result: EpisodeResult) -> RealizedAccounting:
    """Adapt a trusted, fully executed S01 result using Edison's #36 proposal.

    This is an explicit development boundary, not an independent replay validator.
    Missing observations stay missing; duplicate slot observations are ambiguous errors.
    Forecasts are deliberately not an input. No completed_work scalar is populated.
    """
    episode = PrivateEpisode.model_validate(episode.model_dump())
    result = EpisodeResult.model_validate(result.model_dump())
    if result.episode_id != episode.episode_id:
        raise ValueError("episode/result identity mismatch")
    if (result.n_decision_slots, result.n_completion_slots) != (24, 6):
        raise ValueError("accounting requires all 30 episode slots")
    if (episode.n_decision_slots, episode.n_completion_slots) != (24, 6):
        raise ValueError("accounting requires a 30-slot episode")
    jobs = {p.job.job_id: p.job for p in episode.jobs}
    if set(result.completed_job_ids) | set(result.unfinished_job_ids) != set(jobs):
        raise ValueError("result must retain every episode job outcome")
    carbon = {}
    for observation in episode.realized_carbon:
        if observation.valid_slot in carbon:
            raise ValueError("ambiguous realized carbon: duplicate slot")
        carbon[observation.valid_slot] = observation.value
    site = episode.snapshot.site
    impact = calculate_impact(
        schedule_id=result.run_id,
        input_id=episode.episode_id,
        horizon=Horizon(0, 30),
        site=Site(site.background_kw, site.pue, site.slot_hours),
        work=tuple(Work(j.job_id, j.power_kw, j.duration_slots) for j in jobs.values()),
        placements=tuple(
            Placement(job_id, slot.slot) for slot in result.slots for job_id in slot.started_job_ids
        ),
        completed_job_ids=result.completed_job_ids,
        carbon_g_per_kwh=carbon,
    )
    slots = tuple(
        slot.model_copy(update={"energy_kwh": row.energy_kwh, "emissions_kg": row.emissions_kg})
        for slot, row in zip(result.slots, impact.slots, strict=True)
    )
    populated = EpisodeResult.model_validate(
        result.model_dump()
        | {"slots": slots, "totals": EpisodeTotals(**asdict(impact.totals)), "completed_work": None}
    )
    completed_it = math.fsum(
        jobs[job_id].power_kw * jobs[job_id].duration_slots * site.slot_hours
        for job_id in sorted(result.completed_job_ids)
    )
    if not math.isfinite(completed_it):
        raise ValueError("completed IT energy is not finite")
    return RealizedAccounting(populated, impact, completed_it)
