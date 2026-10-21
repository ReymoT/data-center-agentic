"""Observe socket pairs in existing synthetic tests; never contact a model endpoint.

Keep payloads, assertions and deadlines unchanged. The observer changes timing, so
a passing run is not a timeout fix. Output contains lengths/hashes, not body text.
Use a new output path for each run; previous evidence is never overwritten.
"""

import argparse
import hashlib
import json
import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402


def diagnose(*, full_suite: bool, output: Path) -> int:
    # Reserve the output before tests/monkeypatches; preserve earlier observations.
    with output.open("x", encoding="utf-8") as handle:
        events, streams = [], {}
        lock, started = threading.Lock(), time.monotonic()
        current_test = None
        send_original = socket.socket.sendall
        recv_original = socket.socket.recv_into
        shutdown_original = socket.socket.shutdown

        def endpoints(sock):
            try:
                return (sock.getsockname(), sock.getpeername())
            except OSError:
                return None

        def record(kind, pair=None, **fields):
            with lock:
                events.append(
                    dict(
                        event=kind,
                        pair=pair,
                        seconds=time.monotonic() - started,
                        test=current_test,
                        **fields,
                    )
                )

        def send(sock, data, *args, **kwargs):
            pair, raw = endpoints(sock), bytes(data)
            record("send_start", pair, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            try:
                result = send_original(sock, data, *args, **kwargs)
                record("send_done", pair, bytes=len(raw))
                return result
            except Exception as exc:
                record("send_error", pair, error=str(exc))
                raise

        def recv(sock, buffer, *args, **kwargs):
            pair = endpoints(sock)
            try:
                size = recv_original(sock, buffer, *args, **kwargs)
                raw = bytes(memoryview(buffer)[:size])
                with lock:
                    streams.setdefault(pair, bytearray()).extend(raw)
                record("recv", pair, bytes=size)
                return size
            except Exception as exc:
                record("recv_error", pair, error=str(exc))
                raise

        def shutdown(sock, how):
            pair = endpoints(sock)
            record("shutdown_start", pair, how=how)
            try:
                result = shutdown_original(sock, how)
                record("shutdown_done", pair, how=how)
                return result
            except Exception as exc:
                record("shutdown_error", pair, how=how, error=str(exc))
                raise

        class TestIdentity:
            def pytest_runtest_setup(self, item):
                nonlocal current_test
                current_test = item.nodeid
                record("test")

        target = ROOT / "tests" if full_suite else ROOT / "tests/llm/test_ollama_provider.py"
        exit_code = None
        socket.socket.sendall = send
        socket.socket.recv_into = recv
        socket.socket.shutdown = shutdown
        try:
            exit_code = int(
                pytest.main([str(target), "-q", "--tb=short"], plugins=[TestIdentity()])
            )
        finally:
            socket.socket.sendall = send_original
            socket.socket.recv_into = recv_original
            socket.socket.shutdown = shutdown_original
            with lock:
                captured_events = list(events)
                captured_streams = {pair: bytes(raw) for pair, raw in streams.items()}
            summaries = []
            for pair, raw in captured_streams.items():
                # Each test connection contains one request/response. Do not emit
                # headers or body text. Pair + stream hash correlates send/receive.
                _, separator, body = bytes(raw).partition(b"\r\n\r\n")
                summaries.append(
                    dict(
                        pair=pair,
                        bytes=len(raw),
                        header_boundary_found=bool(separator),
                        body_bytes=len(body),
                        body_sha256=hashlib.sha256(body).hexdigest(),
                    )
                )
            handle.write(
                json.dumps(
                    dict(
                        evidence_kind="synthetic_http_wire_observation_not_inference",
                        model_calls=0,
                        full_suite=full_suite,
                        pytest_exit_code=exit_code,
                        observer_changes_timing=True,
                        events=captured_events,
                        streams=summaries,
                    ),
                    indent=2,
                )
                + "\n"
            )
    return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-suite", action="store_true")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(diagnose(full_suite=args.full_suite, output=args.out))


if __name__ == "__main__":
    main()
