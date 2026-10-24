"""Independent expected outcomes for real A03 logic, using labeled synthetic F02 inputs."""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.verification.checker import check_schedule
from tests.contracts import fixtures as f


def state(snapshot=None, *, current=0, waiting=None, running=(), completed=(), **fields):
    snapshot = snapshot or f.snapshot()
    return s.VisibleState.from_snapshot(
        snapshot,
        episode_id=f.EPISODE_ID,
        current_slot=current,
        state_version=current,
        waiting_jobs=tuple(waiting if waiting is not None else (f.jobs()["J1"], f.jobs()["J2"])),
        running_jobs=running,
        completed_jobs=completed,
        **fields,
    )


def plan(view, starts=(), **fields):
    return s.Plan(
        episode_id=view.episode_id,
        slot=view.current_slot,
        state_version=view.state_version,
        starts=tuple(s.PlannedStart(job_id=j, start_slot=t) for j, t in starts),
        status="proposed",
        **fields,
    )


def outcome(result, name):
    return next(c.outcome for c in result.performed if c.name == name)


def test_sequential_hand_plan_passes_all_agreed_physical_checks():
    snap = f.snapshot()
    view = state(snap)
    proposal = plan(view, (("J1", 0), ("J2", 2)))
    before = view.to_json()
    result = check_schedule(proposal, view, snap)
    assert all(c.outcome == "pass" for c in result.performed)
    assert result.status == "pass" and not result.violations
    assert result.plan_hash == proposal.plan_hash and result.state_version == view.state_version
    assert view.to_json() == before
    assert s.CheckResult.from_json(result.to_json()) == result
    assert s.ApprovedActions.from_checked_plan(proposal, result, view.state_version).starts == (
        s.ApprovedStart(job_id="J1", start_slot=0),
    )


def test_consumer_reads_committed_f02_examples_without_changing_the_contract():
    proposal = s.Plan.from_json((f.EXAMPLES_DIR / "plan.json").read_text())
    view = s.VisibleState.from_json((f.EXAMPLES_DIR / "visible_state.json").read_text())
    snap = s.ConstraintSnapshot.from_json((f.EXAMPLES_DIR / "constraint_snapshot.json").read_text())
    result = check_schedule(proposal, view, snap)
    assert outcome(result, "capacity") == "pass"
    assert result.status == "pass" and not result.violations
    assert result.impact_claim_support == "unsupported"  # fixture semantics are unresolved


def test_exact_it_capacity_before_pue_is_allowed():
    snap = f.snapshot(pue=1.2)
    j2 = f.jobs()["J2"].model_copy(update={"power_kw": 20.0})
    view = state(snap, waiting=(f.jobs()["J1"], j2))
    result = check_schedule(plan(view, (("J1", 0), ("J2", 0))), view, snap)
    assert outcome(result, "capacity") == "pass"  # 40 + 40 + 20 = 100, not 120


def test_overlap_overload_reports_actual_slots_and_constraint():
    snap = f.snapshot()
    view = state(snap)
    result = check_schedule(plan(view, (("J1", 0), ("J2", 0))), view, snap)
    assert result.status == "fail"
    violations = [v for v in result.violations if v.violation_type == "capacity"]
    assert [v.slot for v in violations] == [0, 1]
    assert all(v.constraint_ids == ("CON-CAP-01",) and "110" in v.message for v in violations)


def test_constraint_change_100_to_70_changes_actual_check_without_code_change():
    for capacity, expected in ((100, "pass"), (70, "fail")):
        snap = f.snapshot(capacity_kw=capacity)
        view = state(snap, waiting=(f.jobs()["J1"],))
        assert outcome(check_schedule(plan(view, (("J1", 0),)), view, snap), "capacity") == expected


def test_running_work_counts_and_cannot_be_rescheduled():
    snap = f.snapshot()
    running = s.RunningJobView(job=f.jobs()["J1"], start_slot=0)
    view = state(snap, current=1, waiting=(f.jobs()["J2"],), running=(running,))
    result = check_schedule(plan(view, (("J2", 1),)), view, snap)
    assert outcome(result, "capacity") == "fail"
    assert result.violations[0].job_ids == ("J1", "J2")
    result = check_schedule(plan(view, (("J1", 1),)), view, snap)
    assert outcome(result, "ids") == "fail"


def test_half_open_interval_does_not_count_finished_work():
    snap = f.snapshot()
    completed = s.CompletedJobView(job_id="J1", start_slot=0, end_slot=2)
    view = state(snap, current=2, waiting=(f.jobs()["J2"],), completed=(completed,))
    result = check_schedule(plan(view, (("J2", 2),)), view, snap)
    assert outcome(result, "capacity") == "pass"


@pytest.mark.parametrize("start,expected", [(4, "pass"), (5, "fail")])
def test_deadline_is_completion_boundary(start, expected):
    snap = f.snapshot()
    view = state(snap, waiting=(f.jobs()["J1"],))
    result = check_schedule(plan(view, (("J1", start),)), view, snap)
    assert outcome(result, "deadline") == expected
    if expected == "fail":
        assert result.violations[0].constraint_ids == ("CON-DL-J1",)


def test_start_before_arrival_and_current_are_distinct_violations():
    snap = f.snapshot()
    j3 = f.jobs()["J3"]
    view = state(snap, current=4, waiting=(j3,))
    result = check_schedule(plan(view, (("J3", 3),)), view, snap)
    kinds = {v.violation_type for v in result.violations}
    assert {"start_before_arrival", "start_before_current"} <= kinds
    view = state(snap, current=3, waiting=(f.jobs()["J1"],))
    result = check_schedule(plan(view, (("J1", 2),)), view, snap)
    assert {v.violation_type for v in result.violations} == {"start_before_current"}


def test_nonflexible_delay_fails():
    snap = f.snapshot()
    job = f.jobs()["J1"].model_copy(update={"flexible": False})
    view = state(snap, waiting=(job,))
    result = check_schedule(plan(view, (("J1", 1),)), view, snap)
    assert outcome(result, "nonflexible") == "fail"


@pytest.mark.parametrize("invalid", [True, 0.5, float("nan"), float("inf")])
def test_checker_revalidates_bypassed_invalid_start_types(invalid):
    snap = f.snapshot()
    view = state(snap)
    bad_start = s.PlannedStart.model_construct(job_id="J1", start_slot=invalid)
    bad = plan(view).model_copy(update={"starts": (bad_start,)})
    with pytest.raises(ValueError):
        check_schedule(bad, view, snap)


def test_duplicate_start_rejected_at_boundary():
    view = state()
    bad = plan(view, (("J1", 0),))
    bad = bad.model_copy(update={"starts": bad.starts * 2})
    with pytest.raises(ValueError):
        check_schedule(bad, view, f.snapshot())


def test_unknown_job_fails_without_looking_up_future_jobs():
    view = state()
    result = check_schedule(plan(view, (("J99", 0),)), view, f.snapshot())
    assert outcome(result, "ids") == "fail"
    assert result.violations[0].job_ids == ("J99",)
    assert "CON-DL-J3" not in {i for e in result.evidence for i in e.ids}


def test_missing_capacity_is_error_not_infinite_capacity():
    snap = f.snapshot(include_capacity=False)
    view = state(snap)
    result = check_schedule(plan(view, (("J1", 0),)), view, snap)
    assert outcome(result, "capacity") == "error"
    assert result.status == "error"
    assert next(e.status for e in result.evidence if e.kind == "capacity") == "missing"


def test_fabricated_citations_never_override_real_capacity():
    snap = f.snapshot(capacity_kw=70)
    view = state(snap)
    result = check_schedule(plan(view, (("J1", 0),), evidence_ids=("CON-FAKE",)), view, snap)
    assert outcome(result, "evidence") == outcome(result, "capacity") == "fail"


def test_missing_carbon_does_not_fail_capacity_or_support_savings():
    view = state(missing_carbon_slots=tuple(range(24)))
    result = check_schedule(plan(view, (("J1", 0),)), view, f.snapshot())
    assert outcome(result, "capacity") == "pass"
    assert result.impact_claim_support == "unsupported"
    assert any(c.name == "freshness" and "Q04" in c.reason for c in result.skipped)


def test_impossible_deadline_remains_real_violation_not_a_silent_omission_rule():
    snap = f.snapshot()
    view = state(snap, current=4, waiting=(f.jobs()["J3"],))
    result = check_schedule(plan(view, (("J3", 4),)), view, snap)
    assert result.status == "fail"
    assert outcome(result, "deadline") == "fail"


@pytest.mark.parametrize(
    "field,value", [("state_version", 5), ("episode_id", "EP-OTHER"), ("slot", 3)]
)
def test_proposal_state_binding_mismatch_is_error(field, value):
    view = state()
    result = check_schedule(plan(view).model_copy(update={field: value}), view, f.snapshot())
    assert result.status == "error" and outcome(result, "ids") == "error"


def test_authoritative_job_constraint_conflict_is_not_ignored():
    snap = f.snapshot()
    snap = snap.model_copy(
        update={
            "constraints": tuple(
                c.model_copy(update={"limit_value": 5.0}) if c.constraint_id == "CON-DL-J1" else c
                for c in snap.constraints
            )
        }
    )
    view = state(snap)
    result = check_schedule(plan(view, (("J1", 0),)), view, snap)
    assert outcome(result, "evidence") == "error"
    assert "conflicts" in result.errors[0]


def test_agreed_completion_start_prohibition_is_a_real_failure():
    snap = f.snapshot()
    job = s.Job(
        job_id="J4", arrival_slot=17, duration_slots=2, power_kw=20, deadline_slot=30, flexible=True
    )
    view = state(snap, current=23, waiting=(job,))
    result = check_schedule(plan(view, (("J4", 24),)), view, snap)
    assert outcome(result, "capacity") == "pass"
    assert result.status == "fail" and any("Q01" in v.message for v in result.violations)
