"""D03 private synthetic fixtures. All sampling is provisional, never Frontier-calibrated."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from dc_sustainability.schemas import (
    CarbonObservation,
    ConstraintSnapshot,
    Job,
    PrivateEpisode,
    PrivateJob,
    SourceRef,
)

GENERATOR_VERSION = "d03-provisional-v1"
SCENARIOS = {
    "normal": (12, 7, 2, 10),
    "spike": (20, 12, 2, 10),
    "limited": (12, 2, 0, 2),
    "infeasible": (12, 7, 2, 10),
}
SOURCE = SourceRef(
    source_id="SRC-D03-SYNTHETIC",
    path="dc_sustainability/data/scenarios.py",
    redistribution_status="permitted",
)


def generate_jobs(scenario: str, *, seed: int, split: str) -> tuple[PrivateJob, ...]:
    """Generate private jobs; split is caller metadata, not a D04 allocation.

    Independent discrete uniforms: power 10..40 kW, duration 1..4 hours,
    arrival 0..17, slack per scenario capped at 30-arrival-duration. Slack applies to every job, including
    nonflexible jobs (which must still start at arrival). Spike has exactly eight
    arrivals in 6..9; remaining arrivals sample uniformly outside that interval.
    These development choices require Q06 agreement before scientific freeze.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if split not in ("development", "held_out"):
        raise ValueError("split must be development or held_out")
    count, flexible_count, slack_low, slack_high = SCENARIOS[scenario]
    rng = random.Random(seed)
    flexible = set(rng.sample(range(count), flexible_count))
    impossible = min(flexible) if scenario == "infeasible" else None
    arrivals = tuple(range(18))
    outside_spike = tuple(a for a in arrivals if not 6 <= a <= 9)
    result = []
    for index in range(count):
        if scenario == "spike":
            arrival = rng.choice((6, 7, 8, 9) if index < 8 else outside_spike)
        else:
            arrival = rng.choice(arrivals)
        duration = rng.randint(1, 4)
        power = rng.randint(10, 40)
        slack = rng.randint(slack_low, min(slack_high, 30 - arrival - duration))
        intentional = index == impossible
        deadline = arrival + duration + (-1 if intentional else slack)
        result.append(
            PrivateJob(
                job=Job(
                    job_id=f"J{index + 1:02d}",
                    arrival_slot=arrival,
                    duration_slots=duration,
                    power_kw=power,
                    deadline_slot=deadline,
                    flexible=index in flexible,
                ),
                scenario_id=scenario,
                split=split,
                seed=seed,
                synthetic=True,
                intentionally_infeasible=intentional,
            )
        )
    return tuple(result)


def generate_episode(
    scenario: str,
    *,
    seed: int,
    split: str,
    episode_id: str,
    snapshot: ConstraintSnapshot,
    realized_carbon: tuple[CarbonObservation, ...],
    withhold_forecast: bool = False,
) -> PrivateEpisode:
    """Assemble an F02 private fixture from explicit caller-owned carbon/evidence.

    No carbon mapping, forecast issue times, policy views or simulator are invented.
    Withholding changes only forecast visibility, preserving all private actuals.
    """
    if type(withhold_forecast) is not bool:
        raise ValueError("withhold_forecast must be Boolean")
    if withhold_forecast and scenario != "normal":
        raise ValueError("the withheld-forecast variant is defined for normal demand")
    if len(realized_carbon) != 30 or sorted(
        o.valid_slot for o in realized_carbon if o.valid_slot is not None
    ) != list(range(30)):
        raise ValueError("private actual carbon must cover each slot 0..29 exactly once")
    source_ids = {source.source_id for source in snapshot.sources}
    if any(o.source_id not in source_ids for o in realized_carbon):
        raise ValueError("private carbon source must resolve in the snapshot")
    return PrivateEpisode(
        episode_id=episode_id,
        scenario_id=scenario,
        seed=seed,
        split=split,
        n_decision_slots=24,
        n_completion_slots=6,
        snapshot=snapshot,
        jobs=generate_jobs(scenario, seed=seed, split=split),
        realized_carbon=realized_carbon,
        forecast_visibility="withheld" if withhold_forecast else "perfect_foresight",
    )


def private_manifest(episode: PrivateEpisode) -> dict:
    """Local provenance sidecar, not a new shared record or policy input."""
    return {
        "generator_version": GENERATOR_VERSION,
        "calibration_status": "provisional_not_Frontier_validated",
        "synthetic": True,
        "source": SOURCE.to_jsonable(),
        "scenario": episode.scenario_id,
        "seed": episode.seed,
        "split": episode.split,
        "schema_version": episode.schema_version,
        "episode_sha256": episode.canonical_hash(),
        "forecast_visibility": episode.forecast_visibility,
        "distribution_specification": generate_jobs.__doc__,
    }


def hand_jobs() -> tuple[Job, ...]:
    """Proposal hand fixture; J3 is intentionally impossible. No impact computation."""
    return tuple(
        Job(
            job_id=job_id,
            arrival_slot=arrival,
            duration_slots=duration,
            power_kw=power,
            deadline_slot=6,
            flexible=True,
        )
        for job_id, arrival, duration, power in (
            ("J1", 0, 2, 40),
            ("J2", 0, 2, 30),
            ("J3", 4, 3, 20),
        )
    )


def main() -> None:
    """Write a tiny private job catalog exclusively; never overwrite prior artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--split", choices=("development", "held_out"), required=True)
    args = parser.parse_args()
    catalog = {
        "generator_version": GENERATOR_VERSION,
        "calibration_status": "provisional_not_Frontier_validated",
        "source": SOURCE.to_jsonable(),
        "seed": args.seed,
        "split": args.split,
        "synthetic": True,
        "distribution_specification": generate_jobs.__doc__,
        "scenarios": {
            name: [
                job.to_jsonable() for job in generate_jobs(name, seed=args.seed, split=args.split)
            ]
            for name in SCENARIOS
        },
        "hand_jobs": [job.to_jsonable() for job in hand_jobs()],
    }
    with args.output.open("x", encoding="utf-8") as output:
        output.write(json.dumps(catalog, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
