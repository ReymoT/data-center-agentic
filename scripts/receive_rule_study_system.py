"""RULE-03: independently receive and verify the current RULE-02 implementation.

Without --execute this only prints the exact plan (independent code pin, domains, run
counts); nothing is run. With --execute it runs the actual common runner once per case and
policy into a NEW --out directory, checks every binding and raw artifact against the
independent pin and replays the records with the merged trace reader. Execute only for an
approved bounded run on a clean, pinned checkout.

Exit codes: 0 PASS (or plan printed), 1 FAIL, 2 INCOMPLETE. --report is created exclusively.

Examples:
    python scripts/receive_rule_study_system.py --domain primary --domain authored
    python scripts/receive_rule_study_system.py --domain primary --domain authored \
        --policy rules-v1 --execute --out receiving_runs --report receiving.json
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.evaluation import rule_study_receiving as rv  # noqa: E402
from dc_sustainability.evaluation import rule_study_verifier as v  # noqa: E402

SPEC_PATH = ROOT / "docs" / "rule_study" / "specification.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--domain", action="append", choices=rv.DOMAINS, required=True)
    parser.add_argument("--policy", action="append", choices=rv.POLICIES)
    parser.add_argument("--execute", action="store_true", help="actually run the runner")
    parser.add_argument("--out", type=Path, help="new directory for runner output")
    parser.add_argument("--report", type=Path, help="new JSON report path")
    args = parser.parse_args(argv)
    policies = args.policy or ["rules-v1"]
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if args.report is not None and args.report.exists():
        raise SystemExit(f"refusing to overwrite {args.report}")
    if not args.execute:
        plan = rv.plan_receiving(args.domain, policies, ROOT, spec)
        print(json.dumps(plan, indent=2))
        return 0
    if args.out is None:
        raise SystemExit("--execute needs a new --out directory")
    if args.out.exists():
        raise SystemExit(f"refusing to reuse {args.out}")
    report = rv.run_receiving(args.domain, policies, args.out, ROOT, spec)
    summary = {
        "overall": report["overall"],
        "pin": {k: report["pin"][k] for k in ("code_commit", "clean_tree", "commit_source")},
        "domains": {
            name: {
                "overall": s["overall"],
                "runs_completed": s["runs_completed"],
                "run_errors": len(s["run_errors"]),
                "binding_check": s["binding_check"]["status"],
                "properties": s["property_statuses"],
            }
            for name, s in report["domains"].items()
        },
    }
    print(json.dumps(summary, indent=2))
    if args.report is not None:
        text = json.dumps(
            report, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
        with args.report.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text + "\n")
        print(f"wrote {args.report} sha256={v.canonical_sha256(report)}")
    return {"PASS": 0, "FAIL": 1}.get(report["overall"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
