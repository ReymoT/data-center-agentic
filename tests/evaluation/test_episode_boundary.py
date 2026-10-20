"""Synthetic hand checks of the proposal's fixed end at boundary 30."""

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import validator as v
from tests.contracts import fixtures as f


def inputs():
    late = s.Job(
        job_id="LATE",
        arrival_slot=22,
        duration_slots=8,
        power_kw=20,
        deadline_slot=40,
        flexible=True,
    )
    snapshot = f.snapshot()
    state = s.VisibleState.from_snapshot(
        snapshot, episode_id=f.EPISODE_ID, current_slot=22, state_version=22, waiting_jobs=(late,)
    )
    return v.facts_from_state(state, snapshot)


def test_episode_boundary_is_not_extended_by_a_later_job_deadline():
    plan = s.Plan(
        episode_id=f.EPISODE_ID,
        slot=22,
        state_version=22,
        starts=(s.PlannedStart(job_id="LATE", start_slot=23),),
        status="proposed",
    )
    result = v.validate_plan(plan, inputs(), v.Q03_DRAFT)
    assert result.status == "invalid"
    assert [x.code for x in result.findings] == ["episode_horizon"]
    # Starting now ends exactly at 30 and is legal.
    on_time = plan.model_copy(update={"starts": (s.PlannedStart(job_id="LATE", start_slot=22),)})
    assert v.validate_plan(on_time, inputs(), v.Q03_DRAFT).valid


def test_deferral_cannot_push_completion_past_the_episode():
    plan = s.Plan(
        episode_id=f.EPISODE_ID,
        slot=22,
        state_version=22,
        deferrals=(s.Deferral(job_id="LATE", reason="waiting_for_lower_carbon"),),
        status="proposed",
    )
    result = v.validate_plan(plan, inputs(), v.Q03_DRAFT)
    assert [x.code for x in result.findings] == ["invalid_deferral"]
