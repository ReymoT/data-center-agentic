"""Single-use supervised development state export. Pending approvals never read inputs.

No source acquisition, model/solver/training path or automatic dispatch on import.
Authenticate referenced human/source/custody decisions separately before use.
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dc_sustainability import schemas as s  # noqa: E402
from dc_sustainability.data import state_export as export  # noqa: E402
from dc_sustainability.data.carbon_source import SHA256  # noqa: E402
from dc_sustainability.data.held_out_custody import _private_path  # noqa: E402
from dc_sustainability.runtime.bounded_worker import supervise  # noqa: E402


def read_bounded(path, maximum):
    with Path(path).open("rb") as handle:
        if os.fstat(handle.fileno()).st_size > maximum:
            raise ValueError("bounded file size exceeded")
        raw = handle.read(maximum)
        if os.fstat(handle.fileno()).st_size > maximum:
            raise ValueError("bounded file size exceeded")
    return raw


def code_pins():
    paths = sorted((ROOT / "dc_sustainability").rglob("*.py")) + [Path(__file__).resolve()]
    return {
        str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
            p.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for p in paths
    }


def clean_revision():
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise ValueError("clean export checkout required")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def preflight(raw, output):
    approval = json.loads(raw)
    if (
        approval.get("status") != "approved"
        or approval.get("approved_by") != "MattyAnd"
        or approval.get("scope") != "cf60-development-state-export"
    ):
        raise ValueError("fresh explicit state-export authorization required")
    if (
        approval.get("route") not in {"recover", "capture"}
        or approval.get("source_sha256") != SHA256
    ):
        raise ValueError("invalid export scope/source")
    for name in (
        "approval_ref",
        "source_use_ref",
        "custody_ref",
        "executor",
        "machine",
        "storage_ref",
        "trajectory_agreement_ref",
        "provenance_ref",
        "authorization_id",
    ):
        if not isinstance(approval.get(name), str) or not approval[name].strip():
            raise ValueError("missing authenticated authorization reference")
    for name, ceiling in (
        ("maximum_input_bytes", export.MAX_INPUT),
        ("maximum_output_bytes", export.MAX_OUTPUT),
    ):
        if type(approval.get(name)) is not int or not 0 < approval[name] <= ceiling:
            raise ValueError("invalid byte bounds")
    seconds = approval.get("time_limit_s")
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 900:
        raise ValueError("invalid export time bound")
    if (
        approval.get("code_revision") != clean_revision()
        or approval.get("code_sha256") != code_pins()
    ):
        raise ValueError("export code identity mismatch")
    output = _private_path(Path(output))
    if (
        not Path(approval.get("output_directory", "")).is_absolute()
        or output != _private_path(Path(approval["output_directory"]))
        or output.exists()
        or not output.parent.is_dir()
    ):
        raise ValueError("new exact private output required")
    rows, bindings = export.public_cohort(ROOT)
    if approval.get("development_episode_ids") != sorted(bindings):
        raise ValueError("exact fixed 40-episode allowlist required")
    if approval.get("route") == "capture" and approval.get("trajectory") != export.TRAJECTORY:
        raise ValueError("explicit controller refusal/drain trajectory required")
    inputs = approval.get("inputs")
    maximum = 40  # combined episode+forecast bundles; never a hidden CSV fallback
    if (
        not isinstance(inputs, list)
        or not 0 < len(inputs) <= maximum
        or (approval["route"] == "capture" and len(inputs) != 40)
    ):
        raise ValueError("invalid explicit input count")
    seen = set()
    for item in inputs:
        path = Path(item["path"])
        if not path.is_absolute() or path.suffix.lower() != ".json":
            raise ValueError("explicit private JSON inputs required")
        resolved = _private_path(path)
        if (
            resolved in seen
            or resolved.is_relative_to(output)
            or not resolved.is_file()
            or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", "")))
        ):
            raise ValueError("invalid input path/hash binding")
        seen.add(resolved)
    if approval["route"] == "recover":
        hashes = approval.get("original_state_hashes")
        if not isinstance(hashes, dict) or len(hashes) > 1200:
            raise ValueError("authenticated original-state commitments required")
        for key, value in hashes.items():
            ep, _, slot = key.rpartition("@")
            if (
                ep not in bindings
                or slot not in {str(i) for i in range(30)}
                or not re.fullmatch(r"[0-9a-f]{64}", str(value))
            ):
                raise ValueError("invalid original-state commitment")
    return approval, output, rows, bindings


def check_tree(output, maximum, deadline):
    export.deadline_check(deadline)
    if sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) > maximum:
        raise ValueError("private output cap exceeded")


def work(raw, output):
    approval, output, rows, bindings = preflight(raw, output)
    key = hashlib.sha256(approval["authorization_id"].encode()).hexdigest()
    dispatch = json.loads(
        read_bounded(
            output.parent / ".state-export-consumed-authorizations" / (key + ".json"), 4096
        )
    )
    if dispatch.get("approval_sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("authenticated dispatch reservation missing")
    worker_ledger = output.parent / ".state-export-worker-consumed-authorizations"
    worker_ledger.mkdir(exist_ok=True)
    export.write_artifact(
        worker_ledger / (key + ".json"),
        {"approval_sha256": hashlib.sha256(raw).hexdigest(), "single_use": True},
    )
    output.mkdir(exist_ok=False)
    deadline = monotonic() + approval["time_limit_s"]
    approval_hash = hashlib.sha256(raw).hexdigest()
    entries, consumed, input_hashes, seen = [], 0, {}, set()
    try:
        for item in approval["inputs"]:
            export.deadline_check(deadline)
            data = read_bounded(Path(item["path"]), approval["maximum_input_bytes"] - consumed)
            consumed += len(data)
            h = hashlib.sha256(data).hexdigest()
            if h != item["sha256"]:
                raise ValueError("approved input checksum mismatch")
            input_hashes[str(len(input_hashes))] = h
            value = json.loads(data)
            if approval["route"] == "recover":
                if not isinstance(value, list) or len(entries) + len(value) > 1200:
                    raise ValueError("invalid original-state file")
                entries.extend(value)
            else:
                eid = value["episode"]["episode_id"]
                if eid not in bindings or eid in seen:
                    raise ValueError("unexpected development bundle")
                seen.add(eid)
                row = next(r for r in rows if r["episode_id"] == eid)
                ep, forecasts = export.decode_bundle(value, bindings[eid], row)
                entries.extend(
                    export.capture_episode(
                        ep,
                        forecasts,
                        output / ("traces-" + s.sha256_hex(eid)[:16]),
                        approval_hash,
                        deadline=deadline,
                    )
                )
            check_tree(output, approval["maximum_output_bytes"], deadline)
        if approval["route"] == "recover":
            entries = export.validate_entries(
                entries, bindings, approval["original_state_hashes"], deadline=deadline
            )
        elif len(entries) != 1200 or seen != set(bindings):
            raise ValueError("capture coverage incomplete")
        # Deterministic order follows the fixed public allocation, not a new selection.
        rank = {r["episode_id"]: i for i, r in enumerate(rows)}
        entries.sort(key=lambda e: (rank[e["state"]["episode_id"]], e["state"]["current_slot"]))
        origins = {
            r["episode_id"]: datetime.fromisoformat(r["window"]["proposed_start_utc"]) for r in rows
        }
        for entry in entries:
            state = s.VisibleState.from_jsonable(entry["state"])
            issue = origins[state.episode_id] + timedelta(hours=state.current_slot)
            if any(f.issued_at_utc > issue for f in state.carbon_facts):
                raise ValueError("recovered forecast has future issue time")
        if code_pins() != approval["code_sha256"] or clean_revision() != approval["code_revision"]:
            raise ValueError("export code changed during execution")
        digest = export.write_artifact(
            output / "states.json", entries, maximum=approval["maximum_output_bytes"]
        )
        provenance = {
            "kind": "recovered_original"
            if approval["route"] == "recover"
            else "new_diagnostic_not_P04_original",
            "trajectory": approval.get("trajectory"),
            "original_provenance_ref": approval["provenance_ref"],
            "approval_sha256": approval_hash,
            "code_revision": approval["code_revision"],
            "code_sha256": approval["code_sha256"],
            "input_sha256": input_hashes,
            "states_sha256": digest,
            "coverage": len(entries),
            "missing": 1200 - len(entries),
            "receiving_status": "pending_independent_receiving",
            "model_calls": 0,
            "solver_calls": 0,
            "source_csv_reads": 0,
            "scientific_compatibility": False,
        }
        export.write_artifact(output / "provenance.json", provenance)
        check_tree(output, approval["maximum_output_bytes"], deadline)
    except Exception as exc:
        export.write_artifact(
            output / "failure.json", {"exception": type(exc).__name__, "no_retry": True}
        )
        raise


def launch(authorization, output):
    started = monotonic()
    raw = read_bounded(authorization, 2 * 1024 * 1024)
    approval, output, _, _ = preflight(raw, output)
    if os.name != "nt":
        raise OSError("Windows process containment required")
    if output.with_name(output.name + ".dispatch").exists():
        raise FileExistsError("preserve existing dispatch receipt")
    ledger = output.parent / ".state-export-consumed-authorizations"
    ledger.mkdir(exist_ok=True)
    approval_hash = hashlib.sha256(raw).hexdigest()
    export.write_artifact(
        ledger / (hashlib.sha256(approval["authorization_id"].encode()).hexdigest() + ".json"),
        {"approval_sha256": approval_hash, "single_use": True},
    )
    receipt = output.with_name(output.name + ".dispatch")
    receipt.mkdir(exist_ok=False)
    snapshot = receipt / "authorization.json"
    with snapshot.open("xb") as handle:
        handle.write(raw)
    export.write_artifact(
        receipt / "intent.json",
        {
            "approval_sha256": approval_hash,
            "scope": approval["scope"],
            "route": approval["route"],
            "limit_s": approval["time_limit_s"],
            "retries": 0,
        },
    )
    if monotonic() - started >= approval["time_limit_s"]:
        result = {
            "status": "timed_out_before_dispatch",
            "cleanup_verified": True,
            "released": False,
            "approval_sha256": approval_hash,
        }
        export.write_artifact(receipt / "result.json", result)
        return result
    result = supervise(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--authorization",
            str(snapshot),
            "--out",
            str(output),
            "--approval-sha256",
            approval_hash,
        ],
        max(0.001, approval["time_limit_s"] - (monotonic() - started)),
        cwd=ROOT,
    )
    result["approval_sha256"] = approval_hash
    result["elapsed_total_s"] = monotonic() - started
    if result["status"] == "succeeded":
        if (
            not (output / "states.json").is_file()
            or not (output / "provenance.json").is_file()
            or (output / "failure.json").exists()
        ):
            result["status"] = "output_unverified"
        else:
            result["states_sha256"] = hashlib.sha256(
                read_bounded(output / "states.json", export.MAX_OUTPUT)
            ).hexdigest()
    export.write_artifact(receipt / "result.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--approval-sha256", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        if sys.stdin.buffer.read(1) != b"G":
            return 2
        if (
            args.authorization.resolve()
            != args.out.with_name(args.out.name + ".dispatch").resolve() / "authorization.json"
        ):
            return 2
        raw = read_bounded(args.authorization, 2 * 1024 * 1024)
        if hashlib.sha256(raw).hexdigest() != args.approval_sha256:
            return 2
        work(raw, args.out)
        return 0
    result = launch(args.authorization, args.out)
    print(result["status"])
    return 0 if result["status"] == "succeeded" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"State export stopped: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
