"""P01 review: hand-derived numeric boundaries and existing F02 value conversion.

These synthetic component checks do not implement/adopt the production S02 adapter
or certify a completed_work scalar mapping, source semantics or a real episode.
"""

import math
from decimal import getcontext, localcontext

import pytest

from dc_sustainability.metrics.impact import (
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
from tests.contracts import fixtures as f


def tiny_and_large():
    common = (
        "same-inputs",
        Horizon(0, 2),
        Site(0, 1, 1),
        (Work("J", 1, 1),),
    )
    carbon = {0: 1e-320, 1: 1e300}
    tiny = calculate_impact("tiny", *common, (Placement("J", 0),), ("J",), carbon)
    large = calculate_impact("large", *common, (Placement("J", 1),), ("J",), carbon)
    return tiny, large


def test_nonfinite_fraction_from_finite_ledgers_raises_existing_error():
    tiny, large = tiny_and_large()
    assert 0 < tiny.totals.site_emissions_kg < 1e-320
    assert math.isfinite(large.totals.site_emissions_kg)
    with pytest.raises(ImpactError, match="not finite"):
        compare(tiny, large)


def test_extreme_but_finite_reverse_comparison_stays_available():
    tiny, large = tiny_and_large()
    result = compare(large, tiny)
    assert isinstance(result, Savings)
    assert math.isfinite(result.savings_kg)
    assert result.savings_kg > 0
    assert result.of_baseline_job == result.of_baseline_site == 1.0


@pytest.mark.parametrize("value,prefix", [(1e30, ""), (-1e30, "-")])
def test_large_finite_display_has_one_decimal_without_global_context_change(value, prefix):
    with localcontext() as context:
        context.prec = 12
        precision = getcontext().prec
        assert display1(value) == prefix + "1" + "0" * 30 + ".0"
        assert display1(1.25) == "1.3"
        assert getcontext().prec == precision


def test_existing_f02_values_preserve_hand_truth_and_pue_boundary():
    # Explicit test-only conversion; Reimo/Edison still agree S02's actual adapter.
    site_record = f.site(pue=1.2)
    jobs = f.jobs()
    work = tuple(
        Work(jobs[j].job_id, jobs[j].power_kw, jobs[j].duration_slots) for j in ["J1", "J2"]
    )
    site = Site(site_record.background_kw, site_record.pue, site_record.slot_hours)
    carbon = dict(enumerate(f.HAND_CARBON))
    baseline = calculate_impact(
        "baseline",
        "F02-hand",
        Horizon(0, 7),
        site,
        work,
        (Placement("J1", 0), Placement("J2", 2)),
        ("J1", "J2"),
        carbon,
    )
    shifted = calculate_impact(
        "shifted",
        "F02-hand",
        Horizon(0, 7),
        site,
        work,
        (Placement("J1", 2), Placement("J2", 4)),
        ("J1", "J2"),
        carbon,
    )
    assert baseline.totals.job_emissions_kg == pytest.approx(65.4, abs=0.01)
    assert shifted.totals.job_emissions_kg == pytest.approx(58.08, abs=0.01)
    assert shifted.totals.site_energy_kwh == pytest.approx(504, abs=0.01)
    assert shifted.totals.job_energy_kwh == pytest.approx(168, abs=0.01)
    # The 168 facility kWh must not be mislabeled as the 140 completed IT kWh.
    assert sum(j.power_kw * j.duration_slots for j in work) == 140
    result = compare(baseline, shifted)
    assert isinstance(result, Savings)
    assert result.savings_kg == pytest.approx(7.32, abs=0.01)
