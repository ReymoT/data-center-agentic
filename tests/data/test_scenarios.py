"""D03 tests use synthetic carbon, never Frontier observations."""

import json
import random
from datetime import timedelta
from pathlib import Path

import pytest

from dc_sustainability.data.scenarios import (
    SCENARIOS,
    generate_episode,
    generate_jobs,
    hand_jobs,
    private_manifest,
)
from dc_sustainability.schemas import CarbonObservation, PrivateEpisode, VisibleState
from tests.contracts import fixtures as f


@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("seed", range(100))
def test_constraints_and_exact_scenario_requirements(scenario, seed):
    jobs = generate_jobs(scenario, seed=seed, split="development")
    count, flexible, low, high = {
        "normal": (12, 7, 2, 10),
        "spike": (20, 12, 2, 10),
        "limited": (12, 2, 0, 2),
        "infeasible": (12, 7, 2, 10),
    }[scenario]
    assert len(jobs) == count
    assert len({p.job.job_id for p in jobs}) == count
    assert sum(p.job.flexible for p in jobs) == flexible
    assert sum(p.intentionally_infeasible for p in jobs) == (scenario == "infeasible")
    for private in jobs:
        job = private.job
        assert private.synthetic and private.scenario_id == scenario
        assert private.seed == seed and private.split == "development"
        assert 0 <= job.arrival_slot < 18
        assert 1 <= job.duration_slots <= 4
        assert 10 <= job.power_kw <= 40
        assert 0 <= job.deadline_slot <= 30
        if private.intentionally_infeasible:
            assert job.slack_slots == -1 and job.flexible
        else:
            assert low <= job.slack_slots <= high
    if scenario == "spike":
        assert sum(6 <= p.job.arrival_slot <= 9 for p in jobs) == 8


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_determinism_and_rng_isolation(scenario):
    random.seed(10)
    before = random.getstate()
    first = generate_jobs(scenario, seed=47, split="development")
    assert random.getstate() == before
    random.random()
    assert first == generate_jobs(scenario, seed=47, split="development")
    assert first != generate_jobs(scenario, seed=48, split="development")
    held = generate_jobs(scenario, seed=47, split="held_out")
    assert [p.job for p in held] == [p.job for p in first]


@pytest.mark.parametrize(
    "args",
    [
        dict(scenario="bad", seed=1, split="development"),
        dict(scenario="normal", seed=True, split="development"),
        dict(scenario="normal", seed=1.5, split="development"),
        dict(scenario="normal", seed=1, split="train"),
    ],
)
def test_invalid_inputs(args):
    with pytest.raises(ValueError):
        generate_jobs(**args)


def episode_args():
    # Strip hand-job-specific constraints; only the common site constraints apply.
    snapshot = f.snapshot(pue=1.2)
    snapshot = snapshot.model_copy(
        update={"constraints": tuple(c for c in snapshot.constraints if not c.applies_to_jobs)}
    )
    carbon = tuple(
        CarbonObservation(
            fact_id=f"FACT-OBS-{slot}",
            value=f.HAND_CARBON[slot % 7],
            unit="g/kWh",
            source_id=f.SOURCE_ID,
            observed_at_utc=f.SLOT0_UTC + timedelta(hours=slot),
            valid_slot=slot,
            semantics=f.semantics(),
            quality_status="unvalidated",
        )
        for slot in range(30)
    )
    return dict(
        seed=42, split="development", episode_id="EP-D03", snapshot=snapshot, realized_carbon=carbon
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_episode_roundtrip_and_manifest(scenario):
    episode = generate_episode(scenario, **episode_args())
    assert (episode.n_decision_slots, episode.n_completion_slots) == (24, 6)
    assert PrivateEpisode.from_json(episode.to_json()) == episode
    assert generate_episode(scenario, **episode_args()).to_json() == episode.to_json()
    manifest = private_manifest(episode)
    assert manifest["episode_sha256"] == episode.canonical_hash()
    assert manifest["calibration_status"] == "provisional_not_Frontier_validated"
    assert manifest["source"]["source_id"] == "SRC-D03-SYNTHETIC"
    assert manifest["seed"] == 42 and manifest["synthetic"]


def test_withheld_actuals_and_visibility_boundary():
    normal = generate_episode("normal", **episode_args())
    withheld = generate_episode("normal", withhold_forecast=True, **episode_args())
    assert withheld.forecast_visibility == "withheld"
    assert normal.realized_carbon == withheld.realized_carbon
    assert normal.jobs == withheld.jobs
    assert len(withheld.realized_carbon) == 30
    # D03 supplies only private inputs; it does not add a simulator/public export.
    with pytest.raises(ValueError):
        VisibleState.from_json(withheld.to_json())
    for private in withheld.jobs:
        assert set(json.loads(private.job.to_json())) == {
            "record_type",
            "schema_version",
            "job_id",
            "arrival_slot",
            "duration_slots",
            "power_kw",
            "deadline_slot",
            "flexible",
        }


def test_invalid_carbon_and_variant():
    args = episode_args()
    for carbon in (
        (),
        args["realized_carbon"][:-1],
        args["realized_carbon"][:-1] + args["realized_carbon"][:1],
    ):
        with pytest.raises(ValueError, match="cover each slot"):
            generate_episode("normal", **(args | {"realized_carbon": carbon}))
    foreign = tuple(o.model_copy(update={"source_id": "UNKNOWN"}) for o in args["realized_carbon"])
    with pytest.raises(ValueError, match="source must resolve"):
        generate_episode("normal", **(args | {"realized_carbon": foreign}))
    with pytest.raises(ValueError):
        generate_episode("spike", withhold_forecast=True, **args)


def test_hand_fixture_matches_f02_and_retains_impossible_job():
    assert hand_jobs() == tuple(f.jobs().values())
    assert hand_jobs()[2].slack_slots == -1


def test_published_catalog_and_cli_reproduction(tmp_path, monkeypatch):
    from dc_sustainability.data.scenarios import main

    catalog_path = Path("data/manifests/d03-provisional-jobs.json")
    output = tmp_path / "catalog.json"
    monkeypatch.setattr(
        "sys.argv", ["scenarios", str(output), "--seed", "42", "--split", "development"]
    )
    main()
    assert output.read_bytes() == catalog_path.read_bytes()
    with pytest.raises(FileExistsError):
        main()
    catalog = json.loads(output.read_text())
    for scenario in SCENARIOS:
        assert catalog["scenarios"][scenario] == [
            job.to_jsonable() for job in generate_jobs(scenario, seed=42, split="development")
        ]
