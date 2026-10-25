"""Real loopback HTTP against synthetic test responses; no Ollama/model inference.

The test server is deliberately not a model and is never shipped as a production
fallback. Tests exercise actual serialization, sockets, deadlines and bookkeeping.
"""

import http.client
import json
import threading
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.llm.plain import PlainLLMPolicy
from dc_sustainability.llm.provider import CallBlocked, Deployment, OllamaProvider
from tests.contracts import fixtures as f
from tests.llm.http_fixture import DrainingHTTPServer

DIGEST = "a" * 64  # synthetic artifact identity, not an installed model checksum


def envelope():
    return {
        "model": "qwen3:8b",
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": f.plan().to_json()},
        "prompt_eval_count": 20,
        "eval_count": 12,
        "total_duration": 1000000,
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
            if self.server.request_id:
                self.send_header("X-Request-ID", self.server.request_id)
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def do_GET(self):
            if self.path == "/api/version":
                self.respond({"version": self.server.version})
            elif self.path == "/api/tags":
                self.respond({"models": self.server.models})
            else:
                self.respond(b"unexpected", 404)

        def do_POST(self):
            assert self.path == "/api/chat"
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            self.server.requests.append(json.loads(raw))
            self.server.received.set()
            if self.server.trickle_headers:
                try:
                    for char in b"HTTP/1.0 200 OK\r\nContent-Length: 999\r\n\r\n":
                        self.wfile.write(bytes([char]))
                        self.wfile.flush()
                        time.sleep(0.05)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
                return
            if self.server.delay:
                time.sleep(self.server.delay)
            self.respond(self.server.body, self.server.status)

    httpd = DrainingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    httpd.requests, httpd.delay, httpd.status = [], 0, 200
    httpd.version, httpd.request_id, httpd.body = "synthetic-1", None, envelope()
    httpd.models = [
        {"name": "qwen3:8b", "digest": DIGEST, "details": {"quantization_level": "Q4_K_M"}}
    ]
    httpd.received = threading.Event()
    httpd.trickle_headers = False
    thread = threading.Thread(
        target=httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=2)


def deployment(server, **changes):
    config = Deployment(
        base_url=f"http://127.0.0.1:{server.server_port}",
        runtime_version="synthetic-1",
        model_digest=DIGEST,
        max_run_attempts=8,
        max_response_bytes=100000,
        max_prompt_tokens=1000,
        context_policy_ref="synthetic-test-counter-only",
    )
    return replace(config, **changes)


def provider(server, **changes):
    # A synthetic counter belongs only to this test. No production tokenizer is implied.
    return OllamaProvider(deployment(server, **changes), count_prompt_tokens=lambda request: 20)


def generate(client, **changes):
    args = dict(
        system="agent",
        state=f.visible_state(),
        seed=7,
        messages=[{"role": "user", "content": "Synthetic transport test, not inference."}],
        response_model=s.Plan,
        decision_deadline=time.monotonic() + 3,
    )
    args.update(changes)
    return client.generate(**args)


def test_real_http_serialization_f02_parse_and_evidence_preservation(server):
    client = provider(server)
    result = generate(client)
    assert result.error is None and result.output == f.plan()
    assert result.prompt_tokens == 20 and result.completion_tokens == 12
    assert result.total_duration_ns == 1000000 and result.http_status == 200
    assert result.provider_request_id is None and result.client_trace_id
    assert json.loads(result.raw_response) == envelope()
    assert result.latency_ms > 0 and not result.uncertain_outcome
    assert result.model_digest == DIGEST and client.attempts == (result,)
    payload = server.requests[0]
    assert payload["format"] == s.Plan.model_json_schema()
    assert payload["stream"] is False and payload["think"] is False
    assert payload["keep_alive"] == "30m"
    assert payload["options"] == {
        "temperature": 0.2,
        "top_p": 1,
        "seed": 7,
        "num_ctx": 16384,
        "num_predict": 1536,
    }


@pytest.mark.parametrize("protocol", ["HTTP/1.0", "HTTP/1.1"])
def test_http_response_stream_is_closed_on_interrupted_body_read(server, monkeypatch, protocol):
    # HTTP/1.0 detaches the response from HTTPConnection before returning it. Keep
    # it alive here so GC cannot conceal a stream/socket leak after an early error.
    observed = []
    original = http.client.HTTPConnection.getresponse
    monkeypatch.setattr(server.RequestHandlerClass, "protocol_version", protocol)

    def capture(connection):
        response = original(connection)
        observed.append(response)
        return response

    monkeypatch.setattr(http.client.HTTPConnection, "getresponse", capture)
    result = generate(provider(server, max_response_bytes=250))
    assert "response exceeds configured byte limit" in result.error
    assert len(result.raw_response) == 251 and result.http_status == 200
    assert len(observed) == 3  # real version, tags and synthetic chat responses
    assert all(response.isclosed() for response in observed)


def test_both_systems_share_identical_artifact_and_generation_settings(server):
    client = provider(server)
    generate(client, system="agent")
    generate(client, system="plain_llm")
    assert server.requests[0] == server.requests[1]
    assert len(client.attempts) == 2


def test_existing_f02_policy_envelope_and_llm_explanation_parse(server):
    response = s.PolicyOutput(
        system="plain_llm",
        output_status="ok",
        plan=f.plan(),
        explanation=s.Explanation(
            source="llm", summary="Synthetic test explanation, no physical claim."
        ),
    )
    server.body["message"]["content"] = response.to_json()
    result = generate(provider(server), system="plain_llm", response_model=s.PolicyOutput)
    assert result.output == response and result.error is None


def test_output_cannot_impersonate_another_system(server):
    response = s.PolicyOutput(system="plain_llm", output_status="ok", plan=f.plan())
    server.body["message"]["content"] = response.to_json()
    result = generate(provider(server), system="agent", response_model=s.PolicyOutput)
    assert result.output is None and "different system" in result.error


def test_model_explanation_cannot_claim_template_origin(server):
    response = s.Explanation(source="template", summary="Synthetic wrong-source explanation.")
    server.body["message"]["content"] = response.to_json()
    result = generate(provider(server), response_model=s.Explanation)
    assert result.output is None and "template" in result.error


@pytest.mark.parametrize("system,cap", [("agent", 3), ("plain_llm", 1)])
def test_invalid_responses_consume_attempt_cap_without_hidden_retry(server, system, cap):
    server.body = b"not JSON"
    client = provider(server)
    for _ in range(cap):
        assert generate(client, system=system).error
    with pytest.raises(CallBlocked, match="per-decision"):
        generate(client, system=system, seed=999)
    assert len(client.attempts) == len(server.requests) == cap


def test_run_cap_applies_across_systems(server):
    client = provider(server, max_run_attempts=1)
    generate(client)
    with pytest.raises(CallBlocked, match="run attempt"):
        generate(client, system="plain_llm")
    assert len(server.requests) == 1


@pytest.mark.parametrize("fault", ["version", "digest", "quantization", "missing"])
def test_pin_verification_blocks_before_any_model_attempt(server, fault):
    if fault == "version":
        server.version = "changed-runtime"
    elif fault == "digest":
        server.models[0]["digest"] = "b" * 64
    elif fault == "quantization":
        server.models[0]["details"]["quantization_level"] = "Q8_0"
    else:
        server.models = []
    client = provider(server)
    with pytest.raises(CallBlocked, match="pre-dispatch"):
        generate(client)
    assert client.attempts == () and server.requests == []


@pytest.mark.parametrize(
    "fault",
    [
        "schema",
        "binding",
        "approved",
        "incomplete",
        "model",
        "length",
        "tokens",
        "usage",
        "tools",
        "thinking",
        "role",
    ],
)
def test_invalid_or_unfinished_output_retained_and_never_returned_as_success(server, fault):
    if fault == "schema":
        server.body["message"]["content"] = '{"fake":true}'
    elif fault in {"binding", "approved"}:
        p = f.plan().model_copy(
            update={"slot": 1} if fault == "binding" else {"status": "approved"}
        )
        server.body["message"]["content"] = p.to_json()
    elif fault == "incomplete":
        server.body["done"] = False
    elif fault == "model":
        server.body["model"] = "other-model"
    elif fault == "length":
        server.body["done_reason"] = "length"
    elif fault == "tokens":
        server.body["prompt_eval_count"] = 16384
    elif fault == "usage":
        server.body["eval_count"] = True
    elif fault == "tools":
        server.body["message"]["tool_calls"] = [{"function": "execute"}]
    elif fault == "thinking":
        server.body["message"]["thinking"] = "unexpected"
    else:
        server.body["message"]["role"] = "user"
    client = provider(server)
    result = generate(client)
    assert result.error and result.output is None and result.raw_response
    assert len(server.requests) == len(client.attempts) == 1


def test_http_error_retains_body_request_id_and_consumes_plain_attempt(server):
    server.body, server.status, server.request_id = b"unavailable", 503, "real-test-header"
    client = provider(server)
    result = generate(client, system="plain_llm")
    assert result.error and result.http_status == 503 and result.raw_response == b"unavailable"
    assert result.provider_request_id == "real-test-header"
    assert result.prompt_tokens is None and result.completion_tokens is None
    with pytest.raises(CallBlocked):
        generate(client, system="plain_llm")
    assert len(server.requests) == 1


def test_unknown_usage_is_not_fabricated(server):
    for field in ("prompt_eval_count", "eval_count", "total_duration"):
        server.body.pop(field)
    result = generate(provider(server))
    assert result.output and result.error is None
    assert result.prompt_tokens is result.completion_tokens is result.total_duration_ns is None


def test_real_socket_timeout_is_uncertain_and_cannot_retry_plain(server):
    server.delay = 0.8
    client = provider(server)
    started = time.monotonic()
    result = generate(client, system="plain_llm", decision_deadline=started + 0.4)
    assert result.error and result.uncertain_outcome and result.output is None
    assert time.monotonic() - started < 0.7
    with pytest.raises(CallBlocked, match="per-decision"):
        generate(client, system="plain_llm")
    assert len(client.attempts) == len(server.requests) == 1


def test_total_deadline_interrupts_slow_trickling_headers(server):
    server.trickle_headers = True
    started = time.monotonic()
    result = generate(provider(server), decision_deadline=started + 0.4)
    assert result.error and result.uncertain_outcome
    assert time.monotonic() - started < 0.8
    assert len(server.requests) == 1


def test_expired_deadline_never_dispatches(server):
    client = provider(server)
    with pytest.raises(CallBlocked):
        generate(client, decision_deadline=time.monotonic() - 1)
    assert not client.attempts and not server.requests


def test_completion_slot_calls_are_blocked_before_network(server):
    view = s.VisibleState.from_snapshot(
        f.snapshot(), episode_id=f.EPISODE_ID, current_slot=24, state_version=24
    )
    client = provider(server)
    with pytest.raises(CallBlocked, match="completion"):
        generate(client, state=view)
    assert not client.attempts and not server.requests


def test_response_byte_limit_preserves_received_failure_evidence(server):
    client = provider(server, max_response_bytes=250)
    result = generate(client)
    assert result.error and result.output is None
    assert len(result.raw_response) == 251 and result.uncertain_outcome


@pytest.mark.parametrize("count", [1001, True, 0, -1])
def test_invalid_or_excessive_context_count_blocks_before_dispatch(server, count):
    client = OllamaProvider(deployment(server), count_prompt_tokens=lambda request: count)
    with pytest.raises(CallBlocked, match="context"):
        generate(client)
    assert not client.attempts and not server.requests


@pytest.mark.parametrize("error", [ValueError, RuntimeError, RecursionError])
def test_counter_failure_is_an_explicit_predispatch_block(server, monkeypatch, error):
    def broken_counter(request):
        raise error("synthetic counter failure")

    client = OllamaProvider(deployment(server), count_prompt_tokens=broken_counter)

    def no_network(*args):
        pytest.fail("a failed counter must block before any HTTP operation")

    monkeypatch.setattr(client, "_http", no_network)
    with pytest.raises(CallBlocked, match="prompt token counting failed") as caught:
        generate(client)
    assert isinstance(caught.value.__cause__, error)
    assert not client.attempts and not server.requests


@pytest.mark.parametrize("path", ["/api/version", "/api/tags"])
def test_nested_pin_response_is_an_explicit_predispatch_block(server, monkeypatch, path):
    # Separate metadata test; original chat deep-JSON payloads/deadlines stay unchanged.
    raw = b"[" * 4000 + b"0" + b"]" * 4000
    original = server.RequestHandlerClass.do_GET

    def respond(handler):
        if handler.path == path:
            handler.respond(raw)
        else:
            original(handler)

    monkeypatch.setattr(server.RequestHandlerClass, "do_GET", respond)
    client = provider(server)
    with pytest.raises(CallBlocked, match="pre-dispatch verification failed") as caught:
        generate(client)
    # CPython/platform stack limits differ. If decoding accepts this nesting,
    # its outer list is still invalid pin metadata and .get raises AttributeError.
    # Either actual cause must be retained under the same pre-dispatch block.
    assert isinstance(caught.value.__cause__, (RecursionError, AttributeError))
    assert not client.attempts and not server.requests


def test_plain_consumer_keeps_counter_failure_and_does_not_retry(server, monkeypatch):
    def broken_counter(request):
        raise RuntimeError("synthetic unavailable tokenizer")

    client = OllamaProvider(deployment(server), count_prompt_tokens=broken_counter)
    monkeypatch.setattr(client, "_http", lambda *args: pytest.fail("must not use HTTP"))
    policy = PlainLLMPolicy(client)
    state = f.visible_state()
    context = s.Context.build(state, f.snapshot(), "flat")
    result = policy.propose(state, context, seed=7, decision_deadline=time.monotonic() + 3)
    assert result.output.output_status == "error" and result.attempt is None
    assert "prompt token counting failed" in result.blocked_reason
    assert not client.attempts and not server.requests
    with pytest.raises(CallBlocked, match="already used its one request"):
        policy.propose(state, context, seed=7, decision_deadline=time.monotonic() + 3)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://192.168.1.5",
        "http://user:secret@localhost",
        "http://localhost/path",
    ],
)
def test_nonlocal_or_credentialed_endpoint_is_refused(server, url):
    with pytest.raises(ValueError, match="loopback"):
        deployment(server, base_url=url)


def test_concurrent_attempt_is_refused_without_a_second_dispatch(server):
    server.delay = 0.2
    client = provider(server)
    results = []
    thread = threading.Thread(target=lambda: results.append(generate(client)))
    thread.start()
    assert server.received.wait(timeout=2)
    with pytest.raises(CallBlocked, match="one request"):
        generate(client, system="plain_llm")
    thread.join(timeout=2)
    assert len(results) == len(server.requests) == len(client.attempts) == 1


@pytest.mark.parametrize("system", ["agent", "plain_llm"])
@pytest.mark.parametrize("shape", ["array", "object"])
def test_deep_json_failure_is_recorded_and_exhausts_run_budget(server, system, shape):
    # Real HTTP with deliberately invalid-for-this-boundary synthetic content.
    # This exceeds CPython's decoder nesting limit within the allowed byte limit.
    if shape == "array":
        raw = b"[" * 4000 + b"0" + b"]" * 4000
    else:
        raw = b'{"x":' * 4000 + b"0" + b"}" * 4000
    server.body = raw
    client = provider(server, max_run_attempts=1)
    attempt = generate(client, system=system, decision_deadline=time.monotonic() + 10)
    assert attempt.output is None and "invalid response:" in attempt.error
    assert attempt.raw_response == raw and attempt.http_status == 200
    assert attempt.prompt_tokens is attempt.completion_tokens is None
    assert client.attempts == (attempt,) and len(server.requests) == 1
    # A new slot must not bypass a run cap after the decoder failed.
    state = s.VisibleState.from_snapshot(
        f.snapshot(), episode_id=f.EPISODE_ID, current_slot=1, state_version=1
    )
    server.body = envelope()
    with pytest.raises(CallBlocked, match="run attempt cap"):
        generate(client, system=system, state=state)
    assert client.attempts == (attempt,) and len(server.requests) == 1


@pytest.mark.parametrize("system,cap", [("agent", 3), ("plain_llm", 1)])
def test_deep_json_failures_keep_the_existing_per_decision_caps(server, system, cap):
    server.body = b"[" * 4000 + b"0" + b"]" * 4000
    client = provider(server)
    for _ in range(cap):
        attempt = generate(client, system=system, decision_deadline=time.monotonic() + 10)
        assert attempt.error and attempt.output is None
        assert attempt.raw_response == server.body
    with pytest.raises(CallBlocked, match="per-decision attempt cap"):
        generate(client, system=system, seed=999)
    assert len(client.attempts) == len(server.requests) == cap
