"""Render the E06 study tables JSON as LaTeX tables for the report.

Reads only the JSON written by ``build_study_tables.py``; nothing is recomputed. The
output file must not exist. Captions state the split, so development tables cannot pass
as held-out findings.

    python scripts/render_study_tables.py --report study_tables.json --out tables.tex
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dc_sustainability.evaluation import table_report  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--scenario-metric",
        action="append",
        choices=sorted(table_report.METRICS),
        help="metric for a per-scenario table (repeatable; default: the four main ones)",
    )
    args = parser.parse_args(argv)
    raw = args.report.read_bytes()
    report = json.loads(raw)
    text = table_report.render(
        report,
        hashlib.sha256(raw).hexdigest(),
        args.scenario_metric or table_report.SCENARIO_METRICS,
    )
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    print(
        f"wrote {text.count('begin{table')} tables; source_sha256 {hashlib.sha256(raw).hexdigest()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
