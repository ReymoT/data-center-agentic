"""Actual B/A-fallback, K02, A03, A04, S01/S02; synthetic hand data, no model calls."""

from datetime import timedelta

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.knowledge import retrieve
from dc_sustainability.policies import propose
from dc_sustainability.runtime import ExecutionController, TraceStore
from dc_sustainability.simulator import SchedulingSimulator
from dc_sustainability.simulator.impact import account_realized
from dc_sustainability.verification.checker import check_schedule
from tests.contracts import fixtures as f
from tests.simulator.test_core import episode


@pytest.mark.parametrize("withheld", [False, True])
def test_b_replans_and_retains_requested_system_and_checked_fallback_stage(tmp_path, withheld):
    ep = episode((f.jobs()["J1"], f.jobs()["J2"]), withheld=withheld)
    sim = SchedulingSimulator(allow_completion_starts=False)
    # Explicit public synthetic forecasts, never converted private actuals.
    forecast_map = (
        {}
        if withheld
        else {
            slot: tuple(fact for fact in f.forecasts(issued_slot=slot) if fact.valid_slot >= slot)
            for slot in range(30)
        }
    )
    sim.reset(ep, forecasts_by_slot=forecast_map)
    store = TraceStore(tmp_path / "traces")
    controller = ExecutionController(sim, lambda: ep.snapshot, store)
    fallback_slots, executed = [], []
    for slot in range(30):
        state = sim.state()
        output = propose(
            state,
            retrieve(state, ep.snapshot).context,
            system="greedy_b",
            decision_time_utc=f.SLOT0_UTC + timedelta(hours=slot),
        )
        check = check_schedule(output.plan, state, ep.snapshot)
        assert check.status == "pass", (slot, check)
        is_fallback = output.system == "greedy_a"
        stage = "fallback" if is_fallback else "initial"
        draft = s.DecisionRecord(
            decision_id=f"DEC-P02B-{slot}",
            run_id="RUN-P02B",
            system="greedy_b",  # requested system, even when its effective proposal is A
            episode_id=state.episode_id,
            slot=slot,
            **{stage: s.StageRecord(plan=output.plan, check=check)},
            not_applicable_stages=("initial", "repaired")
            if is_fallback
            else ("repaired", "fallback"),
            explanation=output.explanation,
            final_status="blocked",
        )
        result = controller.execute_step(
            draft, stage=stage, expected_state_version=state.state_version
        )
        assert result.record.system == "greedy_b"
        assert result.record.final_status == "executed"
        assert result.record.execution_check.status == "pass"
        assert result.record.model_call_count == result.record.repair_count == 0
        assert store.read(draft.decision_id) == result.record
        executed.extend((slot, x.job_id) for x in result.record.executed_starts)
        if is_fallback:
            fallback_slots.append(slot)
            assert result.record.initial is None and result.record.fallback.check.status == "pass"
            assert result.record.explanation.summary == "missing"
            assert not result.record.explanation.claims
        else:
            assert result.record.initial.check.status == "pass" and result.record.fallback is None
    assert fallback_slots == ([0, 1, 2] if withheld else [])
    # Public hand arithmetic: J1 takes slots 2/3 (300+250); J2 then
    # prefers 4/5 (400+480) over the remaining 0/1 (500+450).
    assert executed == ([(0, "J1"), (2, "J2")] if withheld else [(2, "J1"), (4, "J2")])
    assert sim.state().current_slot == len(sim.history) == 30
    accounting = account_realized(ep, sim.result(run_id="RUN-P02B", system="greedy_b"))
    assert accounting.result.completed_job_ids == ("J1", "J2")
    assert accounting.completed_it_energy_kwh == 140
    assert accounting.result.totals.site_energy_kwh == 1340
