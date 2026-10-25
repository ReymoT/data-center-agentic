"""Greedy B's accepted Q01/Q04 boundaries, using real policy/checker code."""

from datetime import datetime, timedelta, timezone

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.policies import propose
from dc_sustainability.verification.checker import check_schedule
from tests.contracts import fixtures as f


def job(job_id="JWAIT", **updates):
    return s.Job(**(f.jobs()["J2"].model_dump(mode="python") | {"job_id": job_id} | updates))


def facts(slots, *, age=0, decision_time=f.SLOT0_UTC):
    return tuple(
        s.CarbonForecast(
            fact_id=f"FACT-GB-{slot}",
            value=value,
            unit="g/kWh",
            source_id=f.SOURCE_ID,
            valid_slot=slot,
            issued_at_utc=decision_time - timedelta(hours=age),
            forecast_kind="perfect_foresight",
            semantics=f.semantics(),
            quality_status="unvalidated",
        )
        for slot, value in slots
    )


def inputs(jobs, carbon=(), *, current=0, running=()):
    snapshot = f.snapshot()
    state = s.VisibleState.from_snapshot(
        snapshot,
        episode_id=f.EPISODE_ID,
        current_slot=current,
        state_version=current,
        waiting_jobs=tuple(jobs),
        running_jobs=tuple(running),
        carbon_facts=tuple(carbon),
    )
    return state, s.Context.build(state, snapshot, "flat"), snapshot


@pytest.mark.parametrize("system", ["greedy_a", "greedy_b"])
@pytest.mark.parametrize("flexible", [True, False])
@pytest.mark.parametrize("duration,expected", [(7, (23,)), (8, ())])
def test_completion_boundary_never_proposes_or_scores_occupancy_after_slot_29(
    system, flexible, duration, expected
):
    state, context, snapshot = inputs(
        (job(arrival_slot=23, flexible=flexible, duration_slots=duration, deadline_slot=40),),
        facts(
            ((slot, 400) for slot in range(23, 30)),
            decision_time=f.SLOT0_UTC + timedelta(hours=23),
        ),
        current=23,
    )
    output = propose(
        state, context, system=system, decision_time_utc=f.SLOT0_UTC + timedelta(hours=23)
    )
    assert tuple(x.start_slot for x in output.plan.starts) == expected
    assert check_schedule(output.plan, state, snapshot).status == "pass"


@pytest.mark.parametrize(
    "age,expected_system,expected_start", [(2, "greedy_b", 2), (3, "greedy_a", 0)]
)
def test_exact_freshness_boundary_uses_trusted_time(age, expected_system, expected_start):
    state, context, snapshot = inputs(
        (job(duration_slots=1, deadline_slot=3),), facts(enumerate((300, 200, 100)), age=age)
    )
    output = propose(state, context, system="greedy_b", decision_time_utc=f.SLOT0_UTC)
    assert output.system == expected_system
    assert output.plan.starts[0].start_slot == expected_start
    assert check_schedule(output.plan, state, snapshot).status == "pass"
    if age == 3:
        assert output.explanation.summary == "stale"
        assert not output.explanation.claims


def test_partial_union_falls_back_for_whole_decision_without_shortening_windows():
    state, context, snapshot = inputs(
        (
            job("JA", duration_slots=1, deadline_slot=3),
            job("JB", duration_slots=1, deadline_slot=4),
        ),
        facts(enumerate((900, 500, 100))),  # slot 3 needed by JB is absent
    )
    output = propose(state, context, system="greedy_b", decision_time_utc=f.SLOT0_UTC)
    assert output.system == "greedy_a"
    assert output.plan == propose(state, context).plan
    assert output.plan.status == "proposed"
    assert output.explanation.summary == "partial" and not output.explanation.claims
    assert check_schedule(output.plan, state, snapshot).status == "pass"


def test_known_running_load_excludes_an_illegal_candidate_from_required_forecast_union():
    running = s.RunningJobView(job=job("JRUN", power_kw=30), start_slot=0)
    state, context, snapshot = inputs(
        (job(power_kw=40, duration_slots=1, deadline_slot=4),),
        facts(((2, 100), (3, 500))),
        current=1,
        running=(running,),
    )
    output = propose(
        state, context, system="greedy_b", decision_time_utc=f.SLOT0_UTC + timedelta(hours=1)
    )
    assert output.system == "greedy_b" and output.explanation is None
    assert output.plan.starts[0].start_slot == 2
    assert check_schedule(output.plan, state, snapshot).status == "pass"


@pytest.mark.parametrize(
    "time",
    [None, datetime(2022, 1, 1), datetime(2022, 1, 1, tzinfo=timezone(timedelta(hours=1))), "UTC"],
)
def test_greedy_b_does_not_guess_missing_naive_or_non_utc_decision_time(time):
    state, context, _ = inputs((job(),))
    with pytest.raises(ValueError, match="trusted UTC"):
        propose(state, context, system="greedy_b", decision_time_utc=time)


def test_no_waiting_jobs_do_not_create_spurious_forecast_fallback():
    state, context, snapshot = inputs(())
    output = propose(state, context, system="greedy_b", decision_time_utc=f.SLOT0_UTC)
    assert output.system == "greedy_b" and output.explanation is None
    assert not output.plan.starts and not output.plan.abstentions
    assert check_schedule(output.plan, state, snapshot).status == "pass"
