"""Compare two original E05 ratings files and write the agreement report and adjudication record.

Neither original is changed. Writes the agreement report, the matching record and the
adjudication record. The adjudication starts with every disagreement undecided, for the
raters to fill in jointly; check it afterwards with --check-adjudication.

    python scripts/compare_e05_ratings.py --a RATINGS_A.json --b RATINGS_B.json --out-dir DIR
    python scripts/compare_e05_ratings.py --a ... --b ... --matches MATCHES.json --out-dir DIR
    python scripts/compare_e05_ratings.py --a ... --b ... --check-adjudication FILLED.json
    python scripts/compare_e05_ratings.py --cases docs/e04/calibration/calibration_cases.json ...

MATCHES.json maps "CASE/OUTPUT" to [a ID, b ID] pairs for summary or limitation
assertions both raters agree describe the same fact, e.g. {"DEV02/X": [["S2", "S1"]]}.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.evaluation import agreement, review  # noqa: E402

CASES_FILE = ROOT / "docs" / "e04" / "development_cases.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--a", type=Path, required=True, help="first original ratings file")
    parser.add_argument("--b", type=Path, required=True, help="second original ratings file")
    parser.add_argument("--matches", type=Path, help="agreed summary/limitation ID pairs")
    parser.add_argument("--out-dir", type=Path, help="where to write the output files")
    parser.add_argument(
        "--confirmed-by", action="append", default=[], help="a rater who agreed the matching"
    )
    parser.add_argument("--check-adjudication", type=Path, help="validate a filled record")
    parser.add_argument(
        "--cases", type=Path, default=CASES_FILE, help="case file (default: development cases)"
    )
    args = parser.parse_args()

    cases = review.load_cases(json.loads(args.cases.read_text(encoding="utf-8")))
    a = agreement.load_original(args.a.read_bytes(), cases)
    b = agreement.load_original(args.b.read_bytes(), cases)
    matches = {}
    if args.matches:
        raw = json.loads(args.matches.read_text(encoding="utf-8"))
        matches = {tuple(k.split("/")): [tuple(p) for p in v] for k, v in raw.items()}
    comparison = agreement.compare(a, b, matches)

    if args.check_adjudication:
        record = json.loads(args.check_adjudication.read_text(encoding="utf-8"))
        agreement.validate_adjudication(record, comparison)
        print(f"adjudication complete: {len(record['items'])} items decided")
        return 0

    report = agreement.summary(comparison)
    print(json.dumps(report, indent=2))
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        outputs = (
            ("agreement_report.json", report),
            ("matching.json", agreement.matching_record(comparison, args.confirmed_by)),
            ("adjudication.json", agreement.adjudication_record(comparison)),
        )
        for name, data in outputs:
            path = args.out_dir / name
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
            print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
