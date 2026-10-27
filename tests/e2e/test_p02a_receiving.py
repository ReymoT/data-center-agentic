"""Actual greedy A/checker/controller receiving on synthetic development inputs.

Only the agent test uses synthetic HTTP, renderers and token counting. Its fallback
is the real P02 function, and its checker, controller and evidence store are real.
No model inference, production prompts, B policy or experiment runner is implied.
"""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.agent import AgentHarness
from dc_sustainability.knowledge import retrieve
from dc_sustainability.policies import propose
from dc_sustainability.runtime import ExecutionController, TraceStore
from dc_sustainability.simulator import SchedulingSimulator
from dc_sustainability.simulator.impact import account_realized
from dc_sustainability.verification.checker import check_schedule
from tests.agent.test_harness import decide, messages, plan, response, setup
from tests.contracts import fixtures as f
from tests.llm.test_ollama_provider import server as server  # noqa: F401
from tests.simulator.test_core import episode


@pytest.mark.parametrize("pue", [1.0, 2.0])
def test_real_greedy_a_reserves_background_and_other_proposed_jobs(pue):
    snapshot = f.snapshot(pue=pue)
    state = f.visible_state(snapshot)
    output = propose(state, retrieve(state, snapshot).context)
    assert output.plan.status == "proposed"
    assert [(x.job_id, x.start_slot) for x in output.plan.starts] == [("J1", 0), ("J2", 2)]
    assert check_schedule(output.plan, state, snapshot).status == "pass"


def test_seventy_kw_limit_credits_background_and_checks_individual_abstention():
    snapshot = f.snapshot(capacity_kw=70)
    state = f.visible_state(snapshot)
    output = propose(state, retrieve(state, snapshot).context)
    assert [(x.job_id, x.start_slot) for x in output.plan.starts] == [("J2", 0)]
    assert [(x.job_id, x.reason) for x in output.plan.abstentions] == [
        ("J1", "constraint_violation")
    ]
    assert check_schedule(output.plan, state, snapshot).status == "pass"


@pytest.mark.parametrize("pue", [1.0, 1.2])
def test_real_greedy_a_controller_replans_running_work_and_drains_thirty_slots(tmp_path, pue):
    ep = episode(tuple(f.jobs()[j] for j in ("J1", "J2")))
    ep = ep.model_copy(
        update={
            "snapshot": ep.snapshot.model_copy(
                update={"site": ep.snapshot.site.model_copy(update={"pue": pue})}
            )
        }
    )
    sim = SchedulingSimulator(allow_completion_starts=False)
    sim.reset(ep)
    store = TraceStore(tmp_path / "traces")
    controller = ExecutionController(sim, lambda: ep.snapshot, store)
    records = []
    for slot in range(30):
        state = sim.state()
        output = propose(state, retrieve(state, ep.snapshot).context)
        check = check_schedule(output.plan, state, ep.snapshot)
        assert check.status == "pass", (slot, check)
        draft = s.DecisionRecord(
            decision_id=f"DEC-P02A-{slot}",
            run_id="RUN-P02A",
            system="greedy_a",
            episode_id=state.episode_id,
            slot=slot,
            initial=s.StageRecord(plan=output.plan, check=check),
            not_applicable_stages=("repaired", "fallback"),
            final_status="blocked",
        )
        result = controller.execute_step(
            draft, stage="initial", expected_state_version=state.state_version
        )
        assert result.record.final_status == "executed"
        assert result.record.execution_check.status == "pass"
        assert result.record.model_call_count == result.record.repair_count == 0
        assert store.read(draft.decision_id) == result.record
        if slot == 1:
            assert state.running_job_load_kw(slot) == 40
            assert output.plan.starts[0].start_slot == 2
            assert result.record.executed_starts == ()
        records.append(result.record)
    assert sim.state().current_slot == len(sim.history) == len(records) == 30
    assert [(r.slot, x.job_id) for r in records for x in r.executed_starts] == [
        (0, "J1"),
        (2, "J2"),
    ]
    accounting = account_realized(ep, sim.result(run_id="RUN-P02A", system="greedy_a"))
    assert accounting.completed_it_energy_kwh == 140
    assert accounting.result.totals.site_energy_kwh == pytest.approx(1340 * pue)


def test_agent_failed_repair_uses_real_greedy_a_and_actual_execution_gate(server, tmp_path):
    ep, sim, store, controller, client = setup(server, tmp_path)
    response(server, plan(sim.state(), overlap=True))
    result = decide(
        AgentHarness(
            client,
            controller,
            proposal_messages=messages,
            repair_messages=messages,
            fallback=propose,
        ),
        sim,
        ep,
    )
    record = result.execution.record
    assert record.initial.check.status == record.repaired.check.status == "fail"
    assert record.fallback.check.status == "pass"
    assert record.execution_check is not None and record.execution_check.status == "pass"
    assert record.final_status == "executed"
    assert [(x.job_id, x.start_slot) for x in record.fallback.plan.starts] == [("J1", 0), ("J2", 2)]
    assert tuple(x.job_id for x in record.executed_starts) == ("J1",)
    assert record.model_call_count == len(client.attempts) == len(server.requests) == 2
    assert record.repair_count == 1
    assert store.read(record.decision_id) == record
