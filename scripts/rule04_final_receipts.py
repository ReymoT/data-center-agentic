"""Final host/receipt hardening. No policy, RNG, oracle or release CLI.

The canonical trusted host remains the authority. These guards detect accidental
direct calls and incomplete/tampered artifacts; they are not a sandbox against a
person who can rewrite Python and the host's ledger.
"""

import hashlib
import json
import os
import re
import stat
from time import monotonic

from scripts import prepare_rule_study_rollout as w


def digest(value):
    return w.pf.sha(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    )


def is_digest(value):
    return isinstance(value, str) and re.fullmatch("[a-f0-9]{64}", value) is not None


def slot_path(root, phase, stage):
    if (phase, stage) not in (("generate", None), ("evaluate", 0), ("evaluate", 1)):
        raise ValueError("fixed final phase/stage slot required")
    return root.parent / "RuleStudy_Run_Ledger" / f"rule04-final-{phase}-{stage}.slot.json"


def worker_authority(root, request):
    """Match release-bound request to an active exclusive host reservation."""
    original = os.environ.get("RULE04_AUTHENTICATED_REQUEST_SHA256")
    worker = os.environ.get("RULE04_WORKER_REQUEST_SHA256")
    if not is_digest(original) or not is_digest(worker):
        raise PermissionError("authenticated contained worker release required")
    ledger = root.parent / "RuleStudy_Run_Ledger"
    ident = request["plan"]["proposed_authorization_id"]
    entry = ledger / (w.pf.sha(ident.encode()) + ".json")
    slot = slot_path(root, request["phase"], request["stage"])
    if entry.with_suffix(".result.json").exists() or slot.with_suffix(".result.json").exists():
        raise PermissionError("completed/failed release cannot execute again")
    try:
        record, reserved = w.read_json(entry), w.read_json(slot)
    except (OSError, ValueError) as exc:
        raise PermissionError("active canonical host reservation required") from exc
    expected = record.get("receipt", {})
    if (
        expected.get("actor") != "MattyAnd"
        or expected.get("decision") != "approved"
        or expected.get("protocol_freeze_authenticated") is not True
        or expected.get("request_sha256") != original
        or expected.get("authorization_id") != ident
        or expected.get("phase") != request["phase"]
        or expected.get("stage") != request["stage"]
        or expected.get("code_commit") != request["plan"]["code_commit"]
        or expected.get("limits") != request["limits"]
        or expected.get("freeze_reference") != request["freeze_reference"]
        or expected.get("output_directory") != request["plan"]["output_directory"]
        or record.get("canonical_request_sha256") != digest(request)
        or reserved.get("request_sha256") != original
        or reserved.get("authorization_id") != ident
        or reserved.get("canonical_request_sha256") != digest(request)
        or (
            request["phase"] == "evaluate"
            and expected.get("generation_and_isolation_receiving_authenticated") is not True
        )
        or (request["stage"] == 1 and expected.get("parent_stage_authenticated") is not True)
    ):
        raise PermissionError("worker request differs from authenticated host release")
    return original


def inventory(directory, *, deadline=None):
    """Exact bounded raw-byte tree inventory; excludes only its two root wrappers."""
    directory = w.safe_path(directory)
    if not directory.is_dir():
        raise ValueError("actual stage output directory required")
    files, size = {}, 0
    for p in sorted(directory.rglob("*")):
        if deadline is not None and monotonic() >= deadline:
            raise TimeoutError("stage publication inventory deadline")
        info = p.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("linked stage evidence refused")
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("nonregular stage evidence refused")
        name = p.relative_to(directory).as_posix()
        if name in ("stage-receipt.json", "stage-manifest.json"):
            continue
        size += info.st_size
        if len(files) >= 100000 or size > 256 * 1024 * 1024:
            raise ValueError("stage evidence inventory bound exceeded")
        h = hashlib.sha256()
        with p.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                if deadline is not None and monotonic() >= deadline:
                    raise TimeoutError("stage publication inventory deadline")
                h.update(chunk)
        files[name] = dict(sha256=h.hexdigest(), bytes=info.st_size)
    return dict(kind="rule04_stage_output_inventory_v1", files=files)


def verify_stage_tree(receipt_path, report, *, verify_files=True, deadline=None):
    directory = w.safe_path(receipt_path).parent
    item = report.get("output_inventory")
    if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
        raise ValueError("stage output inventory binding required")
    if item["path"] != "stage-manifest.json" or not is_digest(item["sha256"]):
        raise ValueError("fixed stage inventory path/hash required")
    raw = w.pf.bounded_bytes(directory / item["path"])
    if w.pf.sha(raw) != item["sha256"]:
        raise ValueError("stage output manifest changed")
    manifest = w.decode_json(raw)
    if verify_files and inventory(directory, deadline=deadline) != manifest:
        raise ValueError("stage output tree changed")
    report_hash = report.get("rollout_report_sha256")
    if (
        not is_digest(report_hash)
        or manifest.get("files", {}).get("rollout-report.json", {}).get("sha256") != report_hash
    ):
        raise ValueError("original rollout report binding missing")
    if verify_files:
        saved = w.read_json(directory / "rollout-report.json")
        if report.get("pair_supervision") != saved.get("supervision"):
            raise ValueError("per-pair supervision was lost or changed")
        for key in (
            "strata",
            "selected_pairs",
            "runs",
            "charged_steps",
            "authenticated_request_sha256",
        ):
            if report.get(key) != saved.get(key):
                raise ValueError("stage differs from inventoried rollout report")
        for row in report["pair_supervision"]:
            if (
                row.get("supervision", {}).get("status") != "succeeded"
                or row.get("supervision", {}).get("cleanup_verified") is not True
            ):
                raise ValueError("pair cleanup or execution failed")
        supervised = [
            (row.get("case_id"), row.get("policy_id")) for row in report["pair_supervision"]
        ]
        expected = [tuple(p) for p in report["selected_pairs"]]
        if supervised != expected:
            raise ValueError("per-pair supervision coverage differs")
        metrics = {
            (m["case_id"], m["policy_id"]): m for group in report["strata"].values() for m in group
        }
        used = dict(states=0, transitions=0)
        for case_id, policy in expected:
            if deadline is not None and monotonic() >= deadline:
                raise TimeoutError("stage pair-evidence validation deadline")
            pair = w.read_json(directory / f"{case_id}-{policy}" / "pair-result.json")
            task_raw = w.pf.bounded_bytes(directory / f"request-{case_id}-{policy}.json")
            row = metrics[(case_id, policy)]
            if (
                pair.get("status") != "PASS"
                or pair.get("case_id") != case_id
                or pair.get("policy_id") != policy
                or pair.get("authenticated_request_sha256")
                != report["authenticated_request_sha256"]
                or pair.get("pair_request_sha256") != w.pf.sha(task_raw)
                or digest(w.decode_json(task_raw)) != report.get("canonical_request_sha256")
                or pair.get("replay", {}).get("overall") != "PASS"
                or dict(pair.get("metric", {}), stratum=row["stratum"]) != row
            ):
                raise ValueError("inventoried pair evidence/request/metric differs")
            for key in used:
                value = pair.get("budget", {}).get(key + "_used")
                if type(value) is not int or not 0 <= value <= 10800:
                    raise ValueError("inventoried pair counter invalid")
                used[key] += value
        if used != report["charged_steps"]:
            raise ValueError("inventoried pair counters differ")
    return directory


def authenticate_completed(root, path, report, phase, stage):
    """Require the receipt actually published by this canonical host result."""
    ident = report.get("authorization_id")
    if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", ident):
        raise ValueError("receipt authorization ID required")
    ledger = root.parent / "RuleStudy_Run_Ledger"
    entry = ledger / (w.pf.sha(ident.encode()) + ".json")
    record = w.read_json(entry)
    result = w.read_json(entry.with_suffix(".result.json"))
    slot = w.read_json(slot_path(root, phase, stage))
    slot_result = w.read_json(slot_path(root, phase, stage).with_suffix(".result.json"))
    authority = record.get("receipt", {})
    if (
        authority.get("actor") != "MattyAnd"
        or authority.get("decision") != "approved"
        or authority.get("protocol_freeze_authenticated") is not True
        or authority.get("phase") != phase
        or authority.get("stage") != stage
        or authority.get("authorization_id") != ident
        or authority.get("request_sha256") != report.get("authenticated_request_sha256")
        or not is_digest(report.get("authenticated_request_sha256"))
        or authority.get("freeze_reference") != report.get("freeze_reference")
        or authority.get("limits") != report.get("limits")
        or authority.get("code_commit") != report.get("code_commit")
        or (
            phase == "evaluate"
            and authority.get("generation_and_isolation_receiving_authenticated") is not True
        )
        or (stage == 1 and authority.get("parent_stage_authenticated") is not True)
        or record.get("canonical_request_sha256") != report.get("canonical_request_sha256")
        or w.safe_path(path)
        != w.safe_path(authority["output_directory"])
        / ("generation-receipt.json" if phase == "generate" else "stage-receipt.json")
        or result.get("status") != "succeeded"
        or result.get("cleanup_verified") is not True
        or result.get("published_receipt_sha256") != w.pf.sha(w.pf.bounded_bytes(path))
        or slot.get("authorization_id") != ident
        or slot.get("request_sha256") != report.get("authenticated_request_sha256")
        or slot_result != result
    ):
        raise ValueError("actual complete canonical host receipt required")
