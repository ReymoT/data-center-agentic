"""Trace existing synthetic loopback tests; never contact Ollama/model endpoints.

Keep the original test assertions, payloads and deadlines. The optional full-suite
mode investigates ordering effects. JSON contains byte counts, not response text.
"""

import argparse
import http.client
import json
import socketserver
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from dc_sustainability.llm.provider import OllamaProvider  # noqa: E402


def diagnose(*, full_suite: bool, output: Path) -> int:
    # Refuse an existing output before running tests; retain all prior evidence.
    with output.open("x", encoding="utf-8") as handle:
        events = []
        lock = threading.Lock()
        originals = (
            HTTP_READ := http.client.HTTPResponse.read1,
            HTTP_CALL := OllamaProvider._http,
            SERVER_WRITE := socketserver._SocketWriter.write,
        )

        def record(**event):
            with lock:
                events.append(event)

        def read(response, size=-1):
            before = response.length
            try:
                data = HTTP_READ(response, size)
                record(event="read", before=before, received=len(data), remaining=response.length)
                return data
            except Exception as exc:
                record(event="read_error", before=before, error=str(exc))
                raise

        def request(client, method, path, body, deadline):
            record(event="start", method=method, path=path)
            started = time.monotonic()
            try:
                result = HTTP_CALL(client, method, path, body, deadline)
                record(event="done", bytes=len(result[0]), seconds=time.monotonic() - started)
                return result
            except Exception as exc:
                record(
                    event="error",
                    error=str(exc),
                    bytes=len(getattr(exc, "raw", b"")),
                    status=getattr(exc, "status", None),
                    seconds=time.monotonic() - started,
                )
                raise

        def write(writer, data):
            try:
                result = SERVER_WRITE(writer, data)
                if len(data) > 20000:
                    record(event="server_write", bytes=len(data), returned=result)
                return result
            except Exception as exc:
                record(event="server_write_error", bytes=len(data), error=str(exc))
                raise

        class TestIdentity:
            def pytest_runtest_setup(self, item):
                record(event="test", nodeid=item.nodeid)

        args = [str(ROOT / "tests"), "-q", "--tb=short"]
        if not full_suite:
            args += ["-k", "deep_json_failure_is_recorded"]
        http.client.HTTPResponse.read1 = read
        OllamaProvider._http = request
        socketserver._SocketWriter.write = write
        try:
            result = int(pytest.main(args, plugins=[TestIdentity()]))
        finally:
            (
                http.client.HTTPResponse.read1,
                OllamaProvider._http,
                socketserver._SocketWriter.write,
            ) = originals
            handle.write(
                json.dumps(
                    {
                        "evidence_kind": "synthetic_http_diagnostic_not_inference",
                        "model_calls": 0,
                        "events": events,
                    },
                    indent=2,
                )
                + "\n"
            )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-suite", action="store_true")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(diagnose(full_suite=args.full_suite, output=args.out))


if __name__ == "__main__":
    main()
