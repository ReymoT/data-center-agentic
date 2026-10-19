"""Synthetic execution capabilities test S01 mechanics, never production approval."""

import pytest

from dc_sustainability.data.scenarios import generate_jobs, hand_jobs
from dc_sustainability.schemas import ApprovedActions, ApprovedStart, PrivateEpisode, PrivateJob
from dc_sustainability.simulator import SchedulingSimulator
from tests.contracts.fixtures import forecasts, observations, snapshot


def episode(jobs=None, scenario="normal", withheld=False):
    constraints = snapshot()
    if jobs is None:
        constraints = constraints.model_copy(
            update={
                "constraints": tuple(c for c in constraints.constraints if not c.applies_to_jobs)
            }
        )
    private = (
        generate_jobs(scenario, seed=42, split="development")
        if jobs is None
        else tuple(
            PrivateJob(job=j, scenario_id=scenario, split="development", seed=42, synthetic=True)
            for j in jobs
        )
    )
    ids = {p.job.job_id for p in private}
    constraints = constraints.model_copy(
        update={
            "constraints": tuple(
                c for c in constraints.constraints if set(c.applies_to_jobs) <= ids
            )
        }
    )
    return PrivateEpisode(
        episode_id="EP-S01",
        scenario_id=scenario,
        split="development",
        seed=42,
        n_decision_slots=24,
        n_completion_slots=6,
        snapshot=constraints,
        jobs=private,
        realized_carbon=observations(),
        forecast_visibility="withheld" if withheld else "perfect_foresight",
    )


def action(sim, *ids, **changes):
    state = sim.state()
    fields = dict(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        plan_hash="a" * 64,
        check_id="CHK-SYNTHETIC",
        starts=tuple(ApprovedStart(job_id=j, start_slot=state.current_slot) for j in ids),
    )
    return ApprovedActions(**(fields | changes))


def simulator(ep=None, allow=False):
    sim = SchedulingSimulator(allow_completion_starts=allow)
    sim.reset(ep or episode(hand_jobs()))
    return sim


def test_arrival_hidden_information_and_impossible_miss():
    sim = simulator()
    state = sim.state()
    assert {j.job_id for j in state.waiting_jobs} == {"J1", "J2"}
    assert "CON-DL-J3" not in state.constraint_ids
    assert "J3" not in state.to_json()
    assert not state.carbon_facts
    assert state.missing_carbon_slots == tuple(range(24))
    for _ in range(4):
        sim.step(action(sim))
    assert sim.state().missed_job_ids == ("J3",)
    assert "CON-DL-J3" in sim.state().constraint_ids
    assert sim.history[-1].missed_job_ids == ("J3",)
    assert not any(
        key in state.to_json() for key in ("realized_carbon", "split", "seed", "scenario")
    )


def test_nonpreemption_and_rejection_progression():
    sim = simulator()
    first = sim.step(action(sim, "J1"))
    assert first.slot.job_load_kw == 40
    assert first.slot.running_job_ids == ("J1",)
    assert sim.state().running_jobs[0].end_slot == 2
    second = sim.step(action(sim, "J1"))
    assert second.rejection
    assert second.slot.job_load_kw == 40
    assert second.slot.completed_job_ids == ("J1",)
    assert sim.state().current_slot == 2
    assert sim.state().completed_jobs[0].end_slot == 2


@pytest.mark.parametrize(
    "kind", ["capacity", "unknown", "future", "version", "episode", "dict", "duplicate", "past"]
)
def test_atomic_rejection(kind):
    sim = simulator()
    bad = action(sim, "J1")
    if kind == "capacity":
        bad = action(sim, "J1", "J2")
    elif kind == "unknown":
        bad = action(sim, "J1", "UNKNOWN")
    elif kind == "future":
        bad = action(sim, "J1", "J3")
    elif kind == "version":
        bad = action(sim, "J1", state_version=9)
    elif kind == "episode":
        bad = action(sim, "J1", episode_id="EP-OTHER")
    elif kind == "dict":
        bad = bad.model_dump()
    elif kind == "duplicate":
        bad = bad.model_copy(update={"starts": bad.starts * 2})
    elif kind == "past":
        bad = bad.model_copy(update={"slot": 1})
    transition = sim.step(bad)
    assert transition.rejection
    assert transition.slot.started_job_ids == ()
    assert transition.slot.job_load_kw == 0
    assert sim.state().current_slot == 1


def test_capacity_counts_running_before_pue():
    sim = simulator()
    sim.step(action(sim, "J1"))
    assert sim.step(action(sim, "J2")).rejection
    assert sim.step(action(sim, "J2")).rejection is None


def test_exact_deadline_and_latest_start_miss():
    sim = simulator()
    for _ in range(4):
        sim.step(action(sim))
    assert "J1" not in sim.state().missed_job_ids
    sim.step(action(sim, "J1"))
    assert "J2" in sim.state().missed_job_ids
    sim.step(action(sim))
    assert sim.state().completed_jobs[0].end_slot == 6


def test_nonflexible_violation_explicit():
    job = hand_jobs()[0].model_copy(update={"flexible": False})
    sim = simulator(episode([job]))
    result = sim.step(action(sim))
    assert result.nonflexible_violation_ids == ("J1",)
    assert sim.state().missed_job_ids == ("J1",)
    assert sim.step(action(sim, "J1")).rejection


@pytest.mark.parametrize("allow", [False, True])
def test_completion_period_explicit_choice(allow):
    job = hand_jobs()[1].model_copy(update={"deadline_slot": 30})
    sim = simulator(episode([job]), allow=allow)
    for _ in range(24):
        sim.step(action(sim))
    result = sim.step(action(sim, "J2"))
    assert bool(result.rejection) is not allow
    while sim.state().current_slot < 30:
        sim.step(action(sim))
    output = sim.result(run_id="RUN-S01", system="greedy_a")
    assert len(output.slots) == 30
    assert sum(s.phase == "completion" for s in output.slots) == 6
    assert output.totals.site_energy_kwh is None
    assert ("J2" in output.completed_job_ids) is allow
    with pytest.raises(RuntimeError):
        sim.step(action(sim))


@pytest.mark.parametrize("scenario", ["normal", "spike", "limited", "infeasible"])
def test_d03_replay_reset_and_no_lost_jobs(scenario):
    ep = episode(scenario=scenario)
    sim = simulator(ep)

    def replay():
        states = []
        for _ in range(30):
            states.append(sim.state().to_json())
            sim.step(action(sim))
        return states, sim.history, sim.result(run_id="RUN-S01", system="greedy_a")

    first = replay()
    sim.reset(ep)
    assert replay() == first
    output = first[2]
    assert set(output.unfinished_job_ids) == {p.job.job_id for p in ep.jobs}
    assert set(output.deadline_missed_job_ids) == set(output.unfinished_job_ids)
    assert not output.completed_job_ids


def test_forecasts_explicit_and_withheld_actuals_private():
    sim = SchedulingSimulator(allow_completion_starts=False)
    sim.reset(episode(hand_jobs()), forecasts_by_slot={0: forecasts()})
    assert sim.state().carbon_facts == forecasts()
    assert sim.state().missing_carbon_slots == tuple(range(7, 24))
    old = sim.state()
    with pytest.raises(ValueError):
        sim.reset(episode(hand_jobs(), withheld=True), forecasts_by_slot={0: forecasts()})
    assert sim.state() == old
    sim.reset(episode(hand_jobs(), withheld=True))
    assert not sim.state().carbon_facts


def test_reset_validation_and_lifecycle():
    sim = SchedulingSimulator(allow_completion_starts=False)
    with pytest.raises(RuntimeError):
        sim.state()
    with pytest.raises(TypeError):
        SchedulingSimulator()
    ep = episode(hand_jobs())
    with pytest.raises(ValueError):
        sim.reset(ep.model_copy(update={"n_decision_slots": 7}))
    with pytest.raises(ValueError):
        sim.reset(ep.model_copy(update={"snapshot": snapshot(include_capacity=False)}))
    sim.reset(ep)
    with pytest.raises(RuntimeError):
        sim.result(run_id="RUN-S01", system="greedy_a")


def test_capacity_exact_limit_and_reset_replay_with_starts():
    jobs = hand_jobs()[:2]
    jobs = (jobs[0], jobs[1].model_copy(update={"power_kw": 20}))
    ep = episode(jobs)
    sim = simulator(ep)

    def replay():
        output = [sim.step(action(sim, "J1", "J2"))]
        for _ in range(29):
            output.append(sim.step(action(sim)))
        return output, sim.result(run_id="RUN-S01", system="greedy_a")

    first = replay()
    assert first[0][0].slot.job_load_kw == 60
    assert first[0][1].slot.job_load_kw == 60
    assert first[0][2].slot.job_load_kw == 0
    assert first[1].completed_job_ids == ("J1", "J2")
    sim.reset(ep)
    assert replay() == first


def test_job_runs_across_decision_completion_boundary():
    job = hand_jobs()[1].model_copy(update={"deadline_slot": 30, "duration_slots": 4})
    sim = simulator(episode([job]))
    for _ in range(23):
        sim.step(action(sim))
    sim.step(action(sim, "J2"))
    for slot in range(24, 27):
        transition = sim.step(action(sim))
        assert transition.slot.job_load_kw == 30
        assert transition.slot.phase == "completion"
        assert transition.slot.completed_job_ids == (("J2",) if slot == 26 else ())
    assert sim.state().completed_jobs[0].end_slot == 27


def test_deadline_violation_action_and_constraint_conflict():
    sim = simulator()
    # Corrupt the schema-valid action's interval to exercise defensive revalidation.
    bad = action(sim, "J1").model_copy(
        update={"starts": (ApprovedStart(job_id="J1", start_slot=3),)}
    )
    assert sim.step(bad).rejection
    ep = episode(hand_jobs())
    changed = ep.jobs[0].model_copy(
        update={"job": ep.jobs[0].job.model_copy(update={"deadline_slot": 5})}
    )
    with pytest.raises(ValueError, match="conflicts"):
        sim.reset(ep.model_copy(update={"jobs": (changed, *ep.jobs[1:])}))
    assert sim.state().current_slot == 1


def test_arrival_at_boundary_is_waiting_and_can_start():
    job = hand_jobs()[1].model_copy(update={"arrival_slot": 2})
    sim = simulator(episode([job]))
    for _ in range(2):
        assert not sim.state().waiting_jobs
        sim.step(action(sim))
    assert sim.state().waiting_jobs == (job,)
    assert sim.step(action(sim, "J2")).rejection is None


@pytest.mark.parametrize("scenario", ["normal", "spike", "limited", "infeasible"])
def test_actual_d03_episode_consumer(scenario):
    from datetime import timedelta

    from dc_sustainability.data.scenarios import generate_episode
    from dc_sustainability.schemas import CarbonObservation
    from tests.contracts.fixtures import HAND_CARBON, SLOT0_UTC, semantics

    actuals = tuple(
        CarbonObservation(
            fact_id=f"FACT-PRIVATE-{slot}",
            value=HAND_CARBON[slot % 7],
            unit="g/kWh",
            source_id="SRC-HAND",
            valid_slot=slot,
            observed_at_utc=SLOT0_UTC + timedelta(hours=slot),
            semantics=semantics(),
            quality_status="unvalidated",
        )
        for slot in range(30)
    )
    snap = snapshot()
    snap = snap.model_copy(
        update={"constraints": tuple(c for c in snap.constraints if not c.applies_to_jobs)}
    )
    ep = generate_episode(
        scenario,
        seed=42,
        split="development",
        episode_id="EP-D03",
        snapshot=snap,
        realized_carbon=actuals,
    )
    sim = simulator(ep)
    # A simple test driver, not a proposed research policy: attempt one waiting job each slot.
    for _ in range(30):
        waiting = sim.state().waiting_jobs
        sim.step(action(sim, *((waiting[0].job_id,) if waiting else ())))
    result = sim.result(run_id="RUN-D03", system="greedy_a")
    assert set(result.completed_job_ids) | set(result.unfinished_job_ids) == {
        p.job.job_id for p in ep.jobs
    }
    if scenario == "infeasible":
        impossible = next(p.job.job_id for p in ep.jobs if p.intentionally_infeasible)
        assert impossible in result.deadline_missed_job_ids
    changed = ep.model_copy(update={"realized_carbon": (), "seed": 100})
    first = sim.reset(ep)
    assert sim.reset(changed) == first
