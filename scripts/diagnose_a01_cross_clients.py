"""Fixed synthetic loopback experiment; never Ollama or model inference."""

import argparse
import hashlib
import http.client
import json
import shutil
import socket
import subprocess
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


def server(events):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            request = self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Length", str(len(BODY)))
            self.end_headers()
            events.append(
                {
                    "event": "request",
                    "bytes": len(request),
                    "sha256": hashlib.sha256(request).hexdigest(),
                }
            )
            events.append(
                {
                    "event": "socket_buffers",
                    "send": self.connection.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF),
                    "receive": self.connection.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF),
                }
            )
            try:
                written = self.wfile.write(BODY)
                events.append({"event": "write_returned", "bytes": written})
            except OSError as exc:
                events.append({"event": "write_error", "error": str(exc)})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.daemon_threads = True
    th = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    th.start()
    return srv, th


def observe(kind, process, native_server=None):
    events, child = [], None
    if process:
        command = (
            [str(native_server.resolve())]
            if native_server
            else [sys.executable, __file__, "--server"]
        )
        child = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        port = json.loads(child.stdout.readline())["port"]
    else:
        srv, thread = server(events)
        port = srv.server_port
    captured = []

    def capture(payload):
        captured.append(payload)
        raise CallBlocked("synthetic shape capture only; no provider dispatch")

    class Address:
        server_port = port

    provider = OllamaProvider(deployment(Address()), count_prompt_tokens=capture)
    try:
        generate(provider)
    except CallBlocked:
        pass
    assert len(captured) == 1 and not provider.attempts
    payload = json.dumps(captured[0], allow_nan=False, separators=(",", ":")).encode()
    start = time.monotonic()
    deadline = start + 10
    raw, wire, chunks, error = bytearray(), bytearray(), [], None
    response = conn = None
    client_info = {}

    def remaining():
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("synthetic client deadline")
        return left

    try:
        if kind == "curl":
            curl = shutil.which("curl.exe")
            assert curl is not None
            result = subprocess.run(
                [
                    curl,
                    "--silent",
                    "--show-error",
                    "--noproxy",
                    "*",
                    "--max-time",
                    "10",
                    "--header",
                    "Content-Type: application/json",
                    "--data-binary",
                    "@-",
                    f"http://127.0.0.1:{port}/api/chat",
                ],
                input=payload,
                capture_output=True,
                timeout=12,
            )
            raw.extend(result.stdout)
            client_info = {"executable": Path(curl).name, "exit_code": result.returncode}
            error = result.stderr.decode(errors="replace").strip() or None
        elif kind == "raw_socket":
            with socket.create_connection(("127.0.0.1", port), timeout=remaining()) as sock:
                sock.sendall(
                    f"POST /api/chat HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n".encode()
                    + payload
                )
                while True:
                    sock.settimeout(remaining())
                    block = sock.recv(65536)
                    chunks.append(len(block))
                    if not block:
                        break
                    wire.extend(block)
                    if len(wire.partition(b"\r\n\r\n")[2]) >= len(BODY):
                        break
                raw.extend(wire.partition(b"\r\n\r\n")[2])
        else:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=remaining())
            conn.request(
                "POST", "/api/chat", body=payload, headers={"Content-Type": "application/json"}
            )
            response = conn.getresponse()
            while not response.isclosed():
                sock = conn.sock if conn.sock is not None else response.fp.raw._sock
                sock.settimeout(remaining())
                block = response.read1(65536)
                chunks.append(len(block))
                if not block:
                    break
                raw.extend(block)
    except (OSError, http.client.HTTPException) as exc:
        error = str(exc)
        if kind == "raw_socket":
            raw = bytearray(wire.partition(b"\r\n\r\n")[2])
    finally:
        if response is not None:
            response.close()
        if conn is not None:
            conn.close()
        if child is not None:
            stdout, stderr = child.communicate(b"stop\n", timeout=4)
            events = json.loads(stdout)["events"]
            assert child.returncode == 0, stderr
        else:
            srv.shutdown()
            srv.server_close()
            thread.join(2)
    return {
        "client": kind,
        "server_process": "native_go"
        if native_server
        else "separate_python"
        if process
        else "same_python",
        "request_bytes": len(payload),
        "request_sha256": hashlib.sha256(payload).hexdigest(),
        "response_bytes": len(raw),
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "body_matches": bytes(raw) == BODY,
        "read_chunks": chunks,
        "error": error,
        "seconds": time.monotonic() - start,
        "client_info": client_info,
        "server_events": events,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--native-server", type=Path)
    args = parser.parse_args()
    if args.server:
        events = []
        srv, thread = server(events)
        print(json.dumps({"port": srv.server_port}), flush=True)
        sys.stdin.readline()
        srv.shutdown()
        srv.server_close()
        thread.join(2)
        print(json.dumps({"events": events}), flush=True)
        return
    assert args.out is not None
    with args.out.open("x", encoding="utf-8") as handle:
        rows = []
        conditions = [(False, None), (True, None)]
        if args.native_server:
            conditions.append((True, args.native_server))
        for process, native in conditions:
            for client in ("raw_socket", "http_client_read1", "curl"):
                row = observe(client, process, native)
                rows.append(row)
                print(json.dumps(row), flush=True)
        json.dump(
            {
                "evidence_kind": "fixed_cross_client_process_synthetic_control_not_inference",
                "body_bytes": len(BODY),
                "body_sha256": hashlib.sha256(BODY).hexdigest(),
                "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "model_calls": 0,
                "one_observation_per_condition": True,
                "native_server_source_sha256": hashlib.sha256(
                    Path(__file__).with_name("a01_native_control.go").read_bytes()
                ).hexdigest()
                if args.native_server
                else None,
                "native_server_binary_sha256": hashlib.sha256(
                    args.native_server.read_bytes()
                ).hexdigest()
                if args.native_server
                else None,
                "native_headers_differ_from_python": True if args.native_server else None,
                "curl_version": subprocess.check_output(
                    [shutil.which("curl.exe"), "--version"], text=True
                ).splitlines()[0],
                "observations": rows,
            },
            handle,
            indent=2,
        )
        handle.write("\n")


if __name__ == "__main__":
    main()
