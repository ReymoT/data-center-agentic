"""Real graph/components over synthetic HTTP, not inference or production P02.

Prompt renderers, counter and optional fallback below are test-only fixtures.
"""

import base64
import json
import time
from dataclasses import replace

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.agent import AgentHarness
from dc_sustainability.data.scenarios import hand_jobs
from dc_sustainability.llm.provider import CallBlocked
from dc_sustainability.runtime import ExecutionController, TraceStore
from dc_sustainability.simulator import SchedulingSimulator
from tests.llm.test_ollama_provider import envelope, provider
from tests.llm.test_ollama_provider import server as server  # noqa: F401
from tests.simulator.test_core import episode


def setup(server, tmp_path, *, jobs=None, **options):
    ep = episode(hand_jobs()[:2] if jobs is None else jobs)
    sim = SchedulingSimulator(allow_completion_starts=False)
    sim.reset(ep)
    store = TraceStore(tmp_path / "traces")
    controller = ExecutionController(sim, lambda: ep.snapshot, store)
    return ep, sim, store, controller, provider(server, **options)


def plan(view, *, overlap=False):
    return s.Plan(
        episode_id=view.episode_id,
        slot=view.current_slot,
        state_version=view.state_version,
        status="proposed",
        starts=(
            s.PlannedStart(job_id="J1", start_slot=0),
            s.PlannedStart(job_id="J2", start_slot=0 if overlap else 2),
        ),
    )


def response(server, value):
    server.body = {**envelope(), "message": {"role": "assistant", "content": value.to_json()}}


def messages(context, *args):
    return [
        {"role": "user", "content": "SYNTHETIC TEST, NOT INFERENCE\n" + context.content.to_json()}
    ]


def decide(harness, sim, ep, **changes):
    args = dict(
        decision_id=f"DEC-A{sim.state().current_slot}",
        run_id="RUN-AGENT",
        trial=0,
        seed=7,
        decision_deadline=time.monotonic() + 10,
    )
    args.update(changes)
    return harness.run_decision(sim.state(), ep.snapshot, **args)


def test_real_plan_is_checked_executed_and_saved_losslessly(server, tmp_path):
    ep, sim, store, controller, client = setup(server, tmp_path)
    response(server, plan(sim.state()))
    result = decide(AgentHarness(client, controller, proposal_messages=messages), sim, ep)
    record = result.execution.record
    assert record.final_status == "executed" and record.initial.check.status == "pass"
    assert record.model_call_count == len(result.attempts) == len(server.requests) == 1
    assert record.repair_count == 0 and record.fallback is None
    assert result.execution.transition.slot.started_job_ids == ("J1",)
    artifact = json.loads(next((store.directory / "provider-attempts").iterdir()).read_text())
    assert base64.b64decode(artifact["raw_response"]) == result.attempts[0].raw_response
    assert json.loads(artifact["request_json"]) == server.requests[0]
    assert (artifact["decision_id"], artifact["run_id"], artifact["stage"]) == (
        record.decision_id,
        record.run_id,
        "propose",
    )
    assert "CON-DL-J3" not in json.dumps(server.requests)
    assert store.read(record.decision_id) == record


def test_one_actual_successful_repair(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path)
    good = plan(sim.state())
    response(server, plan(sim.state(), overlap=True))

    def repair(context, initial, errors):
        assert initial.check.status == "fail"
        response(server, good)
        return messages(context)

    result = decide(
        AgentHarness(client, controller, proposal_messages=messages, repair_messages=repair),
        sim,
        ep,
    )
    record = result.execution.record
    assert record.model_call_count == len(server.requests) == 2 and record.repair_count == 1
    assert record.initial.check.status == "fail" and record.repaired.check.status == "pass"
    assert record.final_status == "executed" and record.execution_check.plan_hash == good.plan_hash
    assert result.route.count("repair") == 1


def test_failed_repair_has_no_fake_p02(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path)
    response(server, plan(sim.state(), overlap=True))
    result = decide(
        AgentHarness(client, controller, proposal_messages=messages, repair_messages=messages),
        sim,
        ep,
    )
    record = result.execution.record
    assert record.model_call_count == 2 and record.repair_count == 1 and record.fallback is None
    assert record.final_status == "blocked" and not record.executed_starts
    assert any("real P02 fallback unavailable" in error for error in record.errors)
    assert sim.state().current_slot == len(sim.history) == 1


def test_test_only_fallback_and_explanation_stay_within_three_calls(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path)
    good = plan(sim.state())
    response(server, plan(sim.state(), overlap=True))

    def fixture_fallback(view, context):
        return s.PolicyOutput(system="greedy_a", output_status="ok", plan=good)

    def explain(context, selected):
        assert selected.plan == good and selected.check.status == "pass"
        response(server, s.Explanation(summary="Synthetic proposed hand plan.", source="llm"))
        return messages(context)

    result = decide(
        AgentHarness(
            client,
            controller,
            proposal_messages=messages,
            repair_messages=messages,
            fallback=fixture_fallback,
            explanation_messages=explain,
        ),
        sim,
        ep,
    )
    record = result.execution.record
    assert record.model_call_count == len(server.requests) == 3 and record.repair_count == 1, (
        record.errors,
        result.route,
        record.fallback,
    )
    assert record.initial.check.status == record.repaired.check.status == "fail"
    assert record.fallback.check.status == "pass" and record.final_status == "executed"
    assert record.explanation.source == "llm" and len(client.attempts) == 3


def test_malformed_wire_bytes_are_spent_and_preserved(server, tmp_path):
    ep, sim, store, controller, client = setup(server, tmp_path)
    server.body = b"not-json-\xff"
    result = decide(AgentHarness(client, controller, proposal_messages=messages), sim, ep)
    assert result.execution.record.model_call_count == 1 and result.execution.record.initial is None
    assert result.execution.record.final_status == "blocked"
    saved = json.loads(next((store.directory / "provider-attempts").iterdir()).read_text())
    assert base64.b64decode(saved["raw_response"]) == b"not-json-\xff"


def test_runtime_mismatch_does_not_spend_or_retry(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path)
    server.version = "different"
    result = decide(
        AgentHarness(client, controller, proposal_messages=messages, repair_messages=messages),
        sim,
        ep,
    )
    assert result.execution.record.model_call_count == result.execution.record.repair_count == 0
    assert not server.requests and not client.attempts and "repair" not in result.route


def test_run_cap_is_not_reset_for_repair(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path, max_run_attempts=1)
    response(server, plan(sim.state(), overlap=True))
    result = decide(
        AgentHarness(client, controller, proposal_messages=messages, repair_messages=messages),
        sim,
        ep,
    )
    assert (
        len(server.requests)
        == len(client.attempts)
        == result.execution.record.model_call_count
        == 1
    )
    assert result.execution.record.repair_count == 0
    assert any("run attempt cap" in error for error in result.execution.record.errors)


def test_explanation_cannot_replace_selected_actions(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path)
    good = plan(sim.state())
    response(server, good)

    def malicious(context, selected):
        server.body = {
            **envelope(),
            "message": {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "record_type": "Explanation",
                        "schema_version": s.SCHEMA_VERSION,
                        "source": "llm",
                        "summary": "not an action",
                        "plan": {"starts": []},
                    }
                ),
            },
        }
        return messages(context)

    result = decide(
        AgentHarness(
            client, controller, proposal_messages=messages, explanation_messages=malicious
        ),
        sim,
        ep,
    )
    assert (
        result.execution.record.explanation is None
        and result.execution.record.model_call_count == 2
    )
    assert result.execution.record.execution_check.plan_hash == good.plan_hash
    assert result.execution.transition.slot.started_job_ids == ("J1",)


def test_all_empty_and_completion_slots_dispatch_zero_calls(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path, jobs=[])
    harness = AgentHarness(client, controller)
    for slot in range(30):
        result = decide(harness, sim, ep)
        assert result.execution.record.slot == slot
        assert result.execution.record.model_call_count == result.execution.record.repair_count == 0
        assert result.execution.record.final_status == "executed"
    assert not server.requests and not client.attempts and len(sim.history) == 30


@pytest.mark.parametrize("missing", ["renderer", "deadline"])
def test_unavailable_inputs_never_dispatch(server, tmp_path, missing):
    ep, sim, _, controller, client = setup(server, tmp_path)
    harness = AgentHarness(
        client, controller, proposal_messages=None if missing == "renderer" else messages
    )
    extra = {"decision_deadline": time.monotonic() - 1} if missing == "deadline" else {}
    result = decide(harness, sim, ep, **extra)
    assert result.execution.record.final_status == "blocked" and not server.requests
    assert not result.attempts and sim.state().current_slot == 1


def test_duplicate_decision_spends_no_new_call_or_step(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path)
    response(server, plan(sim.state()))
    view = sim.state()
    harness = AgentHarness(client, controller, proposal_messages=messages)
    decide(harness, sim, ep)
    with pytest.raises(CallBlocked, match="already handled"):
        harness.run_decision(
            view,
            ep.snapshot,
            decision_id="DEC-A0",
            run_id="RUN-AGENT",
            trial=0,
            seed=7,
            decision_deadline=time.monotonic() + 10,
        )
    assert len(server.requests) == len(sim.history) == 1


def test_unreported_usage_stays_unknown(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path)
    response(server, plan(sim.state()))
    del server.body["prompt_eval_count"]
    del server.body["eval_count"]
    result = decide(AgentHarness(client, controller, proposal_messages=messages), sim, ep)
    assert result.execution.record.prompt_tokens is None
    assert result.execution.record.completion_tokens is None


def test_attempt_storage_failure_withholds_execution(server, tmp_path, monkeypatch):
    ep, sim, _, controller, client = setup(server, tmp_path)
    response(server, plan(sim.state()))

    def fail(attempt, **link):
        raise OSError("test-only provider-artifact failure")

    monkeypatch.setattr(controller, "record_attempt", fail)
    result = decide(AgentHarness(client, controller, proposal_messages=messages), sim, ep)
    assert result.execution.record.model_call_count == 1 and len(client.attempts) == 1
    assert (
        result.execution.record.final_status == "blocked"
        and not result.execution.record.executed_starts
    )
    assert any("persistence failed" in error for error in result.execution.record.errors)


@pytest.mark.parametrize("change", [{"run_id": "RUN-OTHER"}, {"trial": 1}, {"seed": 8}])
def test_run_identity_cannot_change_within_a_shared_provider(server, tmp_path, change):
    ep, sim, _, controller, client = setup(server, tmp_path, jobs=[])
    harness = AgentHarness(client, controller)
    decide(harness, sim, ep)
    with pytest.raises(CallBlocked, match="one harness/provider"):
        decide(harness, sim, ep, **change)
    assert not client.attempts and len(sim.history) == 1


def test_original_attempt_artifact_cannot_be_replaced(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path)
    response(server, plan(sim.state()))
    result = decide(AgentHarness(client, controller, proposal_messages=messages), sim, ep)
    attempt = result.attempts[0]
    link = dict(decision_id="DEC-A0", run_id="RUN-AGENT", stage="propose")
    path = controller.record_attempt(attempt, **link)
    original = path.read_bytes()
    with pytest.raises(ValueError, match="different provider attempt"):
        controller.record_attempt(replace(attempt, raw_response=b"changed test bytes"), **link)
    assert path.read_bytes() == original


def test_failed_http_attempt_is_counted_and_never_replaced_with_success(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path)
    server.status = 500
    result = decide(AgentHarness(client, controller, proposal_messages=messages), sim, ep)
    assert result.execution.record.model_call_count == len(client.attempts) == 1
    assert result.attempts[0].http_status == 500 and result.attempts[0].uncertain_outcome
    assert (
        result.execution.record.initial is None
        and result.execution.record.final_status == "blocked"
    )
