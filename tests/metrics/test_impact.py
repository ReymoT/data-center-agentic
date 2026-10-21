import pytest

from dc_sustainability.metrics.impact import (
    Blocked,
    Horizon,
    ImpactError,
    Placement,
    Savings,
    Site,
    Work,
    calculate_impact,
    compare,
    display1,
)

CARBON = {0: 500, 1: 450, 2: 300, 3: 250, 4: 400, 5: 480, 6: 520}
WORK = (Work("J1", 40, 2), Work("J2", 30, 2))
HORIZON = Horizon(0, 7)


def ledger(schedule_id, starts, *, pue=1, carbon=None, completed=("J1", "J2"), work=WORK):
    if carbon is None:
        carbon = CARBON
    return calculate_impact(
        schedule_id,
        "hand",
        HORIZON,
        Site(40, pue, 1),
        work,
        tuple(Placement(job_id, start) for job_id, start in starts.items()),
        completed,
        carbon,
    )


def test_hand_check_at_pue_1():
    asap = ledger("asap", {"J1": 0, "J2": 2})
    shifted = ledger("shifted", {"J1": 2, "J2": 4})
    asap_job_kg = 40 * (500 + 450) / 1000 + 30 * (300 + 250) / 1000
    shifted_job_kg = 40 * (300 + 250) / 1000 + 30 * (400 + 480) / 1000
    background_kg = 40 * sum(CARBON.values()) / 1000
    assert asap_job_kg == pytest.approx(54.5, abs=0.01)
    assert shifted_job_kg == pytest.approx(48.4, abs=0.01)
    assert background_kg == pytest.approx(116, abs=0.01)
    assert asap.totals.job_energy_kwh == pytest.approx(140, abs=0.01)
    assert asap.totals.job_emissions_kg == pytest.approx(asap_job_kg, abs=0.01)
    assert asap.totals.background_emissions_kg == pytest.approx(background_kg, abs=0.01)
    assert asap.totals.site_emissions_kg == pytest.approx(asap_job_kg + background_kg, abs=0.01)
    assert shifted.totals.job_energy_kwh == pytest.approx(140, abs=0.01)
    assert shifted.totals.job_emissions_kg == pytest.approx(shifted_job_kg, abs=0.01)
    assert shifted.totals.background_emissions_kg == pytest.approx(background_kg, abs=0.01)
    assert shifted.totals.site_emissions_kg == pytest.approx(shifted_job_kg + background_kg, abs=0.01)
    assert shifted_job_kg + background_kg == pytest.approx(164.4, abs=0.01)
    assert asap_job_kg + background_kg == pytest.approx(170.5, abs=0.01)


def test_compare_shifted_against_asap():
    asap = ledger("asap", {"J1": 0, "J2": 2})
    shifted = ledger("shifted", {"J1": 2, "J2": 4})
    savings = compare(asap, shifted)
    assert isinstance(savings, Savings)
    assert savings.baseline_schedule_id == "asap"
    assert savings.horizon == HORIZON
    assert savings.input_id == "hand"
    assert savings.completed_job_ids == frozenset({"J1", "J2"})
    assert savings.savings_kg == pytest.approx(6.1, abs=0.01)
    assert display1(100 * savings.of_baseline_job) == "11.2"
    assert display1(100 * savings.of_baseline_site) == "3.6"


def test_pue_1_2_scales_job_energy_and_emissions():
    asap = ledger("asap", {"J1": 0, "J2": 2}, pue=1.2)
    shifted = ledger("shifted", {"J1": 2, "J2": 4}, pue=1.2)
    assert asap.totals.job_energy_kwh == pytest.approx(168, abs=0.01)
    assert asap.totals.job_emissions_kg == pytest.approx(65.4, abs=0.01)
    assert shifted.totals.job_emissions_kg == pytest.approx(58.08, abs=0.01)
    assert display1(58.08) == "58.1"


def test_constant_carbon_gives_equal_job_emissions():
    flat = {slot: 400 for slot in range(7)}
    asap = ledger("asap", {"J1": 0, "J2": 2}, carbon=flat)
    shifted = ledger("shifted", {"J1": 2, "J2": 4}, carbon=flat)
    assert asap.totals.job_emissions_kg is not None
    assert shifted.totals.job_emissions_kg == pytest.approx(asap.totals.job_emissions_kg, abs=0.01)


def test_leftover_job_blocks_savings():
    work = WORK + (Work("J3", 20, 1),)
    baseline = ledger("asap", {"J1": 0, "J2": 2}, work=work)
    running = ledger("running", {"J1": 0, "J2": 2, "J3": 4}, work=work)
    blocked = compare(baseline, running)
    assert isinstance(blocked, Blocked)
    assert blocked.reason == "unfinished_work"
    assert not hasattr(blocked, "savings_kg")
    assert running.totals.job_energy_kwh == pytest.approx(160, abs=0.01)


def test_fewer_completed_jobs_are_blocked():
    baseline = ledger("asap", {"J1": 0, "J2": 2})
    only_j1 = ledger("only-j1", {"J1": 0}, completed=("J1",))
    blocked = compare(baseline, only_j1)
    assert isinstance(blocked, Blocked)
    assert blocked.reason == "completed_jobs_differ"
    assert not hasattr(blocked, "savings_kg")


def test_missing_carbon_keeps_energy_and_blocks_savings():
    gap = {slot: grams for slot, grams in CARBON.items() if slot != 6}
    asap = ledger("asap", {"J1": 0, "J2": 2}, carbon=gap)
    shifted = ledger("shifted", {"J1": 2, "J2": 4}, carbon=gap)
    open_slot = next(row for row in asap.slots if row.slot == 6)
    assert open_slot.energy_kwh == pytest.approx(40, abs=0.01)
    assert open_slot.emissions_kg is None
    assert asap.emissions_complete is False
    blocked = compare(asap, shifted)
    assert isinstance(blocked, Blocked)
    assert blocked.reason == "missing_carbon"


def test_bool_power_and_negative_carbon_raise():
    with pytest.raises(ImpactError):
        ledger("asap", {"J1": 0, "J2": 2}, work=(Work("J1", True, 2), Work("J2", 30, 2)))
    bad = dict(CARBON)
    bad[4] = -400
    with pytest.raises(ImpactError):
        ledger("asap", {"J1": 0, "J2": 2}, carbon=bad)


def test_display1_does_not_change_the_stored_total():
    asap = ledger("asap", {"J1": 0, "J2": 2})
    stored = asap.totals.site_emissions_kg
    assert display1(6.1) == "6.1"
    display1(stored)
    assert asap.totals.site_emissions_kg == stored
    assert stored == pytest.approx(170.5, abs=0.01)
