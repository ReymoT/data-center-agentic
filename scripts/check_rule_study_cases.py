"""RULE-03: independently check synthetic case sets (labels, strata, diversity, overlap).

Each --set FILE is a JSON object {"set_id": ..., "cases": [...]} in the shape described in
dc_sustainability/evaluation/rule_study_cases.py. Sets are checked individually, then
against each other and against the authored specification examples. Offline: no
generator, scheduler, network or model is run.

Exit codes: 0 PASS, 1 FAIL, 2 INCOMPLETE. The output file is created exclusively.

Example:
    python scripts/check_rule_study_cases.py --set final.json --set development.json \\
        --expected final=40 --expected development=none --out case_check.json
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.evaluation import rule_study_cases as rc  # noqa: E402
from dc_sustainability.evaluation import rule_study_verifier as v  # noqa: E402

SPEC_PATH = ROOT / "docs" / "rule_study" / "specification.json"


def _expected(items: list[str]) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    for item in items:
        name, sep, value = item.partition("=")
        if not sep or not name:
            raise SystemExit("--expected must look like set_id=40 or set_id=none")
        if name in out:
            raise SystemExit("duplicate --expected set_id")
        if value == "none":
            out[name] = None
        elif value.isdigit() and 1 <= int(value) <= 40:
            out[name] = int(value)
        else:
            raise SystemExit(f"--expected {item!r}: count must be an integer or none")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", action="append", type=Path, required=True, dest="sets")
    parser.add_argument(
        "--expected",
        action="append",
        default=[],
        help="per-stratum count per set, e.g. final=40 (default 40); none skips the count",
    )
    parser.add_argument("--out", type=Path, help="new JSON report path")
    parser.add_argument("--max-states", type=int, default=10_000)
    parser.add_argument("--max-transitions", type=int, default=50_000)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    args = parser.parse_args(argv)
    if args.out is not None and args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    expected = _expected(args.expected)
    try:
        budget = v.Budget(
            max_states=args.max_states,
            max_transitions=args.max_transitions,
            max_seconds=args.max_seconds,
        )
        rc._validate_budget(budget)
        if len(args.sets) > rc.MAX_SETS:
            raise ValueError("supply at most two sets")
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        sets = [rc.load_case_set(p) for p in args.sets]
        report = rc.check_case_sets(
            sets, spec=spec, expected_per_stratum=expected, graph_budget=budget
        )
    except (ValueError, OSError, TypeError, RecursionError) as exc:
        report = {
            "record_kind": rc.RECORD_KIND,
            "overall": "FAIL",
            "sets": [],
            "checks": {"no_full_case_overlap": {"status": "NOT_RUN"}},
            "input_error": type(exc).__name__,
            "reason": str(exc),
            "study_acceptance": "NOT_ESTABLISHED",
        }
    summary = {
        "overall": report["overall"],
        "study_acceptance": report["study_acceptance"],
        "scope": report.get("scope", "input refused; no case checks performed"),
        "input_error": report.get("input_error"),
        "unseen_isolation": report.get("unseen_isolation", "NOT_RUN"),
        "overlap_check": report["checks"]["no_full_case_overlap"]["status"],
        "sets": {
            s["set_id"]: {
                "checks": {k: c["status"] for k, c in s["checks"].items()},
                "strata": s["strata"],
            }
            for s in report["sets"]
        },
    }
    print(json.dumps(summary, indent=2))
    if args.out is not None:
        text = json.dumps(
            report, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
        try:
            with args.out.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(text + "\n")
        except OSError as exc:
            parser.exit(2, f"Report output refused: {type(exc).__name__}\n")
        print(f"wrote {args.out} sha256={v.canonical_sha256(report)}")
    return {"PASS": 0, "FAIL": 1}.get(report["overall"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
