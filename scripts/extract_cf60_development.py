"""One-shot authorized local extraction; never downloads, simulates or calls models.

Approval JSON is linkage, not authentication. Matty must authenticate the exact
source/custody decisions before dispatch. This wrapper is not called by imports.
"""

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.data.carbon_source import SHA256  # noqa: E402
from dc_sustainability.data.cf60_extract import (  # noqa: E402
    MAX_BYTES,
    MAX_SECONDS,
    REQUIRED_ROWS,
    check_deadline,
    extract_bytes,
)
from dc_sustainability.data.cf60_receiving import development_footprints  # noqa: E402
from dc_sustainability.data.materialize_development import allocation  # noqa: E402

CODE_FILES = (
    "scripts/extract_cf60_development.py",
    "dc_sustainability/data/cf60_extract.py",
    "scripts/launch_cf60_ingest.py",
    "dc_sustainability/runtime/windows_job.py",
)


def code_pins():
    return {
        name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in CODE_FILES
    }


def revision():
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    if status.stdout.strip():
        raise ValueError("clean extractor checkout required")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def preflight(source, approval_bytes, output):
    """Validate metadata/approval without reading source contents or consuming the ID."""
    approval = json.loads(approval_bytes)
    if (
        approval.get("status") != "approved"
        or approval.get("approved_by") != "MattyAnd"
        or approval.get("scope") != "cf60-development-row-extract-only"
        or approval.get("source_sha256") != SHA256
    ):
        raise ValueError("explicit bounded source-ingest authorization required")
    for field in (
        "approval_ref",
        "source_use_ref",
        "custody_disposition_ref",
        "nonce_timing_ref",
        "executor",
        "machine",
        "storage_ref",
        "authorization_id",
    ):
        if not isinstance(approval.get(field), str) or not approval[field].strip():
            raise ValueError(f"missing authenticated input reference: {field}")
    if approval.get("nonce_relation") not in {"before_nonce", "after_nonce"}:
        raise ValueError("explicit accepted nonce timing required")
    if (
        approval.get("physical_read_scope")
        != "whole-file-bytes-all-timestamps-selected-numeric-only"
        or approval.get("maximum_bytes") != MAX_BYTES
        or approval.get("required_data_rows") != REQUIRED_ROWS
    ):
        raise ValueError("physical read scope or bounds differ")
    limit = approval.get("time_limit_s")
    if type(limit) not in (int, float) or not math.isfinite(limit) or not 0 < limit <= MAX_SECONDS:
        raise ValueError("ingest time limit must be positive and at most 120 seconds")
    pins = code_pins()
    if approval.get("code_sha256") != pins:
        raise ValueError("extractor code pin mismatch")
    if (
        not re.fullmatch(r"[0-9a-f]{40}", str(approval.get("code_revision", "")))
        or approval["code_revision"] != revision()
    ):
        raise ValueError("extractor checkout differs from authorized revision")
    for field, actual in (("source_path", source), ("output_path", output)):
        expected = approval.get(field)
        if (
            not isinstance(expected, str)
            or not Path(expected).is_absolute()
            or Path(expected).resolve() != actual.resolve()
        ):
            raise ValueError(f"authorized path mismatch: {field}")
    records = allocation()[0]["records"]
    indices = sorted(
        {
            i
            for row in development_footprints(records)
            for name in ("legacy_reads", "start_cf60_reads", "end_cf60_reads")
            for i in row[name]
        }
    )
    supplied = approval.get("permitted_indices")
    if (
        not isinstance(supplied, list)
        or any(type(i) is not int for i in supplied)
        or supplied != indices
    ):
        raise ValueError("exact development index set required")
    if output.exists():
        raise FileExistsError("preserve existing extract")
    if not output.parent.is_dir() or not source.is_file() or source.resolve() == output.resolve():
        raise ValueError("source or destination metadata unavailable")
    return approval, pins, limit


def run(source, authorization, output, *, approval_bytes=None):
    # The supervisor supplies the exact approval snapshot it validated, not a reread.
    if approval_bytes is None:
        approval_bytes = authorization.read_bytes()
    approval, pins, limit = preflight(source, approval_bytes, output)
    indices = approval["permitted_indices"]
    ledger = output.parent / ".cf60-extract-consumed-authorizations"
    ledger.mkdir(exist_ok=True)
    key = hashlib.sha256(approval["authorization_id"].encode()).hexdigest()
    with (ledger / (key + ".json")).open("x", encoding="utf-8") as handle:
        json.dump(
            {
                "authorization_id": approval["authorization_id"],
                "approval_sha256": hashlib.sha256(approval_bytes).hexdigest(),
            },
            handle,
        )
    deadline = monotonic() + limit
    try:
        check_deadline(deadline)
        with source.open("rb") as stream:
            payload = stream.read(MAX_BYTES + 1)
        check_deadline(deadline)
        result = extract_bytes(payload, indices, expected_sha256=SHA256, deadline=deadline)
        result["extractor_code_sha256"] = pins
        result["ingestion"] = {
            "code_revision": approval["code_revision"],
            "approval_sha256": hashlib.sha256(approval_bytes).hexdigest(),
            "source_bytes_read": len(payload),
            "decoded_data_rows": REQUIRED_ROWS,
            "timestamps_interpreted": REQUIRED_ROWS,
            "selected_numeric_values": len(indices),
            "unselected_numeric_values_retained": False,
            "custody_disposition_ref": approval["custody_disposition_ref"],
            "nonce_timing_ref": approval["nonce_timing_ref"],
            "nonce_relation": approval["nonce_relation"],
        }
        encoded = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode()
        check_deadline(deadline)
        with output.open("xb") as stream:
            stream.write(encoded)
        check_deadline(deadline)
        return result
    except Exception as exc:
        failure = output.with_name(output.name + ".failure.json")
        try:
            with failure.open("x", encoding="utf-8") as handle:
                json.dump(
                    {
                        "status": "failed",
                        "exception": type(exc).__name__,
                        "reason": str(exc),
                        "authorization_consumed": True,
                    },
                    handle,
                )
        except FileExistsError:
            pass
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source, args.authorization, args.out)
    print(f"Extracted {len(result['rows'])} authorized rows; no source values printed")


if __name__ == "__main__":
    main()
