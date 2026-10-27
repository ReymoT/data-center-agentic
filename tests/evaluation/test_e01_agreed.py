"""E01 hand-truth tests for the agreed #24 portion.

Completed work, the completed_work mapping, per-unit claim tolerances, the strict energy
basis and unscored-claim counting. Hand values use the shared fixture: J1 40 kW x 2,
J2 30 kW x 2, J3 impossible on arrival; site PUE 1 unless stated, hourly slots.
J1 IT energy 80 kWh, facility energy at PUE 1.2 is 96 kWh.
"""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import claims as c
from dc_sustainability.evaluation import replay as r
from dc_sustainability.evaluation.validator import Q03_DRAFT
from tests.contracts import fixtures as f
from tests.evaluation.test_replay import hand_result, starts


def claim(value, unit, text="Synthetic claim.", evidence=()):
    return s.Claim(claim_id="C1", text=text, value=value, unit=unit, evidence_ids=evidence)


# ----------------------------------------------------------------- completed work
def test_completed_count_and_it_energy_are_separate_quantities():
    both = r.replay_episode(f.private_episode(), starts(s0=["J1"], s2=["J2"]), Q03_DRAFT)
    assert (both.completed_job_count, both.completed_it_energy_kwh) == (2, 140.0)
    only_j1 = r.replay_episode(f.private_episode(), starts(s0=["J1"]), Q03_DRAFT)
    assert (only_j1.completed_job_count, only_j1.completed_it_energy_kwh) == (1, 80.0)
    assert only_j1.missed_job_ids == ("J2", "J3")  # no credit, listed separately


def test_absent_completed_work_is_the_expected_case():
    replay = r.replay_episode(f.private_episode(), starts(s0=["J1"], s2=["J2"]), Q03_DRAFT)
    work = r.compare_completed_work(replay, hand_result())
    assert (work.status, work.recorded, work.derived_kwh) == ("absent", None, 140.0)
    assert r.compare_result(replay, hand_result()) == ()


def test_agreed_mapping_is_still_not_comparable_and_keeps_the_difference():
    replay = r.replay_episode(f.private_episode(), starts(s0=["J1"], s2=["J2"]), Q03_DRAFT)
    exact = s.CompletedWork(value=140.0, unit="kWh", definition=r.WORK_DEFINITION)
    work = r.compare_completed_work(replay, hand_result(completed_work=exact))
    assert (work.status, work.reason, work.difference_kwh) == (
        "not_comparable",
        "precision_not_agreed",
        0.0,
    )
    near = exact.model_copy(update={"value": 140.004})
    work = r.compare_completed_work(replay, hand_result(completed_work=near))
    assert work.reason == "precision_not_agreed" and work.difference_kwh == pytest.approx(0.004)
    # Even an exact match is never a clean comparison while precision is unagreed.
    assert [m.field for m in r.compare_result(replay, hand_result(completed_work=exact))] == [
        "completed_work"
    ]


@pytest.mark.parametrize(
    "unit,definition",
    [
        ("kWh", "IT job energy of jobs run to completion (example)"),  # the F02 example
        ("kWh", "completed_facility_energy_v1"),
        ("jobs", r.WORK_DEFINITION),
    ],
)
def test_any_other_mapping_is_not_comparable(unit, definition):
    replay = r.replay_episode(f.private_episode(), starts(s0=["J1"], s2=["J2"]), Q03_DRAFT)
    work = s.CompletedWork(value=140.0, unit=unit, definition=definition)
    result = r.compare_completed_work(replay, hand_result(completed_work=work))
    assert (result.status, result.reason, result.difference_kwh) == (
        "not_comparable",
        "mapping_differs",
        None,
    )


# ----------------------------------------------------------------- unit tolerances
@pytest.mark.parametrize(
    "unit,reference,claimed,expected",
    [
        ("kW", 80.0, 80.05, "correct"),  # inclusive boundary
        ("kW", 80.0, 79.95, "correct"),
        ("kW", 80.0, 80.0500001, "incorrect"),  # no extra epsilon
        ("g/kWh", 250.0, 250.05, "correct"),
        ("g/kWh", 250.0, 249.9, "incorrect"),
        ("kg", 22.0, 22.05, "correct"),
    ],
)
def test_absolute_0_05_tolerance_for_kw_g_per_kwh_and_kg(unit, reference, claimed, expected):
    assert c.score_numeric_claim(claim(claimed, unit), reference, unit).status == expected


@pytest.mark.parametrize(
    "unit,claimed,expected",
    [("slot", 4, "correct"), ("slot", 4.0, "correct"), ("slot", 5, "incorrect"),
     ("slot", 4.04, "incorrect"), ("h", 2, "correct"), ("h", 2.5, "incorrect")],
)  # fmt: skip
def test_slot_and_hour_claims_are_exact_integers(unit, claimed, expected):
    reference = 4 if unit == "slot" else 2
    assert c.score_numeric_claim(claim(claimed, unit), reference, unit).status == expected


def test_fractional_slot_reference_is_a_caller_error():
    with pytest.raises(ValueError, match="whole number"):
        c.score_numeric_claim(claim(4, "slot"), 4.5, "slot")


# ----------------------------------------------------------------- strict energy basis
@pytest.mark.parametrize(
    "text,evidence,claimed,expected",
    [
        ("J1 uses 80 kWh of IT energy.", (), 80.0, "correct"),
        ("J1 uses 80 kWh before PUE.", (), 80.0, "correct"),
        ("J1 uses 96 kWh of facility energy.", (), 96.0, "correct"),
        ("J1 uses 96 kWh including PUE.", (), 96.0, "correct"),
        ("J1 uses 96 kWh.", ("FACT-SITE-PUE", "FACT-JOB-J1"), 96.0, "correct"),
        # A stated basis is checked only on that basis: matching the other never rescues it.
        ("J1 uses 80 kWh of facility energy.", (), 80.0, "incorrect"),
        ("J1 uses 96 kWh of IT energy.", (), 96.0, "incorrect"),
        # Unstated: unsupported even though 80 matches the IT basis exactly.
        ("J1 uses 80 kWh.", ("FACT-JOB-J1",), 80.0, "basis_unstated"),
        ("Starting it now uses 80 kWh.", (), 80.0, "basis_unstated"),  # lowercase "it"
        ("80 kWh of IT energy, 96 kWh at the facility.", (), 80.0, "basis_unstated"),
    ],
)
def test_energy_claims_follow_the_strict_basis_rule(text, evidence, claimed, expected):
    result = c.score_energy_claim(
        claim(claimed, "kWh", text, evidence), it_kwh=80.0, facility_kwh=96.0
    )
    assert result.status == expected


def test_kwh_reference_must_say_its_basis():
    with pytest.raises(ValueError, match="basis"):
        c.score_numeric_claim(claim(80.0, "kWh", "80 kWh of IT energy."), 80.0, "kWh")
    with pytest.raises(ValueError, match="different energy basis"):
        c.score_numeric_claim(
            claim(80.0, "kWh", "80 kWh of IT energy."), 96.0, "kWh", energy_basis="facility"
        )


# ----------------------------------------------------------------- counting
def test_unscored_claims_are_counted_and_never_correct():
    text_only = s.Claim(claim_id="C9", text="Emissions fall 12% compared with starting now.")
    scores = [
        c.score_numeric_claim(claim(22.0, "kg"), 22.0, "kg"),
        c.score_numeric_claim(claim(30.0, "kg"), 22.0, "kg"),
        c.score_energy_claim(claim(80.0, "kWh", "J1 uses 80 kWh."), it_kwh=80.0, facility_kwh=96),
        c.score_numeric_claim(text_only, 22.0, "kg"),  # percent stays manual
        c.score_numeric_claim(claim(22.0, "kg"), None, "kg"),
    ]
    summary = c.summarize(scores)
    assert (summary.total, summary.correct, summary.incorrect) == (5, 1, 1)
    assert summary.unscored == {"basis_unstated": 1, "not_numeric": 1, "reference_unavailable": 1}
    assert summary.correct_of_all == pytest.approx(0.2)
    assert summary.correct_of_scored == pytest.approx(0.5)
    assert c.summarize([]).correct_of_all is None
