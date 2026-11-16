"""Separately authorized, supervised legacy JSON bundle assembly; never open a CSV."""

import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dc_sustainability.data import development_bundles as build  # noqa: E402
from dc_sustainability.data import state_export as export  # noqa: E402
from dc_sustainability.data.carbon_source import SHA256  # noqa: E402
from dc_sustainability.data.held_out_custody import _private_path  # noqa: E402
from dc_sustainability.runtime.bounded_worker import supervise  # noqa: E402
from scripts.export_development_states import clean_revision, read_bounded  # noqa: E402

SCOPE = "development-legacy-bundle-assembly"


def code_pins():
    paths = sorted((ROOT / "dc_sustainability").rglob("*.py")) + [
        Path(__file__).resolve(),
        ROOT / "scripts/export_development_states.py",
    ]
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(
            p.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for p in paths
    }


def preflight(raw, output):
    a = json.loads(raw)
    if (
        a.get("status") != "approved"
        or a.get("approved_by") != "MattyAnd"
        or a.get("scope") != SCOPE
    ):
        raise ValueError("fresh explicit bundle authorization required")
    for name in (
        "approval_ref",
        "authorization_id",
        "source_use_ref",
        "full_episode_access_ref",
        "extract_provenance_ref",
        "custody_ref",
        "executor",
        "machine",
        "storage_ref",
    ):
        if not isinstance(a.get(name), str) or not a[name].strip():
            raise ValueError("authenticated scope reference missing")
    if a.get("source_sha256") != SHA256:
        raise ValueError("source identity differs")
    for name, cap in (
        ("maximum_input_bytes", export.MAX_INPUT),
        ("maximum_output_bytes", export.MAX_OUTPUT),
    ):
        if type(a.get(name)) is not int or not 0 < a[name] <= cap:
            raise ValueError("invalid byte bound")
    seconds = a.get("time_limit_s")
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 900:
        raise ValueError("invalid bundle deadline")
    if a.get("code_revision") != clean_revision() or a.get("code_sha256") != code_pins():
        raise ValueError("bundle code identity differs")
    if not Path(a.get("output_directory", "")).is_absolute():
        raise ValueError("absolute output required")
    output = _private_path(Path(output))
    if (
        output != _private_path(Path(a["output_directory"]))
        or output.exists()
        or not output.parent.is_dir()
    ):
        raise ValueError("new exact output required")
    records, commitments = export.public_cohort(ROOT)
    inputs = a.get("episodes")
    if (
        not isinstance(inputs, list)
        or len(inputs) != 40
        or {x.get("episode_id") for x in inputs} != set(commitments)
    ):
        raise ValueError("exact forty unique development inputs required")
    if a.get("permitted_indices") != build.permitted_indices(records):
        raise ValueError("exact approved extract footprint required")
    items = [{"path": a.get("extract_path"), "sha256": a.get("extract_sha256")}] + inputs
    paths, total = set(), 0
    for item in items:
        if not isinstance(item.get("path"), str):
            raise ValueError("explicit JSON input required")
        p = Path(item["path"])
        if not p.is_absolute() or p.suffix.lower() != ".json":
            raise ValueError("absolute JSON input required; no CSV fallback")
        p = _private_path(p)
        if (
            p in paths
            or p.is_relative_to(output)
            or not p.is_file()
            or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", "")))
        ):
            raise ValueError("input path/hash differs")
        if (
            item.get("episode_id")
            and item["sha256"] != commitments[item["episode_id"]]["file_sha256"]
        ):
            raise ValueError("episode file differs from fixed receipt")
        paths.add(p)
        total += p.stat().st_size
    if total > a["maximum_input_bytes"]:
        raise ValueError("aggregate input cap exceeded")
    return a, output, records, commitments, items


def work(raw, output):
    a, output, records, commitments, items = preflight(raw, output)
    approval_sha = hashlib.sha256(raw).hexdigest()
    key = hashlib.sha256(a["authorization_id"].encode()).hexdigest() + ".json"
    dispatch = json.loads(
        read_bounded(_private_path(output.parent / ".bundle-consumed" / key), 4096)
    )
    if dispatch.get("approval_sha256") != approval_sha:
        raise ValueError("dispatch reservation missing")
    ledger = _private_path(output.parent / ".bundle-worker-consumed")
    ledger.mkdir(exist_ok=True)
    export.write_artifact(ledger / key, {"approval_sha256": approval_sha})
    output.mkdir(exist_ok=False)
    deadline = monotonic() + a["time_limit_s"]
    try:
        values, hashes, consumed = [], [], 0
        for item in items:
            export.deadline_check(deadline)
            data = read_bounded(item["path"], a["maximum_input_bytes"] - consumed)
            consumed += len(data)
            digest = hashlib.sha256(data).hexdigest()
            if digest != item["sha256"]:
                raise ValueError("input checksum differs")
            values.append(json.loads(data))
            hashes.append(digest)
        episodes = {
            item["episode_id"]: value for item, value in zip(a["episodes"], values[1:], strict=True)
        }
        bundles = build.assemble(
            episodes, values[0], records=records, commitments=commitments, deadline=deadline
        )
        if a["code_revision"] != clean_revision() or a["code_sha256"] != code_pins():
            raise ValueError("code changed during assembly")
        encoded = {eid: export.payload(bundle) for eid, bundle in bundles.items()}
        manifest = {
            eid + ".json": hashlib.sha256(data).hexdigest() for eid, data in encoded.items()
        }
        provenance = {
            "kind": "new_legacy_forecast_bundles_not_original_states",
            "approval_sha256": approval_sha,
            "code_revision": a["code_revision"],
            "code_sha256": a["code_sha256"],
            "input_sha256": hashes,
            "source_sha256": a["source_sha256"],
            "bundles": manifest,
            "episode_count": 40,
            "source_use_ref": a["source_use_ref"],
            "extract_provenance_ref": a["extract_provenance_ref"],
            "full_episode_access_ref": a["full_episode_access_ref"],
            "receiving_status": "pending_independent_receiving",
            "source_csv_reads": 0,
            "model_calls": 0,
            "solver_calls": 0,
            "simulator_steps": 0,
            "scientific_acceptance": False,
        }
        if (
            sum(map(len, encoded.values())) + len(export.payload(provenance))
            > a["maximum_output_bytes"]
        ):
            raise ValueError("aggregate output cap exceeded")
        for eid, data in encoded.items():
            export.deadline_check(deadline)
            with (output / (eid + ".json")).open("xb") as handle:
                handle.write(data)
        export.write_artifact(output / "provenance.json", provenance)
        export.deadline_check(deadline)
        if a["code_revision"] != clean_revision() or a["code_sha256"] != code_pins():
            raise ValueError("code changed before completion")
    except Exception as exc:
        export.write_artifact(
            output / "failure.json", {"exception": type(exc).__name__, "no_retry": True}
        )
        raise


def launch(authorization, output):
    started = monotonic()
    raw = read_bounded(authorization, 2 * 1024 * 1024)
    a, output, _, _, _ = preflight(raw, output)
    if os.name != "nt":
        raise OSError("Windows containment required")
    receipt = _private_path(output.with_name(output.name + ".dispatch"))
    if receipt.exists():
        raise FileExistsError("preserve existing dispatch")
    approval_sha = hashlib.sha256(raw).hexdigest()
    ledger = _private_path(output.parent / ".bundle-consumed")
    ledger.mkdir(exist_ok=True)
    key = hashlib.sha256(a["authorization_id"].encode()).hexdigest() + ".json"
    export.write_artifact(ledger / key, {"approval_sha256": approval_sha})
    receipt.mkdir(exist_ok=False)
    snapshot = receipt / "authorization.json"
    with snapshot.open("xb") as handle:
        handle.write(raw)
    export.write_artifact(
        receipt / "intent.json",
        {
            "approval_sha256": approval_sha,
            "scope": SCOPE,
            "retries": 0,
            "limit_s": a["time_limit_s"],
        },
    )
    remaining = a["time_limit_s"] - (monotonic() - started)
    if remaining <= 0:
        result = {"status": "timed_out_before_dispatch", "cleanup_verified": True}
    else:
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
                approval_sha,
            ],
            remaining,
            cwd=ROOT,
        )
    result.update(approval_sha256=approval_sha, elapsed_total_s=monotonic() - started)
    if result["status"] == "succeeded":
        try:
            export.deadline_check(started + a["time_limit_s"] + 3)
            p = json.loads(read_bounded(output / "provenance.json", export.MAX_OUTPUT))
            if (
                p["approval_sha256"] != approval_sha
                or set(p["bundles"]) != {item["episode_id"] + ".json" for item in a["episodes"]}
                or p["input_sha256"]
                != [a["extract_sha256"]] + [item["sha256"] for item in a["episodes"]]
                or (output / "failure.json").exists()
            ):
                raise ValueError("incomplete output")
            for name, digest in p["bundles"].items():
                if (
                    not re.fullmatch(r"EP-[0-9a-f]{24}\.json", name)
                    or hashlib.sha256(read_bounded(output / name, export.MAX_OUTPUT)).hexdigest()
                    != digest
                ):
                    raise ValueError("output checksum differs")
                export.deadline_check(started + a["time_limit_s"] + 3)
            result["receiving_status"] = "pending_independent_receiving"
        except Exception:
            result["status"] = "output_unverified"
    export.write_artifact(receipt / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--approval-sha256", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if (
            sys.stdin.buffer.read(1) != b"G"
            or args.authorization.resolve()
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
        print(f"Bundle preparation stopped: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
