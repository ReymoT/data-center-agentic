"""A01 local Ollama REST transport and attempt accounting, with no hidden retries.

Uses the standard library, not an unselected SDK. This low-level consumer uses F02
records unchanged. Prompts/output projection, a validated model-specific context
counter, deployment pins and the complete experiment protocol remain caller inputs.
"""

import http.client
import json
import math
import re
import socket
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from dc_sustainability import schemas as s


class CallBlocked(ValueError):
    """A pre-dispatch failure; no model attempt was made."""


@dataclass(frozen=True)
class Deployment:
    """Explicit local deployment inputs; observed versions are not implicit pins."""

    base_url: str
    runtime_version: str
    model_digest: str
    max_run_attempts: int
    max_response_bytes: int
    max_prompt_tokens: int
    context_policy_ref: str

    def __post_init__(self):
        url = urlsplit(self.base_url)
        if (
            url.scheme != "http"
            or url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or url.username
            or url.password
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
        ):
            raise ValueError(
                "Ollama must use an explicit loopback HTTP endpoint without credentials"
            )
        if not re.fullmatch(r"[0-9a-f]{64}", self.model_digest):
            raise ValueError("model_digest must be the full installed artifact SHA256")
        if not self.runtime_version.strip() or not self.context_policy_ref.strip():
            raise ValueError("runtime and validated context policy must be explicitly recorded")
        for value in (self.max_run_attempts, self.max_response_bytes, self.max_prompt_tokens):
            if type(value) is not int or value <= 0:
                raise ValueError("limits must be positive strict integers")
        if self.max_prompt_tokens > 16384 - 1536:
            raise ValueError("prompt limit must leave room for the accepted generation target")


@dataclass(frozen=True)
class Attempt:
    """Internal transport audit, not a replacement shared F02 trace schema.

    Missing usage/timing remains None. A client trace ID is not a provider request ID.
    The caller must persist these records and map real evidence into DecisionRecord.
    """

    client_trace_id: str
    system: str
    episode_id: str
    slot: int
    seed: int
    started_at_utc: str
    latency_ms: float
    request_json: str
    runtime_version: str
    model_digest: str
    raw_response: bytes
    http_status: int | None
    provider_request_id: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_duration_ns: int | None
    error: str | None
    uncertain_outcome: bool
    output: s.Record | None


class _TransportError(Exception):
    def __init__(self, message, *, raw=b"", status=None, request_id=None):
        super().__init__(message)
        self.raw, self.status, self.request_id = raw, status, request_id


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("request/decision deadline exhausted")
    return remaining


class OllamaProvider:
    """One serialized adapter/ledger per run, shared by agent and plain paths.

    Reserve attempts before dispatch, including failed/uncertain requests. No automatic
    retries, repairs, alternate models, installs, tools, or execution. Reuse this run
    instance; constructing another ledger is a new run, not checkpoint/resume support.
    """

    def __init__(self, deployment: Deployment, *, count_prompt_tokens: Callable[[dict], int]):
        self.deployment = deployment
        self._count_prompt_tokens = count_prompt_tokens
        self._lock = threading.Lock()
        self._counts: dict[tuple[str, str, int], int] = {}
        self._attempts: list[Attempt] = []

    @property
    def attempts(self) -> tuple[Attempt, ...]:
        with self._lock:
            return tuple(self._attempts)

    def _http(self, method: str, path: str, body: bytes | None, deadline: float):
        url = urlsplit(self.deployment.base_url)
        conn = http.client.HTTPConnection(
            url.hostname, url.port or 80, timeout=_remaining(deadline)
        )
        raw = bytearray()
        status = request_id = None
        cutoff = None
        response = None
        try:
            conn.connect()
            request_socket = conn.sock

            def interrupt_at_deadline():
                # http.client's header reads may receive a slow trickle indefinitely.
                # Interrupt this owned socket at the total deadline as well as setting
                # operation timeouts; no retry or second request is made.
                try:
                    request_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

            cutoff = threading.Timer(_remaining(deadline), interrupt_at_deadline)
            cutoff.daemon = True
            cutoff.start()
            conn.sock.settimeout(_remaining(deadline))
            conn.request(method, path, body=body, headers={"Content-Type": "application/json"})
            conn.sock.settimeout(_remaining(deadline))
            response = conn.getresponse()
            status = response.status
            request_id = response.getheader("X-Request-ID")
            while True:
                if response.isclosed():
                    break
                # A slow trickle cannot renew the total deadline on each read.
                response_socket = conn.sock
                if response_socket is None:
                    response_socket = response.fp.raw._sock
                response_socket.settimeout(_remaining(deadline))
                chunk = response.read1(
                    min(65536, self.deployment.max_response_bytes + 1 - len(raw))
                )
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > self.deployment.max_response_bytes:
                    raise ValueError("response exceeds configured byte limit")
            if response.length is not None and response.length > 0:
                raise http.client.HTTPException("incomplete response body")
            _remaining(deadline)
            if status != 200:
                raise ValueError(f"HTTP {status}; response retained")
            return bytes(raw), status, request_id
        except (OSError, TimeoutError, ValueError, http.client.HTTPException) as exc:
            raise _TransportError(
                str(exc), raw=bytes(raw), status=status, request_id=request_id
            ) from exc
        finally:
            if cutoff is not None:
                cutoff.cancel()
            # A will-close response (including HTTP/1.0) is detached by
            # HTTPConnection.getresponse. Own its stream explicitly on early
            # size/deadline/read errors rather than relying on garbage collection.
            try:
                if response is not None:
                    response.close()
            finally:
                conn.close()

    def _verify_pins(self, deadline: float):
        version = json.loads(self._http("GET", "/api/version", None, deadline)[0])
        if version.get("version") != self.deployment.runtime_version:
            raise CallBlocked("Ollama runtime differs from the explicit deployment pin")
        models = json.loads(self._http("GET", "/api/tags", None, deadline)[0]).get("models", [])
        matches = [m for m in models if m.get("name") == "qwen3:8b"]
        if len(matches) != 1:
            raise CallBlocked("accepted qwen3:8b artifact is not uniquely installed")
        model = matches[0]
        if model.get("digest") != self.deployment.model_digest:
            raise CallBlocked("installed model digest differs from the explicit deployment pin")
        if model.get("details", {}).get("quantization_level") != "Q4_K_M":
            raise CallBlocked("installed artifact is not the accepted Q4_K_M quantization")

    def generate(
        self,
        *,
        system: Literal["agent", "plain_llm"],
        state: s.VisibleState,
        seed: int,
        messages: Sequence[dict[str, str]],
        response_model: type[s.Record],
        decision_deadline: float,
    ) -> Attempt:
        """Make at most one chat attempt; deadlines use time.monotonic().

        Context counting must cover the actual rendered prompt/schema with the pinned
        tokenizer/template. This module supplies no character-count approximation.
        A validated record is a parsed proposal/explanation, never an execution approval.
        """
        state = s.VisibleState.model_validate(
            state.model_dump(mode="python", warnings="none"), strict=True
        )
        if system not in {"agent", "plain_llm"}:
            raise CallBlocked("only the two LLM systems may use this adapter")
        if state.current_slot >= s.PROPOSED_DECISION_SLOTS:
            raise CallBlocked("no model calls in completion slots")
        if type(seed) is not int or seed < 0:
            raise CallBlocked("an explicit strict nonnegative trial seed is required")
        if (
            not isinstance(decision_deadline, (float, int))
            or isinstance(decision_deadline, bool)
            or not math.isfinite(decision_deadline)
        ):
            raise CallBlocked("a finite monotonic decision deadline is required")
        if response_model not in {s.Plan, s.PolicyOutput, s.Explanation}:
            raise CallBlocked("response model must be an existing F02 output record")
        if not messages or any(
            set(m) != {"role", "content"}
            or m["role"] not in {"system", "user", "assistant"}
            or not isinstance(m["content"], str)
            or not m["content"]
            for m in messages
        ):
            raise CallBlocked("messages must be nonempty text with recognized roles")
        payload = {
            "model": "qwen3:8b",
            "messages": [dict(m) for m in messages],
            "format": response_model.model_json_schema(),
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {
                "temperature": 0.2,
                "top_p": 1,
                "seed": seed,
                "num_ctx": 16384,
                "num_predict": 1536,
            },
        }
        count = self._count_prompt_tokens(json.loads(json.dumps(payload)))
        if type(count) is not int or count <= 0 or count > self.deployment.max_prompt_tokens:
            raise CallBlocked("prompt exceeds validated context budget or token count is invalid")
        request_json = json.dumps(payload, allow_nan=False, separators=(",", ":"))
        deadline = min(float(decision_deadline), time.monotonic() + 120)
        if not self._lock.acquire(blocking=False):
            raise CallBlocked("one request at a time; concurrent dispatch is blocked")
        try:
            key = (system, state.episode_id, state.current_slot)
            if self._counts.get(key, 0) >= (3 if system == "agent" else 1):
                raise CallBlocked("per-decision attempt cap exhausted")
            if len(self._attempts) >= self.deployment.max_run_attempts:
                raise CallBlocked("run attempt cap exhausted")
            try:
                self._verify_pins(deadline)
                _remaining(deadline)
            except (_TransportError, TimeoutError, ValueError, TypeError, AttributeError) as exc:
                raise CallBlocked(f"pre-dispatch verification failed: {exc}") from exc
            self._counts[key] = self._counts.get(key, 0) + 1  # reserve before sending
            started = time.perf_counter()
            utc = datetime.now(timezone.utc).isoformat()
            raw, status, request_id, output, error = b"", None, None, None, None
            uncertain = False
            usage = {"prompt_eval_count": None, "eval_count": None, "total_duration": None}
            try:
                raw, status, request_id = self._http(
                    "POST", "/api/chat", request_json.encode(), deadline
                )
                envelope = json.loads(raw)
                for name in usage:
                    value = envelope.get(name)
                    if value is not None and (type(value) is not int or value < 0):
                        raise ValueError(f"invalid provider usage field {name}")
                    usage[name] = value
                if envelope.get("model") != "qwen3:8b" or envelope.get("done") is not True:
                    raise ValueError("model mismatch or incomplete response")
                if envelope.get("done_reason") != "stop":
                    raise ValueError("generation did not finish normally; possible token limit")
                if usage["prompt_eval_count"] is not None and usage["prompt_eval_count"] >= 16384:
                    raise ValueError("provider reports a context-boundary prompt; output rejected")
                message = envelope.get("message", {})
                if (
                    message.get("role") != "assistant"
                    or message.get("tool_calls")
                    or message.get("thinking")
                ):
                    raise ValueError("unexpected role, tool calls or thinking response")
                output = response_model.from_json(message["content"])
                if isinstance(output, s.PolicyOutput) and output.system != system:
                    raise ValueError("policy output names a different system")
                explanation = (
                    output
                    if isinstance(output, s.Explanation)
                    else getattr(output, "explanation", None)
                )
                if explanation is not None and explanation.source != "llm":
                    raise ValueError(
                        "model-generated text cannot claim to be a deterministic template"
                    )
                bound_plan = output if isinstance(output, s.Plan) else getattr(output, "plan", None)
                if bound_plan is not None and bound_plan.status != "proposed":
                    raise ValueError("the model cannot mark a plan approved, rejected or executed")
                if bound_plan is not None and (
                    bound_plan.episode_id,
                    bound_plan.slot,
                    bound_plan.state_version,
                ) != (state.episode_id, state.current_slot, state.state_version):
                    raise ValueError("parsed proposal does not match the requesting visible state")
            except _TransportError as exc:
                raw, status, request_id = exc.raw, exc.status, exc.request_id
                error, uncertain = str(exc), True
                output = None
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
                # Excessive JSON nesting is a failed response after a spent call.
                # Keep its raw evidence and ledger entry just like other parse errors.
                error, output = f"invalid response: {exc}", None
            attempt = Attempt(
                client_trace_id=uuid4().hex,
                system=system,
                episode_id=state.episode_id,
                slot=state.current_slot,
                seed=seed,
                started_at_utc=utc,
                latency_ms=(time.perf_counter() - started) * 1000,
                request_json=request_json,
                runtime_version=self.deployment.runtime_version,
                model_digest=self.deployment.model_digest,
                raw_response=raw,
                http_status=status,
                provider_request_id=request_id,
                prompt_tokens=usage["prompt_eval_count"],
                completion_tokens=usage["eval_count"],
                total_duration_ns=usage["total_duration"],
                error=error,
                uncertain_outcome=uncertain,
                output=output,
            )
            self._attempts.append(attempt)
            return attempt
        finally:
            self._lock.release()
