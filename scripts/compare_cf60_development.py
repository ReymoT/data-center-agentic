"""Compare a separately authorized extract; never acquire CSV data or run policies."""

import argparse
import hashlib
import json
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
    manifest, _ = allocation()
    # Never overwrite a previous attempt. Failure records retain the stop reason.
    output.mkdir(parents=False, exist_ok=False)
    try:
        result = compare(
            manifest["records"],
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
