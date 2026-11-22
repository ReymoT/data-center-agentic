"""Offline hash preflight and one-use dummy dispatch; never execute the final seed.

JSON status or a comment URL cannot grant approval here. Actual research dispatch
is intentionally absent. Plans remain pending and must be refreshed after code changes.
"""

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.rehearse_rule_study_supervisor import rehearse  # noqa: E402

KIND = "rule_study_dispatch_preparation_v1"
SPEC_HASH = "9597931fcee09bc895605b65401483c9c3658da9e0bdf7c954f8669dfa8542bd"
ROLES = {"development_cases", "development_accounting"}
FIELDS = {
    "kind",
    "status",
    "code_commit",
    "code_sha256",
    "specification_sha256",
    "inputs",
    "output_directory",
    "proposed_authorization_id",
    "proposed_limit_seconds",
    "receiving_references",
}
RECEIPTS = {"rule_adapter", "verifier_freeze", "independent_accounting"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bounded_bytes(path):
    with Path(path).open("rb") as handle:
        raw = handle.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("input exceeds eight MiB reader limit")
    return raw


def snapshot():
    """Actual clean merged checkout and transitive Python/lock/spec commitments."""

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

    if git("status", "--porcelain"):
        raise ValueError("clean checkout required")
    commit = git("rev-parse", "HEAD")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "origin/main"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths = sorted((ROOT / "dc_sustainability").rglob("*.py")) + sorted(
        (ROOT / "scripts").rglob("*.py")
    )
    paths += [
        ROOT / "requirements/requirements-windows-py312.lock.txt",
        ROOT / "docs/rule_study/specification.json",
    ]
    pins = {}
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("code pin escapes repository")
        pins[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes().replace(b"\r\n", b"\n"))
    return commit, pins


def draft():
    commit, pins = snapshot()
    return {
        "kind": KIND,
        "status": "pending_explicit_approval",
        "code_commit": commit,
        "code_sha256": pins,
        "specification_sha256": SPEC_HASH,
        "inputs": {r: {"path": None, "sha256": None} for r in sorted(ROLES)},
        "output_directory": None,
        "proposed_authorization_id": None,
        "proposed_limit_seconds": None,
        "receiving_references": {r: None for r in sorted(RECEIPTS)},
    }


def assess(plan):
    """Hash/shape readiness only. Even a READY report never authorizes execution."""
    problems = []
    if not isinstance(plan, dict) or set(plan) != FIELDS:
        raise ValueError("unknown or missing preparation fields")
    if plan["kind"] != KIND or plan["status"] != "pending_explicit_approval":
        raise ValueError("only pending preparation is supported; JSON cannot approve a run")
    commit, pins = snapshot()
    if plan["code_commit"] != commit or plan["code_sha256"] != pins:
        problems.append("code commit or source/environment pins changed")
    if plan["specification_sha256"] != SPEC_HASH:
        problems.append("unsupported specification")
    inputs = plan["inputs"]
    if not isinstance(inputs, dict) or set(inputs) != ROLES:
        raise ValueError("exact development cases/accounting roles required")
    seen = set()
    for role, item in inputs.items():
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("invalid input binding")
        path, digest = item["path"], item["sha256"]
        if (
            not isinstance(path, str)
            or not Path(path).is_absolute()
            or not isinstance(digest, str)
            or not re.fullmatch("[a-f0-9]{64}", digest)
        ):
            problems.append(f"{role}: actual absolute input path and byte hash missing")
            continue
        source = Path(path)
        if source.is_symlink() or source.suffix.lower() != ".json" or source.resolve() in seen:
            problems.append(f"{role}: duplicate/symlink/non-JSON input")
            continue
        seen.add(source.resolve())
        try:
            if sha(bounded_bytes(source)) != digest:
                problems.append(f"{role}: input hash mismatch")
        except OSError:
            problems.append(f"{role}: input unavailable")
    out = plan["output_directory"]
    if not isinstance(out, str) or not Path(out).is_absolute():
        problems.append("new absolute study output directory missing")
    else:
        path = Path(out)
        if (
            path.exists()
            or path.is_symlink()
            or not path.parent.is_dir()
            or path.resolve().is_relative_to(ROOT.resolve())
        ):
            problems.append("output must be absent with an existing parent outside the checkout")
    ident = plan["proposed_authorization_id"]
    if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", ident):
        problems.append("proposed single-use authorization ID missing/invalid")
    seconds = plan["proposed_limit_seconds"]
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 900:
        problems.append("proposed time bound missing/invalid for existing supervisor")
    refs = plan["receiving_references"]
    if not isinstance(refs, dict) or set(refs) != RECEIPTS:
        raise ValueError("exact receiving-reference roles required")
    for role, ref in refs.items():
        if not isinstance(ref, str) or not ref.strip():
            problems.append(f"{role}: actual receiving/freeze reference missing")
    return {
        "status": "BLOCKED" if problems else "HASH_PREFLIGHT_READY_NOT_AUTHORIZATION",
        "problems": problems,
        "research_execution_authorized": False,
        "scope": "byte/hash preflight only; references, input semantics and human approval are not authenticated",
    }


def rehearsal(plan, *, rehearsal_id, ledger, out, mode="success"):
    """Consume only a dummy rehearsal ID; never consume a real authorization ID."""
    if not isinstance(rehearsal_id, str) or not re.fullmatch(
        r"dummy-[A-Za-z0-9._-]{1,100}", rehearsal_id
    ):
        raise ValueError("dummy-prefixed rehearsal ID required")
    if mode not in ("success", "failure", "timeout", "descendant"):
        raise ValueError("built-in dummy mode required")
    if assess(plan)["status"] != "HASH_PREFLIGHT_READY_NOT_AUTHORIZATION":
        raise ValueError("preflight blocked; no worker released")
    if Path(out).is_symlink() or Path(ledger).is_symlink():
        raise ValueError("symlink rehearsal paths refused")
    out, ledger = Path(out).resolve(), Path(ledger).resolve()
    study = Path(plan["output_directory"]).resolve()
    if (
        ledger.is_relative_to(study)
        or ledger == out
        or out.is_relative_to(ledger)
        or ledger.is_relative_to(out)
    ):
        raise ValueError(
            "rehearsal ledger/output must be separate from study output and each other"
        )
    if out.exists() or not out.parent.is_dir() or out == study:
        raise ValueError("new rehearsal output separate from proposed study output required")
    # An exclusive ledger entry survives worker failure: no silent retry of the same ID.
    ledger.mkdir(exist_ok=True)
    entry = ledger / (sha(rehearsal_id.encode()) + ".json")
    with entry.open("x", encoding="utf-8") as handle:
        json.dump(
            {
                "scope": "dummy_rehearsal_only",
                "id": rehearsal_id,
                "plan_sha256": sha(json.dumps(plan, sort_keys=True).encode()),
            },
            handle,
        )
    if assess(plan)["status"] != "HASH_PREFLIGHT_READY_NOT_AUTHORIZATION":
        raise ValueError("preflight changed after ID consumption; stop without retry")
    report = rehearse(mode, out, 0.7 if mode == "timeout" else 4)
    return {
        "rehearsal": report,
        "research_execution_authorized": False,
        "real_authorization_consumed": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--draft", action="store_true")
    group.add_argument("--assess", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    # This CLI cannot dispatch even the dummy worker, let alone research code.
    try:
        result = draft() if args.draft else assess(json.loads(bounded_bytes(args.assess)))
        with args.out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, allow_nan=False)
            handle.write("\n")
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"Preparation refused: {type(exc).__name__}: {exc}\n")
    return 2 if result.get("status") == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
