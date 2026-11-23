"""RULE-03: independently receive and verify the current RULE-02 implementation.

Without --execute this only prints the exact plan (independent code pin, domains, run
counts); nothing is run. Uncontained --execute is refused. The execution API is for a separately authorized
contained host; a command-line flag cannot provide human approval or hard containment.

Exit codes: 0 PASS (or plan printed), 1 FAIL, 2 INCOMPLETE. --report is created exclusively.

Examples:
    python scripts/receive_rule_study_system.py --domain primary --domain authored
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.evaluation import rule_study_receiving as rv  # noqa: E402

SPEC_PATH = ROOT / "docs" / "rule_study" / "specification.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--domain", action="append", choices=rv.DOMAINS, required=True)
    parser.add_argument("--policy", action="append", choices=rv.POLICIES)
    parser.add_argument(
        "--execute", action="store_true", help="reserved; uncontained execution is refused"
    )
    parser.add_argument("--out", type=Path, help="new directory for runner output")
    parser.add_argument("--report", type=Path, help="new JSON report path")
    args = parser.parse_args(argv)
    policies = args.policy or ["rules-v1"]
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if args.report is not None and args.report.exists():
        raise SystemExit(f"refusing to overwrite {args.report}")
    if not args.execute:
        plan = rv.plan_receiving(args.domain, policies, ROOT, spec)
        if args.report is not None:
            with args.report.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(plan, stream, indent=2, allow_nan=False)
                stream.write("\n")
        print(json.dumps(plan, indent=2))
        return 0
    if args.out is None:
        raise SystemExit("--execute needs a new --out directory")
    if args.out.exists():
        raise SystemExit(f"refusing to reuse {args.out}")
    raise SystemExit(
        "Uncontained --execute is disabled: use the exact approved trusted supervisor "
        "after fresh bounded authorization. This CLI is plan-only."
    )


if __name__ == "__main__":
    raise SystemExit(main())
