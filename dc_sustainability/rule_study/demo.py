"""Deterministic offline demo of the authored RULE-01 cases (RULE-02, issue #240).

Usage: ``python -m dc_sustainability.rule_study.demo --output-dir /tmp/rule-study-demo``

Runs the real simulator, production checker and unchanged Greedy A/B on authored synthetic
cases. It calls no model, reads no source/private/held-out data, does not generate the
120-case evaluation set, and is NOT independent verification or research authorization.
Blocked outcomes (Scenario B) are displayed as blocked; nothing is suppressed.
"""

import argparse
import json
import sys
from pathlib import Path

from dc_sustainability.rule_study import records as r
from dc_sustainability.rule_study.cases import CASE_A, CASE_B, CASE_B_FAULT, CASE_B_PROGRESS
from dc_sustainability.rule_study.runner import BindingError, make_bindings, replay_case, run_case
from dc_sustainability.rule_study.scheduler import ScoreKwhConvention

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICIES = ("rules-v1", "greedy_a", "greedy_b")

# (case, policy). The fault-injection case is a rules-v1 demonstration only: the injected
# slot-0 proposal is never a natural policy output and must be refused by the production gate.
RUNS = (
    [(CASE_A, p) for p in POLICIES]
    + [(CASE_B, p) for p in POLICIES]
    + [(CASE_B_FAULT, "rules-v1")]
    + [(CASE_B_PROGRESS, p) for p in POLICIES]
)


def _fallback_reasons(run) -> dict:
    """Fallback reasons are saved in the hashed transition evidence of decision 0."""
    ref = run.outcomes[0].record.execution.transition_ref
    if ref is None:
        return {}
    return json.loads((run.root / ref).read_text(encoding="utf-8")).get("fallback_reasons", {})


def run_demo(output_dir, *, code_commit=None) -> list[dict]:
    """Run every demo case, replay it, print a concise summary and return the rows.

    ``code_commit`` is for unit tests only; the command line always binds the real clean HEAD.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    convention = ScoreKwhConvention()
    rows = []
    for case, policy in RUNS:
        bindings = make_bindings(case, REPO_ROOT, code_commit=code_commit)
        run, sim, runner = run_case(
            out,
            case,
            policy,
            bindings=bindings,
            score_convention=convention,
            fault_injection=case.fault_injection if case.fault_starts else None,
        )
        first = run.outcomes[0].record
        replayed = replay_case(runner, len(run.outcomes))
        identical = all(
            a.record == b.record and a.decision_sha256 == b.decision_sha256
            for a, b in zip(run.outcomes, replayed)
        ) and all(o.replayed for o in replayed)
        unchanged = len(sim.history) == len(run.outcomes)
        reasons = _fallback_reasons(run)
        stages = " -> ".join(
            f"{st.origin}[{st.check_result.status}"
            + (f", reason={reasons[st.stage_id]}" if st.stage_id in reasons else "")
            + "]"
            for st in first.proposal_stages
        )
        fired = sorted({rule for st in first.proposal_stages for rule in st.rule_ids})
        starts = {
            o.record.decision_index: [job_id for job_id in o.record.execution.current_starts]
            for o in run.outcomes
            if o.record.execution.current_starts
        }
        res = run.result
        status = (
            "BLOCKED" if not res.completed_job_ids and res.missed_job_ids else res.status.upper()
        )
        print(
            f"== case {case.case_id} | policy {policy} | outcome {status} (record status: {res.status})"
        )
        print(
            f"   decision 0: {stages or 'no candidate'}; selected={first.selected_stage_id}; "
            f"execution={first.execution.status}; fired rules={fired or 'n/a'}"
        )
        print(f"   actual starts by slot: {starts or 'none'}")
        print(
            f"   completed={list(res.completed_job_ids)} missed={list(res.missed_job_ids)} "
            f"unscheduled={list(res.accounting.job_outcomes.unscheduled) if res.accounting else 'n/a'} "
            f"unfinished={list(res.unfinished_job_ids)}"
        )
        if res.accounting:
            a = res.accounting
            print(
                f"   synthetic impact={a.synthetic_impact_total} {a.synthetic_impact_unit} "
                f"[{a.score_convention_id}; artificial, not g/kWh or emissions]; "
                f"site energy={a.site_facility_energy_kwh} kWh over {a.slots_recorded} slots"
            )
        print(
            f"   replay: {'identical saved evidence' if identical else 'MISMATCH'}; "
            f"simulator transitions unchanged={unchanged} ({len(sim.history)})"
        )
        print(f"   trace: {run.root} | result sha256={run.result_sha256}")
        print(f"   decision-00 sha256={run.outcomes[0].decision_sha256}")
        rows.append(
            {
                "case": case.case_id,
                "policy": policy,
                "status": status,
                "completed": res.completed_job_ids,
                "missed": res.missed_job_ids,
                "replay_identical": identical and unchanged,
                "model_call_count": sum(o.record.model_call_count for o in run.outcomes),
                "result_sha256": run.result_sha256,
            }
        )
    print(
        f"\nstudy {r.STUDY_ID} adapter {r.ADAPTER_VERSION}; model calls: 0; "
        "synthetic authored inputs only; artificial score-kWh, not g/kWh or emissions; "
        "this demo is not independent verification."
    )
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", required=True, help="new directory for trace files")
    args = parser.parse_args(argv)
    out = Path(args.output_dir)
    if out.exists() and any(out.iterdir()):
        print(f"refusing to reuse non-empty output directory {out}", file=sys.stderr)
        return 2
    try:
        rows = run_demo(out)
    except BindingError as exc:
        print(f"cannot bind the required artifacts: {exc}", file=sys.stderr)
        return 2
    return 0 if all(row["replay_identical"] for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
