"""Windows-only supervised CF60 ingest. Never use a pending approval to dispatch.

Approval authentication, source permission and custody remain external gates.
This module has no automatic dispatch on import. Use synthetic tests offline.
"""

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.runtime.windows_job import WindowsJob  # noqa: E402
from scripts import extract_cf60_development as extractor  # noqa: E402


def supervise(command, limit_s, *, cwd=ROOT):
    """Run a stdin-gated child once; discard output and contain its descendants.

    Deadline starts before Popen. OS process creation itself is not interruptible;
    if it returns late, never release the child. Cleanup has a separate 3s budget.
    The child MUST wait for b'G' before doing any work or spawning descendants.
    """
    if type(limit_s) not in (int, float) or not math.isfinite(limit_s) or not 0 < limit_s <= 120:
        raise ValueError("wall deadline must be positive and at most 120 seconds")
    job, child = None, None
    started = monotonic()
    result = {"status": "failed", "released": False, "cleanup_verified": False}
    try:
        job = WindowsJob()
        child = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
        result["pid"] = child.pid
        job.assign(child.pid)
        remaining = limit_s - (monotonic() - started)
        if remaining <= 0:
            result["status"] = "timed_out_before_release"
        else:
            child.stdin.write(b"G")
            child.stdin.close()
            result["released"] = True
            try:
                child.wait(timeout=max(0, limit_s - (monotonic() - started)))
                result["returncode"] = child.returncode
                if monotonic() - started >= limit_s:
                    result["status"] = "timed_out"
                else:
                    result["status"] = "succeeded" if child.returncode == 0 else "failed"
                # A successful direct child must not leave background descendants.
                if not job.wait_empty(min(started + limit_s, monotonic() + 0.2)):
                    result["status"] = "descendants_left_running"
            except subprocess.TimeoutExpired:
                result["status"] = "timed_out"
    except KeyboardInterrupt:
        result["status"] = "interrupted"
    except Exception as exc:
        result["status"] = "supervision_failed"
        result["exception"] = type(exc).__name__  # no raw child/CSV output
    finally:
        result["elapsed_before_cleanup_s"] = monotonic() - started
        if result["status"] == "succeeded" and monotonic() - started >= limit_s:
            result["status"] = "timed_out"
        cleanup_deadline = monotonic() + 3
        try:
            if job is not None:
                job.stop()
            if child is not None:
                # Includes assign failure: gated/unassigned child is killed directly.
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=max(0, cleanup_deadline - monotonic()))
            result["cleanup_verified"] = True
        except Exception as exc:
            result["status"] = "cleanup_unverified"
            result["cleanup_exception"] = type(exc).__name__
        finally:
            if child is not None and child.stdin is not None:
                child.stdin.close()
            if job is not None:
                job.close()  # kill-on-close also applies if the supervisor crashes
        result["elapsed_including_cleanup_s"] = monotonic() - started
    return result


def write_new(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def launch(source, authorization, output):
    approval_bytes = authorization.read_bytes()
    approval, _, limit = extractor.preflight(source, approval_bytes, output)
    if os.name != "nt":
        raise OSError("Windows containment required; no portable fallback")
    # Exclusive dispatch reservation survives timeout before the worker's own ledger.
    ledger = output.parent / ".cf60-dispatch-consumed-authorizations"
    ledger.mkdir(exist_ok=True)
    key = hashlib.sha256(approval["authorization_id"].encode()).hexdigest()
    digest = hashlib.sha256(approval_bytes).hexdigest()
    write_new(ledger / (key + ".json"), {"approval_sha256": digest, "single_use": True})
    receipt = output.with_name(output.name + ".dispatch")
    receipt.mkdir(exist_ok=False)
    snapshot = receipt / "authorization.json"
    with snapshot.open("xb") as handle:
        handle.write(approval_bytes)
    write_new(
        receipt / "intent.json",
        {
            "approval_sha256": digest,
            "deadline_s": limit,
            "scope": "source-ingest-only",
            "no_retries": True,
        },
    )
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--source",
        str(source.resolve()),
        "--authorization",
        str(snapshot.resolve()),
        "--out",
        str(output.resolve()),
        "--approval-sha256",
        digest,
    ]
    result = supervise(command, limit)
    result["approval_sha256"] = digest
    if result["status"] == "succeeded":
        if not output.is_file() or output.with_name(output.name + ".failure.json").exists():
            result["status"] = "output_unverified"
        else:
            result["extract_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    write_new(receipt / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--approval-sha256", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if sys.stdin.buffer.read(1) != b"G":
            return 2  # never touch source on absent supervisor release
        payload = args.authorization.read_bytes()
        if hashlib.sha256(payload).hexdigest() != args.approval_sha256:
            return 2
        extractor.run(args.source, args.authorization, args.out, approval_bytes=payload)
        return 0
    result = launch(args.source, args.authorization, args.out)
    print(result["status"])
    return 0 if result["status"] == "succeeded" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"CF60 ingest stopped: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
