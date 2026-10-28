"""E03 equal-work comparison tests (#61), on the hand fixture.

Realized carbon equals the hand series 500, 450, 300, 250, 400, 480, 520 g/kWh, PUE 1:
baseline J1@0, J2@2 emits 38.0 + 16.5 = 54.5 kg; candidate J1@2, J2@4 emits
22.0 + 26.4 = 48.4 kg; savings 6.1 kg. J3 is impossible on arrival, so both runs miss it,
as in the infeasible scenario.
"""

import ast
import dataclasses
from pathlib import Path
from typing import get_args

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import comparison as e
from dc_sustainability.evaluation import replay as r
from dc_sustainability.evaluation.validator import Q03_DRAFT, Q03_OPTION_B
from tests.contracts import fixtures as f
from tests.evaluation.test_replay import starts

BASELINE = starts(s0=["J1"], s2=["J2"])
CANDIDATE = starts(s2=["J1"], s4=["J2"])


def run(system, executed, episode=None, trial=0, protocol=Q03_DRAFT):
    return e.Run(
        system, trial, r.replay_episode(episode or f.private_episode(), executed, protocol)
    )


def compare(baseline_starts=BASELINE, candidate_starts=CANDIDATE, **candidate_options):
    return e.compare_savings(
        run("greedy_a", baseline_starts), run("agent", candidate_starts, **candidate_options)
    )


def test_same_completed_and_missed_jobs_are_comparable_with_the_hand_savings():
    result = compare()
    assert (result.status, result.reasons) == ("comparable", ())
    assert result.baseline_kg == pytest.approx(54.5)
    assert result.candidate_kg == pytest.approx(48.4)
    assert result.savings_kg == pytest.approx(6.1)
    # Both miss impossible J3: the infeasible-scenario case is comparable, no exemption needed.
    assert result.counts == {
        "baseline": e.WorkCounts(completed=2, unfinished=1, missed=1),
        "candidate": e.WorkCounts(completed=2, unfinished=1, missed=1),
    }


def test_less_completed_work_is_blocked_not_savings():
    result = compare(candidate_starts=starts(s2=["J1"]))  # J2 never runs: emits less
    assert result.status == "blocked"
    assert result.reasons == ("completed_set_differs", "unfinished_set_differs")
    assert result.savings_kg is None  # never zero savings
    assert result.counts["candidate"] == e.WorkCounts(completed=1, unfinished=2, missed=2)


@pytest.mark.parametrize(
    "options",
    [
        {"trial": 1},  # not the paired trial
        {"episode": f.private_episode().model_copy(update={"snapshot": f.snapshot(pue=1.2)})},
        {"episode": f.private_episode().model_copy(update={"realized_carbon": f.observations()[:6]})},
        {"protocol": Q03_OPTION_B},
    ],
)  # fmt: skip
def test_different_inputs_or_pairing_are_blocked(options):
    result = compare(**options)
    assert "inputs_differ" in result.reasons and result.savings_kg is None


def test_different_capacity_is_an_input_difference():
    snapshot = f.snapshot(include_capacity=False)
    episode = f.private_episode().model_copy(update={"snapshot": snapshot})
    assert compare(episode=episode).reasons == ("inputs_differ",)


def test_unfinished_job_with_executed_occupancy_is_blocked():
    # The replay cannot produce this from legal starts, so the trace is edited by hand:
    # J3 shown running in slot 5 but never completed.
    base = run("greedy_a", BASELINE)
    slots = list(base.replay.slots)
    slots[5] = dataclasses.replace(slots[5], running=("J3",))
    tampered = e.Run("greedy_a", 0, dataclasses.replace(base.replay, slots=tuple(slots)))
    result = e.compare_savings(tampered, run("agent", CANDIDATE))
    assert result.reasons == ("unfinished_job_occupied",) and result.savings_kg is None


def test_missing_realized_carbon_is_blocked_not_filled():
    # No realized value for slot 5, which the candidate's J2 (slots 4-5) needs.
    episode = f.private_episode()
    kept = tuple(o for o in episode.realized_carbon if o.valid_slot != 5)
    episode = episode.model_copy(update={"realized_carbon": kept})
    result = e.compare_savings(run("greedy_a", BASELINE, episode), run("agent", CANDIDATE, episode))
    assert result.reasons == ("carbon_missing",)
    assert (result.baseline_kg, result.candidate_kg, result.savings_kg) == (None, None, None)


def test_every_failed_reason_is_recorded_together():
    # Realized carbon only for slots 0-2, but the candidate's J1@2 also needs slot 3.
    other = f.private_episode().model_copy(update={"realized_carbon": f.observations()[:3]})
    result = compare(candidate_starts=starts(s2=["J1"]), episode=other, trial=2)
    assert result.reasons == (
        "completed_set_differs",
        "unfinished_set_differs",
        "inputs_differ",
        "carbon_missing",
    )


def test_summary_counts_comparable_blocked_and_reasons():
    results = [
        compare(),
        compare(candidate_starts=starts(s2=["J1"])),
        compare(trial=1),
    ]
    summary = e.summarize(results)
    assert (summary.total, summary.comparable, summary.blocked) == (3, 1, 2)
    assert summary.by_reason == {
        "completed_set_differs": 1,
        "unfinished_set_differs": 1,
        "inputs_differ": 1,
    }


def test_comparison_does_not_use_production_impact_or_the_s02_helper():
    tree = ast.parse(Path(e.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    for forbidden in ("metrics", "simulator", "policies", "runtime", "verification"):
        assert not any(forbidden in module for module in imported), forbidden


# ----------------------------------------------------------------- replay findings (#61)
def _slot_mismatch():
    executed = dict(CANDIDATE)
    executed[3] = (s.ApprovedStart(job_id="J2", start_slot=4),)  # recorded for another slot
    return executed


@pytest.mark.parametrize(
    "executed,invalidating",
    [
        # J1 and J2 together at slot 0: 110 kW > 100 kW in slots 0 and 1. Both still finish.
        (starts(s0=["J1", "J2"]), ("capacity@0", "capacity@1")),
        ({**CANDIDATE, 1: starts(s1=["J9"])[1]}, ("executed_unknown_job@1:J9",)),
        ({**CANDIDATE, 3: starts(s3=["J1"])[3]}, ("executed_not_waiting@3:J1",)),
        (_slot_mismatch(), ("executed_slot_mismatch@3:J2",)),
    ],
)
def test_findings_that_invalidate_execution_block_the_comparison(executed, invalidating):
    result = compare(candidate_starts=executed)
    assert result.reasons == ("replay_findings",)  # same completed and missed jobs
    assert result.savings_kg is None
    assert result.invalidating_findings == {"baseline": (), "candidate": invalidating}
    assert result.findings["candidate"] == invalidating


def test_option_b_start_of_an_impossible_arrival_blocks():
    baseline = run("greedy_a", BASELINE, protocol=Q03_OPTION_B)
    candidate = run("agent", {**CANDIDATE, 4: starts(s4=["J2", "J3"])[4]}, protocol=Q03_OPTION_B)
    result = e.compare_savings(baseline, candidate)
    assert result.reasons == ("replay_findings",)
    assert result.invalidating_findings["candidate"] == ("executed_no_legal_start@4:J3",)


def test_missing_capacity_evidence_is_recorded_but_does_not_block():
    episode = f.private_episode().model_copy(
        update={"snapshot": f.snapshot(include_capacity=False)}
    )
    result = e.compare_savings(run("greedy_a", BASELINE, episode), run("agent", CANDIDATE, episode))
    assert (result.status, result.reasons) == ("comparable", ())
    assert result.savings_kg is not None
    assert result.findings["candidate"] == ("capacity_unverifiable@2", "capacity_unverifiable@4")
    assert result.invalidating_findings == {"baseline": (), "candidate": ()}


def test_every_replay_code_is_classified_exactly_once():
    codes = set(get_args(r.ReplayCode))
    assert e.INVALIDATING_FINDINGS | e.NON_BLOCKING_FINDINGS == codes
    assert not e.INVALIDATING_FINDINGS & e.NON_BLOCKING_FINDINGS


def test_an_unclassified_finding_code_is_refused():
    base = run("greedy_a", BASELINE)
    odd = dataclasses.replace(base.replay, findings=(r.ReplayFinding("new_code", 0),))
    with pytest.raises(ValueError, match="not classified"):
        e.compare_savings(e.Run("greedy_a", 0, odd), run("agent", CANDIDATE))


def test_replay_findings_are_counted_in_the_summary():
    summary = e.summarize([compare(), compare(candidate_starts=starts(s0=["J1", "J2"]))])
    assert (summary.comparable, summary.blocked) == (1, 1)
    assert summary.by_reason == {"replay_findings": 1}


def test_an_invalid_baseline_blocks_too():
    result = compare(baseline_starts=starts(s0=["J1", "J2"]))  # overload in the baseline
    assert result.reasons == ("replay_findings",)
    assert result.invalidating_findings == {
        "baseline": ("capacity@0", "capacity@1"),
        "candidate": (),
    }
