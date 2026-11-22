"""RULE-03: independently check an evaluator-only accounting sidecar against its case set.

Reads the policy-visible case set (--cases) and the generator's accounting sidecar
(--accounting) and checks binding, coverage, identity hashes, weight domain, visibility
and hidden-profile acceptance. See dc_sustainability/evaluation/rule_study_accounting.py.
Offline: no generator, scheduler, network or model is run.

Exit codes: 0 PASS, 1 FAIL, 2 INCOMPLETE. The output file is created exclusively.

Example:
    python scripts/check_rule_study_accounting.py --cases dev.json \
        --accounting dev.accounting.json --out accounting_check.json
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.evaluation import rule_study_accounting as ra  # noqa: E402
from dc_sustainability.evaluation import rule_study_cases as rc  # noqa: E402
from dc_sustainability.evaluation import rule_study_verifier as v  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--accounting", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="new JSON report path")
    args = parser.parse_args(argv)
    if args.out is not None and args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    try:
        report = ra.check_accounting(rc.load_case_set(args.cases), ra.load_sidecar(args.accounting))
    except (ValueError, OSError, TypeError, RecursionError) as exc:
        report = {
            "record_kind": ra.RECORD_KIND,
            "overall": "FAIL",
            "cases": {},
            "checks": {},
            "input_error": type(exc).__name__,
            "reason": str(exc),
            "study_acceptance": "NOT_ESTABLISHED",
            "scope": "input refused; no pair checks performed",
        }
    summary = {
        "overall": report["overall"],
        "scope": report["scope"],
        "study_acceptance": report["study_acceptance"],
        "binding_authentication": report.get("binding_authentication", "NOT_RUN"),
        "input_error": report.get("input_error"),
        "cases": report["cases"],
        "checks": {k: c["status"] for k, c in report["checks"].items()},
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
