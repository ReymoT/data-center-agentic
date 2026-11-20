"""RULE-03: run the independent bounded verifier over synthetic domains.

Domains run in the order given under one combined ceiling (RULE-01 review-2): primary
first, then the optional supplement in whatever allowance remains. Without --system it
runs the oracle only (feasibility census and legal-action-graph counts; every property
NOT_RUN). With --system package.module:function it verifies that callable, which must
accept a SystemView and return a SystemDecision (the rules-v1 adapter or a test fixture).
Offline and deterministic: no network, model, solver or private input. The output file
must not exist; it is written with the canonical JSON convention.

Examples:
    python scripts/verify_rule_study.py --domain primary --domain extended
    python scripts/verify_rule_study.py --domain primary --system pkg.adapter:decide \\
        --system-id rules-v1 --rules-v1 --out verification.json
"""

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.evaluation import rule_study_verifier as v  # noqa: E402

SPEC_PATH = ROOT / "docs" / "rule_study" / "specification.json"


def load_system(path: str):
    module_name, _, attr = path.partition(":")
    if not module_name or not attr:
        raise SystemExit("--system must look like package.module:function")
    return getattr(importlib.import_module(module_name), attr)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--domain",
        action="append",
        choices=("primary", "extended", "authored"),
        required=True,
        help="repeat to run several domains in order under one budget",
    )
    parser.add_argument("--system", help="package.module:function under test")
    parser.add_argument("--system-id", default=None)
    parser.add_argument("--rules-v1", action="store_true", help="system is the rules-v1 adapter")
    parser.add_argument("--out", type=Path, help="new JSON report path")
    parser.add_argument("--max-states", type=int, default=10_000)
    parser.add_argument("--max-transitions", type=int, default=50_000)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    args = parser.parse_args(argv)

    if len(set(args.domain)) != len(args.domain):
        raise SystemExit("each --domain may appear once")
    if args.out is not None and args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    if args.rules_v1 and not args.system:
        raise SystemExit("--rules-v1 requires --system")
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    builders = {
        "primary": v.primary_domain,
        "extended": v.extended_domain,
        "authored": lambda: v.authored_cases(spec),
    }
    domains = [(name, builders[name]()) for name in args.domain]
    system = load_system(args.system) if args.system else None
    report = v.verify_domains(
        domains,
        system,
        system_id=args.system_id or args.system or "oracle-only",
        is_rules_v1=args.rules_v1,
        budget=v.Budget(args.max_states, args.max_transitions, args.max_seconds),
        spec_sha256=v.canonical_sha256(spec),
    )
    summary = {
        r["domain"]: {
            "counts": r["counts"],
            "properties": {p: r["properties"][p]["status"] for p in v.PROPERTY_IDS},
            "oracle_crosscheck_mismatches": r["oracle_crosscheck"]["mismatches"],
        }
        for r in report["results"]
    }
    budget = {k: report["budget"][k] for k in ("states_used", "transitions_used", "ceiling_hit")}
    print(json.dumps({"budget": budget, "results": summary}, indent=2))
    if args.out is not None:
        text = json.dumps(
            report, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
        args.out.write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {args.out} sha256={v.canonical_sha256(report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
