"""Local synthetic control: same deep-JSON body, independent clients; never Ollama."""

import argparse
import hashlib
import http.client
import json
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dc_sustainability.llm.provider import CallBlocked, OllamaProvider  # noqa: E402
from tests.llm.test_ollama_provider import deployment, generate  # noqa: E402

BODY = b'{"x":' * 4000 + b"0" + b"}" * 4000


def observe(client_kind, close_kind):
    events = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Length", str(len(BODY)))
            self.end_headers()
            written = self.wfile.write(BODY)
            events.append({"event": "write_returned", "bytes": written})
            if close_kind == "drain":
                self.connection.shutdown(socket.SHUT_WR)
                self.connection.settimeout(2)
                try:
                    while self.connection.recv(65536):
                        pass
                    events.append({"event": "peer_eof"})
                except OSError as exc:
                    events.append({"event": "drain_error", "error": str(exc)})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    request = []

    def capture(payload):
        request.append(payload)
        raise CallBlocked("capture synthetic request only; zero provider dispatch")

    provider = OllamaProvider(deployment(server), count_prompt_tokens=capture)
    try:
        generate(provider)
    except CallBlocked:
        pass
    assert len(request) == 1 and not provider.attempts
    payload = json.dumps(request[0], allow_nan=False, separators=(",", ":")).encode()
    raw, wire, error, response, conn = bytearray(), bytearray(), None, None, None
    start = time.monotonic()
    deadline = start + 10

    def remaining():
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("synthetic client deadline")
        return left

    try:
        if client_kind == "raw_socket":
            with socket.create_connection(
                ("127.0.0.1", server.server_port), timeout=remaining()
            ) as sock:
                sock.sendall(
                    (
                        f"POST /api/chat HTTP/1.1\r\nHost: 127.0.0.1:{server.server_port}\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n"
                    ).encode()
                    + payload
                )
                while True:
                    sock.settimeout(remaining())
                    block = sock.recv(65536)
                    if not block:
                        break
                    wire.extend(block)
                    _, sep, body = wire.partition(b"\r\n\r\n")
                    if sep and len(body) >= len(BODY):
                        break
                raw.extend(wire.partition(b"\r\n\r\n")[2])
        else:
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=remaining())
            conn.request(
                "POST", "/api/chat", body=payload, headers={"Content-Type": "application/json"}
            )
            response = conn.getresponse()
            while not response.isclosed():
                sock = conn.sock if conn.sock is not None else response.fp.raw._sock
                sock.settimeout(remaining())
                block = response.read1(65536)
                if not block:
                    break
                raw.extend(block)
    except (OSError, http.client.HTTPException) as exc:
        error = str(exc)
        if client_kind == "raw_socket":
            raw = bytearray(wire.partition(b"\r\n\r\n")[2])
    finally:
        if response is not None:
            response.close()
        if conn is not None:
            conn.close()
        server.shutdown()
        server.server_close()
        thread.join(2)
    return {
        "client": client_kind,
        "server_close": close_kind,
        "response_bytes": len(raw),
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "body_matches": bytes(raw) == BODY,
        "error": error,
        "seconds": time.monotonic() - start,
        "server_events": events,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with args.out.open("x", encoding="utf-8") as handle:
        rows = []
        for close in ("immediate", "drain"):
            for client in ("raw_socket", "http_client_read1"):
                row = observe(client, close)
                rows.append(row)
                print(json.dumps(row), flush=True)
        json.dump(
            {
                "evidence_kind": "independent_synthetic_http_peer_control_not_inference",
                "body_bytes": len(BODY),
                "body_sha256": hashlib.sha256(BODY).hexdigest(),
                "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "model_calls": 0,
                "one_observation_per_condition": True,
                "acceptance_or_root_cause_proof": False,
                "observations": rows,
            },
            handle,
            indent=2,
        )
        handle.write("\n")


if __name__ == "__main__":
    main()
