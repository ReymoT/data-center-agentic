"""Fixed synthetic response/close controls; never Ollama or model inference."""

import argparse
import base64
import hashlib
import json
import platform
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dc_sustainability.llm.provider import CallBlocked, OllamaProvider  # noqa: E402
from tests.llm.test_ollama_provider import deployment, generate, provider  # noqa: E402
from tests.llm.test_ollama_provider import server as server_fixture  # noqa: E402

BODY = b'{"x":' * 4000 + b"0" + b"}" * 4000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_sha(path):
    return sha(path.read_bytes().replace(b"\r\n", b"\n"))


def request_body():
    captured = []

    def capture(payload):
        captured.append(payload)
        raise CallBlocked("synthetic shape capture only; no provider dispatch")

    class Address:
        server_port = 1  # No connection is made: the counter blocks first.

    client = OllamaProvider(deployment(Address()), count_prompt_tokens=capture)
    try:
        generate(client)
    except CallBlocked:
        pass
    assert len(captured) == 1 and not client.attempts
    return json.dumps(captured[0], allow_nan=False, separators=(",", ":")).encode()


def raw_client(port, payload):
    started = time.monotonic()
    wire, chunks, error = bytearray(), [], None
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=10) as connection:
            connection.sendall(
                f"POST /api/chat HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
                f"Content-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n".encode()
                + payload
            )
            while True:
                left = started + 10 - time.monotonic()
                if left <= 0:
                    raise TimeoutError("fixed synthetic client deadline")
                connection.settimeout(left)
                block = connection.recv(65536)
                chunks.append({"bytes": len(block), "seconds": time.monotonic() - started})
                wire.extend(block)
                if not block or len(wire.partition(b"\r\n\r\n")[2]) >= len(BODY):
                    break
    except OSError as exc:
        error = str(exc)
    raw = wire.partition(b"\r\n\r\n")[2]
    return {
        "response_bytes": len(raw),
        "response_sha256": sha(raw),
        "body_matches": bytes(raw) == BODY,
        "header_bytes": len(wire.partition(b"\r\n\r\n")[0]) + 4,
        "wire_sha256": sha(wire),
        "read_chunks": chunks,
        "error": error,
        "seconds": time.monotonic() - started,
    }


def python_observation(mode, client_kind, payload):
    fixture = server_fixture.__wrapped__()
    srv = next(fixture)
    srv.body = BODY
    events, sent = [], bytearray()
    closed = threading.Event()
    post_connection = [None]
    started = time.monotonic()
    original_post = srv.RequestHandlerClass.do_POST
    original_shutdown = srv.shutdown_request

    def event(kind, **fields):
        events.append({"event": kind, "seconds": time.monotonic() - started, **fields})

    class Writer:
        def __init__(self, original):
            self.original = original

        def write(self, data):
            event("write_start", bytes=len(data), sha256=sha(data))
            result = self.original.write(data)
            sent.extend(data)
            event("write_returned", bytes=result)
            return result

        def __getattr__(self, name):
            return getattr(self.original, name)

    def post(handler):
        post_connection[0] = handler.connection
        original_writer = handler.wfile
        handler.wfile = Writer(original_writer)
        try:
            event(
                "post_start",
                tcp_nodelay=handler.connection.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY),
                send_buffer=handler.connection.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF),
            )
            original_post(handler)
            event("post_returned")
            if mode == "half_close_then_wait":
                handler.connection.shutdown(socket.SHUT_WR)
                event("server_write_half_closed")
            if mode != "original_close":
                handler.connection.settimeout(10)
                try:
                    value = handler.connection.recv(1)
                    event("client_close_observed", eof=value == b"", extra_bytes=len(value))
                except OSError as exc:
                    event("client_close_wait_error", error=str(exc))
        finally:
            handler.wfile = original_writer
            event("post_handler_exit")

    def shutdown(connection):
        event("server_shutdown_start")
        try:
            original_shutdown(connection)
        finally:
            event("server_shutdown_returned")
            # Metadata uses other connections; only the POST satisfies this event.
            if connection is post_connection[0]:
                closed.set()

    srv.RequestHandlerClass.do_POST = post
    srv.shutdown_request = shutdown
    row = {}
    try:
        if client_kind == "shared_provider":
            client = provider(srv, max_run_attempts=1)
            attempt = generate(client, decision_deadline=time.monotonic() + 10)
            assert len(client.attempts) == len(srv.requests) == 1
            assert attempt.request_json.encode() == payload
            row = {
                "response_bytes": len(attempt.raw_response),
                "response_sha256": sha(attempt.raw_response),
                "body_matches": attempt.raw_response == BODY,
                "error": attempt.error,
                "uncertain_outcome": attempt.uncertain_outcome,
                "http_status": attempt.http_status,
                "attempts": len(client.attempts),
                "seconds": time.monotonic() - started,
            }
        else:
            row = raw_client(srv.server_port, payload)
        event("client_returned")
        row["server_post_shutdown_observed"] = closed.wait(2)
    finally:
        next(fixture, None)
    wire = bytes(sent)
    assert wire.partition(b"\r\n\r\n")[2] == BODY
    row.update(
        server="original_python_fixture",
        client=client_kind,
        close_mode=mode,
        request_bytes=len(payload),
        request_sha256=sha(payload),
        sent_wire_bytes=len(wire),
        sent_wire_sha256=sha(wire),
        events=events,
    )
    return row, wire


def native_observation(binary, mode, payload, wire):
    child = subprocess.Popen(
        [str(binary.resolve())],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    config = {"wire_base64": base64.b64encode(wire).decode(), "close_mode": mode}
    try:
        child.stdin.write(json.dumps(config).encode() + b"\n")
        child.stdin.flush()
        port = json.loads(child.stdout.readline())["port"]
        row = raw_client(port, payload)
        stdout, stderr = child.communicate(b"stop\n", timeout=4)
        assert child.returncode == 0, stderr.decode(errors="replace")
        server = json.loads(stdout)
        assert server["request_bytes"] == len(payload) and server["request_sha256"] == sha(payload)
        assert server["configured_wire_sha256"] == sha(wire)
        row.update(
            server="native_go_exact_wire",
            client="raw_socket",
            close_mode=mode,
            reference_wire_bytes=len(wire),
            reference_wire_sha256=sha(wire),
            native_events=server,
        )
        return row
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--native-server", type=Path)
    args = parser.parse_args()
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        rows, reference = [], None
        try:
            payload = request_body()
            for mode in ("original_close", "wait_for_client", "half_close_then_wait"):
                for client in ("shared_provider", "raw_socket"):
                    row, wire = python_observation(mode, client, payload)
                    if reference is None:
                        reference = wire
                    rows.append(row)
                    print(json.dumps(row), flush=True)
            if args.native_server:
                for mode in ("original_close", "wait_for_client"):
                    row = native_observation(args.native_server, mode, payload, reference)
                    rows.append(row)
                    print(json.dumps(row), flush=True)
        finally:
            report = {
                "evidence_kind": "fixed_synthetic_write_close_and_exact_wire_controls",
                "python": sys.version,
                "platform": platform.platform(),
                "model_calls": 0,
                "body_bytes": len(BODY),
                "body_sha256": sha(BODY),
                "source_sha256_lf": source_sha(Path(__file__)),
                "provider_source_sha256_lf": source_sha(ROOT / "dc_sustainability/llm/provider.py"),
                "fixture_source_sha256_lf": source_sha(ROOT / "tests/llm/test_ollama_provider.py"),
                "native_source_sha256_lf": source_sha(
                    Path(__file__).with_name("a01_exact_wire_control.go")
                )
                if args.native_server
                else None,
                "native_binary_sha256": sha(args.native_server.read_bytes())
                if args.native_server
                else None,
                "single_observation_per_condition": True,
                "original_deadlines_and_production_transport_unchanged": True,
                "limits": "Instrumentation itself affects timing; Python Date headers may differ "
                "between observations. Native controls replay the exact first captured wire, "
                "but change process/server implementation. Controlled close modes are not "
                "production proposals. Successful samples cannot erase failures or prove reliability.",
                "observations": rows,
            }
            json.dump(report, handle, indent=2)
            handle.write("\n")


if __name__ == "__main__":
    main()
