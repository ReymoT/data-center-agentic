"""Offline narrow RULE03 continuation; the public CLI never dispatches research."""

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prepare_rule_study_dispatch as preflight  # noqa: E402
from scripts import prepare_rule_study_receiving as base  # noqa: E402
from scripts import prepare_rule_study_worker as worker  # noqa: E402

KIND = "rule03_narrow_continuation_preparation_v1"
FROZEN_COMMIT = "3daf00f7af5b130e8b17ae67b2f79a7dadb7ea00"
CONSUMED_ID = "rule03-primary-authored-3daf00f7-20261122"
REPORT_SHA = "f1e11a4f781c4d3efc920975a67d032d623cd7648ad60c63bd5bf2f6d008915e"
ARCHIVE_SHA = "7513b60c0f3656ef876dee9e6847f7a721f53669d5aed2aefa672356c9e7b7ca"
EVIDENCE = "docs/evidence/rule03-nov22/"
ARCHIVE = EVIDENCE + "primary-authored-attempt-3daf00f7.tar.gz"
EVIDENCE_PATHS = tuple(
    EVIDENCE + n
    for n in (
        "receiving-report.json",
        "attempt-receipt.json",
        "continuation-proposal.json",
        "SHA256SUMS.txt",
        "primary-authored-attempt-3daf00f7.tar.gz",
        "nisha-receiving-receipt.json",
        "nisha-receiving-nov23.txt",
    )
)
FILE_COUNT = 29569
EXPANDED_BYTES = 85881667
MAX_FILE_BYTES = 8 * 1024 * 1024
POLICIES = ["rules-v1", "greedy_a", "greedy_b"]
LIMITS = {
    "states": 10000,
    "transitions": 50000,
    "wall_seconds": 600,
    "new_case_policy_runs": 10,
    "saved_trace_replays": 51,
}
FIELDS = base.FIELDS
# Fixed import and fixed evidence allowlist, never a module/command from JSON.
_EVIDENCE_GATE = """
expected_evidence = data["receiving_plan"]["evidence_sha256"]
if set(expected_evidence) != set(EVIDENCE_PATHS):
    raise SystemExit(94)
for rel in EVIDENCE_PATHS:
    path = root/rel
    if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(root.resolve()):
        raise SystemExit(92)
    with path.open("rb") as handle:
        blob=handle.read(8*1024*1024+1)
    if len(blob)>8*1024*1024 or hashlib.sha256(blob).hexdigest()!=expected_evidence[rel]:
        raise SystemExit(94)
"""
BOOTSTRAP = base.BOOTSTRAP.replace(
    "from scripts.prepare_rule_study_receiving import execute_prepared",
    "from scripts.prepare_rule_study_continuation import execute_prepared",
).replace(
    "sys.path.insert(0,str(root))",
    "EVIDENCE_PATHS = "
    + repr(EVIDENCE_PATHS)
    + "\n"
    + _EVIDENCE_GATE
    + "\nsys.path.insert(0,str(root))",
)


def _evidence_bytes(relative):
    from dc_sustainability.evaluation import rule_study_receiving as rv

    path = ROOT / relative
    rv._safe_file(path)
    return preflight.bounded_bytes(path)


def receiving_plan():
    """Reconstruct source and retained-data identities without running a policy/replay."""
    from dc_sustainability.evaluation import rule_study_receiving as rv
    from dc_sustainability.evaluation import rule_study_trace as tr
    from dc_sustainability.evaluation import rule_study_verifier as v

    blobs = {p: _evidence_bytes(p) for p in EVIDENCE_PATHS}
    if hashlib.sha256(blobs[EVIDENCE + "receiving-report.json"]).hexdigest() != REPORT_SHA:
        raise ValueError("original report changed")
    if hashlib.sha256(blobs[ARCHIVE]).hexdigest() != ARCHIVE_SHA:
        raise ValueError("original archive changed")
    report = json.loads(blobs[EVIDENCE + "receiving-report.json"])
    received = json.loads(blobs[EVIDENCE + "nisha-receiving-receipt.json"])
    if (
        received["source_author"] != "nkolekar-nk"
        or received["source_comment_id"] != 7109387548
        or received["original_body_sha256"]
        != hashlib.sha256(blobs[EVIDENCE + "nisha-receiving-nov23.txt"]).hexdigest()
    ):
        raise ValueError("independent receiving identity differs")
    pin = report["pin"]
    if pin["code_commit"] != FROZEN_COMMIT or report["overall"] != "INCOMPLETE":
        raise ValueError("only the received incomplete original attempt is supported")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", FROZEN_COMMIT, "origin/main"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    current = rv.reconstruct_pin(ROOT)
    keys = (
        "spec_sha256",
        "adapter_source_sha256",
        "adapter_files",
        "generator_source_sha256",
        "environment_lock_sha256",
    )
    if any(current[k] != pin[k] for k in keys):
        raise ValueError("scientific source differs from the frozen producer")
    # Corroborate immutable original Git blobs, not just a producer assertion.
    paths = [rv.ADAPTER_DIR / n for n in pin["adapter_files"]]
    paths += [rv.SPEC_REL, rv.GENERATOR_REL, rv.LOCK_REL]
    paths += [Path(m.__file__).relative_to(ROOT) for m in (rv, tr, v)]
    for path in paths:
        original = subprocess.check_output(
            ["git", "show", FROZEN_COMMIT + ":" + path.as_posix()], cwd=ROOT
        )
        if original.replace(b"\r\n", b"\n") != (ROOT / path).read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError("frozen scientific source bytes changed")
    proposal = json.loads(blobs[EVIDENCE + "continuation-proposal.json"])
    remaining = proposal["saved_greedy_b_replay_remaining"]
    expected = [c.case_id for c in v.primary_domain()[13:]]
    if len(remaining) != 51 or [r["case_id"] for r in remaining] != expected:
        raise ValueError("exact 51 outstanding saved traces required")
    for r in remaining:
        if (
            set(r) != {"case_id", "folder", "result_sha256"}
            or r["folder"] != f"traces/primary/greedy_b/{r['case_id']}-greedy_b"
            or not re.fullmatch("[a-f0-9]{64}", r["result_sha256"])
        ):
            raise ValueError("unexpected saved-trace identity")
    spec = json.loads((ROOT / rv.SPEC_REL).read_bytes())
    return {
        "status": "NOT_RUN",
        "evidence_sha256": {p: hashlib.sha256(b).hexdigest() for p, b in blobs.items()},
        "saved_producer_pin": pin,
        "saved_replay_records": remaining,
        "authored_plan": rv.plan_receiving(["authored"], POLICIES, ROOT, spec),
        "original_state_count": report["combined_budget"]["states_used"],
        "original_transition_count": report["combined_budget"]["transitions_used"],
        "note": "Historical saved producer pin remains original; authored outputs bind the new host commit with identical scientific source.",
    }


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
        raise ValueError("fixed combined continuation limits required")
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
    if ident == CONSUMED_ID:
        problems.append("original authorization ID is consumed")
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


def extract_verified(destination, expected_evidence, budget):
    """Extract only exact received regular files into a new owned directory."""
    if set(expected_evidence) != set(EVIDENCE_PATHS):
        raise ValueError("exact received evidence allowlist required")
    captured = {p: _evidence_bytes(p) for p in EVIDENCE_PATHS}
    if any(hashlib.sha256(captured[p]).hexdigest() != h for p, h in expected_evidence.items()):
        raise ValueError("received evidence drift")
    expected = {}
    for line in captured[EVIDENCE + "SHA256SUMS.txt"].decode("utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if name in expected or not re.fullmatch("[a-f0-9]{64}", digest):
            raise ValueError("duplicate/invalid manifest entry")
        expected[name] = digest
    if len(expected) != FILE_COUNT:
        raise ValueError("unexpected received manifest size")
    destination.mkdir(exist_ok=False)
    seen = set()
    total = 0
    # Parse the exact bytes just authenticated; do not reopen a replaceable path.
    with tarfile.open(fileobj=io.BytesIO(captured[ARCHIVE]), mode="r:gz") as tar:
        for member in tar:
            if not budget.check_time():
                raise TimeoutError("combined continuation budget stopped extraction")
            name = member.name
            parts = PurePosixPath(name).parts
            if (
                not member.isfile()
                or name in seen
                or name not in expected
                or not parts
                or name.startswith("/")
                or ".." in parts
                or "\\" in name
                or ":" in name
                or member.size < 0
                or member.size > MAX_FILE_BYTES
                or len(seen) >= FILE_COUNT
            ):
                raise ValueError("unsafe or unexpected archive member")
            total += member.size
            if total > EXPANDED_BYTES:
                raise ValueError("archive expansion exceeds received bytes")
            raw = tar.extractfile(member).read(MAX_FILE_BYTES + 1)
            if len(raw) != member.size or hashlib.sha256(raw).hexdigest() != expected[name]:
                raise ValueError("received artifact hash differs")
            target = destination.joinpath(*parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError("archive escape refused")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as h:
                h.write(raw)
            seen.add(name)
    if seen != set(expected) or total != EXPANDED_BYTES:
        raise ValueError("missing/truncated received archive")


def execute_prepared(request):
    """Contained backend only; no authority is taken from the pending request."""
    if assess(request)["problems"]:
        raise ValueError("continuation preflight blocked after containment")
    from dc_sustainability.evaluation import rule_study_receiving as rv
    from dc_sustainability.evaluation import rule_study_verifier as v

    plan = request["receiving_plan"]
    out = Path(request["output_directory"])
    out.mkdir(exist_ok=False)
    budget = v.Budget(max_states=10000, max_transitions=50000, max_seconds=600)
    try:
        extract_verified(out / "received", plan["evidence_sha256"], budget)
        spec = json.loads((ROOT / rv.SPEC_REL).read_bytes())
        authored = rv.run_receiving(
            ["authored"], POLICIES, out / "authored", ROOT, spec, budget=budget
        )
        phases = {"authored": authored}
        if authored["overall"] == "PASS" and not budget.exhausted:
            folders = []
            for r in plan["saved_replay_records"]:
                folder = out / "received" / r["folder"]
                if (
                    hashlib.sha256(preflight.bounded_bytes(folder / "result.json")).hexdigest()
                    != r["result_sha256"]
                ):
                    raise ValueError("outstanding saved result changed")
                folders.append((r["case_id"], "greedy_b", folder))
            phases["saved_greedy_b"] = rv._receive_folders(
                "saved_primary_greedy_b_remainder",
                51,
                folders,
                [],
                plan["saved_producer_pin"],
                spec,
                budget=budget,
            )
        stable = receiving_plan() == plan
        statuses = [r["overall"] for r in phases.values()]
        overall = (
            "FAIL"
            if not stable or "FAIL" in statuses
            else (
                "PASS"
                if len(phases) == 2 and all(s == "PASS" for s in statuses) and not budget.exhausted
                else "INCOMPLETE"
            )
        )
        report = {
            "record_kind": "rule03_narrow_continuation_v1",
            "overall": overall,
            "scope": "Only this continuation; original attempt stays INCOMPLETE and scientific freeze/person receiving remains separate.",
            "original_report_sha256": REPORT_SHA,
            "original_attempt_overall": "INCOMPLETE",
            "saved_producer_pin": plan["saved_producer_pin"],
            "new_authored_pin": plan["authored_plan"]["pin"],
            "phases": phases,
            "combined_budget": budget.summary(),
            "source_evidence_stable": stable,
            "cumulative_charged_states": plan["original_state_count"] + budget.states,
            "cumulative_charged_transitions": plan["original_transition_count"]
            + budget.transitions,
            "scientific_freeze_accepted": False,
            "independent_person_receiving": "PENDING",
            "new_primary_executions": 0,
            "model_calls": 0,
            "final_cases_generated": 0,
        }
        with (out / "continuation-report.json").open("x", encoding="utf-8") as h:
            json.dump(report, h, indent=2, allow_nan=False)
        return 0 if overall == "PASS" else 7
    except BaseException as exc:
        with (out / "continuation-failure.json").open("x", encoding="utf-8") as h:
            json.dump(
                {
                    "exception": type(exc).__name__,
                    "retry_allowed": False,
                    "budget": budget.summary(),
                },
                h,
            )
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
        "operation": "rule03_saved51_authored10_not_final_evaluation",
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
            report_path = out / "continuation-report.json"
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
        parser.exit(2, f"Continuation preparation refused: {exc}\n")
    return 2 if report.get("status") == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
