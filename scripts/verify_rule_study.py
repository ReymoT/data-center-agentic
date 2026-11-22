"""RULE-03: run the independent bounded verifier over synthetic domains or recorded traces.

Exploration mode (--domain): domains run in the order given under one combined ceiling
(RULE-01 review-2): primary first, then the optional supplement in whatever allowance
remains. Without --system it runs the oracle only (feasibility census and
legal-action-graph counts; every property NOT_RUN). With --system package.module:function
it verifies that callable, which must accept a SystemView and return a SystemDecision.

Trace mode (--traces DIR): each subfolder of DIR holds case.json, result.json and
decisions/*.json in the agreed rule_study_decision_v1 / result_v1 shape and is read
strictly and replayed independently, including P2.

Offline and deterministic: no network, model, solver or private input. The output file
must not exist; it is written with the canonical JSON convention.

Examples:
    python scripts/verify_rule_study.py --domain primary --domain extended
    python scripts/verify_rule_study.py --domain primary --system pkg.adapter:decide \\
        --system-id rules-v1 --rules-v1 --out verification.json
    python scripts/verify_rule_study.py --traces runs/ --out trace_verification.json
"""

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dc_sustainability.evaluation import rule_study_trace as tr  # noqa: E402
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
        help="repeat to run several domains in order under one budget",
    )
    parser.add_argument("--traces", type=Path, help="folder of recorded trace subfolders")
    parser.add_argument("--system", help="package.module:function under test")
    parser.add_argument("--system-id", default=None)
    parser.add_argument("--rules-v1", action="store_true", help="the system/traces are rules-v1")
    parser.add_argument("--out", type=Path, help="new JSON report path")
    parser.add_argument("--max-states", type=int, default=10_000)
    parser.add_argument("--max-transitions", type=int, default=50_000)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    args = parser.parse_args(argv)

    if (
        type(args.max_states) is not int
        or not 0 <= args.max_states <= 10_000
        or type(args.max_transitions) is not int
        or not 0 <= args.max_transitions <= 50_000
        or not 0 <= args.max_seconds <= 600
    ):
        raise SystemExit("limits must be finite/nonnegative and cannot exceed review-2 ceilings")
    if args.domain and "primary" in args.domain and args.domain[0] != "primary":
        raise SystemExit("primary must run before supplemental domains")
    if args.out is not None and args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    if bool(args.traces) == bool(args.domain):
        raise SystemExit("give either --domain (exploration) or --traces (trace mode)")
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if args.traces:
        return _trace_mode(args, spec)
    if len(set(args.domain)) != len(args.domain):
        raise SystemExit("each --domain may appear once")
    if args.rules_v1 and not args.system:
        raise SystemExit("--rules-v1 requires --system")
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
    _write(args.out, report)
    return _exit_code(report)


def _trace_mode(args, spec) -> int:
    folders = sorted(p for p in args.traces.iterdir() if p.is_dir())
    if not folders:
        raise SystemExit(f"no trace folders under {args.traces}")
    report = tr.verify_traces(
        [tr.load_trace_dir(f) for f in folders],
        expected_spec_sha256=v.canonical_sha256(spec),
        is_rules_v1_run=args.rules_v1,
        budget=v.Budget(args.max_states, args.max_transitions, args.max_seconds),
    )
    summary = {
        policy: {
            "counts": r["counts"],
            "properties": {p: r["properties"][p]["status"] for p in v.PROPERTY_IDS},
            "arithmetic_mismatches": r["arithmetic_consistency"]["mismatches"],
        }
        for policy, r in report["results"].items()
    }
    print(json.dumps({"refused": report["refused_traces"], "results": summary}, indent=2))
    _write(args.out, report)
    return _exit_code(report)


def _exit_code(report: dict) -> int:
    results = report["results"]
    groups = list(results.values()) if isinstance(results, dict) else list(results)
    statuses = [p["status"] for group in groups for p in group["properties"].values()]
    if (
        report.get("refused_traces")
        or "FAIL" in statuses
        or any(group.get("oracle_crosscheck", {}).get("mismatches", 0) for group in groups)
    ):
        return 1
    if (
        "INCOMPLETE" in statuses
        or report.get("budget", {}).get("ceiling_hit")
        or report.get("binding_validation", {}).get("status") == "INCOMPLETE"
    ):
        return 2
    return 0  # Oracle-only NOT_RUN is diagnostic success, never study acceptance.


def _write(out: Path | None, report: dict) -> None:
    if out is None:
        return
    text = json.dumps(
        report, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    # Exclusive creation closes the check/write race; never overwrite another run.
    with out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text + "\n")
    print(f"wrote {out} sha256={v.canonical_sha256(report)}")


if __name__ == "__main__":
    raise SystemExit(main())
