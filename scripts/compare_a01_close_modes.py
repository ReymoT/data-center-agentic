"""Six fixed, order-balanced synthetic close pairs; no model calls or retries."""

import argparse
import json
import platform
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from diagnose_a01_lifecycle import (  # noqa: E402
    BODY,
    ROOT,
    native_observation,
    python_observation,
    request_body,
    sha,
    source_sha,
)

# Fixed before observation; never expand, replace, filter or retry based on results.
ORDERS = (
    ("original_close", "wait_for_client"),
    ("wait_for_client", "original_close"),
) * 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--native-server", required=True, type=Path)
    args = parser.parse_args()
    rows = []
    report = {
        "evidence_kind": "six_fixed_order_balanced_synthetic_close_pairs",
        "plan": {
            "orders": ORDERS,
            "pairs": 6,
            "native_observations": 12,
            "reference_captures": 1,
            "raw_client_deadline_seconds": 10,
            "serial": True,
            "retry_or_replacement": False,
        },
        "python": sys.version,
        "platform": platform.platform(),
        "model_calls": 0,
        "source_sha256_lf": source_sha(Path(__file__)),
        "observer_source_sha256_lf": source_sha(SCRIPTS / "diagnose_a01_lifecycle.py"),
        "native_source_sha256_lf": source_sha(SCRIPTS / "a01_exact_wire_control.go"),
        "native_binary_sha256": sha(args.native_server.read_bytes()),
        "provider_source_sha256_lf": source_sha(ROOT / "dc_sustainability/llm/provider.py"),
        "fixture_source_sha256_lf": source_sha(ROOT / "tests/llm/test_ollama_provider.py"),
        "body_bytes": len(BODY),
        "body_sha256": sha(BODY),
        "observations": rows,
        "completed": False,
        "limits": "Small diagnostic on one machine, not a reliability estimate or production "
        "fix. Conditions use fresh connections/processes and different ephemeral request ports. "
        "Order is balanced deterministically, not randomized. Original fixture/provider/tests, "
        "shared settings and prior failures remain unchanged.",
    }
    # Reserve first. Even an interrupted/failed run retains its completed observations.
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        try:
            payload = request_body()
            reference, wire = python_observation("original_close", "shared_provider", payload)
            report.update(
                reference_observation=reference,
                reference_wire_bytes=len(wire),
                reference_wire_sha256=sha(wire),
                reference_headers_latin1=wire.partition(b"\r\n\r\n")[0].decode("latin1")
                + "\r\n\r\n",
                request_bytes=len(payload),
                request_sha256=sha(payload),
            )
            print(json.dumps({"reference": reference}), flush=True)
            for pair, order in enumerate(ORDERS, start=1):
                for position, mode in enumerate(order, start=1):
                    row = native_observation(args.native_server, mode, payload, wire)
                    row.update(pair=pair, position=position)
                    row["complete_transport"] = row["body_matches"] and row["error"] is None
                    rows.append(row)
                    print(json.dumps(row), flush=True)
            report["completed"] = True
        except Exception as exc:
            report["execution_error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            report["completed_native_observations"] = len(rows)
            report["outcome_counts"] = {
                mode: dict(
                    Counter(
                        "complete" if row["complete_transport"] else "incomplete_or_error"
                        for row in rows
                        if row["close_mode"] == mode
                    )
                )
                for mode in ORDERS[0]
            }
            json.dump(report, handle, indent=2)
            handle.write("\n")


if __name__ == "__main__":
    main()
