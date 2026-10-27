"""Real S01/A03 consumer checks on synthetic development episodes, no fake approvals.

Only the agreed no-completion-start input is used; no raw proposal may bypass S01.
These are rejection-path checks, not the unimplemented A04 gate or an agent episode.
"""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.simulator import SchedulingSimulator
from dc_sustainability.verification.checker import check_schedule
from tests.simulator.test_core import episode

SCENARIOS = ("normal", "spike", "limited", "infeasible")


def proposal(state, starts):
    return s.Plan(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        starts=tuple(s.PlannedStart(job_id=job_id, start_slot=slot) for job_id, slot in starts),
        status="proposed",
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_real_states_check_without_approval_and_rejected_plans_advance_30_slots(scenario):
    private = episode(scenario=scenario)
    simulator = SchedulingSimulator(allow_completion_starts=False)
    simulator.reset(private)
    for slot in range(30):
        state = simulator.state()
        assert state.current_slot == state.state_version == slot
        assert all(job.arrival_slot <= slot for job in state.waiting_jobs)
        assert not {"realized_carbon", "split", "seed", "scenario_id"} & state.model_dump().keys()
        # Use only an actually waiting job, never private future arrivals or an oracle.
        starts = ((state.waiting_jobs[0].job_id, slot),) if state.waiting_jobs and slot < 24 else ()
        plan = proposal(state, starts)
        check = check_schedule(plan, state, private.snapshot)
        omitted = {j.job_id for j in state.waiting_jobs} - {j for j, _ in starts}
        late = (
            bool(starts)
            and slot + state.waiting_jobs[0].duration_slots > state.waiting_jobs[0].deadline_slot
        )
        assert check.status == ("fail" if omitted or late else "pass")
        assert not check.errors
        if omitted:
            assert any(
                "omitted" in v.message and set(v.job_ids) == omitted for v in check.violations
            )
        if late:
            assert any(v.violation_type == "deadline" for v in check.violations)
        assert check.impact_claim_support == "unsupported"
        assert check.state_version == slot and check.plan_hash == plan.plan_hash
        if check.status != "pass":
            with pytest.raises(ValueError):
                s.ApprovedActions.from_checked_plan(plan, check, slot)
        else:
            assert s.ApprovedActions.from_checked_plan(plan, check, slot).state_version == slot

        # A raw model proposal cannot bypass S01's capability boundary. This is an
        # adversarial input, not a production execution-gate implementation.
        transition = simulator.step(plan)
        assert transition.rejection and "ApprovedActions" in transition.rejection
        assert transition.slot.started_job_ids == () and transition.slot.job_load_kw == 0
        assert transition.slot.background_load_kw == 40
        assert len(simulator.history) == simulator.state().current_slot == slot + 1

    result = simulator.result(run_id="RUN-INTAKE", system="agent")
    assert len(result.slots) == 30 and not result.completed_job_ids
    assert set(result.unfinished_job_ids) == {
        private_job.job.job_id for private_job in private.jobs
    }
    assert result.totals.job_energy_kwh is None  # S02/P01 not invented from load-only history.


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_future_job_from_private_episode_is_unknown_to_actual_visible_state(scenario):
    private = episode(scenario=scenario)
    simulator = SchedulingSimulator(allow_completion_starts=False)
    state = simulator.reset(private)
    future = next(
        private_job.job for private_job in private.jobs if private_job.job.arrival_slot > 0
    )
    assert future.job_id not in {job.job_id for job in state.waiting_jobs}
    plan = proposal(state, ((future.job_id, 0),))
    check = check_schedule(plan, state, private.snapshot)
    assert check.status == "fail"
    assert any(v.violation_type == "unknown_job" for v in check.violations)
    assert all(future.job_id not in item for e in check.evidence for item in e.ids)
    transition = simulator.step(plan)
    assert transition.rejection and transition.slot.started_job_ids == ()
    assert simulator.state().current_slot == 1


def test_retired_completion_start_setting_is_not_an_alternate_experiment():
    with pytest.raises(ValueError, match="Q01"):
        SchedulingSimulator(allow_completion_starts=True)
