"""RULE-07 executable demo driver (issue #246) over the merged RULE-02 implementation.

    python -m dc_sustainability.rule_demo                       # interactive menu (terminal)
    python -m dc_sustainability.rule_demo --list
    python -m dc_sustainability.rule_demo --scenario A          # A | B | B-fault | B-progress
    python -m dc_sustainability.rule_demo --all [--json]
    python -m dc_sustainability.rule_demo --replay RUN_DIR      # saved run, replayed from disk

This module adds no scheduler, checker, runner or trace format. It calls the merged
``dc_sustainability.rule_study`` cases, ``run_case`` and ``RuleStudyRunner`` (real rules-v1
scheduler, unchanged production checker, unchanged Greedy A fallback, real simulator), then
presents expected behavior (from ``docs/rule_study/specification.json``) separately from
observed behavior, replays the saved evidence from disk, and writes a small hashed summary.

Every invocation writes to a NEW directory; nothing existing is overwritten. Scores are
artificial synthetic weights, not measured carbon intensity or emissions. No model call, network
access, private or source data. This is NOT Nisha's independent verification.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dc_sustainability.rule_study import records as r
from dc_sustainability.rule_study.cases import AUTHORED_CASES
from dc_sustainability.rule_study.runner import (
    BindingError,
    CaseRun,
    RuleStudyRunner,
    build_result,
    make_bindings,
    replay_case,
    run_case,
)
from dc_sustainability.rule_study.scheduler import ScoreKwhConvention
from dc_sustainability.runtime.traces import IndeterminateExecution
from dc_sustainability.simulator import SchedulingSimulator

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "docs" / "rule_study" / "specification.json"
DEFAULT_OUT_ROOT = REPO_ROOT / "results" / "runs" / "rule07_demo"
SUMMARY_NAME = "demo_summary.json"
SUMMARY_KIND = "rule07_demo_summary_v1"

INDEPENDENT_VERIFICATION_STATUS = (
    "NOT_RUN - not performed by this tool; pending Nisha's actual findings under #241"
)
READER_SMOKE_STATUS = (
    "not run by this command. The separate manual run of scripts/verify_rule_study.py "
    "(documented in the handoff) reports INCOMPLETE with exit code 2 because binding "
    "validation lacks externally supplied artifacts; it is not independent verification"
)
SCENARIOS = ("A", "B", "B-fault", "B-progress")
DEFAULT_POLICY = "rules-v1"
BANNER = (
    "SYNTHETIC DEMO - scores are artificial weights (score-kWh), not measured carbon intensity "
    "or emissions; no CO2e-savings claim. Not independent verification."
)
DESCRIPTIONS = {
    "A": "normal scheduling: both jobs fit under the 60 kW IT capacity",
    "B": "overloaded: two rigid 30 kW jobs plus 20 kW background cannot run together",
    "B-fault": "case B with a deliberately injected invalid slot-0 proposal (J1@0, J2@0); "
    "not a natural policy output",
    "B-progress": "separate feasible sequential case: J2 flexible with a later deadline "
    "(never combined with the impossible case B)",
}


class UsageError(ValueError):
    """Bad command-line choice (exit code 2)."""


def normalize_scenario(name: str) -> str:
    lowered = str(name).strip().lower()
    for scenario in SCENARIOS:
        if scenario.lower() == lowered:
            return scenario
    raise UsageError(f"unknown scenario {name!r}; choose one of {', '.join(SCENARIOS)}")


def load_expectations() -> dict[str, str]:
    """Expected behavior text per scenario, straight from the accepted specification file."""
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    entries = spec["scenarios"]
    entries = entries if isinstance(entries, list) else list(entries.values())
    by_id = {e["id"]: e for e in entries}
    base_a, base_b = by_id["A"], by_id["B"]
    return {
        "A": base_a["expected_not_measured"],
        "B": base_b["expected_not_measured"],
        "B-fault": "injected plan "
        + ", ".join(base_b["fault_injection_not_natural_output"]["starts"])
        + " is refused; "
        + base_b["fault_injection_not_natural_output"]["purpose"],
        "B-progress": "feasible sequential subcase: J2 flexible, deadline "
        f"{base_b['feasible_progress_subcase']['deadline_slot']}",
    }


# ------------------------------------------------------------------------------ running
@dataclass(frozen=True)
class ScenarioRun:
    scenario: str
    policy: str
    run: CaseRun
    bindings: r.Bindings
    replay: dict
    observed: dict
    inputs: dict


def describe_inputs(case) -> dict:
    """The permitted synthetic input identities for a case (authored; nothing private)."""
    data = case.case_json()
    return {
        "case_id": case.case_id,
        "episode_id": case.episode_id,
        "scenario_id": f"SCN-{case.case_id}".replace("_", "-"),
        "origin": "authored synthetic example from docs/rule_study/specification.json; no private "
        "or source data; schema labels split=development, seed=0 (not a held-out or previously "
        "used episode)",
        "capacity_kw": data["capacity_kw"],
        "background_kw": data["background_kw"],
        "jobs": data["jobs"],
        "forecast_present": case.forecast_present,
        "artificial_scores_slots_0_5": None if data["scores"] is None else data["scores"][:6],
        "fault_starts": data.get("fault_starts"),
        "case_sha256": case.case_sha256(),
    }


def _fallback_reasons(run: CaseRun) -> dict:
    ref = run.outcomes[0].record.execution.transition_ref
    if ref is None:
        return {}
    saved = json.loads((run.root / ref).read_text(encoding="utf-8"))
    return saved.get("fallback_reasons", {})


def _arith(a) -> dict:
    return {
        "slot": a.slot,
        "constraint_id": a.constraint_id,
        "terms": [{"label": x.label, "job_id": x.job_id, "value": x.value} for x in a.terms],
        "total_kw": a.total,
        "limit_kw": a.limit,
        "signed_excess_kw": a.signed_excess,
        "outcome": a.outcome,
    }


def _stage_view(stage, reasons: dict) -> dict:
    plan = stage.plan
    check = stage.check_result
    return {
        "stage_id": stage.stage_id,
        "origin": stage.origin,
        "rule_ids": list(stage.rule_ids),
        "starts": [f"{p.job_id}@{p.start_slot}" for p in plan.starts],
        "abstentions": [f"{a.job_id}({a.reason})" for a in plan.abstentions],
        "deferrals": [f"{d.job_id}" for d in plan.deferrals],
        "production_check": None if check is None else check.status,
        "check_violations": []
        if check is None
        else [f"{v.violation_type}: {v.message}" for v in check.violations] + list(check.errors),
        "stage_errors": [f"{e.code}: {e.message}" for e in stage.errors],
        "fallback_reason": reasons.get(stage.stage_id),
        "capacity_arithmetic": [_arith(a) for a in stage.arithmetic if a.rule_id == "R04"],
        "hypothetical_joint_arithmetic": [
            _arith(a)
            for a in stage.arithmetic
            if a.rule_id == "R05"
            and a.outcome == "fail"
            and a.formula.startswith("rejected candidate")
        ],
    }


OUTCOME_MEANING = {
    "COMPLETED": "every job completed",
    "BLOCKED": "no job executed or completed; a safe refusal, not a scheduling success",
    "PARTIAL": "some work executed but not every job completed",
}


def scenario_outcome(*, completed, missed, unfinished, executed_any: bool) -> str:
    """Overall result of the scenario, independent of any literal expectation bound."""
    if not unfinished and not missed:
        return "COMPLETED"
    if not executed_any and not completed:
        return "BLOCKED"
    return "PARTIAL"


def observe(run: CaseRun) -> dict:
    """What actually happened, read only from the saved decision and result records."""
    reasons = _fallback_reasons(run)
    first = run.outcomes[0].record
    executed = {
        o.record.decision_index: list(o.record.execution.current_starts)
        for o in run.outcomes
        if o.record.execution.current_starts
    }
    only_current = True
    rejected_executed = False
    advisory = []
    for o in run.outcomes:
        rec = o.record
        selected = next(
            (s for s in rec.proposal_stages if s.stage_id == rec.selected_stage_id), None
        )
        if selected is None:
            if rec.execution.current_starts:
                rejected_executed = True  # something executed with no passed, selected stage
            continue
        if selected.check_result is None or selected.check_result.status != "pass":
            if rec.execution.current_starts:
                rejected_executed = True
        current = {p.job_id for p in selected.plan.starts if p.start_slot == rec.decision_index}
        future = [
            f"{p.job_id}@{p.start_slot}"
            for p in selected.plan.starts
            if p.start_slot > rec.decision_index
        ]
        if set(rec.execution.current_starts) != current:
            only_current = False
        if future and rec.decision_index == 0:
            advisory = future
    res = run.result
    acc = res.accounting
    outcome = scenario_outcome(
        completed=list(res.completed_job_ids),
        missed=list(res.missed_job_ids),
        unfinished=list(res.unfinished_job_ids),
        executed_any=bool(executed),
    )
    return {
        "scenario_outcome": outcome,
        "scenario_outcome_meaning": OUTCOME_MEANING[outcome],
        "no_rejected_plan_executed": not rejected_executed,
        "decision_0": {
            "stages": [_stage_view(st, reasons) for st in first.proposal_stages],
            "selected_stage_id": first.selected_stage_id,
            "execution_status": first.execution.status,
            "current_starts": list(first.execution.current_starts),
            "advisory_future_placements": advisory,
            "errors": [f"{e.code}: {e.message}" for e in first.errors],
        },
        "executed_starts_by_slot": {str(k): v for k, v in executed.items()},
        "only_approved_current_slot_starts_executed": only_current,
        "completed": list(res.completed_job_ids),
        "missed": list(res.missed_job_ids),
        "unscheduled": list(acc.job_outcomes.unscheduled) if acc else None,
        "unfinished": list(res.unfinished_job_ids),
        "record_status": res.status,
        "record_status_meaning": "trace status only (all 30 decisions recorded); not a scheduling outcome",
        "decision_count": len(run.outcomes),
        "model_call_count": sum(o.record.model_call_count for o in run.outcomes),
        "accounting": None
        if acc is None
        else {
            "synthetic_impact_total": acc.synthetic_impact_total,
            "synthetic_impact_unit": acc.synthetic_impact_unit,
            "score_convention_id": acc.score_convention_id,
            "label": "artificial score-kWh; not g/kWh, not emissions",
        },
    }


def compare_with_expectation(scenario: str, observed: dict) -> list[dict]:
    """Expected-versus-observed rows. Kept separate from the run itself."""
    rows = []

    def row(expected, actual, verdict, note=""):
        rows.append({"expected": expected, "observed": actual, "verdict": verdict, "note": note})

    d0 = observed["decision_0"]
    done = set(observed["completed"])
    if scenario == "A":
        starts = {j: int(k) for k, v in observed["executed_starts_by_slot"].items() for j in v}
        row(
            "J2 starts at slot 0",
            f"J2 start={starts.get('J2')}",
            "MATCH" if starts.get("J2") == 0 else "DIFFERS",
        )
        row(
            "J1 preferably at slot 1",
            f"J1 start={starts.get('J1')}",
            "MATCH" if starts.get("J1") == 1 else "DIFFERS",
        )
        row(
            "slot 0 executes only current starts; J1@1 stays advisory",
            f"current_starts={d0['current_starts']}, advisory={d0['advisory_future_placements']}",
            "MATCH"
            if d0["current_starts"] == ["J2"] and d0["advisory_future_placements"] == ["J1@1"]
            else "DIFFERS",
        )
        row(
            "scenario outcome: all jobs complete",
            f"{observed['scenario_outcome']}",
            "MATCH" if observed["scenario_outcome"] == "COMPLETED" else "DIFFERS",
        )
    elif scenario == "B":
        row(
            "at most one job can complete (joint 80 kW exceeds 60 kW)",
            f"completed={sorted(done)}",
            "BOUND-MET-LITERAL" if len(done) <= 1 else "DIFFERS",
            "only the literal upper bound is satisfied; zero completions is not progress"
            if not done
            else "",
        )
        row(
            "scenario outcome (issue #246: safe refusal does not count as success)",
            f"{observed['scenario_outcome']}: {observed['scenario_outcome_meaning']}",
            "BLOCKED" if observed["scenario_outcome"] == "BLOCKED" else "DIFFERS",
            "the unchanged production gate refuses the partial-plan abstention and the Greedy A "
            "fallback; the merged RULE-02 handoff requires this no-start outcome to stay visible. "
            "No new joint-exclusion semantics adopted."
            if observed["scenario_outcome"] == "BLOCKED"
            else "",
        )
    elif scenario == "B-fault":
        s1 = d0["stages"][0] if d0["stages"] else None
        row(
            "injected invalid proposal is refused by the production checker",
            f"{s1['origin']} check={s1['production_check']}" if s1 else "no stage",
            "MATCH"
            if s1 and s1["origin"] == "fault_injection" and s1["production_check"] != "pass"
            else "DIFFERS",
        )
        fb = next((s for s in d0["stages"] if s["origin"] == "greedy_a_fallback"), None)
        row(
            "Greedy A fallback is built and checked",
            f"fallback check={fb['production_check']}" if fb else "no fallback stage",
            "MATCH" if fb and fb["production_check"] is not None else "DIFFERS",
        )
        if fb and fb["production_check"] != "pass":
            row(
                "(informational; #246 asks only for actual fallback outcomes) fallback passes",
                "fallback failed the checker; nothing executed",
                "DOCUMENTED-LIMITATION",
                "no successful fallback is claimed",
            )
        row(
            "scenario outcome (safe refusal does not count as success)",
            f"{observed['scenario_outcome']}: {observed['scenario_outcome_meaning']}",
            "BLOCKED" if observed["scenario_outcome"] == "BLOCKED" else "DIFFERS",
        )
    elif scenario == "B-progress":
        starts = {j: int(k) for k, v in observed["executed_starts_by_slot"].items() for j in v}
        row(
            "J1 then J2 in sequence; both complete",
            f"starts={starts}, completed={sorted(done)}",
            "MATCH"
            if done == {"J1", "J2"} and starts.get("J1") == 0 and starts.get("J2") == 1
            else "DIFFERS",
        )
        row(
            "scenario outcome: all jobs complete",
            f"{observed['scenario_outcome']}",
            "MATCH" if observed["scenario_outcome"] == "COMPLETED" else "DIFFERS",
        )
    return rows


def _fresh_out_dir(out_dir: Path | None) -> Path:
    if out_dir is not None:
        out = Path(out_dir)
        if out.exists() and any(out.iterdir()):
            raise UsageError(f"refusing to reuse non-empty output directory {out}")
        out.mkdir(parents=True, exist_ok=True)
        return out
    DEFAULT_OUT_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(8):
        candidate = DEFAULT_OUT_ROOT / f"{stamp}-{secrets.token_hex(3)}"
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue
    raise UsageError("could not allocate a fresh output directory")


def run_scenario(
    scenario: str, policy: str, out_dir: Path, *, code_commit: str | None = None
) -> ScenarioRun:
    scenario = normalize_scenario(scenario)
    if policy not in r.POLICY_IDS:
        raise UsageError(f"unknown policy {policy!r}; choose one of {', '.join(r.POLICY_IDS)}")
    if scenario == "B-fault" and policy != "rules-v1":
        raise UsageError("B-fault is a rules-v1 demonstration only")
    case = AUTHORED_CASES[scenario]
    bindings = make_bindings(case, REPO_ROOT, code_commit=code_commit)
    run, _sim, _runner = run_case(
        out_dir,
        case,
        policy,
        bindings=bindings,
        score_convention=ScoreKwhConvention(),
        fault_injection=case.fault_injection if case.fault_starts else None,
    )
    replay = replay_saved(
        run.root, expect_decision_sha256s=[o.decision_sha256 for o in run.outcomes]
    )
    return ScenarioRun(scenario, policy, run, bindings, replay, observe(run), describe_inputs(case))


# ------------------------------------------------------------------------------ replay
def replay_saved(root, *, expect_decision_sha256s: list[str] | None = None) -> dict:
    """Replay one saved case/policy folder from disk. No new simulator step is taken.

    Uses the merged runner's own replay: every decision must have its reservation, completion
    commitment and hash-addressed state/snapshot/transition/case evidence intact. The result file
    is rebuilt from that evidence and must equal the saved result exactly.
    """
    root = Path(root)
    report: dict = {"root": str(root), "status": "fail", "problems": []}
    try:
        if not (root / "result.json").is_file() or not (root / "decisions").is_dir():
            raise ValueError("not a saved rule-study case folder (no result.json / decisions)")
        saved_text = (root / "result.json").read_text(encoding="utf-8")
        result = r.RuleStudyResult.from_json(saved_text)
        policy, case_id = result.policy_id, result.case_id
        if root.name != f"{case_id}-{policy}" or root.parent.name != policy:
            raise ValueError("folder layout does not match the saved result identity")
        if case_id not in AUTHORED_CASES:
            raise ValueError(f"unknown authored case {case_id!r}")
        case = AUTHORED_CASES[case_id]
        if case.case_sha256() != result.bindings.case_sha256:
            raise ValueError("saved case binding differs from the current authored case")
        case_file = root / "case.json"
        if not case_file.is_file():
            raise ValueError("case.json is missing from the saved run (required evidence)")
        if r.study_sha256(case_file.read_text(encoding="utf-8")) != result.bindings.case_sha256:
            raise ValueError("saved case.json does not match the bound case_sha256")
        convention = ScoreKwhConvention() if policy == "rules-v1" else None
        sim = SchedulingSimulator(allow_completion_starts=False)
        sim.reset(case.episode(), forecasts_by_slot=case.forecasts_by_slot())
        snapshot = case.snapshot()
        runner = RuleStudyRunner(
            sim,
            lambda: snapshot,
            root.parent.parent,
            policy_id=policy,
            case_id=case_id,
            decision_time_utc=case.decision_time_utc,
            bindings=result.bindings,
            score_convention=convention,
            fault_injection=case.fault_injection if case.fault_starts else None,
        )
        count = len(list((root / "decisions").glob("decision-*.json")))
        outcomes = replay_case(runner, count)
        rebuilt = build_result(root, case, policy, result.bindings, convention)
        hashes = [o.decision_sha256 for o in outcomes]
        report.update(
            {
                "case_id": case_id,
                "policy_id": policy,
                "decisions_replayed": count,
                "all_replayed_from_saved_evidence": all(o.replayed for o in outcomes),
                "simulator_steps_during_replay": len(sim.history),
                "result_rebuilt_equals_saved": rebuilt.to_json() == saved_text,
                "result_sha256": r.study_sha256(saved_text),
                "decision_sha256s": hashes,
                "code_commit_saved": result.bindings.code_commit,
            }
        )
        if expect_decision_sha256s is not None and hashes != list(expect_decision_sha256s):
            report["problems"].append("replayed decision hashes differ from the original run")
        if not report["all_replayed_from_saved_evidence"]:
            report["problems"].append("a decision was not served from saved evidence")
        if report["simulator_steps_during_replay"] != 0:
            report["problems"].append("replay stepped the simulator")
        if not report["result_rebuilt_equals_saved"]:
            report["problems"].append("result rebuilt from evidence differs from saved result")
        report["binding_drift_vs_current_checkout"] = _binding_drift(case, result.bindings)
    except IndeterminateExecution as exc:
        report["problems"].append(f"indeterminate: {exc}")
    except (ValueError, KeyError, OSError) as exc:
        report["problems"].append(f"{type(exc).__name__}: {exc}")
    report["status"] = "pass" if not report["problems"] else "fail"
    return report


def _binding_drift(case, saved: r.Bindings) -> dict:
    """Informational: do today's sources still hash to the saved bindings?"""
    try:
        now = make_bindings(case, REPO_ROOT, code_commit=saved.code_commit)
    except BindingError as exc:
        return {"status": "unavailable", "reason": str(exc)}
    fields = (
        "spec_sha256",
        "adapter_source_sha256",
        "generator_source_sha256",
        "case_sha256",
        "environment_lock_sha256",
    )
    return {f: getattr(now, f) == getattr(saved, f) for f in fields}


def replay_path(path) -> list[dict]:
    """Replay a case folder, or every case folder under a demo output directory."""
    path = Path(path)
    if (path / "result.json").is_file():
        return [replay_saved(path)]
    roots = sorted(p.parent for p in path.glob("*/*/result.json"))
    if not roots:
        raise UsageError(f"no saved rule-study run found under {path}")
    return [replay_saved(root) for root in roots]


# ------------------------------------------------------------------------------ reporting
def _hr(title: str, n: int) -> str:
    return f"\n[{n}] {title}\n" + "-" * (len(title) + 5)


def _terms(a: dict) -> str:
    return " + ".join(
        f"{x['job_id'] or x['label'].replace('_kw', '')} {x['value']}" for x in a["terms"]
    )


def render(sr: ScenarioRun, expected_text: str, rows: list[dict]) -> str:
    obs = sr.observed
    out = [
        BANNER,
        _hr(f"Scenario {sr.scenario} / policy {sr.policy}", 1),
        DESCRIPTIONS[sr.scenario],
        f"SCENARIO OUTCOME: {obs['scenario_outcome']} - {obs['scenario_outcome_meaning']}",
    ]
    b = sr.bindings
    out.append(_hr("Bindings (actual, from the clean committed checkout)", 2))
    for name in (
        "code_commit",
        "spec_sha256",
        "adapter_source_sha256",
        "generator_source_sha256",
        "case_sha256",
        "environment_lock_sha256",
    ):
        out.append(f"  {name}: {getattr(b, name)}")
    inp = sr.inputs
    out.append(_hr("Inputs (permitted synthetic identities)", 3))
    out.append(f"  case {inp['case_id']} / episode {inp['episode_id']} / {inp['scenario_id']}")
    out.append(f"  origin: {inp['origin']}")
    out.append(
        f"  site: {inp['capacity_kw']} kW IT capacity, {inp['background_kw']} kW background; "
        f"forecast present={inp['forecast_present']}"
    )
    for job in inp["jobs"]:
        kind = "flexible" if job["flexible"] else "rigid"
        out.append(
            f"  {job['job_id']}: {job['power_kw']} kW x {job['duration_slots']} slot(s), arrival "
            f"{job['arrival_slot']}, deadline {job['deadline_slot']}, {kind}"
        )
    if inp["artificial_scores_slots_0_5"]:
        out.append(
            f"  artificial score weights, slots 0-5: {inp['artificial_scores_slots_0_5']} "
            "(not measured carbon intensity)"
        )
    if inp["fault_starts"]:
        out.append(f"  injected (not natural) slot-0 proposal: {inp['fault_starts']}")
    out.append(_hr("EXPECTED (specification.json; not a measurement)", 4))
    out.append(f"  {expected_text}")
    d0 = obs["decision_0"]
    out.append(_hr("OBSERVED: decision 0 stages (proposal / production check / fallback)", 5))
    for st in d0["stages"]:
        out.append(
            f"  {st['stage_id']} {st['origin']}: starts={st['starts']} abstain={st['abstentions']} "
            f"| production check={st['production_check']} | rules={','.join(st['rule_ids'])}"
        )
        for a in st["capacity_arithmetic"][:3]:
            out.append(
                f"      PROPOSED load, slot {a['slot']} (R04): {_terms(a)} = {a['total_kw']} kW "
                f"vs limit {a['limit_kw']} kW -> excess {a['signed_excess_kw']} ({a['outcome']})"
            )
        for a in st["hypothetical_joint_arithmetic"][:3]:
            out.append(
                f"      HYPOTHETICAL, not proposed (R05 rejected candidate), slot {a['slot']}: "
                f"{_terms(a)} = {a['total_kw']} kW vs limit {a['limit_kw']} kW -> excess "
                f"{a['signed_excess_kw']} ({a['outcome']})"
            )
        for text in st["check_violations"]:
            out.append(f"      checker reason: {text}")
        if (
            st["production_check"] != "pass"
            and st["capacity_arithmetic"]
            and st["hypothetical_joint_arithmetic"]
        ):
            actual = st["capacity_arithmetic"][0]
            hypo = st["hypothetical_joint_arithmetic"][0]
            out.append(
                f"      reading: the proposed {actual['total_kw']} kW load is "
                f"{'within' if actual['outcome'] == 'pass' else 'over'} the {actual['limit_kw']} kW "
                f"limit; the {hypo['total_kw']} kW overload exists only in the "
                f"hypothetical joint start that this plan excluded ({st['abstentions']}). The plan "
                "is rejected for the reason above, not because it overloads the site."
            )
        if st["fallback_reason"]:
            out.append(f"      fallback reason: {st['fallback_reason']}")
    out.append(
        f"  selected={d0['selected_stage_id']} execution={d0['execution_status']} "
        f"current_starts={d0['current_starts']} advisory_future={d0['advisory_future_placements']}"
    )
    if d0["selected_stage_id"] is None:
        out.append(
            "  no stage passed the production gate: no new work executed (visible, not hidden)"
        )
    out.append(_hr("OBSERVED: execution and result", 6))
    out.append(f"  executed starts by slot: {obs['executed_starts_by_slot'] or 'none'}")
    out.append(
        f"  only approved current-slot starts executed: {obs['only_approved_current_slot_starts_executed']}"
        f"; no rejected plan executed: {obs['no_rejected_plan_executed']}"
    )
    out.append(
        f"  completed={obs['completed']} missed={obs['missed']} unscheduled={obs['unscheduled']} "
        f"unfinished={obs['unfinished']}"
    )
    out.append(f"  trace record status: {obs['record_status']} ({obs['record_status_meaning']})")
    if obs["accounting"]:
        a = obs["accounting"]
        out.append(
            f"  synthetic impact={a['synthetic_impact_total']} {a['synthetic_impact_unit']} [{a['label']}]"
        )
    out.append(_hr("EXPECTED vs OBSERVED (kept separate)", 7))
    for item in rows:
        out.append(f"  [{item['verdict']}] expected: {item['expected']}")
        out.append(f"      observed: {item['observed']}")
        if item["note"]:
            out.append(f"      note: {item['note']}")
    rep = sr.replay
    out.append(_hr("Trace and replay", 8))
    out.append(f"  trace folder: {sr.run.root}")
    out.append(f"  result sha256: {sr.run.result_sha256}")
    out.append(
        f"  replay from disk: {rep['status']} (decisions={rep.get('decisions_replayed')}, "
        f"simulator steps={rep.get('simulator_steps_during_replay')}, "
        f"result rebuilt equals saved={rep.get('result_rebuilt_equals_saved')})"
    )
    for problem in rep["problems"]:
        out.append(f"  replay problem: {problem}")
    out.append(_hr("Scope", 9))
    out.append(f"  model calls: {obs['model_call_count']}; synthetic authored inputs only.")
    out.append("  Not independent verification; not frozen-policy or research evidence.")
    out.append(f"  independent verification (Nisha, #241): {INDEPENDENT_VERIFICATION_STATUS}")
    out.append(f"  trace-reader compatibility smoke: {READER_SMOKE_STATUS}")
    return "\n".join(out)


def summary_record(runs: list[ScenarioRun], expectations: dict[str, str], command: str) -> dict:
    return {
        "record_kind": SUMMARY_KIND,
        "study_id": r.STUDY_ID,
        "command": command,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "synthetic_scores": "artificial score-kWh; not measured carbon intensity or emissions",
        "independent_verification": INDEPENDENT_VERIFICATION_STATUS,
        "verification_statuses": {
            "independent_verification": "NOT_RUN",
            "trace_reader_compatibility_smoke": "NOT_RUN_BY_THIS_COMMAND",
            "vocabulary": ["PASS", "FAIL", "INCOMPLETE", "NOT_RUN"],
        },
        "trace_reader_compatibility_smoke": READER_SMOKE_STATUS,
        "runs": [
            {
                "scenario": sr.scenario,
                "policy": sr.policy,
                "trace_root": str(sr.run.root),
                "result_sha256": sr.run.result_sha256,
                "decision_sha256s": [o.decision_sha256 for o in sr.run.outcomes],
                "bindings": sr.bindings.to_jsonable(),
                "inputs": sr.inputs,
                "expected_not_measured": expectations[sr.scenario],
                "observed": sr.observed,
                "expected_vs_observed": compare_with_expectation(sr.scenario, sr.observed),
                "replay": sr.replay,
            }
            for sr in runs
        ],
    }


def _write_summary(out_dir: Path, summary: dict) -> Path:
    path = out_dir / SUMMARY_NAME
    with open(path, "x", encoding="utf-8", newline="\n") as handle:  # create-only
        handle.write(r.study_json(summary))
    return path


# ------------------------------------------------------------------------------ main
def _interactive_choice() -> str:
    print(BANNER)
    print("Choose a scenario:")
    for index, name in enumerate(SCENARIOS, 1):
        print(f"  {index}. {name}: {DESCRIPTIONS[name]}")
    raw = input("Scenario (number or name, q to quit): ").strip()
    if raw.lower() in {"", "q", "quit"}:
        raise SystemExit(0)
    if raw.isdigit() and 1 <= int(raw) <= len(SCENARIOS):
        return SCENARIOS[int(raw) - 1]
    return normalize_scenario(raw)


def main(argv: list[str] | None = None, *, code_commit: str | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--scenario", help="A, B, B-fault or B-progress (any letter case)")
    group.add_argument("--all", action="store_true", help="run all four scenarios (rules-v1)")
    group.add_argument("--list", action="store_true", help="list scenarios and exit")
    group.add_argument(
        "--replay", type=Path, metavar="RUN_DIR", help="replay a saved run from disk"
    )
    parser.add_argument(
        "--policy", default=DEFAULT_POLICY, help="rules-v1 (default), greedy_a, greedy_b"
    )
    parser.add_argument(
        "--out-dir", type=Path, default=None, help="NEW or empty directory for traces"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output on stdout")
    args = parser.parse_args(argv)
    command = "python -m dc_sustainability.rule_demo " + " ".join(
        argv if argv is not None else sys.argv[1:]
    )
    try:
        if args.list:
            if args.json:
                print(json.dumps(DESCRIPTIONS, indent=2))
            else:
                for name in SCENARIOS:
                    print(f"{name}: {DESCRIPTIONS[name]}")
            return 0
        if args.replay is not None:
            reports = replay_path(args.replay)
            print(json.dumps(reports, indent=2, sort_keys=True))
            return 0 if all(rep["status"] == "pass" for rep in reports) else 1
        if args.all:
            names = list(SCENARIOS)
        elif args.scenario:
            names = [normalize_scenario(args.scenario)]
        elif sys.stdin.isatty():
            names = [_interactive_choice()]
        else:
            parser.print_usage(sys.stderr)
            print(
                "no scenario given and stdin is not a terminal; use --scenario, --all or --list",
                file=sys.stderr,
            )
            return 2
        policy = DEFAULT_POLICY if args.all else args.policy
        out_dir = _fresh_out_dir(args.out_dir)
        expectations = load_expectations()
        runs = [run_scenario(n, policy, out_dir, code_commit=code_commit) for n in names]
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except BindingError as exc:
        print(f"cannot bind the required artifacts: {exc}", file=sys.stderr)
        return 2
    summary = summary_record(runs, expectations, command)
    summary_path = _write_summary(out_dir, summary)
    if args.json:
        print(json.dumps({"summary_path": str(summary_path), **summary}, indent=2, sort_keys=True))
    else:
        for sr in runs:
            rows = compare_with_expectation(sr.scenario, sr.observed)
            print(render(sr, expectations[sr.scenario], rows))
        print(f"\nsummary: {summary_path}")
    return 0 if all(sr.replay["status"] == "pass" for sr in runs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
