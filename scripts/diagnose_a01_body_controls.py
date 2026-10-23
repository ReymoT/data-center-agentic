"""Fixed synthetic body-content controls; never Ollama, inference or a retry policy."""

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import diagnose_a01_cross_clients as controls  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    original = controls.BODY
    bodies = (
        ("original_nested_object", original),
        ("same_length_ascii", b"a" * len(original)),
        ("same_length_shallow_json", b'{"x":0}' + b" " * (len(original) - 7)),
    )
    # Reserve before any experiment; never erase an earlier outcome.
    with args.out.open("x", encoding="utf-8") as handle:
        rows = []
        try:
            for label, body in bodies:
                controls.BODY = body  # This module's owned synthetic server only.
                for client in ("raw_socket", "curl"):
                    row = controls.observe(client, False)
                    row.update(
                        body_kind=label,
                        body_bytes=len(body),
                        body_sha256=hashlib.sha256(body).hexdigest(),
                    )
                    rows.append(row)
                    print(json.dumps(row), flush=True)
        finally:
            controls.BODY = original
            json.dump(
                {
                    "evidence_kind": "fixed_same_length_content_controls_not_inference",
                    "python": sys.version,
                    "platform": platform.platform(),
                    "model_calls": 0,
                    "one_observation_per_condition": True,
                    "same_process_python_server": True,
                    "client_deadline_seconds": 10,
                    "production_transport_changed": False,
                    "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "control_source_sha256": hashlib.sha256(
                        Path(controls.__file__).read_bytes()
                    ).hexdigest(),
                    "observations": rows,
                    "limits": "Single observations cannot establish reliability or root cause; "
                    "synthetic content variants are not valid model responses.",
                },
                handle,
                indent=2,
            )
            handle.write("\n")


if __name__ == "__main__":
    main()
