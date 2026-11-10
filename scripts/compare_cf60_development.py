"""Compare a separately authorized extract; never acquire CSV data or run policies."""

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

from dc_sustainability.data.carbon_source import SHA256  # noqa: E402
from dc_sustainability.data.cf60_comparison import compare  # noqa: E402
from dc_sustainability.data.materialize_development import allocation  # noqa: E402


def pinned_json(path, expected):
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError(f"input checksum mismatch: {path.name}")
    return json.loads(payload)


def checkout_revision():
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    if status.stdout.strip():
        raise ValueError("clean comparison checkout required")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def run(extract_path, authorization_path, output, states_path=None):
    """The recorded approval must be authenticated by the manager before invocation."""
    approval_bytes = authorization_path.read_bytes()
    approval = json.loads(approval_bytes)
    if (
        approval["status"] != "approved"
        or approval["source_sha256"] != SHA256
        or approval["scope"] != "cf60-development-forecast-features-only"
    ):
        raise ValueError("explicit bounded development authorization required")
    # Canonical code pins prevent an approval from silently binding another driver.
    for name in (
        "scripts/compare_cf60_development.py",
        "dc_sustainability/data/cf60_comparison.py",
        "dc_sustainability/data/cf60_broker.py",
    ):
        actual = hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if approval["code_sha256"].get(name) != actual:
            raise ValueError(f"authorized code pin mismatch: {name}")
    for key, actual_path in (
        ("extract_path", extract_path),
        ("states_path", states_path),
        ("output_path", output),
    ):
        expected_path = approval.get(key)
        if actual_path is None and expected_path is None:
            continue
        if (
            actual_path is None
            or not isinstance(expected_path, str)
            or not Path(expected_path).is_absolute()
            or actual_path.resolve() != Path(expected_path).resolve()
        ):
            raise ValueError(f"authorized path mismatch: {key}")
    # Validate the final record and destinations before consuming its single-use ID.
    for field in ("extract_sha256", "states_sha256"):
        value = approval.get(field)
        if field == "states_sha256" and states_path is None and value is None:
            continue
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError(f"invalid authorization checksum: {field}")
    if states_path is None and approval.get("states_sha256") is not None:
        raise ValueError("authorized saved states were not supplied")
    if states_path is not None and (
        not isinstance(approval.get("states_provenance_ref"), str)
        or not approval["states_provenance_ref"].strip()
    ):
        raise ValueError("saved-state provenance reference required")
    time_limit = approval.get("time_limit_s")
    if (
        type(time_limit) not in (int, float)
        or not math.isfinite(time_limit)
        or not 0 < time_limit <= 1800
    ):
        raise ValueError("time limit must be positive and at most 1800 seconds")
    revision = approval.get("code_revision")
    if (
        not isinstance(revision, str)
        or re.fullmatch(r"[0-9a-f]{40}", revision) is None
        or revision != checkout_revision()
    ):
        raise ValueError("comparison checkout differs from authorized revision")
    records = allocation()[0]["records"]
    from dc_sustainability.data.cf60_receiving import development_footprints

    allowed = sorted(
        {
            index
            for row in development_footprints(records)
            for name in ("legacy_reads", "start_cf60_reads", "end_cf60_reads")
            for index in row[name]
        }
    )
    proposed = approval.get("permitted_indices")
    if (
        not isinstance(proposed, list)
        or any(type(i) is not int for i in proposed)
        or proposed != allowed
    ):
        raise ValueError("authorization must bind the exact development index set")
    if output.exists():
        raise FileExistsError("preserve existing comparison output")
    if not output.parent.is_dir():
        raise ValueError("existing output parent required")
    if not extract_path.is_file() or (states_path is not None and not states_path.is_file()):
        raise ValueError("authorized input file is unavailable")
    authorization_id = approval["authorization_id"]
    if not isinstance(authorization_id, str) or not authorization_id.strip():
        raise ValueError("nonempty single-use authorization ID required")
    ledger = output.parent / ".cf60-consumed-authorizations"
    ledger.mkdir(exist_ok=True)
    key = hashlib.sha256(authorization_id.encode()).hexdigest()
    # Exclusive creation prevents concurrent or repeated use before reading inputs.
    with (ledger / (key + ".json")).open("x", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "authorization_id": authorization_id,
                    "authorization_sha256": hashlib.sha256(approval_bytes).hexdigest(),
                    "output_path": str(output.resolve()),
                }
            )
            + "\n"
        )
    output.mkdir(parents=False, exist_ok=False)
    try:
        extract = pinned_json(extract_path, approval["extract_sha256"])
        if extract["source_sha256"] != SHA256:
            raise ValueError("extract source mismatch")
        rows = {}
        permitted = set(approval["permitted_indices"])
        for row in extract["rows"]:
            index = row["index"]
            if type(index) is not int or index not in permitted or index in rows:
                raise ValueError("duplicate or unauthorized extract row")
            rows[index] = row["value"]
        states = []
        if states_path is not None:
            states = pinned_json(states_path, approval["states_sha256"])
        elif approval.get("states_sha256") is not None:
            raise ValueError("authorized saved states were not supplied")
        result = compare(
            records,
            rows,
            states,
            time_limit_s=approval["time_limit_s"],
            authorization="sha256:" + hashlib.sha256(approval_bytes).hexdigest(),
        )
        result["authorization_sha256"] = hashlib.sha256(approval_bytes).hexdigest()
        result["extract_sha256"] = approval["extract_sha256"]
        result["states_sha256"] = approval.get("states_sha256")
        payload = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode()
        (output / "comparison.json").write_bytes(payload)
        (output / "checksums.json").write_text(
            json.dumps({"comparison.json": hashlib.sha256(payload).hexdigest()}) + "\n",
            encoding="utf-8",
        )
        return result
    except Exception as exc:
        (output / "failure.json").write_text(
            json.dumps({"exception": type(exc).__name__, "reason": str(exc)}) + "\n",
            encoding="utf-8",
        )
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--states", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.extract, args.authorization, args.out, args.states)
    print(
        f"{result['issue_hypothesis_count']} comparisons; "
        f"{result['missing_saved_state_count']} saved states unavailable"
    )


if __name__ == "__main__":
    main()
