"""Replay the committed RULE-02 traces from their saved files only (reviewer tool, not a verifier).

Usage (from the repository root, with the pinned Python 3.12 environment):

    PYTHONPATH=. python docs/evidence/rule02/tools/replay_from_saved.py \
        --traces docs/evidence/rule02/traces --out docs/evidence/rule02/compat/replay-from-saved.json

For each trace folder it copies the saved files to a temporary directory (the committed files are never
modified), builds a fresh runner and simulator for the same case and policy, and asks the runner for
decisions 0..29. Because saved evidence exists for every slot, the runner must return the saved records
without stepping the simulator or running a policy. The tool then compares each replayed decision hash with
the hash recorded in ``result.json`` and checks that the simulator history is empty.

This is replay of saved evidence for determinism and tamper detection. It is NOT independent RULE-03
verification, and it does not re-run the scheduler from scratch (a fresh run mints new production check ids).
Exit code: 0 all replays identical, 1 any mismatch.
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from dc_sustainability.rule_study import records as r
from dc_sustainability.rule_study.cases import CASE_A, CASE_B, CASE_B_FAULT, CASE_B_PROGRESS
from dc_sustainability.rule_study.runner import HORIZON, RuleStudyRunner, replay_case
from dc_sustainability.rule_study.scheduler import ScoreKwhConvention
from dc_sustainability.simulator import SchedulingSimulator

CASES = {c.case_id: c for c in (CASE_A, CASE_B, CASE_B_FAULT, CASE_B_PROGRESS)}


def replay_trace(trace_dir: Path) -> dict:
    result = json.loads((trace_dir / "result.json").read_text(encoding="utf-8"))
    case = CASES[result["case_id"]]
    policy = result["policy_id"]
    bindings = r.Bindings(**result["bindings"])
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        # The runner looks for <directory>/<policy>/<case>-<policy>/; mirror that layout for one trace.
        shutil.copytree(trace_dir, work / trace_dir.parent.name / trace_dir.name)
        sim = SchedulingSimulator(allow_completion_starts=False)
        sim.reset(case.episode(), forecasts_by_slot=case.forecasts_by_slot())
        snapshot = case.snapshot()
        runner = RuleStudyRunner(
            sim,
            lambda: snapshot,
            work,
            policy_id=policy,
            case_id=case.case_id,
            decision_time_utc=case.decision_time_utc,
            bindings=bindings,
            score_convention=ScoreKwhConvention(),
            fault_injection=case.fault_injection if case.fault_starts else None,
            case_json=case.case_json(),
        )
        outcomes = replay_case(runner, HORIZON)
    hashes = [o.decision_sha256 for o in outcomes]
    return {
        "trace": f"{trace_dir.parent.name}/{trace_dir.name}",
        "case_id": case.case_id,
        "policy_id": policy,
        "decisions_replayed": len(outcomes),
        "all_replayed_from_saved_files": all(o.replayed for o in outcomes),
        "decision_hashes_match_result": hashes == result["decision_sha256s"],
        "simulator_transitions_executed": len(sim.history),
        "identical": all(o.replayed for o in outcomes)
        and hashes == result["decision_sha256s"]
        and len(sim.history) == 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new JSON report path")
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    rows = []
    for result_file in sorted(args.traces.glob("*/*/result.json")):
        rows.append(replay_trace(result_file.parent))
    report = {
        "record_kind": "rule02_replay_from_saved_v1",
        "note": "replay of committed saved evidence only; not independent verification",
        "traces": rows,
        "all_identical": bool(rows) and all(row["identical"] for row in rows),
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["all_identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
