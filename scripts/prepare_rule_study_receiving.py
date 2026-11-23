"""Offline RULE03 receiving preparation; public CLI never dispatches research."""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import prepare_rule_study_dispatch as preflight  # noqa: E402
from scripts import prepare_rule_study_worker as worker  # noqa: E402

KIND = "rule03_contained_receiving_preparation_v1"
DOMAINS = ["primary", "authored"]
POLICIES = ["rules-v1", "greedy_a", "greedy_b"]
LIMITS = {"states": 10000, "transitions": 50000, "wall_seconds": 600, "runs": 202}
FIELDS = {
    "kind",
    "status",
    "code_commit",
    "code_sha256",
    "receiving_plan",
    "limits",
    "output_directory",
    "proposed_authorization_id",
}
# Same fixed stdin/hash/source bootstrap as the authored worker. No module/command
# comes from JSON. Its only backend import is this fixed receiving preparation.
BOOTSTRAP = worker.BOOTSTRAP.replace('plan=data["plan"]', "plan=data").replace(
    "from scripts.prepare_rule_study_worker import execute_prepared",
    "from scripts.prepare_rule_study_receiving import execute_prepared",
)


def receiving_plan():
    from dc_sustainability.evaluation import rule_study_receiving as rv

    spec = json.loads((ROOT / rv.SPEC_REL).read_bytes())
    return rv.plan_receiving(DOMAINS, POLICIES, ROOT, spec)


def draft():
    commit, pins = preflight.snapshot()
    return {
        "kind": KIND,
        "status": "pending_explicit_approval",
        "code_commit": commit,
        "code_sha256": pins,
        "receiving_plan": receiving_plan(),
        "limits": dict(LIMITS),
        "output_directory": None,
        "proposed_authorization_id": None,
    }


def safe_external(path):
    """Existing unlinked parent, external path, no linked ancestor."""
    p = Path(path)
    if not p.is_absolute() or not p.parent.is_dir():
        raise ValueError("absolute external path with existing parent required")
    if any(x.is_symlink() or x.is_junction() for x in (p, *p.parents)):
        raise ValueError("linked paths are refused")
    if p.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("path must be outside checkout")
    return p


def assess(request):
    if not isinstance(request, dict) or set(request) != FIELDS:
        raise ValueError("exact receiving fields required; no approval or command fields")
    if request["kind"] != KIND or request["status"] != "pending_explicit_approval":
        raise ValueError("JSON cannot approve receiving")
    # Exact constants, including types: bool/float aliases must not substitute counters.
    if json.dumps(request["limits"], sort_keys=True) != json.dumps(LIMITS, sort_keys=True):
        raise ValueError("fixed combined receiving limits required")
    commit, pins = preflight.snapshot()
    problems = []
    if request["code_commit"] != commit or request["code_sha256"] != pins:
        problems.append("merged commit/source pins changed")
    if request["receiving_plan"] != receiving_plan():
        problems.append("independent receiving pin or domain plan changed")
    out = request["output_directory"]
    try:
        if not isinstance(out, str) or not out:
            raise ValueError("new output missing")
        if safe_external(out).exists():
            raise ValueError("output already exists")
    except (ValueError, OSError) as exc:
        problems.append(str(exc))
    ident = request["proposed_authorization_id"]
    if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", ident):
        problems.append("proposed single-use ID missing/invalid")
    return {
        "status": "BLOCKED" if problems else "PREPARED_NOT_AUTHORIZED",
        "problems": problems,
        "release_allowed": False,
        "study_execution_performed": False,
    }


def contained_command(request_path):
    path = Path(request_path).absolute()
    raw = preflight.bounded_bytes(path)
    request = json.loads(raw)
    if assess(request)["problems"]:
        raise ValueError("receiving preflight blocked")
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError("linked request refused")
    return [
        sys.executable,
        "-X",
        "utf8",
        "-c",
        BOOTSTRAP,
        str(ROOT),
        str(path),
        hashlib.sha256(raw).hexdigest(),
    ]


def execute_prepared(request):
    """Only after trusted approval/reservation and contained bootstrap release.

    Ordinary tests mock the receiving API; this function is not an approval source.
    No private/accounting inputs or final generator are used by closed-case receiving.
    """
    if assess(request)["problems"]:
        raise ValueError("receiving preflight blocked after containment")
    from dc_sustainability.evaluation import rule_study_receiving as rv
    from dc_sustainability.evaluation import rule_study_verifier as v

    spec = json.loads((ROOT / rv.SPEC_REL).read_bytes())
    out = Path(request["output_directory"])
    # Reserve ownership before failure handling; never add evidence to a raced-in folder.
    out.mkdir(exist_ok=False)
    try:
        report = rv.run_receiving(
            DOMAINS,
            POLICIES,
            out / "traces",
            ROOT,
            spec,
            budget=v.Budget(max_states=10000, max_transitions=50000, max_seconds=600),
        )
        with (out / "receiving-report.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
        return 0 if report["overall"] == "PASS" else 7
    except BaseException as exc:
        # This wrapper owns the new directory. Preserve partial traces and failure.
        if out.is_dir():
            with (out / "receiving-failure.json").open("x", encoding="utf-8") as stream:
                json.dump({"exception": type(exc).__name__, "retry_allowed": False}, stream)
        raise


def dispatch_once(request_path, *, ledger, trusted_authorize=None):
    """Trusted host only; callback authenticates the exact fresh human decision.

    A URL, JSON flag or caller-selected import cannot provide this authority.
    No public CLI calls this function. Tests use fixture authority and fake supervision.
    """
    if not callable(trusted_authorize):
        raise PermissionError("fresh trusted host authorization required")
    path = Path(request_path).absolute()
    command = contained_command(path)
    request = json.loads(preflight.bounded_bytes(path))
    environment = worker.environment_evidence()
    subject = {
        "request_sha256": command[-1],
        "authorization_id": request["proposed_authorization_id"],
        "code_commit": request["code_commit"],
        "output_directory": request["output_directory"],
        "operation": "rule03_primary_authored_max202_not_final_evaluation",
        "limits": dict(LIMITS),
    }
    expected = dict(subject, actor="MattyAnd", decision="approved")
    receipt = trusted_authorize(json.loads(json.dumps(subject)))
    if receipt != expected:
        raise PermissionError("exact receiving envelope not approved")
    ledger = safe_external(str(Path(ledger).absolute()))
    out = Path(request["output_directory"]).resolve()
    if ledger.resolve().is_relative_to(out) or out.is_relative_to(ledger.resolve()):
        raise ValueError("ledger and output must be separate")
    ledger.mkdir(exist_ok=True)
    entry = ledger / (hashlib.sha256(subject["authorization_id"].encode()).hexdigest() + ".json")
    with entry.open("x", encoding="utf-8") as stream:
        json.dump({"receipt": receipt, "environment": environment}, stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    result = {
        "status": "stopped_after_reservation",
        "retry_allowed": False,
        "authorization_id": subject["authorization_id"],
    }
    try:
        if contained_command(path) != command or worker.environment_evidence() != environment:
            raise ValueError("request/source/environment drift after reservation")
        from dc_sustainability.runtime.bounded_worker import supervise

        result["supervision"] = supervise(command, LIMITS["wall_seconds"], cwd=ROOT)
        supervision = result["supervision"]
        result["status"] = "failed"
        if supervision["status"] == "succeeded" and supervision["cleanup_verified"]:
            report_path = out / "receiving-report.json"
            if report_path.is_file() and not report_path.is_symlink():
                report = json.loads(preflight.bounded_bytes(report_path))
                result["receiving_overall"] = report.get("overall")
                result["status"] = "completed" if report.get("overall") == "PASS" else "failed"
        return result
    except BaseException as exc:
        result["exception"] = type(exc).__name__
        raise
    finally:
        with entry.with_suffix(".result.json").open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--draft", action="store_true")
    group.add_argument("--inspect", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = (
            draft() if args.draft else assess(json.loads(preflight.bounded_bytes(args.inspect)))
        )
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Receiving preparation refused: {exc}\n")
    return 2 if report.get("status") == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
