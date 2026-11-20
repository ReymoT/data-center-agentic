"""Generate a RULE-04 synthetic case set and its evaluator-only accounting file (#242).

Development sets need no authorization. The final set must not be generated before the
rule/verifier freeze and Matty's bounded approval; pass that approval's issue-comment URL
with --authorization. Output files are created exclusively and never overwritten.

    python scripts/generate_rule_study_cases.py --domain development \
        --out-cases development.json --out-accounting development.accounting.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dc_sustainability.evaluation import rule_study_generator as g  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--domain", choices=sorted(g.SEED_DOMAINS), required=True)
    parser.add_argument("--out-cases", type=Path, required=True)
    parser.add_argument("--out-accounting", type=Path, required=True)
    parser.add_argument("--authorization", help="approving issue-comment URL (final only)")
    args = parser.parse_args(argv)

    if args.out_cases.resolve() == args.out_accounting.resolve():
        parser.error("case and accounting outputs must be different files")
    for path in (args.out_cases, args.out_accounting):
        if path.exists():
            parser.error(f"{path} already exists; outputs are never overwritten")
    try:
        case_set, accounting = g.generate(args.domain, authorization=args.authorization)
    except (PermissionError, ValueError, RuntimeError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    with open(args.out_cases, "x", encoding="utf-8", newline="\n") as handle:
        handle.write(g.dumps(case_set))
    with open(args.out_accounting, "x", encoding="utf-8", newline="\n") as handle:
        handle.write(g.dumps(accounting))
    print(
        json.dumps(
            {"set_id": case_set["set_id"], "report": case_set["metadata"]["report"]}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
