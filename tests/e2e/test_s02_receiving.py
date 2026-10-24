"""Bounded real S01/S02/E01 consumer checks on synthetic development executions.

The test-only actions are not production approvals or an integrated policy runner.
Independent replay is structural; hand truth separately checks physical totals.
"""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data.scenarios import hand_jobs
from dc_sustainability.evaluation.replay import compare_result, replay_episode
from dc_sustainability.evaluation.validator import Protocol
from dc_sustainability.simulator.impact import account_realized
from dc_sustainability.verification.checker import check_schedule
from tests.simulator.test_core import episode, simulator
from tests.simulator.test_s02_impact import run

PROTOCOL = Protocol("S02-receiving-synthetic-starts-0-23", "test input; no shared default", 23)


@pytest.mark.parametrize("pue", [1, 1.2])
@pytest.mark.parametrize("missing", [(), (0,), (29,)])
def test_real_simulator_impact_and_independent_replay_preserve_execution(pue, missing):
    ep, raw, accounting = run({0: ("J1",), 2: ("J2",)}, pue=pue, missing=missing)
    executed = {
        row.slot: tuple(s.ApprovedStart(job_id=j, start_slot=row.slot) for j in row.started_job_ids)
        for row in raw.slots
    }
    replay = replay_episode(ep, executed, PROTOCOL)
    assert replay.valid and compare_result(replay, accounting.result) == ()
    assert replay.completed_it_energy_kwh == accounting.completed_it_energy_kwh == 140
    assert accounting.result.completed_work is None
    assert accounting.result.totals.job_energy_kwh == pytest.approx(140 * pue)
    assert accounting.result.totals.background_energy_kwh == pytest.approx(1200 * pue)
    assert accounting.result.totals.site_energy_kwh == pytest.approx(1340 * pue)
    if missing:
        assert accounting.result.totals.site_emissions_kg is None
    else:
        assert accounting.result.totals.site_emissions_kg == pytest.approx(262.5 * pue)
    assert s.EpisodeResult.from_json(accounting.result.to_json()) == accounting.result


def test_incomplete_execution_stays_in_independent_outcomes():
    ep, raw, accounting = run({0: ("J1",)})
    replay = replay_episode(ep, {0: (s.ApprovedStart(job_id="J1", start_slot=0),)}, PROTOCOL)
    assert replay.valid and compare_result(replay, accounting.result) == ()
    assert replay.unfinished_job_ids == accounting.result.unfinished_job_ids == ("J2",)
    assert replay.completed_it_energy_kwh == accounting.completed_it_energy_kwh == 80
    assert raw.slots == tuple(
        row.model_copy(update={"energy_kwh": None, "emissions_kg": None})
        for row in accounting.result.slots
    )


def test_boundary_revalidation_already_rejects_reordered_slot_records():
    ep, raw, _ = run({0: ("J1",), 2: ("J2",)})
    invalid = raw.model_copy(update={"slots": (raw.slots[1], raw.slots[0], *raw.slots[2:])})
    with pytest.raises(ValueError, match="contiguous"):
        account_realized(ep, invalid)


def test_real_checker_rejects_omission_without_advancing_simulator():
    ep = episode(hand_jobs()[:2])
    sim = simulator(ep)
    before = sim.state()
    plan = s.Plan(
        episode_id=before.episode_id,
        slot=before.current_slot,
        state_version=before.state_version,
        status="proposed",
        starts=(s.PlannedStart(job_id="J1", start_slot=0),),
    )
    check = check_schedule(plan, before, ep.snapshot)
    assert check.status == "fail" and not check.errors
    assert any(v.job_ids == ("J2",) and "omitted" in v.message for v in check.violations)
    with pytest.raises(ValueError):
        s.ApprovedActions.from_checked_plan(plan, check, before.state_version)
    assert sim.state() == before
