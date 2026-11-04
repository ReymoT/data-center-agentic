"""E03 run metrics tests, on the hand fixture.

Hand schedule J1@0, J2@2 emits 54.5 kg at PUE 1 (38.0 + 16.5); J3 arrives at slot 4 and can
never finish, so it is missed. J1 and J2 wait at slot 0, J2 waits at slots 1 and 2, and J3
waits at slot 4 under option B. The other decision slots have an empty queue. Bad plans
below sit at slots 1 and 4, where blocking them leaves the executed schedule unchanged.
"""

import ast
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import run_metrics as m
from dc_sustainability.evaluation.validator import Q03_OPTION_B
from tests.contracts import fixtures as f

END = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS


def plan(slot, starts=(), abstain=()):
    return s.Plan(
        episode_id=f.EPISODE_ID,
        slot=slot,
        state_version=slot,
        starts=tuple(s.PlannedStart(job_id=j, start_slot=t) for j, t in starts),
        abstentions=tuple(
            s.Abstention(job_id=j, reason="infeasible_deadline", constraint_ids=("CON-DL-J3",))
            for j in abstain
        ),
        status="proposed",
    )


def stage(p, passed=True):
    if not passed:
        return s.StageRecord(plan=p)
    return s.StageRecord(plan=p, check=f.check_pass(p))


def record(slot, system="greedy_a", *, initial=None, repaired=None, fallback=None, **fields):
    """A decision record; a stage that passes its check executes its current starts."""
    selected = next((x for x in (fallback, repaired, initial) if x is not None), None)
    fields.setdefault("trial", 0 if system in ("agent", "plain_llm") else None)
    options = {"final_status": "blocked"}
    if selected is not None and selected.check is not None and slot < 24:
        options = {
            "final_status": "executed",
            "execution_check": selected.check,
            "executed_starts": tuple(
                s.ApprovedStart(job_id=p.job_id, start_slot=p.start_slot)
                for p in selected.plan.current_starts
            ),
        }
    not_applicable = () if system == "agent" else ("repaired", "fallback")
    return s.DecisionRecord(
        decision_id=f"DEC-HAND1-{slot:02d}",
        system=system,
        run_id="RUN-HAND",
        episode_id=f.EPISODE_ID,
        slot=slot,
        initial=initial,
        repaired=repaired,
        fallback=fallback,
        not_applicable_stages=not_applicable,
        **options,
        **fields,
    )


def good_plans():
    """Greedy A's hand plans: J1@0, J2@2, then the J3 abstention at slot 4."""
    return {
        0: plan(0, [("J1", 0), ("J2", 2)]),
        1: plan(1, [("J2", 2)]),
        2: plan(2, [("J2", 2)]),
        4: plan(4, abstain=["J3"]),
    }


def run(overrides=None, system="greedy_a"):
    overrides = overrides or {}
    plans = good_plans()
    records = []
    for slot in range(END):
        if slot in overrides:
            records.append(overrides[slot])
        elif slot in plans:
            records.append(record(slot, system, initial=stage(plans[slot])))
        elif slot < 24:
            records.append(record(slot, system, initial=stage(plan(slot))))
        else:
            records.append(record(slot, system))
    return m.run_metrics(f.private_episode(), records, Q03_OPTION_B)


def test_a_valid_hand_run_scores_full_accuracy_on_its_recommendations():
    result = run()
    assert (result.recommendations, result.empty_queue_noops, result.no_plan) == (4, 20, 0)
    assert result.decision_accuracy == 1.0
    assert result.stages["final"].valid == 4
    assert result.stages["final"].unsafe_rate == 0.0


def test_outcomes_match_the_hand_schedule():
    result = run()
    assert (result.jobs, result.completed_jobs, result.missed_jobs) == (3, 2, 1)
    assert result.unfinished_jobs == 1  # the missed job, so these two categories overlap
    assert result.executed_starts == 2
    assert result.completed_it_energy_kwh == pytest.approx(140.0)
    assert result.completed_job_emissions_kg == pytest.approx(54.5)


def test_facility_energy_applies_pue_and_it_energy_does_not():
    episode = f.private_episode().model_copy(update={"snapshot": f.snapshot(pue=1.2)})
    plans = good_plans()
    records = [
        record(t, initial=stage(plans.get(t, plan(t)))) if t < 24 else record(t) for t in range(END)
    ]
    result = m.run_metrics(episode, records, Q03_OPTION_B)
    assert result.completed_it_energy_kwh == pytest.approx(140.0)
    assert result.completed_facility_energy_kwh == pytest.approx(168.0)


def test_missing_realized_carbon_gives_no_emissions_rather_than_zero():
    episode = f.private_episode()
    episode = episode.model_copy(update={"realized_carbon": episode.realized_carbon[:2]})
    plans = good_plans()
    records = [
        record(t, initial=stage(plans.get(t, plan(t)))) if t < 24 else record(t) for t in range(END)
    ]
    assert m.run_metrics(episode, records, Q03_OPTION_B).completed_job_emissions_kg is None


def test_an_empty_queue_noop_does_not_raise_accuracy():
    result = run({4: record(4, initial=stage(plan(4), passed=False))})
    assert (result.recommendations, result.empty_queue_noops) == (4, 20)
    assert result.decision_accuracy == pytest.approx(0.75)  # not 23 of 24


def test_a_plan_claiming_work_on_an_empty_queue_is_a_recommendation():
    result = run({10: record(10, initial=stage(plan(10, [("J1", 12)]), passed=False))})
    assert (result.recommendations, result.empty_queue_noops) == (5, 19)
    assert result.stages["final"].violation_types.get("empty_queue_not_noop") == 1


def test_a_recommendation_with_no_plan_is_invalid_not_skipped():
    result = run({1: record(1)})
    assert result.no_plan == 1
    assert result.recommendations == 4
    assert result.stages["final"].violation_types == {"no_plan": 1}
    assert result.decision_accuracy == pytest.approx(0.75)


def test_no_plan_on_an_empty_queue_is_a_noop():
    assert run({10: record(10)}).no_plan == 0


def test_omissions_are_kept_apart_from_rule_breaking_plans():
    result = run(
        {
            1: record(1, initial=stage(plan(1, [("J2", 20)]), passed=False)),  # misses deadline
            4: record(4, initial=stage(plan(4), passed=False)),  # omits J3
        }
    )
    final = result.stages["final"]
    assert (final.invalid, final.omission_only) == (2, 1)
    assert final.unsafe_rate == pytest.approx(0.5)
    assert final.unsafe_rate_without_omissions == pytest.approx(0.25)
    assert final.violation_types == {"deadline": 1, "omitted_job": 1}


def test_a_plan_with_an_omission_and_another_finding_is_not_omission_only():
    # J9 is unknown and J2 is omitted; J1 still executes, so the schedule is unchanged.
    mixed = record(0, initial=stage(plan(0, [("J1", 0), ("J9", 1)])))
    final = run({0: mixed}).stages["final"]
    assert (final.invalid, final.omission_only) == (1, 0)
    assert final.violation_types == {"not_waiting_job": 1, "omitted_job": 1}


def test_without_a_gate_the_final_stage_is_the_last_recorded_one():
    repaired = record(
        4,
        "agent",
        initial=stage(plan(4), passed=False),
        repaired=stage(good_plans()[4], passed=False),
    )
    result = run({4: repaired}, system="agent")
    assert result.stages["initial"].invalid == 1
    assert result.stages["final"].invalid == 0
    assert result.decision_accuracy == 1.0


def agent_run():
    bad = plan(0)
    good = good_plans()[0]
    first = record(
        0,
        "agent",
        initial=stage(bad, passed=False),
        repaired=stage(bad, passed=False),
        fallback=stage(good),
    )
    return run({0: first}, system="agent")


def test_each_stage_is_judged_separately_with_its_own_denominator():
    result = agent_run()
    assert result.stages["initial"].proposals == 4
    assert result.stages["initial"].invalid == 1
    assert (result.stages["repaired"].proposals, result.stages["repaired"].invalid) == (1, 1)
    assert (result.stages["fallback"].proposals, result.stages["fallback"].valid) == (1, 1)
    assert result.stages["final"].proposals == 4
    assert result.stages["final"].invalid == 0


def test_repair_and_fallback_rates_use_applicable_recommendations():
    result = agent_run()
    assert (result.repairs, result.repair_opportunities) == (1, 4)
    assert result.repair_rate == pytest.approx(0.25)
    assert result.fallback_rate == pytest.approx(0.25)


def test_a_stage_the_system_does_not_have_gives_no_rate_rather_than_zero():
    result = run()
    assert (result.repair_opportunities, result.repair_rate) == (0, None)
    assert result.fallback_rate is None
    assert result.stages["repaired"].unsafe_rate is None


def test_the_final_stage_is_the_plan_the_execution_gate_checked():
    good, bad = good_plans()[0], plan(0)
    # A later stage exists, but the gate checked the initial plan.
    gate = stage(good)
    item = s.DecisionRecord(
        decision_id="DEC-HAND1-00",
        system="agent",
        run_id="RUN-HAND",
        episode_id=f.EPISODE_ID,
        trial=0,
        slot=0,
        initial=gate,
        repaired=stage(bad, passed=False),
        execution_check=gate.check,
        final_status="executed",
        executed_starts=(s.ApprovedStart(job_id="J1", start_slot=0),),
    )
    assert m._final_stage(item) == gate


def test_a_justified_abstention_is_credited_and_counted():
    result = run()
    assert (result.abstained_jobs, result.justified_abstentions) == (1, 1)


def test_an_abstention_from_a_feasible_job_is_not_credited():
    result = run({1: record(1, initial=stage(plan(1, abstain=["J2"]), passed=False))})
    assert result.abstained_jobs == 2
    assert result.justified_abstentions == 1
    final = result.stages["final"]
    assert final.pending == 1
    assert final.valid == 3
    assert result.decision_accuracy == pytest.approx(0.75)  # pending stays in the denominator


def test_the_checker_is_compared_with_e01_and_never_trusted():
    # The record's check says pass, but E01 finds J2 omitted at slot 1.
    result = run({1: record(1, initial=stage(plan(1)))})
    assert result.stages["final"].invalid == 1
    assert result.stages["final"].checker_passed_invalid == 1
    assert result.stages["initial"].checker_passed_invalid == 1


def test_an_executed_rule_break_is_reported_from_the_replay():
    # J1 runs twice as a capacity test: both jobs start at 0 under a tighter limit.
    episode = f.private_episode().model_copy(update={"snapshot": f.snapshot(capacity_kw=70)})
    plans = {0: plan(0, [("J1", 0), ("J2", 0)]), 4: plan(4, abstain=["J3"])}
    records = [
        record(t, initial=stage(plans.get(t, plan(t)))) if t < 24 else record(t) for t in range(END)
    ]
    result = m.run_metrics(episode, records, Q03_OPTION_B)
    assert result.executed_invalid_findings == {"capacity": 2}


def test_cost_sums_recorded_model_calls():
    fields = {"model_call_count": 3, "latency_ms": 10.0, "prompt_tokens": 7, "completion_tokens": 2}
    plans = good_plans()
    result = run(
        {
            0: record(0, "agent", initial=stage(plans[0]), **fields),
            1: record(1, "agent", initial=stage(plans[1]), **fields),
        },
        system="agent",
    )
    assert result.cost.model_calls == 6
    assert result.cost.latency_ms == 20.0
    assert (result.cost.prompt_tokens, result.cost.completion_tokens) == (14, 4)


def test_a_cost_total_with_any_gap_is_none_rather_than_a_partial_sum():
    plans = good_plans()
    result = run(
        {
            0: record(0, "agent", initial=stage(plans[0]), model_call_count=3, latency_ms=10.0),
            1: record(1, "agent", initial=stage(plans[1]), model_call_count=3),
        },
        system="agent",
    )
    assert result.cost.model_calls == 6
    assert result.cost.latency_ms is None


def test_no_model_calls_cost_nothing():
    result = run()
    assert (result.cost.model_calls, result.cost.latency_ms) == (0, 0)


@pytest.mark.parametrize("keep", [list(range(END - 1)), [*range(END), 0]])
def test_a_run_must_have_exactly_one_record_per_slot(keep):
    records = [record(t) for t in keep]
    with pytest.raises(ValueError, match="exactly one decision record"):
        m.run_metrics(f.private_episode(), records, Q03_OPTION_B)


def test_records_from_two_systems_are_refused():
    records = [record(t, "agent" if t == 5 else "greedy_a") for t in range(END)]
    with pytest.raises(ValueError, match="mix"):
        m.run_metrics(f.private_episode(), records, Q03_OPTION_B)


def test_the_module_stays_independent_of_policies_and_production_checks():
    tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(
        name.startswith(
            (
                "dc_sustainability.policies",
                "dc_sustainability.verification",
                "dc_sustainability.simulator",
            )
        )
        for name in imported
    )
