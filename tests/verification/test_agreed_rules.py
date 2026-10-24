"""Hand-derived Q01-Q04 outcomes; synthetic inputs, no evaluator or model oracle."""

from datetime import timedelta

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.verification.checker import check_schedule
from dc_sustainability.verification.rules import assess_forecasts
from tests.contracts import fixtures as f
from tests.verification.test_checker import plan, state


def abstain(job_id=None, reason="other"):
    return s.Abstention(job_id=job_id, reason=reason, detail="no_legal_start")


def test_complete_sequential_plan_is_physically_checked_without_certifying_savings():
    view = state()
    result = check_schedule(plan(view, (("J1", 0), ("J2", 2))), view, f.snapshot())
    assert result.status == "pass" and not result.errors and not result.violations
    assert result.impact_claim_support == "unsupported"
    assert s.ApprovedActions.from_checked_plan(
        plan(view, (("J1", 0), ("J2", 2))), result, 0
    ).starts == (s.ApprovedStart(job_id="J1", start_slot=0),)


def test_omission_is_a_real_failure():
    view = state()
    result = check_schedule(plan(view, (("J1", 0),)), view, f.snapshot())
    assert result.status == "fail"
    assert any(v.job_ids == ("J2",) and "omitted" in v.message for v in result.violations)


@pytest.mark.parametrize("kind", ["duplicate", "defer_and_abstain", "whole_and_start"])
def test_multiple_outcomes_are_rejected(kind):
    view = state(waiting=(f.jobs()["J1"],))
    fields = {
        "duplicate": {"abstentions": (abstain("J1"), abstain("J1"))},
        "defer_and_abstain": {
            "deferrals": (s.Deferral(job_id="J1", reason="capacity"),),
            "abstentions": (abstain("J1"),),
        },
        "whole_and_start": {"starts": (("J1", 0),), "abstentions": (abstain(),)},
    }[kind]
    starts = fields.pop("starts", ())
    result = check_schedule(plan(view, starts, **fields), view, f.snapshot())
    assert result.status == "fail"
    assert next(c.outcome for c in result.performed if c.name == "ids") == "fail"


def test_legal_deferral_has_a_later_opportunity():
    view = state(waiting=(f.jobs()["J1"],))
    proposal = plan(view, deferrals=(s.Deferral(job_id="J1", reason="capacity"),))
    assert check_schedule(proposal, view, f.snapshot()).status == "pass"


def test_deferral_cannot_ignore_occupancy_of_new_current_starts():
    jobs = (
        s.Job(
            job_id="RUN",
            arrival_slot=0,
            duration_slots=4,
            power_kw=40,
            deadline_slot=4,
            flexible=True,
        ),
        s.Job(
            job_id="WAIT",
            arrival_slot=0,
            duration_slots=1,
            power_kw=40,
            deadline_slot=2,
            flexible=True,
        ),
    )
    view = state(waiting=jobs)
    proposal = plan(view, (("RUN", 0),), deferrals=(s.Deferral(job_id="WAIT", reason="capacity"),))
    result = check_schedule(proposal, view, f.snapshot())
    assert result.status == "fail"
    assert any(
        v.job_ids == ("WAIT",) and "no later legal start" in v.message for v in result.violations
    )


@pytest.mark.parametrize("nonflexible", [False, True])
def test_last_opportunity_and_nonflexible_job_cannot_be_deferred(nonflexible):
    job = s.Job(
        job_id="LAST",
        arrival_slot=0,
        duration_slots=1,
        power_kw=10,
        deadline_slot=1 if not nonflexible else 5,
        flexible=not nonflexible,
    )
    view = state(waiting=(job,))
    proposal = plan(view, deferrals=(s.Deferral(job_id="LAST", reason="other"),))
    result = check_schedule(proposal, view, f.snapshot())
    assert result.status == "fail"
    assert any("no later legal start" in v.message for v in result.violations)


def test_impossible_arrival_is_justified_but_feasible_neighbour_must_be_covered():
    impossible = s.Job(
        job_id="IMP", arrival_slot=0, duration_slots=3, power_kw=10, deadline_slot=2, flexible=True
    )
    view = state(waiting=(impossible, f.jobs()["J1"]))
    mixed = plan(view, (("J1", 0),), abstentions=(abstain("IMP"),))
    assert check_schedule(mixed, view, f.snapshot()).status == "pass"
    blanket = check_schedule(plan(view, abstentions=(abstain(),)), view, f.snapshot())
    assert blanket.status == "fail"
    assert any(v.job_ids == ("J1",) for v in blanket.violations)


def test_joint_contention_does_not_justify_individual_abstentions():
    # Each 40 kW job fits alone over 40 kW background, but both need this sole slot.
    jobs = tuple(
        s.Job(
            job_id=j, arrival_slot=0, duration_slots=1, power_kw=40, deadline_slot=1, flexible=True
        )
        for j in ("A", "B")
    )
    view = state(waiting=jobs)
    result = check_schedule(plan(view, abstentions=(abstain(),)), view, f.snapshot())
    assert result.status == "fail"
    assert {j for v in result.violations for j in v.job_ids} == {"A", "B"}


def test_missing_carbon_is_not_physical_infeasibility():
    view = state(waiting=(f.jobs()["J1"],), missing_carbon_slots=tuple(range(24)))
    result = check_schedule(
        plan(view, abstentions=(abstain("J1", "stale_evidence"),)), view, f.snapshot()
    )
    assert result.status == "fail"
    assert check_schedule(plan(view, (("J1", 0),)), view, f.snapshot()).status == "pass"


def test_missing_capacity_cannot_produce_an_execution_pass():
    snapshot = f.snapshot(include_capacity=False)
    view = state(snapshot, waiting=(f.jobs()["J1"],))
    result = check_schedule(
        plan(view, abstentions=(abstain("J1", "missing_evidence"),)), view, snapshot
    )
    assert result.status == "error" and result.errors


def test_completion_start_is_forbidden_even_when_its_finish_fits():
    job = s.Job(
        job_id="EDGE",
        arrival_slot=17,
        duration_slots=2,
        power_kw=10,
        deadline_slot=30,
        flexible=True,
    )
    view = state(current=23, waiting=(job,))
    result = check_schedule(plan(view, (("EDGE", 24),)), view, f.snapshot())
    assert result.status == "fail"
    assert any("Q01" in v.message for v in result.violations)


def forecast_view(*, issued=0, missing=(), job=None):
    facts = tuple(x for x in f.forecasts(issued_slot=issued) if x.valid_slot not in missing)
    return state(waiting=(job or f.jobs()["J1"],), carbon_facts=facts)


def test_required_forecast_union_does_not_shrink_to_the_proposed_start():
    view = forecast_view()
    assessment = assess_forecasts(view, f.snapshot(), decision_time_utc=f.SLOT0_UTC)
    # A two-slot job ending by six has starts 0..4 and occupied union 0..5.
    assert assessment.required_slots == (0, 1, 2, 3, 4, 5)
    assert assessment.usable


@pytest.mark.parametrize("issued,reason", [(-2, None), (-3, "stale"), (1, "future_issued")])
def test_freshness_exact_two_slot_edge_and_future_issue(issued, reason):
    result = assess_forecasts(
        forecast_view(issued=issued), f.snapshot(), decision_time_utc=f.SLOT0_UTC
    )
    assert result.reasons == (() if reason is None else (reason,))
    assert result.usable is (reason is None)


def test_partial_required_coverage_requires_whole_decision_fallback():
    result = assess_forecasts(
        forecast_view(missing=(5,)), f.snapshot(), decision_time_utc=f.SLOT0_UTC
    )
    assert result.required_slots == tuple(range(6))
    assert result.missing_slots == (5,) and result.reasons == ("missing",)


def test_occupied_window_beyond_horizon_is_not_truncated():
    job = s.Job(
        job_id="LONG",
        arrival_slot=0,
        duration_slots=7,
        power_kw=10,
        deadline_slot=30,
        flexible=True,
    )
    result = assess_forecasts(forecast_view(job=job), f.snapshot(), decision_time_utc=f.SLOT0_UTC)
    assert result.required_slots == tuple(range(30))
    assert result.beyond_horizon_slots == tuple(range(24, 30))
    assert "beyond_horizon" in result.reasons


def test_forecast_time_must_be_explicit_utc_and_capacity_must_exist():
    view = forecast_view()
    with pytest.raises(ValueError, match="UTC"):
        assess_forecasts(view, f.snapshot(), decision_time_utc=f.SLOT0_UTC.replace(tzinfo=None))
    snapshot = f.snapshot(include_capacity=False)
    view = state(snapshot, waiting=(f.jobs()["J1"],))
    with pytest.raises(s.MissingEvidenceError):
        assess_forecasts(view, snapshot, decision_time_utc=f.SLOT0_UTC + timedelta(hours=1))
