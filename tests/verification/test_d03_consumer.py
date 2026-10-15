"""Actual A03 checks on D03 synthetic development jobs, never scientific acceptance.

The view builder below is a test fixture, not S01 or a runtime visibility boundary.
It uses no forecast, solver, policy, model, held-out data or private reference answer.
"""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data.scenarios import SOURCE, generate_jobs, hand_jobs
from dc_sustainability.verification.checker import check_schedule
from tests.contracts import fixtures as f

SCENARIOS = ("normal", "spike", "limited", "infeasible")


def constraints(jobs, *, capacity=100):
    """Explicit synthetic constraints from public job fields; no production adapter."""
    records = []
    if capacity is not None:
        records.append(
            s.Constraint(
                constraint_id="CON-D03-CAP",
                constraint_type="capacity",
                limit_value=capacity,
                unit="kW",
                applies_to_site="SITE1",
                source_id=SOURCE.source_id,
            )
        )
    for job in jobs:
        values = [("arrival", job.arrival_slot), ("deadline", job.deadline_slot)]
        if not job.flexible:
            values.append(("nonflexible", job.arrival_slot))
        for kind, value in values:
            records.append(
                s.Constraint(
                    constraint_id=f"CON-D03-{kind}-{job.job_id}",
                    constraint_type=kind,
                    limit_value=value,
                    unit="slot",
                    applies_to_jobs=(job.job_id,),
                    source_id=SOURCE.source_id,
                )
            )
    return s.ConstraintSnapshot(
        snapshot_id="SNAP-D03", site=f.site(pue=1.2), constraints=tuple(records), sources=(SOURCE,)
    )


def view(jobs, snapshot, current):
    return s.VisibleState.from_snapshot(
        snapshot,
        episode_id="EP-D03CHECK",
        current_slot=current,
        state_version=current,
        waiting_jobs=tuple(job for job in jobs if job.arrival_slot <= current),
        carbon_facts=(),
        missing_carbon_slots=tuple(range(current, min(current + 24, 30))),
    )


def proposal(state, starts):
    return s.Plan(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        starts=tuple(s.PlannedStart(job_id=job_id, start_slot=slot) for job_id, slot in starts),
        status="proposed",
    )


def outcome(result, name):
    return next(check.outcome for check in result.performed if check.name == name)


@pytest.fixture(params=SCENARIOS)
def generated(request):
    # This explicit seed is a test input, not an accepted experiment seed or Q06 choice.
    return generate_jobs(request.param, seed=42, split="development")


def test_arrival_starts_check_every_generated_job_without_approving(generated):
    jobs = tuple(private.job for private in generated)
    snapshot = constraints(jobs)
    original = tuple(private.to_json() for private in generated)
    for private in generated:
        job = private.job
        state = view(jobs, snapshot, job.arrival_slot)
        plan = proposal(state, ((job.job_id, job.arrival_slot),))
        result = check_schedule(plan, state, snapshot)
        assert outcome(result, "timing") == outcome(result, "nonflexible") == "pass"
        assert outcome(result, "capacity") == "pass"  # 40 background + at most 40 job kW
        if private.intentionally_infeasible:
            assert result.status == "fail" and outcome(result, "deadline") == "fail"
            assert any(v.violation_type == "deadline" for v in result.violations)
        else:
            assert outcome(result, "deadline") == "pass" and not result.violations
            assert result.status == "error" and any("Q02/Q03" in e for e in result.errors)
        assert result.impact_claim_support == "unsupported"
        assert s.CheckResult.from_json(result.to_json()) == result
        with pytest.raises(ValueError):
            s.ApprovedActions.from_checked_plan(plan, result, state.state_version)
    assert tuple(private.to_json() for private in generated) == original


def test_generated_nonflexible_work_cannot_be_delayed(generated):
    jobs = tuple(private.job for private in generated)
    job = next(job for job in jobs if not job.flexible)
    snapshot = constraints(jobs)
    state = view(jobs, snapshot, job.arrival_slot)
    result = check_schedule(proposal(state, ((job.job_id, job.arrival_slot + 1),)), state, snapshot)
    assert outcome(result, "nonflexible") == "fail"
    assert any(v.violation_type == "nonflexible_start" for v in result.violations)


def test_generated_backdated_start_fails_arrival_and_current_checks(generated):
    jobs = tuple(private.job for private in generated)
    job = next(job for job in jobs if job.arrival_slot > 0)
    snapshot = constraints(jobs)
    state = view(jobs, snapshot, job.arrival_slot)
    result = check_schedule(proposal(state, ((job.job_id, job.arrival_slot - 1),)), state, snapshot)
    assert {"start_before_arrival", "start_before_current"} <= {
        v.violation_type for v in result.violations
    }


def test_duplicate_generated_start_is_rejected_even_after_validation_bypass(generated):
    jobs = tuple(private.job for private in generated)
    job = jobs[0]
    snapshot = constraints(jobs)
    state = view(jobs, snapshot, job.arrival_slot)
    plan = proposal(state, ((job.job_id, job.arrival_slot),))
    bypassed = plan.model_copy(update={"starts": plan.starts * 2})
    with pytest.raises(ValueError):
        check_schedule(bypassed, state, snapshot)


def test_future_job_is_unknown_and_its_constraints_are_not_visible(generated):
    jobs = tuple(private.job for private in generated)
    future = next(job for job in jobs if job.arrival_slot > 0)
    snapshot = constraints(jobs)
    state = view(jobs, snapshot, 0)
    context = s.Context.build(state, snapshot, representation="flat")
    assert future.job_id not in {job.job_id for job in context.content.waiting_jobs}
    assert all(future.job_id not in c.applies_to_jobs for c in context.content.constraints)
    assert not {"scenario_id", "split", "seed", "synthetic"} & state.model_dump().keys()
    result = check_schedule(proposal(state, ((future.job_id, 0),)), state, snapshot)
    assert outcome(result, "ids") == "fail"
    assert any(v.violation_type == "unknown_job" for v in result.violations)
    assert all(future.job_id not in item for e in result.evidence for item in e.ids)


def test_generated_job_capacity_boundary_uses_constraint_and_it_load_before_pue(generated):
    jobs = tuple(private.job for private in generated)
    job = next(private.job for private in generated if not private.intentionally_infeasible)
    for capacity, expected in ((40 + job.power_kw, "pass"), (39 + job.power_kw, "fail")):
        snapshot = constraints(jobs, capacity=capacity)
        state = view(jobs, snapshot, job.arrival_slot)
        result = check_schedule(proposal(state, ((job.job_id, job.arrival_slot),)), state, snapshot)
        assert outcome(result, "capacity") == expected
        violations = [v for v in result.violations if v.violation_type == "capacity"]
        assert [v.slot for v in violations] == (
            list(range(job.arrival_slot, job.arrival_slot + job.duration_slots))
            if expected == "fail"
            else []
        )
        assert all(v.constraint_ids == ("CON-D03-CAP",) for v in violations)


def test_missing_capacity_never_becomes_unlimited_for_generated_jobs(generated):
    jobs = tuple(private.job for private in generated)
    job = jobs[0]
    snapshot = constraints(jobs, capacity=None)
    state = view(jobs, snapshot, job.arrival_slot)
    result = check_schedule(proposal(state, ((job.job_id, job.arrival_slot),)), state, snapshot)
    assert outcome(result, "capacity") == result.status == "error"
    assert next(e.status for e in result.evidence if e.kind == "capacity") == "missing"


def test_d03_hand_jobs_preserve_known_capacity_and_impossible_deadline_results():
    jobs = hand_jobs()
    snapshot = constraints(jobs)
    state = view(jobs, snapshot, 0)
    overlapping = check_schedule(proposal(state, (("J1", 0), ("J2", 0))), state, snapshot)
    assert outcome(overlapping, "capacity") == "fail"
    assert [v.slot for v in overlapping.violations if v.violation_type == "capacity"] == [0, 1]
    sequential = check_schedule(proposal(state, (("J1", 0), ("J2", 2))), state, snapshot)
    assert outcome(sequential, "capacity") == "pass" and sequential.status == "error"
    state = view(jobs, snapshot, 4)
    impossible = check_schedule(proposal(state, (("J3", 4),)), state, snapshot)
    assert outcome(impossible, "deadline") == impossible.status == "fail"
