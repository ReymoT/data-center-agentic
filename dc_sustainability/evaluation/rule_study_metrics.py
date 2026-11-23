"""RULE-04: metric records from retained rule-study run folders (#242).

Implements the metrics Edison accepted in #239 (issuecomment-7052918378) over saved
``rule_study_decision_v1`` / ``rule_study_result_v1`` records. It reads files only: no
policy, scheduler, checker or simulator runs, and nothing is imported from them.

Per run (one case x one policy):

- execution violations: executed starts whose selected stage did not pass its recorded
  check, with checked-decision and executed-start denominators;
- completed, missed and unfinished job counts;
- turnaround (end - arrival) and start delay (start - arrival) for completed jobs, with
  the count they are taken over;
- fallback attempts, fallback selections and blocked decisions with their error codes;
- artificial synthetic impact in score-kWh, recomputed from the case weights and the
  executed per-job intervals and compared with the producer's own total.

Equal-work reduction versus Greedy A is (A - X) / A only when the completed, missed and
unfinished job-ID sets and the case hash match and A > 0. Otherwise it is unavailable
with a reason, never zero. Scores are artificial weights, not g/kWh or emissions.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

RECORD_KIND = "rule_study_metrics_v1"
BASELINE_POLICY = "greedy_a"
FALLBACK_ORIGIN = "greedy_a_fallback"
IMPACT_UNIT = "score-kWh (artificial score weight x kWh; not g/kWh, not emissions)"


def _load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_run(folder: Path) -> tuple[dict, dict, list[dict]]:
    """Read case.json, result.json and decisions/decision-NN.json in index order."""
    folder = Path(folder)
    case = _load(folder / "case.json")
    result = _load(folder / "result.json")
    decisions = [_load(p) for p in sorted((folder / "decisions").glob("decision-*.json"))]
    indexes = [d["decision_index"] for d in decisions]
    if indexes != list(range(len(decisions))):
        raise ValueError(f"{folder}: decision indexes are not contiguous from 0")
    if result.get("record_kind") != "rule_study_result_v1":
        raise ValueError(f"{folder}: unsupported result record")
    if result["case_id"] != case["case_id"]:
        raise ValueError(f"{folder}: result and case IDs differ")
    return case, result, decisions


def _selected_stage(decision: Mapping) -> Mapping | None:
    selected = decision.get("selected_stage_id")
    for stage in decision.get("proposal_stages", []):
        if stage.get("stage_id") == selected:
            return stage
    return None


def _impact(case: Mapping, per_job: Sequence[Mapping], pue: float, slot_hours: float) -> float:
    weights = case["scores"]
    total = 0.0
    for job in per_job:
        for slot in range(job["start_slot"], job["end_slot"]):
            total += job["power_kw"] * slot_hours * pue * weights[slot]
    return total


def run_metrics(case: Mapping, result: Mapping, decisions: Sequence[Mapping]) -> dict:
    accounting = result["accounting"]
    arrivals = {j["job_id"]: j["arrival_slot"] for j in case["jobs"]}
    completed = set(result["completed_job_ids"])
    per_job = [j for j in accounting["per_job"] if j["job_id"] in completed]

    checked = [d for d in decisions if d.get("proposal_stages")]
    executed_starts = 0
    violations = 0
    fallback_attempts = 0
    fallback_selected = 0
    blocked = 0
    error_codes: Counter = Counter()
    for decision in decisions:
        starts = decision["execution"]["current_starts"]
        executed_starts += len(starts)
        stage = _selected_stage(decision)
        if starts and (stage is None or stage["check_result"]["status"] != "pass"):
            violations += len(starts)
        origins = [s.get("origin") for s in decision.get("proposal_stages", [])]
        fallback_attempts += origins.count(FALLBACK_ORIGIN)
        if stage is not None and stage.get("origin") == FALLBACK_ORIGIN:
            fallback_selected += 1
        if decision["execution"]["status"] == "blocked":
            blocked += 1
        error_codes.update(e["code"] for e in decision.get("errors", []))

    turnaround = [j["end_slot"] - arrivals[j["job_id"]] for j in per_job]
    delay = [j["start_slot"] - arrivals[j["job_id"]] for j in per_job]
    weights_visible = case.get("scores") is not None
    recomputed = (
        _impact(case, per_job, accounting["pue"], accounting["slot_hours"])
        if weights_visible
        else None
    )
    return {
        "case_id": result["case_id"],
        "policy_id": result["policy_id"],
        "case_sha256": result["bindings"]["case_sha256"],
        "code_commit": result["bindings"]["code_commit"],
        "status": result["status"],
        "decisions": len(decisions),
        "checked_decisions": len(checked),
        "executed_starts": executed_starts,
        "execution_violations": violations,
        "jobs": len(case["jobs"]),
        "completed": len(completed),
        "missed": len(result["missed_job_ids"]),
        "unfinished": len(result["unfinished_job_ids"]),
        "completed_job_ids": sorted(completed),
        "missed_job_ids": sorted(result["missed_job_ids"]),
        "unfinished_job_ids": sorted(result["unfinished_job_ids"]),
        "turnaround_slots": {"values": sorted(turnaround), "count": len(turnaround)},
        "start_delay_slots": {"values": sorted(delay), "count": len(delay)},
        "fallback": {
            "attempted_stages": fallback_attempts,
            "selected": fallback_selected,
            "blocked_decisions": blocked,
            "error_codes": dict(sorted(error_codes.items())),
        },
        "synthetic_impact": {
            "unit": IMPACT_UNIT,
            "producer_total": accounting["synthetic_impact_total"],
            "recomputed_total": recomputed,
            "matches_producer": None
            if recomputed is None
            else abs(recomputed - accounting["synthetic_impact_total"]) < 1e-9,
        },
    }


def equal_work(records: Sequence[Mapping]) -> list[dict]:
    """Per case, each non-baseline policy against Greedy A, or unavailable with a reason."""
    baseline = {r["case_id"]: r for r in records if r["policy_id"] == BASELINE_POLICY}
    out = []
    for record in records:
        if record["policy_id"] == BASELINE_POLICY:
            continue
        row = {"case_id": record["case_id"], "policy_id": record["policy_id"]}
        base = baseline.get(record["case_id"])
        reason = None
        if base is None:
            reason = "no_greedy_a_run_for_case"
        elif base["case_sha256"] != record["case_sha256"]:
            reason = "case_hash_differs"
        elif any(
            base[k] != record[k]
            for k in ("completed_job_ids", "missed_job_ids", "unfinished_job_ids")
        ):
            reason = "job_outcome_sets_differ"
        else:
            a = base["synthetic_impact"]["producer_total"]
            x = record["synthetic_impact"]["producer_total"]
            if not a > 0:
                reason = "greedy_a_impact_not_positive"
            else:
                row.update(
                    {
                        "available": True,
                        "greedy_a_total": a,
                        "policy_total": x,
                        "reduction": (a - x) / a,
                    }
                )
        if reason is not None:
            row.update({"available": False, "reason": reason})
        out.append(row)
    return out


def metrics_report(folders: Sequence[Path], *, label: str) -> dict:
    records = []
    for folder in folders:
        case, result, decisions = load_run(folder)
        records.append(run_metrics(case, result, decisions))
    records.sort(key=lambda r: (r["case_id"], r["policy_id"]))
    return {
        "record_kind": RECORD_KIND,
        "label": label,
        "metrics_source_sha256": hashlib.sha256(
            Path(__file__).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest(),
        "runs": records,
        "equal_work_vs_greedy_a": equal_work(records),
        "notes": [
            "Computed from retained records only; no policy, checker or simulator ran.",
            "Unavailable comparisons stay unavailable, never zero.",
            "Scores are artificial weights; nothing here concerns emissions.",
        ],
    }
