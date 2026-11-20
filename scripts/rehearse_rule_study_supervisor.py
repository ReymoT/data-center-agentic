"""Offline RULE-06 containment rehearsal; only built-in dummy workers can run.

This CLI cannot dispatch the verifier, scheduler, generator or arbitrary commands.
Actual study wiring and exact single-use authorization remain separate gates.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.runtime.bounded_worker import supervise  # noqa: E402

MODES = ("success", "failure", "timeout", "descendant")
# No user-supplied Python/command is interpolated into this fixed worker.
WORKER = r"""
import json, os, pathlib, subprocess, sys, time
if sys.stdin.buffer.read(1) != b"G":
    raise SystemExit(90)
out, mode = pathlib.Path(sys.argv[1]), sys.argv[2]
(out / "worker.json").write_text(json.dumps({"pid": os.getpid(), "mode": mode}))
if mode == "failure":
    (out / "failure.txt").write_text("deliberate dummy failure; not a study result")
    raise SystemExit(7)
if mode == "timeout":
    time.sleep(60)
if mode == "descendant":
    code = "import pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text('ready'); time.sleep(60)"
    child = subprocess.Popen([sys.executable, "-c", code, str(out / "descendant-ready.txt")],
                             creationflags=subprocess.CREATE_NO_WINDOW)
    (out / "descendant.json").write_text(json.dumps({"pid": child.pid}))
    until = time.monotonic() + 2
    while not (out / "descendant-ready.txt").exists() and time.monotonic() < until:
        time.sleep(0.01)
    if not (out / "descendant-ready.txt").exists():
        raise SystemExit(8)
"""


def rehearse(mode, out, limit_s=3.0):
    """Preserve dummy failure evidence in a new folder; never launch research code."""
    if mode not in MODES:
        raise ValueError("only built-in dummy modes are allowed")
    if type(limit_s) not in (int, float) or not math.isfinite(limit_s) or not 0 < limit_s <= 5:
        raise ValueError("rehearsal limit must be positive and at most five seconds")
    if os.name != "nt":
        raise OSError("Windows Job Object containment is required; no uncontained fallback")
    out = Path(out).resolve()
    out.mkdir(exist_ok=False)
    result = supervise([sys.executable, "-X", "utf8", "-c", WORKER, str(out), mode], limit_s)
    expected = {
        "success": "succeeded",
        "failure": "failed",
        "timeout": "timed_out",
        "descendant": "descendants_left_running",
    }[mode]
    report = {
        "kind": "rule_study_supervisor_rehearsal_v1",
        "scope": "dummy_processes_only_not_scientific_verification",
        "mode": mode,
        "limit_s": limit_s,
        "expected_status": expected,
        "supervision": result,
        "rehearsal_passed": result["status"] == expected
        and result["released"]
        and result["cleanup_verified"],
        "research_execution_authorized": False,
    }
    with (out / "rehearsal.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new dummy-output directory")
    parser.add_argument("--limit-seconds", type=float, default=3.0)
    args = parser.parse_args(argv)
    try:
        report = rehearse(args.mode, args.out, args.limit_seconds)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Rehearsal refused: {exc}\n")
    print(json.dumps(report))
    return 0 if report["rehearsal_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
