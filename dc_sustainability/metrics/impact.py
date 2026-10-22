"""P01 shared energy and emissions calculations; savings are refused without matching work.

Facility kWh = PUE x IT kW x hours and kg = kWh x g/kWh / 1000. PUE scales energy only;
capacity stays an IT-power check elsewhere. Missing carbon leaves emissions as None, never 0.
The pollutant basis (CO2 versus CO2e) is unresolved under Q05, so no label is implied here.
"""

import hashlib
import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Literal

__all__ = [
    "Blocked",
    "Comparison",
    "Horizon",
    "Impact",
    "ImpactError",
    "Placement",
    "Savings",
    "Site",
    "SlotImpact",
    "Totals",
    "Work",
    "calculate_impact",
    "compare",
    "display1",
]

_BlockReason = Literal[
    "missing_carbon",
    "zero_baseline",
    "completed_jobs_differ",
    "unfinished_work",
    "horizon_mismatch",
    "inputs_differ",
]


class ImpactError(ValueError):
    pass


@dataclass(frozen=True)
class Work:
    job_id: str
    power_kw: float
    duration_slots: int


@dataclass(frozen=True)
class Placement:
    job_id: str
    start_slot: int


@dataclass(frozen=True)
class Site:
    background_kw: float
    pue: float
    slot_hours: float


@dataclass(frozen=True)
class Horizon:
    start_slot: int
    end_slot: int


@dataclass(frozen=True)
class SlotImpact:
    slot: int
    job_load_kw: float
    background_load_kw: float
    energy_kwh: float
    emissions_kg: float | None


@dataclass(frozen=True)
class Totals:
    job_energy_kwh: float
    background_energy_kwh: float
    site_energy_kwh: float
    job_emissions_kg: float | None
    background_emissions_kg: float | None
    site_emissions_kg: float | None


@dataclass(frozen=True)
class Impact:
    schedule_id: str
    input_id: str
    input_fingerprint: str
    horizon: Horizon
    site: Site
    completed_job_ids: frozenset[str]
    leftover_job_ids: frozenset[str]
    slots: tuple[SlotImpact, ...]
    totals: Totals

    @property
    def emissions_complete(self) -> bool:
        totals = self.totals
        if totals.job_emissions_kg is None or totals.background_emissions_kg is None:
            return False
        if totals.site_emissions_kg is None:
            return False
        return all(slot.emissions_kg is not None for slot in self.slots)


@dataclass(frozen=True)
class Savings:
    """Baseline minus candidate site emissions for the same inputs, horizon and completed work.

    A positive ``savings_kg`` means the candidate emits less; a negative value means it emits
    more. ``of_baseline_job`` and ``of_baseline_site`` are fractions (0.112, not 11.2) of the
    named baseline denominator.
    """

    kind: Literal["savings"]
    baseline_schedule_id: str
    candidate_schedule_id: str
    input_id: str
    input_fingerprint: str
    horizon: Horizon
    completed_job_ids: frozenset[str]
    savings_kg: float
    of_baseline_job: float
    of_baseline_site: float


@dataclass(frozen=True)
class Blocked:
    kind: Literal["blocked"]
    reason: _BlockReason
    detail: str
    baseline_schedule_id: str
    candidate_schedule_id: str
    baseline_input_id: str
    candidate_input_id: str
    baseline_horizon: Horizon
    candidate_horizon: Horizon
    baseline_completed_job_ids: frozenset[str]
    candidate_completed_job_ids: frozenset[str]


Comparison = Savings | Blocked


def calculate_impact(
    schedule_id: str,
    input_id: str,
    horizon: Horizon,
    site: Site,
    work: Iterable[Work],
    placements: Iterable[Placement],
    completed_job_ids: Iterable[str],
    carbon_g_per_kwh: Mapping[int, float],
) -> Impact:
    """Return per-slot and total energy/emissions for one schedule over ``horizon``.

    Only slots inside the horizon count. A completed job must run fully inside it. A placed
    job that is not completed is leftover unless it already ended before the horizon began.
    """
    schedule_id = _identifier(schedule_id, "schedule_id")
    input_id = _identifier(input_id, "input_id")
    if not isinstance(horizon, Horizon):
        raise ImpactError("horizon must be a Horizon")
    horizon_start = _whole(horizon.start_slot, "horizon start_slot")
    horizon_end = _whole(horizon.end_slot, "horizon end_slot")
    if horizon_end <= horizon_start:
        raise ImpactError("horizon end must be after start")
    if not isinstance(site, Site):
        raise ImpactError("site must be a Site")
    background_kw = _finite(site.background_kw, "background_kw")
    pue = _finite(site.pue, "pue")
    slot_hours = _finite(site.slot_hours, "slot_hours")
    if background_kw < 0:
        raise ImpactError("background_kw must be nonnegative")
    if pue < 1:
        raise ImpactError("pue must be at least 1")
    if slot_hours <= 0:
        raise ImpactError("slot_hours must be positive")

    jobs: dict[str, tuple[float, int]] = {}
    for job in _records(work, Work, "work"):
        job_id = _job_id(job.job_id, "job_id")
        power_kw = _finite(job.power_kw, f"power_kw for {job_id}")
        duration_slots = _whole(job.duration_slots, f"duration_slots for {job_id}")
        if power_kw <= 0:
            raise ImpactError(f"power_kw for {job_id} must be positive")
        if duration_slots < 1:
            raise ImpactError(f"duration_slots for {job_id} must be at least 1")
        if job_id in jobs:
            raise ImpactError(f"duplicate job id {job_id}")
        jobs[job_id] = (power_kw, duration_slots)

    starts: dict[str, int] = {}
    for placement in _records(placements, Placement, "placements"):
        job_id = _job_id(placement.job_id, "start job_id")
        if job_id not in jobs:
            raise ImpactError(f"unknown start id {job_id}")
        if job_id in starts:
            raise ImpactError(f"more than one start for {job_id}")
        starts[job_id] = _whole(placement.start_slot, f"start_slot for {job_id}")

    if isinstance(completed_job_ids, (str, bytes)):
        raise ImpactError("completed_job_ids must be job ids")
    completed: set[str] = set()
    for raw_id in completed_job_ids:
        job_id = _job_id(raw_id, "completed job id")
        if job_id not in jobs:
            raise ImpactError(f"completed job {job_id} is not in the work list")
        _, duration_slots = jobs[job_id]
        start_slot = starts.get(job_id)
        if start_slot is None or not _inside(
            start_slot, duration_slots, horizon_start, horizon_end
        ):
            raise ImpactError(f"completed job {job_id} is not fully inside the horizon")
        completed.add(job_id)

    if not isinstance(carbon_g_per_kwh, Mapping):
        raise ImpactError("carbon must map slots to g/kWh")
    carbon: dict[int, float] = {}
    for raw_slot, raw_grams in carbon_g_per_kwh.items():
        slot = _whole(raw_slot, "carbon slot")
        grams = _finite(raw_grams, f"carbon at slot {slot}")
        if grams < 0:
            raise ImpactError(f"carbon at slot {slot} must be nonnegative")
        carbon[slot] = grams

    loads = {slot: [] for slot in range(horizon_start, horizon_end)}
    for job_id, start_slot in starts.items():
        power_kw, duration_slots = jobs[job_id]
        first = max(start_slot, horizon_start)
        last = min(start_slot + duration_slots, horizon_end)
        for slot in range(first, last):
            loads[slot].append(power_kw)

    slot_rows: list[SlotImpact] = []
    job_parts: list[float] = []
    background_parts: list[float] = []
    site_parts: list[float] = []
    job_gap = False
    carbon_gap = False
    for slot in range(horizon_start, horizon_end):
        job_load = math.fsum(loads[slot])
        energy_kwh = _produced(
            pue * (job_load + background_kw) * slot_hours, f"energy at slot {slot}"
        )
        grams = carbon.get(slot)
        if grams is None:
            emissions_kg = None
            carbon_gap = True
            if job_load != 0.0:
                job_gap = True
        else:
            emissions_kg = _produced(energy_kwh * grams / 1000.0, f"emissions at slot {slot}")
            job_parts.append(pue * job_load * slot_hours * grams / 1000.0)
            background_parts.append(pue * background_kw * slot_hours * grams / 1000.0)
            site_parts.append(emissions_kg)
        slot_rows.append(
            SlotImpact(
                slot=slot,
                job_load_kw=job_load,
                background_load_kw=background_kw,
                energy_kwh=energy_kwh,
                emissions_kg=emissions_kg,
            )
        )

    job_emissions_kg = None if job_gap else _produced(math.fsum(job_parts), "job emissions")
    background_emissions_kg = (
        None if carbon_gap else _produced(math.fsum(background_parts), "background emissions")
    )
    site_emissions_kg = None if carbon_gap else _produced(math.fsum(site_parts), "site emissions")
    totals = Totals(
        job_energy_kwh=_produced(
            math.fsum(pue * row.job_load_kw * slot_hours for row in slot_rows), "job energy"
        ),
        background_energy_kwh=_produced(
            math.fsum(pue * row.background_load_kw * slot_hours for row in slot_rows),
            "background energy",
        ),
        site_energy_kwh=_produced(math.fsum(row.energy_kwh for row in slot_rows), "site energy"),
        job_emissions_kg=job_emissions_kg,
        background_emissions_kg=background_emissions_kg,
        site_emissions_kg=site_emissions_kg,
    )
    return Impact(
        schedule_id=schedule_id,
        input_id=input_id,
        input_fingerprint=_fingerprint(background_kw, pue, slot_hours, carbon, jobs),
        horizon=horizon,
        site=site,
        completed_job_ids=frozenset(completed),
        leftover_job_ids=frozenset(
            job_id
            for job_id, start_slot in starts.items()
            if job_id not in completed and start_slot + jobs[job_id][1] > horizon_start
        ),
        slots=tuple(slot_rows),
        totals=totals,
    )


def compare(baseline: Impact, candidate: Impact) -> Comparison:
    if baseline.horizon != candidate.horizon:
        return _blocked(baseline, candidate, "horizon_mismatch", "horizons differ")
    if (
        baseline.input_id != candidate.input_id
        or baseline.input_fingerprint != candidate.input_fingerprint
    ):
        return _blocked(baseline, candidate, "inputs_differ", "input id or fingerprint differs")
    if baseline.completed_job_ids != candidate.completed_job_ids:
        return _blocked(baseline, candidate, "completed_jobs_differ", "completed jobs differ")
    if baseline.leftover_job_ids or candidate.leftover_job_ids:
        return _blocked(
            baseline, candidate, "unfinished_work", "a schedule still has leftover jobs"
        )
    job_kg = baseline.totals.job_emissions_kg
    site_kg = baseline.totals.site_emissions_kg
    candidate_kg = candidate.totals.site_emissions_kg
    if (
        not baseline.emissions_complete
        or not candidate.emissions_complete
        or job_kg is None
        or site_kg is None
        or candidate_kg is None
    ):
        return _blocked(
            baseline, candidate, "missing_carbon", "a horizon slot has no carbon sample"
        )
    if job_kg == 0 or site_kg == 0:
        return _blocked(
            baseline,
            candidate,
            "zero_baseline",
            "baseline job or site emissions are zero, so no fraction is defined",
        )
    savings_kg = _produced(site_kg - candidate_kg, "savings")
    job_fraction = _produced(savings_kg / job_kg, "baseline job savings fraction")
    site_fraction = _produced(savings_kg / site_kg, "baseline site savings fraction")
    return Savings(
        kind="savings",
        baseline_schedule_id=baseline.schedule_id,
        candidate_schedule_id=candidate.schedule_id,
        input_id=baseline.input_id,
        input_fingerprint=baseline.input_fingerprint,
        horizon=baseline.horizon,
        completed_job_ids=baseline.completed_job_ids,
        savings_kg=savings_kg,
        of_baseline_job=job_fraction,
        of_baseline_site=site_fraction,
    )


def display1(value: float) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ImpactError("display value must be a finite number")
    number = Decimal(str(value))
    # Quantize needs room for the integer digits, one decimal and a rounding carry.
    # Raise precision only locally; reporting must not mutate caller arithmetic.
    with localcontext() as context:
        context.prec = max(context.prec, number.adjusted() + 3)
        quantized = number.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return format(quantized, "f")


def _blocked(baseline: Impact, candidate: Impact, reason: _BlockReason, detail: str) -> Blocked:
    return Blocked(
        kind="blocked",
        reason=reason,
        detail=detail,
        baseline_schedule_id=baseline.schedule_id,
        candidate_schedule_id=candidate.schedule_id,
        baseline_input_id=baseline.input_id,
        candidate_input_id=candidate.input_id,
        baseline_horizon=baseline.horizon,
        candidate_horizon=candidate.horizon,
        baseline_completed_job_ids=baseline.completed_job_ids,
        candidate_completed_job_ids=candidate.completed_job_ids,
    )


def _fingerprint(
    background_kw: float,
    pue: float,
    slot_hours: float,
    carbon: Mapping[int, float],
    jobs: Mapping[str, tuple[float, int]],
) -> str:
    payload = {
        "site": {
            "background_kw": background_kw,
            "pue": pue,
            "slot_hours": slot_hours,
        },
        "carbon": [[slot, grams] for slot, grams in sorted(carbon.items())],
        "work": sorted(
            [job_id, power_kw, duration_slots]
            for job_id, (power_kw, duration_slots) in jobs.items()
        ),
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _records(values: Iterable[object], kind: type[object], label: str) -> tuple[object, ...]:
    if isinstance(values, (str, bytes)):
        raise ImpactError(f"{label} must be {kind.__name__} values")
    rows = tuple(values)
    for row in rows:
        if not isinstance(row, kind):
            raise ImpactError(f"{label} must be {kind.__name__} values")
    return rows


def _inside(start_slot: int, duration_slots: int, horizon_start: int, horizon_end: int) -> bool:
    return start_slot >= horizon_start and start_slot + duration_slots <= horizon_end


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ImpactError(f"{label} must be a non-empty string")
    return value


def _job_id(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ImpactError(f"{label} must be a string")
    return value


def _produced(value: float, label: str) -> float:
    if not math.isfinite(value):
        raise ImpactError(f"{label} is not finite")
    return value


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ImpactError(f"{label} must be a finite number")
    return float(value)


def _whole(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ImpactError(f"{label} must be an integer")
    return value
