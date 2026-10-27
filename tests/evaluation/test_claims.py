"""E01 hand-truth tests for the independent impact reference and claim scoring.

The 54.5 kg and 48.4 kg values are the proposal's hand check on the synthetic series
500, 450, 300, 250, 400, 480, 520 g/kWh, worked out by hand:
J1@0: 40 x (500 + 450) / 1000 = 38.0; J2@2: 30 x (300 + 250) / 1000 = 16.5; total 54.5.
J1@2: 40 x (300 + 250) / 1000 = 22.0; J2@4: 30 x (400 + 480) / 1000 = 26.4; total 48.4.
"""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import claims as c
from tests.contracts import fixtures as f

JOBS = f.jobs()
CARBON = c.carbon_series(f.forecasts())


def claim(value, unit="kg"):
    return s.Claim(claim_id="C1", text="Synthetic claim.", value=value, unit=unit)


def test_hand_check_emissions():
    asap = c.schedule_emissions_kg({"J1": 0, "J2": 2}, JOBS, f.site(), CARBON)
    best = c.schedule_emissions_kg({"J1": 2, "J2": 4}, JOBS, f.site(), CARBON)
    assert asap == pytest.approx(54.5, abs=0.01)
    assert best == pytest.approx(48.4, abs=0.01)


def test_pue_scales_energy_and_emissions():
    assert c.job_it_energy_kwh(JOBS["J1"], f.site(1.2)) == pytest.approx(80.0)
    assert c.job_energy_kwh(JOBS["J1"], f.site(1.2)) == pytest.approx(96.0)
    asap = c.schedule_emissions_kg({"J1": 0, "J2": 2}, JOBS, f.site(1.2), CARBON)
    assert asap == pytest.approx(54.5 * 1.2, abs=0.01)


def test_completed_work_matches_the_shared_example():
    total = sum(c.job_it_energy_kwh(JOBS[j], f.site()) for j in ("J1", "J2"))
    assert total == pytest.approx(f.episode_result().completed_work.value)


def test_realized_observations_can_be_the_reference_series():
    realized = c.carbon_series(f.observations())
    assert realized == CARBON


def test_missing_carbon_slot_is_unavailable_not_zero():
    with pytest.raises(c.CarbonUnavailable):
        c.job_emissions_kg(JOBS["J1"], 6, f.site(), CARBON)  # needs slots 6 and 7


def test_duplicate_carbon_slot_is_refused():
    with pytest.raises(ValueError, match="two carbon values"):
        c.carbon_series(f.forecasts() + f.forecasts()[:1])


@pytest.mark.parametrize(
    ("claimed", "expected"),
    [(54.5, "correct"), (54.55, "correct"), (54.45, "correct"), (54.56, "incorrect")],
)
def test_claim_tolerance_is_0_05(claimed, expected):
    assert c.score_numeric_claim(claim(claimed), 54.5, "kg").status == expected


def test_claim_scoring_edge_statuses():
    assert c.score_numeric_claim(claim(54.5, "kWh"), 54.5, "kg").status == "unit_mismatch"
    assert c.score_numeric_claim(claim(54.5), None, "kg").status == "reference_unavailable"
    text_only = s.Claim(claim_id="C2", text="J1 starts now.")
    assert c.score_numeric_claim(text_only, 54.5, "kg").status == "not_numeric"
    assert c.score_numeric_claim(claim(40.0, "kW"), 40.0, "kW").status == "correct"


def test_savings_need_the_same_completed_jobs():
    same = c.compare_emissions(("J1", "J2"), 48.4, ("J2", "J1"), 54.5, same_horizon_and_inputs=True)
    assert same.status == "comparable" and same.savings_kg == pytest.approx(6.1)
    # Finishing only J1 emits less, but that is missing work, not savings.
    partial = c.compare_emissions(("J1",), 22.0, ("J1", "J2"), 54.5, same_horizon_and_inputs=True)
    assert partial.status == "not_comparable" and partial.savings_kg is None
    other = c.compare_emissions(
        ("J1", "J2"), 48.4, ("J1", "J2"), 54.5, same_horizon_and_inputs=False
    )
    assert other.status == "not_comparable"
