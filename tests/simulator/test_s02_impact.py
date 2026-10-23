"""Synthetic S02 consumer evidence; no production gate or scientific acceptance."""

import pytest

from dc_sustainability.data.scenarios import hand_jobs
from dc_sustainability.metrics.impact import Blocked, Savings
from dc_sustainability.simulator.impact import account_realized, compare_realized
from tests.simulator.test_core import action, episode, simulator


def run(starts, *, pue=1, missing=(), jobs=None, carbon_tail=100):
    ep = episode(hand_jobs()[:2] if jobs is None else jobs)
    observations = list(ep.realized_carbon)
    template = observations[0]
    observations += [
        template.model_copy(
            update={"fact_id": f"FACT-TAIL-{slot}", "valid_slot": slot, "value": carbon_tail}
        )
        for slot in range(7, 30)
    ]
    ep = ep.model_copy(
        update={
            "snapshot": ep.snapshot.model_copy(
                update={
                    "site": ep.snapshot.site.model_copy(update={"pue": pue}),
                    "constraints": tuple(
                        c for c in ep.snapshot.constraints if not c.applies_to_jobs
                    ),
                }
            ),
            "realized_carbon": tuple(o for o in observations if o.valid_slot not in missing),
        }
    )
    sim = simulator(ep)
    for slot in range(30):
        sim.step(action(sim, *starts.get(slot, ())))
    raw = sim.result(run_id="RUN-S02", system="greedy_a")
    return ep, raw, account_realized(ep, raw)


@pytest.mark.parametrize("pue", [1, 1.2])
def test_hand_values_and_all_30_slots(pue):
    _, _, baseline = run({0: ("J1",), 2: ("J2",)}, pue=pue)
    _, _, shifted = run({2: ("J1",), 4: ("J2",)}, pue=pue)
    for accounting, job_kg in [(baseline, 54.5), (shifted, 48.4)]:
        totals = accounting.result.totals
        assert len(accounting.impact.slots) == 30
        assert totals.job_energy_kwh == pytest.approx(140 * pue)
        assert totals.background_energy_kwh == pytest.approx(1200 * pue)
        assert totals.site_energy_kwh == pytest.approx(1340 * pue)
        assert totals.job_emissions_kg == pytest.approx(job_kg * pue)
        assert totals.background_emissions_kg == pytest.approx((116 + 92) * pue)
        assert totals.site_emissions_kg == pytest.approx((job_kg + 208) * pue)
        assert sum(s.emissions_kg for s in accounting.result.slots[:7]) == pytest.approx(
            (job_kg + 116) * pue
        )
        assert accounting.completed_it_energy_kwh == 140
        assert accounting.result.completed_job_ids == ("J1", "J2")
        assert accounting.result.completed_work is None
        assert all(s.energy_kwh == 40 * pue for s in accounting.result.slots[7:])
    comparison = compare_realized(baseline, shifted)
    assert isinstance(comparison, Savings)
    assert comparison.savings_kg == pytest.approx(6.1 * pue)


def test_incomplete_work_is_never_savings_even_when_both_omit_same_job():
    _, _, full = run({0: ("J1",), 2: ("J2",)})
    _, _, incomplete = run({0: ("J1",)})
    assert incomplete.completed_it_energy_kwh == 80
    assert incomplete.result.unfinished_job_ids == ("J2",)
    for first, second in [(full, incomplete), (incomplete, incomplete)]:
        comparison = compare_realized(first, second)
        assert isinstance(comparison, Blocked)
        assert not hasattr(comparison, "savings_kg")


@pytest.mark.parametrize("missing", [(0,), (29,), tuple(range(30))])
def test_missing_actuals_keep_energy_and_refuse_comparison(missing):
    _, _, accounting = run({0: ("J1",), 2: ("J2",)}, missing=missing)
    assert accounting.result.totals.site_energy_kwh == 1340
    assert accounting.result.totals.site_emissions_kg is None
    assert all(accounting.result.slots[s].emissions_kg is None for s in missing)
    assert isinstance(compare_realized(accounting, accounting), Blocked)
    if missing == (29,):
        assert accounting.result.totals.job_emissions_kg == pytest.approx(54.5)


def test_replay_serialization_and_no_forecast_substitution():
    ep, raw, accounting = run({0: ("J1",), 2: ("J2",)})
    assert (
        account_realized(type(ep).from_json(ep.to_json()), type(raw).from_json(raw.to_json()))
        == accounting
    )
    assert run({0: ("J1",), 2: ("J2",)})[2] == accounting
    assert (
        account_realized(ep.model_copy(update={"forecast_visibility": "withheld"}), raw)
        == accounting
    )
    empty = ep.model_copy(update={"realized_carbon": ()})
    assert account_realized(empty, raw).result.totals.site_emissions_kg is None
    duplicate = ep.realized_carbon[0].model_copy(update={"fact_id": "FACT-DUPLICATE"})
    with pytest.raises(ValueError, match="duplicate slot"):
        account_realized(
            ep.model_copy(update={"realized_carbon": (*ep.realized_carbon, duplicate)}), raw
        )


def test_executed_starts_only_and_completion_tail():
    job = hand_jobs()[0].model_copy(update={"deadline_slot": 30, "duration_slots": 4})
    _, _, accounting = run({0: ("UNKNOWN",), 23: ("J1",)}, jobs=(job,))
    assert accounting.impact.totals.job_energy_kwh == 160
    assert accounting.completed_it_energy_kwh == 160
    assert [s.slot for s in accounting.impact.slots if s.job_load_kw] == [23, 24, 25, 26]
    assert accounting.result.slots[0].started_job_ids == ()
