"""Render the numeric sections of an E07/R05 inter-rater reliability report.

Reads an ``agreement_report.json`` written by ``compare_e05_ratings.py`` and writes
Markdown tables and mechanical kappa notes. Interpretation and limitations are added
by the report owner. Example (development ratings):

    .venv\\Scripts\\python.exe scripts/render_irr_report.py ^
        --report docs/e04/ratings/agreement/agreement_report.json ^
        --a-original ../originals/E05_Nisha_2026-10-26.json ^
        --b-original ../originals/E05_Matty_2026-10-22.json ^
        --scope "the 11 synthetic E04 development cases" --out IRR_NUMBERS.md
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dc_sustainability.evaluation import irr_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", type=Path, required=True, help="agreement_report.json")
    parser.add_argument("--a-original", required=True, help="display path of original a")
    parser.add_argument("--b-original", required=True, help="display path of original b")
    parser.add_argument("--scope", required=True, help="which cases and ratings this covers")
    parser.add_argument(
        "--title",
        default="Inter-rater reliability: faithfulness ratings (before adjudication)",
    )
    parser.add_argument("--out", type=Path, help="Markdown file to write (default: print)")
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    text = irr_report.render(
        report,
        title=args.title,
        scope=args.scope,
        originals=(args.a_original, args.b_original),
        artifact_dir=args.report.parent,
    )
    if args.out:
        args.out.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {args.out}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
