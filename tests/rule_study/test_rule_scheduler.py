"""Deterministic rules-v1 scheduler: real F02 records and the real R01-R09 implementation."""

from datetime import timedelta

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.policies import greedy
from dc_sustainability.rule_study import cases as c
from dc_sustainability.rule_study import scheduler as sch
from tests.rule_study.helpers import CONV, candidate, case_with, job, propose, starts, visible


def entries(decision, rule_id):
    return [e for e in decision.arithmetic if e.rule_id == rule_id]


# --------------------------------------------------------------------------- scenarios
def test_scenario_a_selects_j2_now_and_j1_at_lower_score_slot():
    decision = propose(c.CASE_A)
    assert decision.status == "proposed"
    assert starts(decision) == {"J2": 0, "J1": 1}
    assert decision.plan.abstentions == ()
    assert decision.objective == sch.ObjectiveTuple(
        scheduled_count=2,
        inclusion_vector=(1, 1),
        synthetic_score=8000,  # J2@0: 20*300 + J1@1: 20*100
        completion_sum=3,
        start_vector=(0, 1),
    )
    assert decision.search.total_assignments == 8
    assert decision.search.job_order == ("J2", "J1")
    # J1@0 and J1@2 were feasible but strictly worse on the synthetic score.
    assert candidate(decision, J2=0, J1=0).objective.synthetic_score == 12000
    assert candidate(decision, J2=0, J1=2).objective.synthetic_score == 10000


def test_scenario_b_is_jointly_infeasible_and_keeps_both_start_assignment_rejected():
    decision = propose(c.CASE_B)
    both = candidate(decision, J1=0, J2=0)
    assert not both.feasible and both.first_violation == (0, 20)  # 80 kW vs 60 kW
    assert len(decision.search.accepted) == 3 and len(decision.search.rejected) == 1
    assert starts(decision) == {"J1": 0}
    (abstention,) = decision.plan.abstentions
    assert (abstention.job_id, abstention.reason) == ("J2", "constraint_violation")
    assert "not an individual physical certificate" in abstention.detail
    assert decision.unscheduled_job_ids == ("J2",)
    # The rejected joint candidate is filed under R05 so that every R04 entry describes only
    # the stage's own (feasible) plan, which is how the merged trace reader interprets R04.
    joint = [e for e in entries(decision, "R05") if e.outcome == "fail"]
    assert len(joint) == 1 and joint[0].total == 80 and joint[0].signed_excess == 20
    assert "rejected candidate" in joint[0].formula
    assert all(e.outcome == "pass" and e.total <= 60 for e in entries(decision, "R04"))


def test_scenario_b_progress_flexible_j2_is_delayed_and_both_scheduled():
    decision = propose(c.CASE_B_PROGRESS)
    assert starts(decision) == {"J1": 0, "J2": 1}
    assert decision.plan.abstentions == ()
    assert [r for r in decision.search.rejected] == [("SCH-0000", 0, 20)]


def test_repeated_calls_are_identical_and_never_mutate_inputs():
    state, snapshot = visible(c.CASE_A)
    before = (state.to_json(), snapshot.to_json())
    kwargs = dict(decision_time_utc=c.CASE_A.decision_time_utc(0), score_convention=CONV)
    first = sch.propose_rules_v1(state, snapshot, **kwargs)
    second = sch.propose_rules_v1(state, snapshot, **kwargs)
    assert first == second and first.plan.plan_hash == second.plan.plan_hash
    assert (state.to_json(), snapshot.to_json()) == before


# --------------------------------------------------------------------------- objective levels
ONE_AT_A_TIME = dict(capacity=40, background=20)  # 20 kW headroom: one 20 kW job per slot


def test_level_1_more_scheduled_jobs_beats_lower_score():
    decision = propose(c.CASE_A)
    fewer = [
        cand
        for cand in decision.search.candidates
        if cand.feasible and cand.objective.scheduled_count < 2
    ]
    assert fewer and min(f.objective.synthetic_score for f in fewer) < 8000
    assert decision.objective.scheduled_count == 2


def test_level_2_prefers_nonflexible_over_lower_job_id():
    case = case_with([job("J1", 20, 1, True), job("J2", 20, 1, False)], **ONE_AT_A_TIME)
    decision = propose(case)
    assert starts(decision) == {"J2": 0}
    assert candidate(decision, J1=0, J2=None).objective.scheduled_count == 1


def test_level_2_prefers_earliest_latest_start_over_lower_job_id():
    # J1 may start at 0 or 1 (latest 1); J2 only at 0 (latest 0). Both need slots 0-1.
    case = case_with(
        [job("J1", 20, 3, True, duration=2), job("J2", 20, 2, True, duration=2)], **ONE_AT_A_TIME
    )
    decision = propose(case)
    assert starts(decision) == {"J2": 0}


def test_level_2_prefers_earlier_deadline_when_latest_start_ties():
    # Both latest start 0; J2's deadline 1 < J1's deadline 2.
    case = case_with(
        [job("J1", 20, 2, True, duration=2), job("J2", 20, 1, True, duration=1)], **ONE_AT_A_TIME
    )
    decision = propose(case)
    assert starts(decision) == {"J2": 0}


def test_level_2_final_priority_component_is_job_id():
    case = case_with([job("J2", 20, 1, True), job("J1", 20, 1, True)], **ONE_AT_A_TIME)
    assert starts(propose(case)) == {"J1": 0}


def test_level_3_minimizes_synthetic_score():
    decision = propose(c.CASE_A)
    cheaper = candidate(decision, J2=0, J1=1).objective
    for other in (0, 2):
        assert (
            candidate(decision, J2=0, J1=other).objective.synthetic_score > cheaper.synthetic_score
        )


def test_level_4_minimizes_completion_time_when_scores_tie():
    case = case_with([job("J1", 20, 4, True)], scores=(100, 100, 100, 100), remaining=100)
    decision = propose(case)
    assert starts(decision) == {"J1": 0}
    scores = {
        cand.objective.synthetic_score
        for cand in decision.search.candidates
        if cand.feasible and cand.objective.scheduled_count
    }
    assert scores == {2000}  # level 3 cannot decide here
    assert candidate(decision, J1=1).objective.completion_sum > decision.objective.completion_sum


def test_level_5_start_vector_breaks_remaining_ties():
    case = case_with(
        [job("J1", 20, 2, True), job("J2", 20, 2, True)],
        scores=(100, 100),
        remaining=100,
        **ONE_AT_A_TIME,
    )
    decision = propose(case)
    swapped = candidate(decision, J1=1, J2=0).objective
    chosen = decision.objective
    assert (
        chosen.scheduled_count,
        chosen.inclusion_vector,
        chosen.synthetic_score,
        chosen.completion_sum,
    ) == (
        swapped.scheduled_count,
        swapped.inclusion_vector,
        swapped.synthetic_score,
        swapped.completion_sum,
    )
    assert starts(decision) == {"J1": 0, "J2": 1}
    assert chosen.start_vector < swapped.start_vector


def test_unscheduled_option_sorts_after_every_legal_start():
    assert sch.UNSCHEDULED_START > sch.LAST_DECISION_SLOT


# --------------------------------------------------------------------------- physical rules
def test_half_open_occupancy_allows_a_start_exactly_when_running_work_ends():
    case = case_with([job("J2", 20, 6, True)], **ONE_AT_A_TIME, scores=(100,) * 6)
    running = [s.RunningJobView(job=job("J1", 20, 6, True, duration=2), start_slot=0)]  # [0,2)
    decision = propose(case, slot=1, running=running, waiting=[case.jobs[0]])
    assert starts(decision) == {"J2": 2}  # slot 2 is free; the running job occupies [0, 2)
    assert candidate(decision, J2=1).first_violation == (1, 20)
    r04_slots = {e.slot for e in entries(decision, "R04")}
    assert r04_slots == {1, 2}


def test_full_duration_is_checked_not_just_the_first_slot():
    case = case_with(
        [job("J1", 20, 3, True, duration=1), job("J2", 20, 3, True, duration=2)], **ONE_AT_A_TIME
    )
    decision = propose(case)
    clash = candidate(decision, J1=1, J2=0)  # J2 occupies slots 0-1; J1 at 1 collides at slot 1
    assert not clash.feasible and clash.first_violation == (1, 20)
    assert decision.objective.scheduled_count == 2


def test_background_and_running_load_reduce_headroom_before_selection():
    case = case_with([job("J2", 30, 3, True)])  # headroom 60-20-20 = 20 < 30
    running = [s.RunningJobView(job=job("J1", 20, 6, True, duration=3), start_slot=0)]
    decision = propose(case, slot=0, running=running)
    assert decision.plan.starts == ()
    (abstention,) = decision.plan.abstentions
    assert abstention.reason == "constraint_violation"
    assert "no individually capacity-feasible start" in abstention.detail
    terms = {t.label: t.value for e in entries(decision, "R04") for t in e.terms if e.slot == 0}
    assert terms["background_kw"] == 20 and terms["running_kw"] == 20


def test_base_load_over_capacity_fails_closed():
    case = case_with([job("J1", 20, 3, True)], capacity=30)
    running = [s.RunningJobView(job=job("J9", 20, 6, True, duration=2), start_slot=0)]
    decision = propose(case, running=running)
    assert decision.status == "rejected" and decision.plan is None
    assert decision.errors[0].code == "R04_BASE_LOAD_EXCEEDS_CAPACITY"


def test_pue_is_never_multiplied_into_the_it_capacity_limit():
    plain = propose(case_with([job("J1", 20, 3, True), job("J2", 20, 1, False)], pue=1.0))
    hot = propose(case_with([job("J1", 20, 3, True), job("J2", 20, 1, False)], pue=1.7))
    assert plain.plan.starts == hot.plan.starts
    assert {e.limit for e in entries(hot, "R04")} == {60}


def test_arrival_deadline_and_horizon_windows():
    flexible = job("F", 20, 4, True, duration=2, arrival=1)
    assert sch.legal_window(flexible, now=0) == (1, 2)  # arrived at 1, ends by deadline 4
    assert sch.legal_window(flexible, now=2) == (2,)
    assert sch.legal_window(flexible, now=3) == ()
    late = job("L", 20, 30, True, duration=2)
    assert sch.legal_window(late, now=22) == (22, 23)  # new starts stop after slot 23
    assert sch.legal_window(late, now=24) == ()
    assert sch.legal_window(job("H", 20, 40, True, duration=3), now=28) == ()  # slot 30 bound


def test_nonflexible_jobs_start_only_at_arrival_and_never_late():
    nonflex = job("N", 20, 5, False, duration=1, arrival=1)
    assert sch.legal_window(nonflex, now=0) == (1,)
    assert sch.legal_window(nonflex, now=2) == ()
    case = case_with([nonflex])
    state, snapshot = visible(case, slot=2, waiting=[nonflex])
    decision = sch.propose_rules_v1(
        state, snapshot, decision_time_utc=case.decision_time_utc(2), score_convention=CONV
    )
    assert decision.plan.starts == ()
    assert decision.plan.abstentions[0].reason == "infeasible_deadline"
    r03 = [e for e in entries(decision, "R03") if e.outcome == "fail"]
    assert r03 and r03[0].signed_excess == 1  # now 2 - arrival 1


def test_nonflexible_selected_start_is_exactly_arrival_with_zero_excess():
    decision = propose(c.CASE_A)
    (r03,) = [
        e
        for e in entries(decision, "R03")
        if e.signed_excess is not None and e.outcome != "computed" and e.slot is not None
    ]
    assert (r03.total, r03.limit, r03.signed_excess, r03.outcome) == (0, 0, 0, "pass")


def test_no_slot_24_plus_start_and_no_restart():
    case = case_with([job("J1", 20, 30, True)])
    state, snapshot = visible(case, slot=24, waiting=[case.jobs[0]])
    decision = sch.propose_rules_v1(
        state, snapshot, decision_time_utc=case.decision_time_utc(24), score_convention=CONV
    )
    assert decision.plan.starts == ()
    assert decision.plan.abstentions[0].reason == "infeasible_deadline"
    assert len(set(starts(propose(c.CASE_A)))) == len(starts(propose(c.CASE_A)))


# --------------------------------------------------------------------------- R01 / bad inputs
def test_duplicate_job_ids_cannot_be_constructed_and_a_forged_state_is_rejected():
    j = job("J1")
    with pytest.raises(ValueError):
        visible(case_with([j]), waiting=[j, j])
    state, snapshot = visible(case_with([j]))
    forged = state.model_copy(update={"waiting_jobs": (j, j)})
    decision = sch.propose_rules_v1(
        forged, snapshot, decision_time_utc=c.CASE_A.decision_time_utc(0), score_convention=CONV
    )
    assert decision.status == "rejected" and decision.errors[0].code == "R01_MALFORMED_INPUT"


def test_missing_capacity_fails_closed_never_unlimited():
    state, snapshot = visible(c.CASE_A)
    no_capacity = snapshot.model_copy(
        update={
            "constraints": tuple(k for k in snapshot.constraints if k.constraint_type != "capacity")
        }
    )
    decision = sch.propose_rules_v1(
        state, no_capacity, decision_time_utc=c.CASE_A.decision_time_utc(0), score_convention=CONV
    )
    codes = {e.code for e in decision.errors}
    assert decision.status == "rejected" and decision.plan is None
    assert "R01_MISSING_CAPACITY" in codes


@pytest.mark.parametrize(
    "mutate, code",
    [
        (lambda c_: case_with([job("J1", 20.5)]), "R01_NON_INTEGER_POWER"),
        (lambda c_: case_with([job("J1")], background=20.5), "R01_NON_INTEGER_POWER"),
        (lambda c_: case_with([job("J1")], capacity=60.5), "R01_NON_INTEGER_CAPACITY"),
        (lambda c_: case_with([job("J1")], scores=(100.5, 1, 1)), "R01_NON_INTEGER_SCORE"),
    ],
)
def test_malformed_or_non_integer_inputs_fail_closed(mutate, code):
    decision = propose(mutate(None))
    assert decision.status == "rejected" and decision.plan is None
    assert code in {e.code for e in decision.errors}


def test_stale_version_non_state_input_and_naive_time_fail_closed():
    state, snapshot = visible(c.CASE_A)
    good = dict(decision_time_utc=c.CASE_A.decision_time_utc(0), score_convention=CONV)
    stale = sch.propose_rules_v1(state, snapshot, expected_state_version=7, **good)
    assert "R01_STALE_STATE_VERSION" in {e.code for e in stale.errors}
    assert (
        sch.propose_rules_v1({"not": "a state"}, snapshot, **good).errors[0].code
        == "R01_MALFORMED_INPUT"
    )
    naive = sch.propose_rules_v1(
        state, snapshot, decision_time_utc=c.SLOT0_UTC.replace(tzinfo=None), score_convention=CONV
    )
    assert "R01_DECISION_TIME" in {e.code for e in naive.errors}


def test_score_convention_is_explicit_never_assumed():
    state, snapshot = visible(c.CASE_A)
    with pytest.raises(TypeError):
        sch.propose_rules_v1(state, snapshot, decision_time_utc=c.SLOT0_UTC, score_convention=None)


# --------------------------------------------------------------------------- scope, no truncation
def test_more_than_four_waiting_jobs_is_rejected_explicitly_not_truncated():
    jobs = [job(f"J{i}", 10, 6) for i in range(1, 6)]
    decision = propose(case_with(jobs, capacity=500))
    assert decision.status == "rejected" and decision.plan is None and decision.search is None
    assert "SCOPE_TOO_MANY_WAITING_JOBS" in {e.code for e in decision.errors}


def test_more_than_six_candidate_start_slots_is_rejected_explicitly():
    decision = propose(case_with([job("J1", 20, 8, True)]))  # starts 0..7
    codes = {e.code for e in decision.errors}
    assert decision.status == "rejected" and decision.plan is None
    assert {"SCOPE_TOO_MANY_START_SLOTS", "SCOPE_START_SLOT_OUTSIDE"} <= codes


def test_start_slots_outside_zero_to_five_rejected_even_when_six_or_fewer():
    case = case_with([job("J1", 20, 10, True, arrival=3)])
    decision = propose(case, slot=3)  # starts 3..9: six... but 6-9 are outside 0-5
    assert "SCOPE_START_SLOT_OUTSIDE" in {e.code for e in decision.errors}


def test_full_scope_enumerates_all_2401_assignments_without_sampling():
    jobs = [job(f"J{i}", 10, 6, True) for i in range(1, 5)]
    decision = propose(case_with(jobs, capacity=1000, scores=(1,) * 6))
    assert decision.search.total_assignments == sch.MAX_ASSIGNMENTS == 2401
    assert len(decision.search.candidates) == 2401
    assert len(decision.search.accepted) == 2401 and not decision.search.rejected
    assert len({cand.schedule_id for cand in decision.search.candidates}) == 2401
    assert entries(decision, "R05")[0].total == 2401


# --------------------------------------------------------------------------- score arithmetic
def test_score_arithmetic_is_integer_with_artificial_score_kwh_units():
    decision = propose(c.CASE_A)
    (score,) = [e for e in entries(decision, "R06") if e.unit == CONV.unit]
    assert score.total == 8000 == sum(t.value for t in score.terms)
    assert {t.value for t in score.terms} == {6000, 2000}
    assert all(t.unit == CONV.unit for t in score.terms)
    # The unit names itself artificial and explicitly denies being g/kWh or emissions.
    assert "artificial" in CONV.unit and "not g/kWh" in CONV.unit and "not emissions" in CONV.unit
    assert "power_kw * 1 h * PUE(1.0) * weight" in score.formula
    assert "Edison" in score.formula
    assert decision.score_convention_id == "score-kwh-v1"


def test_score_convention_is_isolated_and_swappable_without_touching_the_scheduler():
    class Prefer(sch.ScoreConvention):
        convention_id, unit, status, formula = "test-prefer-late", "test_unit", "TEST", "weight"

        def job_score(self, *, power_kw, start, duration_slots, weights):
            terms = tuple(
                sch.ScoreTerm(t, power_kw, weights[t], -weights[t])
                for t in range(start, start + duration_slots)
            )
            return sch.JobScore(sum(x.value for x in terms), terms)

    assert starts(propose(c.CASE_A, convention=Prefer())) == {"J2": 0, "J1": 0}  # picks max weight
    unweighted = propose(c.CASE_A, convention=sch.UnweightedSlotScore())
    assert starts(unweighted) == {"J2": 0, "J1": 1} and unweighted.objective.synthetic_score == 400


# --------------------------------------------------------------------------- evidence
def test_capacity_explanation_exposes_every_required_quantity():
    decision = propose(c.CASE_A)
    by_slot = {e.slot: e for e in entries(decision, "R04")}
    assert set(by_slot) == {0, 1}
    slot0 = by_slot[0]
    assert [(t.label, t.job_id, t.value, t.unit) for t in slot0.terms] == [
        ("background_kw", None, 20, "kW"),
        ("selected_kw", "J2", 20, "kW"),
    ]
    assert (slot0.total, slot0.limit, slot0.signed_excess, slot0.outcome) == (40, 60, -20, "pass")
    assert slot0.constraint_id == "CON-CAP-01" and "PUE not applied" in slot0.formula
    assert all(e.signed_excess == e.total - e.limit for e in by_slot.values())


def test_rule_ids_cover_r01_to_r09_and_future_start_is_advisory():
    decision = propose(c.CASE_A)
    assert set(decision.rule_ids) == {f"R0{i}" for i in range(1, 10)}
    r07 = {t.job_id: e for e in entries(decision, "R07") for t in e.terms[:1]}
    assert (r07["J2"].signed_excess, r07["J2"].outcome) == (0, "pass")  # executable now
    assert (r07["J1"].signed_excess, r07["J1"].outcome) == (1, "computed")  # advisory
    disposition = entries(decision, "R09")[0]
    assert {(t.label, t.job_id) for t in disposition.terms if t.job_id} == {
        ("waiting:start_now", "J2"),
        ("waiting:advisory_future_start", "J1"),
    }


def test_unscheduled_job_is_distinct_from_missed_in_evidence():
    decision = propose(c.CASE_B)
    labels = {(t.label, t.job_id) for e in entries(decision, "R09") for t in e.terms if t.job_id}
    assert ("waiting:unscheduled", "J2") in labels and ("waiting:start_now", "J1") in labels
    assert not any(label == "missed" for label, _ in labels)


# --------------------------------------------------------------------------- R08 coverage
def _decide_with_facts(case, facts):
    state, snapshot = visible(case, carbon=facts)
    return (
        state,
        snapshot,
        sch.propose_rules_v1(
            state, snapshot, decision_time_utc=case.decision_time_utc(0), score_convention=CONV
        ),
    )


def _facts(case, update=None, keep=None):
    facts = case.forecasts_by_slot()[0]
    facts = [f for f in facts if keep is None or f.valid_slot in keep]
    return tuple(f.model_copy(update=update) if update else f for f in facts)


@pytest.mark.parametrize(
    "label, facts_fn, reason",
    [
        ("missing", lambda case: (), "missing"),
        (
            "stale",
            lambda case: _facts(
                case, {"issued_at_utc": case.decision_time_utc(0) - timedelta(hours=5)}
            ),
            "stale",
        ),
        (
            "future",
            lambda case: _facts(
                case, {"issued_at_utc": case.decision_time_utc(0) + timedelta(hours=2)}
            ),
            "future",
        ),
        ("partial", lambda case: _facts(case, keep={0}), "partial"),
    ],
)
def test_unusable_forecasts_disable_optimization_and_match_greedy_b_reason(label, facts_fn, reason):
    case = c.CASE_A
    state, snapshot, decision = _decide_with_facts(case, facts_fn(case))
    assert decision.status == "fallback_required" and decision.plan is None
    assert decision.fallback_reason == reason
    r08 = entries(decision, "R08")[0]
    assert r08.outcome == "fail" and r08.signed_excess > 0
    out = greedy.propose(
        state,
        s.Context.build(state, snapshot, "flat"),
        system="greedy_b",
        decision_time_utc=case.decision_time_utc(0),
    )
    assert out.system == "greedy_a" and out.explanation.summary == reason


def test_missing_freshness_constraint_routes_to_fallback_with_explicit_reason():
    state, snapshot = visible(c.CASE_A)
    no_fresh = snapshot.model_copy(
        update={
            "constraints": tuple(
                k for k in snapshot.constraints if k.constraint_type != "freshness"
            )
        }
    )
    state = state.model_copy(
        update={"constraint_ids": tuple(i for i in state.constraint_ids if i != "CON-FRESH-01")}
    )
    decision = sch.propose_rules_v1(
        state, no_fresh, decision_time_utc=c.CASE_A.decision_time_utc(0), score_convention=CONV
    )
    assert decision.status == "fallback_required"
    assert decision.fallback_reason == "freshness_evidence_missing"
