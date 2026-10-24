"""Four fixed Windows loopback TCP-state observations; never model inference."""

import argparse
import base64
import json
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import diagnose_a01_lifecycle as controls  # noqa: E402

MODES = ("original_close", "wait_for_client", "wait_for_client", "original_close")


def tcp_snapshot(port):
    """Export only TCP endpoints of this synthetic loopback observation."""
    result = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        timeout=4,
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    rows = []
    endpoint = f"127.0.0.1:{port}"
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) != 5 or fields[0] != "TCP":
            continue
        local, remote, state, pid = fields[1:]
        if endpoint not in {local, remote}:
            continue
        if remote != "0.0.0.0:0" and not remote.startswith("127.0.0.1:"):
            continue
        rows.append({"local": local, "remote": remote, "state": state, "pid": int(pid)})
    return rows


def observation(binary, mode, payload, wire):
    child = subprocess.Popen(
        [str(binary.resolve())],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    snapshots = []
    worker = None
    try:
        config = {"wire_base64": base64.b64encode(wire).decode(), "close_mode": mode}
        child.stdin.write(json.dumps(config).encode() + b"\n")
        child.stdin.flush()
        port = json.loads(child.stdout.readline())["port"]
        started = time.monotonic()

        def sample():
            # One predeclared observation, not outcome-triggered polling.
            time.sleep(max(0, started + 0.25 - time.monotonic()))
            entry = {"snapshot_started_seconds": time.monotonic() - started}
            try:
                entry["connections"] = tcp_snapshot(port)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                entry["error"] = f"{type(exc).__name__}: {exc}"
            entry["snapshot_finished_seconds"] = time.monotonic() - started
            snapshots.append(entry)

        worker = threading.Thread(target=sample)
        worker.start()
        row = controls.raw_client(port, payload)
        row["client_returned_seconds"] = time.monotonic() - started
        worker.join()
        stdout, stderr = child.communicate(b"stop\n", timeout=4)
        if child.returncode != 0:
            raise RuntimeError(stderr.decode(errors="replace"))
        server = json.loads(stdout)
        assert server["configured_wire_sha256"] == controls.sha(wire)
        assert server["request_sha256"] == controls.sha(payload)
        assert server["request_bytes"] == len(payload)
        row.update(close_mode=mode, native_events=server, tcp_snapshots=snapshots)
        return row
    finally:
        if worker is not None:
            worker.join()
        if child.poll() is None:
            child.kill()
            child.communicate()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--native-server", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("this optional netstat observation is Windows-specific")
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    wire = reference["reference_headers_latin1"].encode("latin1") + controls.BODY
    payload = controls.request_body()
    assert controls.sha(wire) == reference["reference_wire_sha256"]
    assert controls.sha(payload) == reference["request_sha256"]
    assert controls.sha(args.native_server.read_bytes()) == reference["native_binary_sha256"]
    rows = []
    report = {
        "evidence_kind": "fixed_synthetic_windows_tcp_state_observations",
        "python": sys.version,
        "platform": platform.platform(),
        "model_calls": 0,
        "plan": {"modes": MODES, "snapshot_delay_seconds": 0.25, "retries": 0},
        "source_sha256_lf": controls.source_sha(Path(__file__)),
        "observer_source_sha256_lf": controls.source_sha(SCRIPTS / "diagnose_a01_lifecycle.py"),
        "native_source_sha256_lf": reference["native_source_sha256_lf"],
        "native_binary_sha256": reference["native_binary_sha256"],
        "reference_wire_sha256": controls.sha(wire),
        "request_sha256": controls.sha(payload),
        "observations": rows,
        "completed": False,
        "limits": "Four single-machine observations, not a reliability estimate or fix. "
        "netstat may perturb timing and samples state after transfers that finish quickly. "
        "TCP state is not packet/queue evidence or proof of which layer lost bytes. "
        "Original raw client, native binary, provider/tests and deadlines unchanged.",
    }
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        try:
            for index, mode in enumerate(MODES, start=1):
                row = observation(args.native_server, mode, payload, wire)
                row["observation"] = index
                rows.append(row)
                print(json.dumps(row), flush=True)
            report["completed"] = True
        except Exception as exc:
            report["execution_error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            json.dump(report, handle, indent=2)
            handle.write("\n")


if __name__ == "__main__":
    main()
