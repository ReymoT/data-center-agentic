"""Prepare a fixed contained RULE02 authored-case worker; public CLI never launches it.

The eventual trusted supervisor must authenticate fresh bounded human approval and
consume its single-use ID before sending G. A pending plan or command is not approval.
Final generation, arbitrary modules and independent verification are not wired here.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import prepare_rule_study_dispatch as preflight  # noqa: E402

KIND = "rule_study_authored_worker_preparation_v1"
CASES = {"A", "B", "B-progress", "B-fault"}
POLICIES = {"rules-v1", "greedy_a", "greedy_b"}
# Only stdlib is imported before the containment release and code-pin checks.
BOOTSTRAP = r"""
import hashlib, json, pathlib, sys
if sys.stdin.buffer.read(1) != b"G":
    raise SystemExit(90)
root, request, expected = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
with request.open("rb") as handle:
    raw = handle.read(8*1024*1024+1)
if len(raw)>8*1024*1024 or hashlib.sha256(raw).hexdigest()!=expected:
    raise SystemExit(91)
data=json.loads(raw)
plan=data["plan"]
paths=sorted((root/"dc_sustainability").rglob("*.py"))+sorted((root/"scripts").rglob("*.py"))
paths += [root/"requirements/requirements-windows-py312.lock.txt", root/"docs/rule_study/specification.json"]
actual={}
for path in paths:
    if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(root.resolve()):
        raise SystemExit(92)
    actual[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes().replace(b"\r\n",b"\n")).hexdigest()
if actual != plan["code_sha256"]:
    raise SystemExit(93)
sys.path.insert(0,str(root))
from scripts.prepare_rule_study_worker import execute_prepared
raise SystemExit(execute_prepared(data))
"""


def validate_request(request):
    if not isinstance(request, dict) or set(request) != {"kind", "plan", "case_id", "policy_id"}:
        raise ValueError("exact prepared-worker fields required; no approval/command fields")
    if (
        request["kind"] != KIND
        or not isinstance(request["case_id"], str)
        or not isinstance(request["policy_id"], str)
        or request["case_id"] not in CASES
        or request["policy_id"] not in POLICIES
    ):
        raise ValueError("supported authored case and fixed policy required")
    if request["case_id"] == "B-fault" and request["policy_id"] != "rules-v1":
        raise ValueError("fault injection belongs only to the rules-v1 fixture")
    return preflight.assess(request["plan"])


def describe(request, request_path):
    """Return a pending descriptor, never a release capability or launched process."""
    assessment = validate_request(request)
    raw = preflight.bounded_bytes(request_path)
    if json.loads(raw) != request:
        raise ValueError("request file differs from inspected object")
    return {
        "status": "BLOCKED" if assessment["problems"] else "WORKER_PREPARED_NOT_AUTHORIZED",
        "operation": "one_authored_case_policy_30_decisions",
        "case_id": request["case_id"],
        "policy_id": request["policy_id"],
        "request_sha256": hashlib.sha256(raw).hexdigest(),
        "preflight": assessment,
        "release_allowed": False,
        "real_authorization_consumed": False,
        "study_execution_performed": False,
        "remaining": "fresh authenticated approval, real single-use ledger and trusted supervisor release",
    }


def contained_command(request_path):
    """Fixed command for future trusted supervisor, not an authorization or launcher.

    Worker output is the plan's new directory, failures retained. No shell, callback,
    module name, interpreter or arbitrary command is taken from the request.
    """
    path = Path(request_path).resolve()
    request = json.loads(preflight.bounded_bytes(path))
    report = describe(request, path)
    if report["status"] == "BLOCKED":
        raise ValueError("worker preflight blocked")
    return [
        sys.executable,
        "-X",
        "utf8",
        "-c",
        BOOTSTRAP,
        str(ROOT),
        str(path),
        report["request_sha256"],
    ]


def execute_prepared(request):
    """Contained backend. Caller authenticates/consumes approval BEFORE release.

    This function is not a human-approval authenticator and is not a CLI operation.
    Ordinary unit tests exercise it on authored fixtures, never as scientific evidence.
    """
    if validate_request(request)["status"] != "HASH_PREFLIGHT_READY_NOT_AUTHORIZATION":
        raise ValueError("worker preflight blocked after containment")
    from dc_sustainability.rule_study import cases, runner, scheduler

    case = {
        c.case_id: c
        for c in (cases.CASE_A, cases.CASE_B, cases.CASE_B_PROGRESS, cases.CASE_B_FAULT)
    }[request["case_id"]]
    bindings = runner.make_bindings(case, ROOT)
    out = Path(request["plan"]["output_directory"])
    out.mkdir(exist_ok=False)
    try:
        run, _, _ = runner.run_case(
            out,
            case,
            request["policy_id"],
            bindings=bindings,
            score_convention=scheduler.ScoreKwhConvention(),
            fault_injection=case.fault_injection if case.fault_starts else None,
        )
        result = {
            "scope": "authored_case_execution_not_independent_verification",
            "case_id": case.case_id,
            "policy_id": request["policy_id"],
            "result_sha256": run.result_sha256,
            "status": run.result.status,
            "decisions_recorded": len(run.outcomes),
            "model_calls": 0,
        }
        with (out / "worker-result.json").open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
        return 0 if run.result.status == "complete" and len(run.outcomes) == 30 else 7
    except BaseException as exc:
        with (out / "worker-failure.json").open("x", encoding="utf-8") as stream:
            json.dump(
                {"status": "failed", "exception": type(exc).__name__, "retry_allowed": False},
                stream,
            )
        raise


def environment_evidence():
    """Check the actual supported interpreter and installed locked versions offline."""
    if os.name != "nt" or sys.version_info[:2] != (3, 12):
        raise ValueError("actual Windows Python 3.12 environment required")
    lock = ROOT / "requirements/requirements-windows-py312.lock.txt"
    versions = dict(re.findall(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)", lock.read_text(), re.MULTILINE))
    if not versions:
        raise ValueError("no locked distributions found")
    for name, version in versions.items():
        if importlib.metadata.version(name) != version:
            raise ValueError(f"installed distribution differs from lock: {name}")
    return {
        "platform": "Windows",
        "python": sys.version.split()[0],
        "locked_versions_checked": len(versions),
        "scope": "interpreter/version evidence, not binary attestation",
    }


def dispatch_once(request_path, *, ledger, trusted_authorize=None):
    """Future trusted-host entry point; never called by the public CLI.

    trusted_authorize is host code that authenticates a fresh exact human decision;
    it must NOT be populated from request JSON, a URL or an import path. The host
    remains responsible for authenticating actual receiving references, not merely
    their text. Tests use fixture authorities and a mocked supervisor, never real
    approval or research dispatch. Without that authority no ID/output is touched.
    """
    if not callable(trusted_authorize):
        raise PermissionError("fresh trusted host authorization is required")
    path = Path(request_path).resolve()
    request = json.loads(preflight.bounded_bytes(path))
    command = contained_command(path)
    environment = environment_evidence()
    plan = request["plan"]
    subject = {
        "request_sha256": hashlib.sha256(preflight.bounded_bytes(path)).hexdigest(),
        "authorization_id": plan["proposed_authorization_id"],
        "code_commit": plan["code_commit"],
        "case_id": request["case_id"],
        "policy_id": request["policy_id"],
        "max_seconds": plan["proposed_limit_seconds"],
        "output_directory": plan["output_directory"],
        "operation": "one_authored_case_policy_30_decisions",
    }
    expected = dict(subject, actor="MattyAnd", decision="approved")
    # A copy prevents a host adapter accidentally mutating the subject under test.
    receipt = trusted_authorize(dict(subject))
    if receipt != expected:
        raise PermissionError("trusted authority did not approve the exact worker envelope")
    ledger = Path(ledger).absolute()
    out = Path(plan["output_directory"]).resolve()
    if (
        not ledger.is_absolute()
        or ledger.is_symlink()
        or ledger.is_junction()
        or not ledger.parent.is_dir()
        or ledger.resolve().is_relative_to(ROOT.resolve())
        or ledger.resolve().is_relative_to(out)
        or out.is_relative_to(ledger.resolve())
    ):
        raise ValueError("separate external one-use ledger required")
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
        # Recheck after irreversible ID reservation; drift preserves the used ID.
        if hashlib.sha256(preflight.bounded_bytes(path)).hexdigest() != subject["request_sha256"]:
            raise ValueError("request changed after one-use reservation")
        if contained_command(path) != command or environment_evidence() != environment:
            raise ValueError("source/input/environment changed after reservation")
        from dc_sustainability.runtime.bounded_worker import supervise

        result["supervision"] = supervise(command, subject["max_seconds"], cwd=ROOT)
        report = result["supervision"]
        result["status"] = (
            "completed"
            if report["status"] == "succeeded" and report["cleanup_verified"]
            else "failed"
        )
        if result["status"] == "completed" and not (out / "worker-result.json").is_file():
            result["status"] = "failed_missing_worker_result"
        return result
    except BaseException as exc:
        result["exception"] = type(exc).__name__
        raise
    finally:
        with entry.with_suffix(".result.json").open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inspect", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        request = json.loads(preflight.bounded_bytes(args.inspect))
        report = describe(request, args.inspect)
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Worker preparation refused: {type(exc).__name__}: {exc}\n")
    return 2 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
