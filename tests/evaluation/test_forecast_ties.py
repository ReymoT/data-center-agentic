"""E03 forecast-tie rate tests, on the hand fixture.

Hand carbon covers slots 0-6: 500, 450, 300, 250, 400, 480, 520 g/kWh. J1 and J2 each take
two slots with deadline 6, so each has legal starts 0-4 at slot 0. J3 arrives at slot 4 and
can never finish in time.
"""

import ast
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import forecast_ties as t
from dc_sustainability.evaluation import replay as r
from dc_sustainability.evaluation.validator import Q03_DRAFT, Q03_OPTION_B
from dc_sustainability.policies.greedy import propose
from tests.contracts import fixtures as f
from tests.evaluation.test_replay import starts

SCHEDULE = starts(s2=["J1"], s4=["J2"])


def replay(executed=SCHEDULE, episode=None):
    return r.replay_episode(episode or f.private_episode(), executed, Q03_OPTION_B)


def shaped():
    return {
        slot: tuple(fact for fact in f.forecasts(slot) if fact.valid_slot >= slot)
        for slot in range(24)
    }


def flat(value=400.0):
    return {
        slot: tuple(fact.model_copy(update={"value": value}) for fact in facts)
        for slot, facts in shaped().items()
    }


def decisions(forecasts, executed=SCHEDULE, episode=None):
    return t.job_decisions(replay(executed, episode), forecasts, Q03_OPTION_B)


def at(result, slot, job_id):
    return next(d for d in result if (d.slot, d.job_id) == (slot, job_id))


def test_a_shaped_forecast_separates_the_starts():
    decision = at(decisions(shaped()), 0, "J1")
    assert decision.status == "distinct"
    assert decision.feasible_starts == (0, 1, 2, 3, 4)


def test_a_flat_forecast_ties_every_comparable_decision():
    summary = t.summarize(decisions(flat()))
    assert summary.comparable > 0
    assert (summary.distinct, summary.tie_rate) == (0, 1.0)


def test_a_tie_needs_every_feasible_start_equal_not_just_two():
    forecasts = flat()
    forecasts[0] = tuple(
        fact.model_copy(update={"value": 500.0}) if fact.valid_slot == 5 else fact
        for fact in forecasts[0]
    )
    assert at(decisions(forecasts), 0, "J1").status == "distinct"


def test_equal_sums_from_different_values_are_a_tie():
    values = {0: 100.0, 1: 300.0, 2: 100.0, 3: 300.0, 4: 100.0, 5: 300.0, 6: 100.0}
    forecasts = flat()
    forecasts[0] = tuple(
        fact.model_copy(update={"value": values[fact.valid_slot]}) for fact in forecasts[0]
    )
    assert at(decisions(forecasts), 0, "J1").status == "tied"


def test_small_real_differences_are_not_rounded_into_ties():
    forecasts = flat()
    forecasts[0] = tuple(
        fact.model_copy(update={"value": 400.0000001}) if fact.valid_slot == 5 else fact
        for fact in forecasts[0]
    )
    assert at(decisions(forecasts), 0, "J1").status == "distinct"


def test_a_different_protocol_cannot_reinterpret_the_replay():
    with pytest.raises(ValueError, match="must match the replay protocol"):
        t.job_decisions(replay(), flat(), Q03_DRAFT)


def test_a_missing_forecast_is_uncovered_and_gives_no_rate_rather_than_zero():
    summary = t.summarize(decisions({}))
    assert summary.uncovered > 0
    assert (summary.comparable, summary.tie_rate) == (0, None)


def test_one_uncovered_start_excludes_the_decision_from_the_rate():
    forecasts = flat()
    forecasts[0] = tuple(fact for fact in forecasts[0] if fact.valid_slot != 5)
    assert at(decisions(forecasts), 0, "J1").status == "uncovered"


def test_a_job_with_one_feasible_start_has_no_choice():
    # At slot 4, J2 has only its last legal start left.
    decision = at(decisions(flat(), starts(s0=["J1"])), 4, "J2")
    assert (decision.status, decision.feasible_starts) == ("no_choice", (4,))


def test_a_job_with_no_legal_start_has_no_choice():
    assert at(decisions(flat()), 4, "J3").status == "no_choice"


def test_running_work_removes_starts_that_would_overload():
    episode = f.private_episode()
    tight = f.snapshot(capacity_kw=70)
    episode = episode.model_copy(update={"snapshot": tight})
    decision = at(decisions(flat(), starts(s0=["J1"]), episode), 0, "J2")
    assert decision.feasible_starts == (0, 1, 2, 3, 4)  # before J1 starts at slot 0
    assert at(decisions(flat(), starts(s0=["J1"]), episode), 1, "J2").feasible_starts == (2, 3, 4)


def test_missing_capacity_evidence_is_unverifiable_not_a_tie():
    episode = f.private_episode().model_copy(
        update={"snapshot": f.snapshot(include_capacity=False)}
    )
    summary = t.summarize(decisions(flat(), starts(), episode))
    assert summary.unverifiable > 0
    assert (summary.comparable, summary.tie_rate) == (0, None)


def test_duplicate_forecasts_for_a_slot_are_refused():
    forecasts = shaped()
    forecasts[0] = (*forecasts[0], forecasts[0][0])
    with pytest.raises(ValueError, match="more than one forecast"):
        decisions(forecasts)


def test_pooling_sums_counts_rather_than_averaging_rates():
    tied = t.JobDecision(0, "J1", "tied", (0, 1))
    distinct = t.JobDecision(0, "J2", "distinct", (0, 1))
    summary = t.summarize([tied, tied, tied, distinct, t.JobDecision(1, "J3", "no_choice", ())])
    assert summary == t.TieSummary(5, 3, 1, 1, 0, 0)
    assert summary.tie_rate == pytest.approx(0.75)


def test_every_decision_slot_and_waiting_job_is_counted_once():
    result = decisions(flat())
    keys = [(d.slot, d.job_id) for d in result]
    assert len(keys) == len(set(keys))
    assert {d.slot for d in result} <= set(range(s.PROPOSED_DECISION_SLOTS))


def test_tied_decisions_are_why_greedy_b_matches_greedy_a():
    snapshot = f.snapshot()
    state = f.visible_state(snapshot).model_copy(update={"carbon_facts": flat()[0]})
    context = s.Context.build(state, snapshot, representation="flat")
    a = propose(state, context, system="greedy_a")
    b = propose(state, context, system="greedy_b", decision_time_utc=f.SLOT0_UTC)
    assert b.explanation is None  # a real Greedy B ranking, not its coverage fallback
    assert b.plan.starts == a.plan.starts


def test_the_module_stays_independent_of_policies_and_production_checks():
    tree = ast.parse(Path(t.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(
        name.startswith(("dc_sustainability.policies", "dc_sustainability.verification"))
        or name.startswith("dc_sustainability.simulator")
        for name in imported
    )
