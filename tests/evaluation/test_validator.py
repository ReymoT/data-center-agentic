"""E01 hand-truth tests for the independent validator.

Expected outcomes are worked out by hand from the rules (site 40 kW background, 100 kW
capacity, J1 40 kW x 2, J2 30 kW x 2, deadlines at slot 6), not taken from the
production checker. Synthetic fixtures only.
"""

import ast
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data import scenarios
from dc_sustainability.evaluation import validator as v
from dc_sustainability.evaluation.validator import Q03_DRAFT, DecisionFacts
from tests.contracts import fixtures as f

JOBS = f.jobs()


def job(job_id, arrival=0, duration=2, power=30.0, deadline=6, flexible=True):
    return s.Job(
        job_id=job_id,
        arrival_slot=arrival,
        duration_slots=duration,
        power_kw=power,
        deadline_slot=deadline,
        flexible=flexible,
    )


def facts(slot=0, waiting=("J1", "J2"), running=None, capacity=100.0, extra=()):
    waiting_jobs = {j: JOBS[j] for j in waiting}
    waiting_jobs.update({j.job_id: j for j in extra})
    evidence = {"FACT-SITE-BG", "FACT-SITE-PUE", "FACT-SITE-SLOTH", "CON-CAP-01"}
    evidence |= {f"FACT-JOB-{j}" for j in waiting_jobs}
    return DecisionFacts(
        episode_id=f.EPISODE_ID,
        slot=slot,
        state_version=slot,
        waiting=waiting_jobs,
        running=running or {},
        unavailable_ids=frozenset(),
        background_kw=40.0,
        capacity_kw=capacity,
        evidence_ids=frozenset(evidence),
    )


def plan(slot=0, starts=(), deferrals=(), abstentions=(), evidence_ids=()):
    return s.Plan(
        episode_id=f.EPISODE_ID,
        slot=slot,
        state_version=slot,
        starts=tuple(s.PlannedStart(job_id=j, start_slot=t) for j, t in starts),
        deferrals=tuple(s.Deferral(job_id=j, reason="waiting_for_lower_carbon") for j in deferrals),
        abstentions=tuple(
            s.Abstention(job_id=j, reason="infeasible_deadline") for j in abstentions
        ),
        evidence_ids=evidence_ids,
        status="proposed",
    )


def check(p, decision_facts, protocol=Q03_DRAFT):
    return v.validate_plan(p, decision_facts, protocol)


def codes(result):
    return sorted(finding.code for finding in result.findings)


# ----------------------------------------------------------------- valid baselines
def test_hand_plan_run_as_soon_as_feasible_is_valid():
    result = check(f.plan(), facts())
    assert result.status == "valid" and result.findings == ()
    assert result.protocol == Q03_DRAFT.name


def test_deferring_flexible_jobs_with_later_slots_is_valid():
    assert check(plan(deferrals=("J1", "J2")), facts()).valid


# ----------------------------------------------------------------- coverage (Q03.1)
def test_omitted_waiting_job_is_invalid():
    result = check(plan(starts=[("J1", 0)]), facts())
    assert codes(result) == ["omitted_job"]
    assert result.findings[0].job_id == "J2"


def test_unknown_job_is_not_a_waiting_job_and_does_not_cover_others():
    result = check(plan(starts=[("J1", 0), ("J9", 2)]), facts())
    assert codes(result) == ["not_waiting_job", "omitted_job"]


def test_job_both_deferred_and_abstained_is_a_duplicate():
    p = plan(starts=[("J2", 2)], deferrals=("J1",), abstentions=("J1",))
    assert "duplicate_job" in codes(check(p, facts()))


def test_running_job_cannot_be_started_again():
    running = {"J1": (JOBS["J1"], 0)}
    result = check(plan(slot=1, starts=[("J1", 1), ("J2", 2)]), facts(1, ("J2",), running))
    assert codes(result) == ["not_waiting_job"]


def test_empty_queue_requires_a_no_op():
    assert check(plan(slot=10), facts(10, ())).status == "valid"
    assert codes(check(plan(slot=10, deferrals=("J1",)), facts(10, ()))) == ["empty_queue_not_noop"]
    assert check(plan(slot=10), facts(10, ())).empty_queue


# ----------------------------------------------------------------- timing
def test_deadline_is_a_completion_boundary():
    # 5 + 2 = 7 > 6; 4 + 2 = 6 is allowed.
    assert "deadline" in codes(check(plan(starts=[("J1", 5), ("J2", 0)]), facts()))
    assert check(plan(starts=[("J1", 4), ("J2", 0)]), facts()).valid


def test_start_before_current_slot_is_invalid():
    result = check(plan(slot=2, starts=[("J1", 1), ("J2", 2)]), facts(2))
    assert codes(result) == ["capacity", "start_before_current"]


def test_start_before_arrival_is_invalid():
    late = job("J5", arrival=3)
    result = check(plan(starts=[("J1", 0), ("J2", 2), ("J5", 2)]), facts(extra=[late]))
    assert "start_before_arrival" in codes(result)


def test_q01_no_new_start_after_slot_23():
    long = job("J7", arrival=20, duration=1, power=10, deadline=30)
    result = check(plan(slot=20, starts=[("J7", 24)]), facts(20, (), extra=[long]))
    assert codes(result) == ["start_after_last_start"]
    assert check(plan(slot=20, starts=[("J7", 23)]), facts(20, (), extra=[long])).valid


def test_nonflexible_job_must_start_at_arrival():
    fixed = job("N1", arrival=0, power=20, flexible=False)
    assert "nonflexible_start" in codes(
        check(plan(starts=[("N1", 1)], deferrals=("J1", "J2")), facts(extra=[fixed]))
    )


# ----------------------------------------------------------------- capacity
def test_overlap_above_capacity_fails_in_each_overloaded_slot():
    # 40 + 40 + 30 = 110 kW > 100 kW in slots 0 and 1.
    result = check(plan(starts=[("J1", 0), ("J2", 0)]), facts())
    assert [(x.code, x.slot) for x in result.findings] == [("capacity", 0), ("capacity", 1)]


def test_running_work_counts_toward_capacity():
    running = {"J1": (JOBS["J1"], 0)}  # occupies slots 0 and 1
    assert codes(check(plan(slot=1, starts=[("J2", 1)]), facts(1, ("J2",), running))) == [
        "capacity"
    ]
    assert check(plan(slot=1, starts=[("J2", 2)]), facts(1, ("J2",), running)).valid


def test_future_intentions_count_toward_capacity():
    result = check(plan(starts=[("J1", 3), ("J2", 3)]), facts())
    assert [(x.code, x.slot) for x in result.findings] == [("capacity", 3), ("capacity", 4)]


def test_start_without_capacity_evidence_is_unverifiable():
    result = check(f.plan(), facts(capacity=None))
    assert codes(result) == ["capacity_unverifiable"]


# ----------------------------------------------------------------- deferral (Q03.2)
def test_deferral_at_last_legal_start_is_invalid():
    # At slot 4, J1's only later start would be 5, and 5 + 2 > 6.
    result = check(plan(slot=4, starts=[("J2", 4)], deferrals=("J1",)), facts(4))
    assert codes(result) == ["invalid_deferral"]
    assert result.findings[0].job_id == "J1"
    # One slot earlier, slot 4 is still available, so the deferral is valid.
    assert check(plan(slot=3, starts=[("J2", 3)], deferrals=("J1",)), facts(3)).valid


def test_deferral_at_slot_23_is_invalid_under_q01():
    long = job("J7", arrival=20, duration=1, power=10, deadline=30)
    result = check(plan(slot=23, deferrals=("J7",)), facts(23, (), extra=[long]))
    assert codes(result) == ["invalid_deferral"]


def test_nonflexible_job_cannot_be_deferred():
    fixed = job("N1", arrival=0, power=20, flexible=False)
    result = check(plan(deferrals=("J1", "J2", "N1")), facts(extra=[fixed]))
    assert codes(result) == ["invalid_deferral"]


# ----------------------------------------------------------------- abstention (Q03.3)
def test_abstaining_from_an_infeasible_job_is_justified():
    # J3 arrives at 4 and needs 3 slots: earliest finish 7 > deadline 6.
    result = check(f.abstention_plan(), facts(4, ("J3",)))
    assert result.valid and result.justified_abstentions == ("J3",)


def test_abstaining_from_a_feasible_job_is_pending_not_credited():
    result = check(plan(starts=[("J2", 0)], abstentions=("J1",)), facts())
    assert result.status == "pending"
    assert codes(result) == ["joint_infeasibility_not_assessed"]
    assert result.justified_abstentions == ()


def test_pending_never_hides_a_real_failure():
    result = check(plan(starts=[("J2", 5)], abstentions=("J1",)), facts())
    assert result.status == "invalid"


def test_whole_decision_abstention_needs_every_job_justified():
    p = s.Plan(
        episode_id=f.EPISODE_ID,
        slot=4,
        state_version=4,
        abstentions=(s.Abstention(reason="other"),),
        status="proposed",
    )
    assert check(p, facts(4, ("J3",))).valid
    mixed = check(p, facts(4, ("J1", "J3")))
    assert mixed.status == "pending" and mixed.justified_abstentions == ("J3",)


def test_running_work_can_make_a_job_infeasible():
    # R runs 30 kW through slot 5: 40 + 30 + 40 = 110 kW > 100 kW at every legal start.
    running = {"R1": (job("R1", duration=6, power=30.0, deadline=6), 0)}
    result = check(plan(abstentions=("J1",)), facts(0, ("J1",), running))
    assert result.valid and result.justified_abstentions == ("J1",)


def test_missing_capacity_evidence_justifies_abstention():
    p = plan(abstentions=("J1", "J2"))
    assert check(p, facts(capacity=None)).valid


def test_nonflexible_job_past_its_arrival_can_only_be_abstained():
    fixed = job("N1", arrival=0, power=20, flexible=False)
    result = check(plan(slot=1, abstentions=("N1",)), facts(1, (), extra=[fixed]))
    assert result.valid and result.justified_abstentions == ("N1",)


# ----------------------------------------------------------------- outputs
@pytest.mark.parametrize("status", ["malformed", "no_output", "error"])
def test_failed_outputs_are_invalid(status):
    output = s.PolicyOutput(system="plain_llm", output_status=status)
    result = v.validate_output(output, facts(), Q03_DRAFT)
    assert codes(result) == ["no_plan"] and result.findings[0].detail == status


def test_missing_output_is_invalid():
    assert codes(v.validate_output(None, facts(), Q03_DRAFT)) == ["no_plan"]


def test_ok_output_is_validated_by_its_plan():
    assert v.validate_output(f.policy_output(), facts(), Q03_DRAFT).valid


def test_plan_for_another_decision_is_invalid():
    assert codes(check(f.plan(), facts(slot=1))) == ["plan_identity", "start_before_current"]


def test_unknown_citation_is_a_note_and_does_not_change_validity():
    p = plan(starts=[("J1", 0), ("J2", 2)], evidence_ids=("FACT-JOB-J1", "CON-MADE-UP"))
    result = check(p, facts())
    assert result.valid
    assert [n.detail for n in result.notes] == ["CON-MADE-UP"]


# ----------------------------------------------------------------- facts from F02 records
def test_facts_from_state_reads_capacity_from_constraints():
    built = v.facts_from_state(f.visible_state(), f.snapshot())
    assert built.capacity_kw == 100.0 and set(built.waiting) == {"J1", "J2"}
    assert "CON-CAP-01" in built.evidence_ids and "FACT-JOB-J3" not in built.evidence_ids
    snap = f.snapshot(include_capacity=False)
    assert v.facts_from_state(f.visible_state(snap), snap).capacity_kw is None


def test_graph_capacity_change_changes_the_verdict():
    snap = f.snapshot(capacity_kw=70.0)
    built = v.facts_from_state(f.visible_state(snap), snap)
    # J1 alone is 40 + 40 = 80 kW > 70 kW, so the hand plan is no longer feasible.
    assert "capacity" in codes(check(f.plan(), built))


def test_completion_slot_has_no_decision():
    state = s.VisibleState.from_snapshot(
        f.snapshot(), episode_id=f.EPISODE_ID, current_slot=24, state_version=24
    )
    with pytest.raises(ValueError, match="completion"):
        v.facts_from_state(state, f.snapshot())


# ----------------------------------------------------------------- disagreement with checker
def test_checker_pass_on_an_invalid_plan_is_reported():
    bad = plan(starts=[("J1", 0), ("J2", 0)])
    assert v.compare_with_check(check(bad, facts()), f.check_pass(bad)) == "checker_passed_invalid"
    assert v.compare_with_check(check(f.plan(), facts()), f.check_pass()) == "agree"


def test_checker_error_is_not_comparable():
    result = check(f.plan(), facts())
    assert v.compare_with_check(result, f.check_missing_capacity()) == "not_comparable"


def test_validator_does_not_import_production_or_shared_logic():
    for name in ("validator.py", "claims.py"):
        tree = ast.parse((Path(v.__file__).parent / name).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
                imported |= {f"{node.module}.{alias.name}" for alias in node.names}
        for forbidden in ("verification", "simulator", "metrics", "policies", "runtime"):
            assert not any(forbidden in module for module in imported), (name, forbidden)


# ----------------------------------------------------------------- D03 consumer check
@pytest.mark.parametrize("scenario", sorted(scenarios.SCENARIOS))
def test_d03_generator_labels_match_independent_feasibility(scenario):
    # At its arrival slot, alone, each job's abstention is justified exactly when the
    # generator marked it intentionally infeasible.
    for seed in range(10):
        for private in scenarios.generate_jobs(scenario, seed=seed, split="development"):
            j = private.job
            decision = facts(j.arrival_slot, (), extra=[j])
            result = check(plan(slot=j.arrival_slot, abstentions=(j.job_id,)), decision)
            justified = result.justified_abstentions == (j.job_id,)
            assert justified == bool(private.intentionally_infeasible), (scenario, seed, j)
