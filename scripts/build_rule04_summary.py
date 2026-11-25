"""Build RULE-04 per-stratum tables and the turnaround-vs-impact plot from a rollout output (#242).

Reads one development rollout output directory; runs no policy, checker or simulator.
Writes a new output directory and never overwrites. A stopped run is reported as partial.

    python scripts/build_rule04_summary.py --run-dir <rollout output> --out <new directory>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import rule04_summary_core as core  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=core.CASES)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} already exists; outputs are never overwritten")
    try:
        summary = core.summarize(core.load_run(args.run_dir, args.cases))
    except (OSError, ValueError, KeyError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    for path in core.write_outputs(summary, args.out):
        print(f"wrote {path}")
    print(f"coverage: {summary['coverage_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
