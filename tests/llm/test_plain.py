"""L01 plain-LLM tests over real loopback HTTP with scripted, synthetic responses.

The test server is not a model. These tests check the one-call rule, preservation of
original output, setting/fact equivalence with the agent and the absence of any repair
or fallback. They are not evidence of model inference or of a real episode.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import validator as v
from dc_sustainability.llm import plain
from dc_sustainability.llm.plain import PlainLLMPolicy
from dc_sustainability.llm.provider import CallBlocked, Deployment, OllamaProvider
from dc_sustainability.llm.response_bounds import bounded_response_schema
from tests.contracts import fixtures as f

DIGEST = "b" * 64  # synthetic artifact identity, not an installed model checksum


def plain_output_json(plan: s.Plan | None = None) -> str:
    return s.PolicyOutput(
        system="plain_llm",
        output_status="ok",
        plan=plan or f.plan(),
        explanation=s.Explanation(
            source="llm",
            summary="Synthetic test explanation; J1 starts now.",
            claims=(s.Claim(claim_id="C1", text="J1 arrived.", evidence_ids=("FACT-JOB-J1",)),),
        ),
    ).to_json()


def envelope(content: str) -> dict:
    return {
        "model": "qwen3:8b",
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": content},
        "prompt_eval_count": 30,
        "eval_count": 15,
        "total_duration": 2000000,
    }


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, body, status=200):
            raw = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path == "/api/version":
                self.respond({"version": self.server.version})
            else:
                models = [
                    {
                        "name": "qwen3:8b",
                        "digest": DIGEST,
                        "details": {"quantization_level": "Q4_K_M"},
                    }
                ]
                self.respond({"models": models})

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            self.server.requests.append(json.loads(raw))
            self.respond(self.server.body, self.server.status)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    httpd.requests, httpd.status, httpd.version = [], 200, "synthetic-1"
    httpd.body = envelope(plain_output_json())
    thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.01})
    thread.daemon = True
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=2)


def provider(server) -> OllamaProvider:
    deployment = Deployment(
        base_url=f"http://127.0.0.1:{server.server_port}",
        runtime_version="synthetic-1",
        model_digest=DIGEST,
        max_run_attempts=8,
        max_response_bytes=100000,
        max_prompt_tokens=1000,
        context_policy_ref="synthetic-test-counter-only",
    )
    # A synthetic counter belongs only to this test. No production tokenizer is implied.
    return OllamaProvider(deployment, count_prompt_tokens=lambda request: 30)


def state_and_context(**changes):
    state = f.visible_state(**changes)
    return state, s.Context.build(state, f.snapshot(), "flat")


def propose(policy, state=None, context=None, seed=101):
    if state is None:
        state, context = state_and_context()
    return policy.propose(state, context, seed=seed, decision_deadline=time.monotonic() + 10)


def test_valid_output_is_kept_with_its_original_text(server):
    decision = propose(PlainLLMPolicy(provider(server)))
    assert len(server.requests) == 1
    assert decision.output.output_status == "ok"
    assert decision.output.system == "plain_llm"
    assert decision.output.plan == f.plan()
    assert decision.output.raw_response == plain_output_json()
    assert decision.attempt.prompt_tokens == 30 and decision.attempt.completion_tokens == 15
    assert decision.blocked_reason is None


def test_request_uses_policy_output_schema_and_rendered_messages(server):
    state, context = state_and_context()
    decision = propose(PlainLLMPolicy(provider(server)), state, context)
    request = server.requests[0]
    expected_format, _ = bounded_response_schema(s.PolicyOutput, state, system="plain_llm")
    assert request["format"] == expected_format
    assert request["messages"] == plain.render_messages(context)
    assert decision.messages_sha256 == plain.messages_sha256(request["messages"])
    assert decision.context_hash == context.content_hash


def test_plain_and_agent_requests_share_model_and_generation_settings(server):
    state, context = state_and_context()
    client = provider(server)
    propose(PlainLLMPolicy(client), state, context, seed=101)
    client.generate(
        system="agent",
        state=state,
        seed=101,
        messages=[{"role": "user", "content": "Synthetic agent request."}],
        response_model=s.Plan,
        decision_deadline=time.monotonic() + 10,
    )
    plain_request, agent_request = server.requests
    for key in ("model", "stream", "think", "keep_alive", "options"):
        assert plain_request[key] == agent_request[key]
    assert plain_request["options"]["temperature"] == 0.2


def test_prompt_contains_every_visible_fact_and_no_private_keys(server):
    state, context = state_and_context()
    user = plain.render_messages(context)[1]["content"]
    for evidence_id in context.content.evidence_ids:
        assert evidence_id in user
    facts = json.loads(user[user.index("{") :])
    assert facts == context.content.to_jsonable()
    s.assert_no_private_keys(facts)
    assert "J3" not in user  # J3 has not arrived at slot 0


def test_malformed_output_is_preserved_without_retry_or_repair(server):
    server.body = envelope('{"plan": not json')
    decision = propose(PlainLLMPolicy(provider(server)))
    assert len(server.requests) == 1
    assert decision.output.output_status == "malformed"
    assert decision.output.plan is None
    assert decision.output.raw_response == '{"plan": not json'
    assert decision.attempt.error.startswith("invalid response")


def test_model_cannot_self_approve_and_is_not_rewritten(server):
    content = plain_output_json(f.plan(status="approved"))
    server.body = envelope(content)
    decision = propose(PlainLLMPolicy(provider(server)))
    assert decision.output.output_status == "malformed"
    assert decision.output.raw_response == content
    assert len(server.requests) == 1


def test_unsafe_but_well_formed_plan_is_passed_through_unchanged(server):
    # Starting J2 at slot 0 overlaps J1 and starting J9 names an unknown job. The
    # plain path does not check or fix this; the shared checker and gate do.
    unsafe = f.plan().model_copy(
        update={
            "starts": (
                s.PlannedStart(job_id="J1", start_slot=0),
                s.PlannedStart(job_id="J2", start_slot=0),
                s.PlannedStart(job_id="J9", start_slot=0),
            )
        }
    )
    server.body = envelope(plain_output_json(unsafe))
    decision = propose(PlainLLMPolicy(provider(server)))
    assert decision.output.output_status == "ok"
    assert decision.output.plan.starts == unsafe.starts
    assert len(server.requests) == 1


def test_empty_content_is_no_output(server):
    server.body = envelope("")
    decision = propose(PlainLLMPolicy(provider(server)))
    assert decision.output.output_status == "no_output"
    assert decision.output.raw_response is None


def test_transport_failure_is_an_uncertain_error_and_not_retried(server):
    server.status, server.body = 500, b"synthetic server failure"
    decision = propose(PlainLLMPolicy(provider(server)))
    assert len(server.requests) == 1
    assert decision.attempt.uncertain_outcome
    assert decision.output.output_status == "error"
    assert decision.output.raw_response == "synthetic server failure"


def test_second_request_for_the_same_decision_is_refused(server):
    policy = PlainLLMPolicy(provider(server))
    server.body = envelope('{"bad": ')
    propose(policy)
    with pytest.raises(CallBlocked, match="one request"):
        propose(policy)
    assert len(server.requests) == 1


def test_pre_dispatch_block_is_recorded_and_still_uses_the_decision(server):
    server.version = "different-runtime"
    policy = PlainLLMPolicy(provider(server))
    decision = propose(policy)
    assert server.requests == []
    assert decision.attempt is None
    assert decision.output.output_status == "error"
    assert "runtime differs" in decision.blocked_reason
    server.version = "synthetic-1"
    with pytest.raises(CallBlocked, match="one request"):
        propose(policy)
    assert server.requests == []


def test_next_slot_is_a_new_decision(server):
    policy = PlainLLMPolicy(provider(server))
    propose(policy)
    later_plan = f.plan().model_copy(update={"slot": 1, "state_version": 1})
    server.body = envelope(plain_output_json(later_plan))
    later_state, later_context = state_and_context(current_slot=1)
    later = propose(policy, later_state, later_context)
    assert len(server.requests) == 2
    assert later.output.output_status == "ok"


def test_graph_context_is_refused_before_any_request(server):
    state = f.visible_state()
    context = s.Context.build(state, f.snapshot(), "graph")
    with pytest.raises(ValueError, match="flat"):
        propose(PlainLLMPolicy(provider(server)), state, context)
    assert server.requests == []


def test_context_for_another_state_is_refused(server):
    state, _ = state_and_context()
    _, other_context = state_and_context(current_slot=1)
    with pytest.raises(ValueError, match="does not match"):
        propose(PlainLLMPolicy(provider(server)), state, other_context)
    assert server.requests == []


def test_completion_slot_makes_no_call(server):
    state, context = state_and_context()
    late = state.model_copy(update={"current_slot": s.PROPOSED_DECISION_SLOTS})
    with pytest.raises(CallBlocked, match="completion"):
        propose(PlainLLMPolicy(provider(server)), late, context)
    assert server.requests == []


def test_empty_queue_records_a_noop_without_any_request(server):
    shared = provider(server)
    state, context = state_and_context(waiting_job_ids=())
    decision = propose(PlainLLMPolicy(shared), state, context)
    assert server.requests == [] and shared.attempts == ()
    assert decision.empty_queue_noop
    assert (decision.attempt, decision.blocked_reason) == (None, None)
    out = decision.output
    assert (out.output_status, out.explanation, out.raw_response) == ("ok", None, None)
    assert (out.plan.episode_id, out.plan.slot, out.plan.state_version) == (f.EPISODE_ID, 0, 0)
    assert (out.plan.starts, out.plan.deferrals, out.plan.abstentions) == ((), (), ())
    assert decision.context_hash == context.content_hash


def test_empty_queue_noop_is_the_valid_decision_for_e01(server):
    state, context = state_and_context(waiting_job_ids=())
    decision = propose(PlainLLMPolicy(provider(server)), state, context)
    facts = v.facts_from_state(state, f.snapshot())
    result = v.validate_output(decision.output, facts, v.Q03_DRAFT)
    assert result.valid and result.empty_queue


def test_empty_queue_noop_does_not_depend_on_the_runtime(server):
    # Even a runtime that would block dispatch is never consulted for an empty queue.
    server.version = "different-runtime"
    state, context = state_and_context(waiting_job_ids=())
    decision = propose(PlainLLMPolicy(provider(server)), state, context)
    assert decision.empty_queue_noop and decision.output.output_status == "ok"
    assert server.requests == []


def test_empty_queue_noop_still_uses_the_decision(server):
    policy = PlainLLMPolicy(provider(server))
    state, context = state_and_context(waiting_job_ids=())
    propose(policy, state, context)
    with pytest.raises(CallBlocked, match="one request"):
        propose(policy, state, context)
    assert server.requests == []


def test_waiting_jobs_still_get_exactly_one_request(server):
    decision = propose(PlainLLMPolicy(provider(server)))
    assert not decision.empty_queue_noop
    assert len(server.requests) == 1


def test_empty_queue_still_refuses_mismatched_context_without_dispatch(server):
    state, context = state_and_context(waiting_job_ids=())
    other = context.model_copy(update={"content_hash": "0" * 64})
    shared = provider(server)
    with pytest.raises(ValueError):
        propose(PlainLLMPolicy(shared), state, other)
    assert server.requests == [] and shared.attempts == ()


def test_empty_queue_still_refuses_completion_slot_without_dispatch(server):
    state, context = state_and_context(waiting_job_ids=())
    shared = provider(server)
    late = state.model_copy(update={"current_slot": s.PROPOSED_DECISION_SLOTS})
    with pytest.raises(CallBlocked, match="completion"):
        propose(PlainLLMPolicy(shared), late, context)
    assert server.requests == [] and shared.attempts == ()


def test_empty_waiting_queue_preserves_running_work_without_dispatch(server):
    snapshot = f.snapshot()
    running = s.RunningJobView(job=f.jobs()["J1"], start_slot=0)
    state = s.VisibleState.from_snapshot(
        snapshot,
        episode_id=f.EPISODE_ID,
        current_slot=1,
        state_version=1,
        running_jobs=(running,),
    )
    context = s.Context.build(state, snapshot, "flat")
    shared = provider(server)
    decision = propose(PlainLLMPolicy(shared), state, context)
    assert decision.empty_queue_noop and decision.output.plan.starts == ()
    assert state.running_jobs == context.content.running_jobs == (running,)
    assert state.current_slot == 1  # only the future runtime owns progression
    assert server.requests == [] and shared.attempts == ()


def test_prompt_hash_ignores_line_endings(tmp_path, monkeypatch):
    original = plain.prompt_template_sha256()
    for name in plain.PROMPT_FILES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (plain.PROMPT_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n")
        target.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    monkeypatch.setattr(plain, "PROMPT_DIR", tmp_path)
    assert plain.prompt_template_sha256() == original
