"""Compute RULE-04 metric records from retained rule-study run folders (#242).

Each folder holds case.json, result.json and decisions/. Reads files only; no policy,
checker or simulator runs. The output file is created exclusively.

    python scripts/rule_study_metrics.py --label authored-dbb8e6f --out metrics.json RUN_DIR...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dc_sustainability.evaluation import rule_study_metrics as m  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("runs", type=Path, nargs="+")
    args = parser.parse_args(argv)
    report = m.metrics_report(sorted(args.runs), label=args.label)
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with open(args.out, "x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(f"wrote {args.out}: {len(report['runs'])} runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
