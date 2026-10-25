"""Start and verify an isolated Arc/Vulkan Ollama metadata server.

This Windows-only A01 helper cannot dispatch inference. Its fixed HTTP allowlist is
limited to version, installed-model metadata and loaded-model inspection. It
refuses occupied ports and existing outputs, checks the accepted runtime/model
identity, requires zero loaded models, and stops only the exact process it started.
"""

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.inspect_ollama import compare_inventory, inventory  # noqa: E402

EXPECTED_RUNTIME = "0.40.5"
EXPECTED_RUNTIME_SHA256 = "ec9f3325f134597c7188b735dcc4e79a9eca4bf53f6b958ddf22aa04bf5ce57a"
METADATA_ENDPOINTS = frozenset({"/api/version", "/api/tags", "/api/show", "/api/ps"})
REQUIRED_ENVIRONMENT = {
    "OLLAMA_IGPU_ENABLE": "1",
    "OLLAMA_VULKAN": "1",
    "OLLAMA_NUM_PARALLEL": "1",
    "OLLAMA_MAX_LOADED_MODELS": "1",
    "OLLAMA_NO_CLOUD": "1",
}


def _local_url(port: int, path: str) -> str:
    if path not in METADATA_ENDPOINTS:
        raise ValueError(f"endpoint is not permitted by the metadata-only preflight: {path}")
    if not 1024 <= port <= 65535:
        raise ValueError("use an unprivileged TCP port from 1024 through 65535")
    return f"http://127.0.0.1:{port}{path}"


def _read_metadata(port: int, path: str) -> dict:
    url = _local_url(port, path)
    if path == "/api/show":
        action = (
            f"Invoke-RestMethod -Uri '{url}' -Method Post -ContentType 'application/json' "
            '-Body \'{"model":"qwen3:8b","verbose":false}\' -TimeoutSec 10'
        )
    else:
        action = f"Invoke-RestMethod -Uri '{url}' -Method Get -TimeoutSec 10"
    command = (
        "$ProgressPreference = 'SilentlyContinue'; "
        f"$result = {action}; $result | ConvertTo-Json -Depth 100 -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    raw = completed.stdout.encode("utf-8")
    if len(raw) > 1024 * 1024:
        raise ValueError("metadata response exceeds 1 MiB")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("metadata response must be a JSON object")
    return result


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _listener_pids(port: int) -> list[int]:
    command = (
        "$items = @(Get-NetTCPConnection -LocalAddress 127.0.0.1 "
        f"-LocalPort {port} -State Listen -ErrorAction SilentlyContinue); "
        "$items | Select-Object -ExpandProperty OwningProcess | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    text = completed.stdout.strip()
    if not text:
        return []
    value = json.loads(text)
    return [int(item) for item in value] if isinstance(value, list) else [int(value)]


def parse_arc_compute(stderr_text: str) -> dict:
    lines = [line for line in stderr_text.splitlines() if 'msg="inference compute"' in line]
    if len(lines) != 1:
        raise ValueError("expected exactly one inference-compute discovery line")
    line = lines[0]
    required = ("library=Vulkan", 'description="Intel(R) Arc(TM) 140V GPU (16GB)"', "type=iGPU")
    if not all(token in line for token in required):
        raise ValueError("runtime did not retain the accepted Intel Arc Vulkan iGPU")
    if "dropping integrated GPU" in stderr_text or re.search(r"\blibrary=cpu\b", line, re.I):
        raise ValueError("runtime dropped the integrated GPU or selected CPU")

    def field(name: str) -> str | None:
        match = re.search(rf'\b{name}=(?:"([^"]*)"|(\S+))', line)
        return (match.group(1) or match.group(2)) if match else None

    return {
        "library": field("library"),
        "name": field("name"),
        "description": field("description"),
        "type": field("type"),
        "reported_total": field("total"),
        "reported_available": field("available"),
        "reported_driver": field("driver"),
        "reported_compute": field("compute"),
    }


def _wait_until_ready(process: subprocess.Popen, port: int, seconds: float = 15) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("isolated runtime exited before metadata readiness")
        try:
            version = _read_metadata(port, "/api/version").get("version")
            if version != EXPECTED_RUNTIME:
                raise ValueError(f"expected Ollama {EXPECTED_RUNTIME}, observed {version!r}")
            return
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            time.sleep(0.25)
    raise TimeoutError("isolated runtime did not become metadata-ready within 15 seconds")


def run_preflight(
    runtime: Path, models: Path, accepted_inventory: Path, output_dir: Path, port: int
) -> dict:
    if os.name != "nt":
        raise RuntimeError("the Arc/Vulkan A01 launcher is Windows-only")
    runtime = runtime.resolve(strict=True)
    models = models.resolve(strict=True)
    accepted_inventory = accepted_inventory.resolve(strict=True)
    output_dir = output_dir.resolve()
    if runtime.name.lower() != "ollama.exe" or not runtime.is_file():
        raise ValueError("runtime must be an existing ollama.exe")
    runtime_sha256 = _file_sha256(runtime)
    if runtime_sha256 != EXPECTED_RUNTIME_SHA256:
        raise ValueError("runtime executable does not match the accepted Ollama 0.40.5 binary")
    if not models.is_dir():
        raise ValueError("models must be an existing isolated model-store directory")
    if not _port_is_free(port):
        raise RuntimeError("isolated loopback port is already in use; its owner was not changed")
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "ollama-metadata-stdout.log"
    stderr_path = output_dir / "ollama-metadata-stderr.log"
    report_path = output_dir / "a01-igpu-preflight.json"
    for path in (stdout_path, stderr_path, report_path):
        if path.exists():
            raise FileExistsError(f"preserve prior evidence; output already exists: {path}")

    environment = {key: value for key, value in os.environ.items() if not key.startswith("OLLAMA_")}
    environment.update(REQUIRED_ENVIRONMENT)
    environment["OLLAMA_HOST"] = f"127.0.0.1:{port}"
    environment["OLLAMA_MODELS"] = str(models)
    process = None
    cleanup = {"owned_server_exited": False, "listener_remaining": None}
    report: dict = {
        "evidence_kind": "metadata_only_arc_vulkan_preflight_not_inference",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "started",
        "runtime_version": None,
        "runtime_executable_sha256": runtime_sha256,
        "model_requests": 0,
        "loaded_models": None,
        "isolated_listener": f"127.0.0.1:{port}",
        "environment": REQUIRED_ENVIRONMENT,
        "identity_matches_accepted_inventory": False,
        "detected_compute": None,
        "cleanup": cleanup,
        "limits": [
            "This launcher has no chat or generate endpoint and cannot dispatch inference.",
            "Metadata readiness does not prove model load, layer offload, context fit or latency.",
            "Runtime-reported integrated graphics memory is not dedicated VRAM.",
            "This preflight does not authorize inference or adopt the candidate settings.",
        ],
    }
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            process = subprocess.Popen(
                [str(runtime), "serve"],
                cwd=runtime.parent,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            _wait_until_ready(process, port)
            if _listener_pids(port) != [process.pid]:
                raise RuntimeError("isolated listener is not owned only by the started runtime")
            version = _read_metadata(port, "/api/version")
            tags = _read_metadata(port, "/api/tags")
            show = _read_metadata(port, "/api/show")
            actual = inventory(version, tags, show)
            # Detect replacement of the mutable tag during the inspection.
            again = inventory(
                _read_metadata(port, "/api/version"),
                _read_metadata(port, "/api/tags"),
                _read_metadata(port, "/api/show"),
            )
            compare_inventory(actual, again)
            expected = json.loads(accepted_inventory.read_text(encoding="utf-8"))
            compare_inventory(expected, actual)
            loaded = _read_metadata(port, "/api/ps").get("models")
            if not isinstance(loaded, list) or loaded:
                raise RuntimeError("metadata-only preflight requires exactly zero loaded models")
            stderr.flush()
            compute = parse_arc_compute(stderr_path.read_text(encoding="utf-8", errors="replace"))
            report.update(
                status="passed",
                runtime_version=actual["runtime_version"],
                loaded_models=0,
                identity_matches_accepted_inventory=True,
                detected_compute=compute,
            )
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if process is not None and process.poll() is None:
            # Popen's retained Windows process handle identifies exactly the child
            # created above; no name-based or broad process termination is used.
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        cleanup["owned_server_exited"] = process is None or process.poll() is not None
        cleanup["listener_remaining"] = bool(_listener_pids(port))
        if cleanup["listener_remaining"]:
            report["status"] = "failed_cleanup"
        with report_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if not cleanup["owned_server_exited"] or cleanup["listener_remaining"]:
        raise RuntimeError("exact-process cleanup verification failed")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--models", required=True, type=Path)
    parser.add_argument("--accepted-inventory", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--port", type=int, default=11437)
    args = parser.parse_args()
    result = run_preflight(
        args.runtime, args.models, args.accepted_inventory, args.output_dir, args.port
    )
    print(
        f"A01 Arc/Vulkan metadata preflight: {result['status']}; "
        "loaded models: 0; model requests: 0; cleanup verified"
    )


if __name__ == "__main__":
    main()
