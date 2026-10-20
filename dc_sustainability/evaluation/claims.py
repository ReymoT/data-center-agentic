"""E01 independent impact reference and numeric claim scoring.

Arithmetic is written directly from the shared rules (energy = PUE x IT kW x slot hours;
emissions = kWh x g/kWh / 1000) and does not import Edison's impact module, so the two
can be compared rather than one checked against itself. The caller chooses the carbon
series: forecasts for forecast claims, private realized observations for outcomes.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from dc_sustainability import schemas as s

CLAIM_TOLERANCE = 0.05  # kWh and kg, the proposal's claim-scoring rule
TOLERANCE_UNITS = frozenset({"kWh", "kg"})


class CarbonUnavailable(KeyError):
    """A slot needed for an emissions value has no carbon value."""


def _nonnegative_finite(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric data")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


def carbon_series(
    facts: Iterable[s.CarbonForecast | s.CarbonObservation],
) -> dict[int, float]:
    """Map slot to g/kWh, refusing duplicate or unmapped slots."""
    series: dict[int, float] = {}
    for fact in facts:
        if fact.valid_slot is None:
            raise ValueError(f"{fact.fact_id} has no slot mapping")
        if fact.valid_slot in series:
            raise ValueError(f"two carbon values for slot {fact.valid_slot}")
        series[fact.valid_slot] = fact.value
    return series


def job_it_energy_kwh(job: s.Job, site: s.SiteConfig) -> float:
    """IT energy of the whole job, before PUE (the Q03 completed-work unit)."""
    return job.power_kw * job.duration_slots * site.slot_hours


def job_energy_kwh(job: s.Job, site: s.SiteConfig) -> float:
    return site.pue * job_it_energy_kwh(job, site)


def job_emissions_kg(
    job: s.Job, start_slot: int, site: s.SiteConfig, carbon: Mapping[int, float]
) -> float:
    """Emissions of the job's own load over [start, start + duration)."""
    total = 0.0
    for t in range(start_slot, start_slot + job.duration_slots):
        if t not in carbon:
            raise CarbonUnavailable(t)
        _nonnegative_finite(carbon[t], f"carbon at slot {t}")
        total += site.pue * job.power_kw * site.slot_hours * carbon[t] / 1000
    _nonnegative_finite(total, "job emissions")
    return total


def schedule_emissions_kg(
    starts: Mapping[str, int],
    jobs: Mapping[str, s.Job],
    site: s.SiteConfig,
    carbon: Mapping[int, float],
) -> float:
    """Job emissions of a schedule given as job ID to start slot; background excluded."""
    return math.fsum(
        job_emissions_kg(jobs[job_id], start, site, carbon) for job_id, start in starts.items()
    )


ScoreStatus = Literal[
    "correct",
    "incorrect",
    "unit_mismatch",
    "not_numeric",
    "reference_unavailable",
    # Pending: no agreed tolerance for kW, g/kWh, slot or h claims, and F02 Unit has
    # no percentage unit for the 0.05 percentage-point rule.
    "unscored_unit",
]


@dataclass(frozen=True)
class ClaimScore:
    claim_id: str
    status: ScoreStatus
    claimed: float | None
    reference: float | None
    abs_error: float | None


def score_numeric_claim(claim: s.Claim, reference: float | None, reference_unit: str) -> ClaimScore:
    """Score one claim against an independently computed reference value.

    Matching a claim to the quantity it describes is the reviewer's job (E04); F02
    claims carry a value and unit but no quantity kind.
    """
    claim = s.Claim.model_validate(claim.model_dump(mode="python", warnings="none"), strict=True)
    if reference is not None and (
        isinstance(reference, bool)
        or not isinstance(reference, (int, float))
        or not math.isfinite(reference)
    ):
        reference = None
    if claim.value is None:
        return ClaimScore(claim.claim_id, "not_numeric", None, reference, None)
    if reference is None:
        return ClaimScore(claim.claim_id, "reference_unavailable", claim.value, None, None)
    # Compare decimal representations of the recorded values. This includes an
    # exact 0.05 boundary without a guessed epsilon that credits larger errors.
    difference = abs(Decimal(str(claim.value)) - Decimal(str(reference)))
    error = float(difference)
    if claim.unit != reference_unit:
        return ClaimScore(claim.claim_id, "unit_mismatch", claim.value, reference, None)
    if claim.unit not in TOLERANCE_UNITS:
        return ClaimScore(claim.claim_id, "unscored_unit", claim.value, reference, error)
    status = "correct" if difference <= Decimal(str(CLAIM_TOLERANCE)) else "incorrect"
    return ClaimScore(claim.claim_id, status, claim.value, reference, error)


@dataclass(frozen=True)
class Comparison:
    status: Literal["comparable", "not_comparable"]
    savings_kg: float | None  # baseline minus candidate; positive means lower emissions
    reason: str


def compare_emissions(
    candidate_completed: Iterable[str],
    candidate_kg: float,
    baseline_completed: Iterable[str],
    baseline_kg: float,
    *,
    same_horizon_and_inputs: bool,
) -> Comparison:
    """A savings value only when both schedules completed exactly the same jobs.

    Otherwise less completed work could look like savings, so no number is given.
    """
    if not same_horizon_and_inputs:
        return Comparison("not_comparable", None, "different horizon or inputs")
    a, b = set(candidate_completed), set(baseline_completed)
    if a != b:
        return Comparison("not_comparable", None, f"completed jobs differ: {sorted(a ^ b)}")
    _nonnegative_finite(candidate_kg, "candidate emissions")
    _nonnegative_finite(baseline_kg, "baseline emissions")
    return Comparison("comparable", baseline_kg - candidate_kg, "same completed jobs")
