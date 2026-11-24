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
import math
from collections import Counter
from itertools import islice
from pathlib import Path
from typing import Mapping, Sequence

RECORD_KIND = "rule_study_metrics_v1"
BASELINE_POLICY = "greedy_a"
FALLBACK_ORIGIN = "greedy_a_fallback"
IMPACT_UNIT = "score-kWh (artificial score weight x kWh; not g/kWh, not emissions)"
MAX_BYTES = 8 * 1024 * 1024


def _pairs(items):
    obj = {}
    for key, value in items:
        if key in obj:
            raise ValueError("duplicate JSON key")
        obj[key] = value
    return obj


def _bytes(path):
    path = Path(path)
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError("linked metric input refused")
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("oversized metric input")
    return raw


def _constant(_):
    raise ValueError("nonfinite JSON number")


def _load(path: Path) -> dict:
    value = json.loads(_bytes(path), object_pairs_hook=_pairs, parse_constant=_constant)
    if not isinstance(value, dict):
        raise ValueError("metric input must be an object")
    return value


def load_run(folder: Path) -> tuple[dict, dict, list[dict]]:
    """Read case.json, result.json and decisions/decision-NN.json in index order."""
    folder = Path(folder)
    case = _load(folder / "case.json")
    result = _load(folder / "result.json")
    decision_paths = list(islice((folder / "decisions").glob("decision-*.json"), 31))
    if len(decision_paths) > 30:
        raise ValueError("too many decision records")
    decisions = [_load(p) for p in sorted(decision_paths)]
    indexes = [d["decision_index"] for d in decisions]
    if indexes != list(range(len(decisions))):
        raise ValueError(f"{folder}: decision indexes are not contiguous from 0")
    if result.get("record_kind") != "rule_study_result_v1":
        raise ValueError(f"{folder}: unsupported result record")
    if result["case_id"] != case["case_id"]:
        raise ValueError(f"{folder}: result and case IDs differ")
    from dc_sustainability.evaluation import rule_study_receiving as receiving
    from dc_sustainability.evaluation import rule_study_trace as trace

    if result.get("status") != "complete" or len(decisions) != 30:
        raise ValueError("incomplete trace cannot supply accepted run metrics")
    paths = [folder / "case.json", folder / "result.json"] + sorted(
        (folder / "decisions").glob("decision-*.json")
    )
    before = [hashlib.sha256(_bytes(p)).hexdigest() for p in paths]
    # Parse/check retained bytes only. Neither helper executes a policy or replay.
    findings = receiving.check_trace_artifacts(folder, result["bindings"])
    if findings:
        raise ValueError(f"retained artifact integrity refused: {findings[:3]}")
    trace.read_trace(case, decisions, result, expected_spec_sha256=receiving.ACCEPTED_SPEC)
    if before != [hashlib.sha256(_bytes(p)).hexdigest() for p in paths]:
        raise ValueError("metric input changed during validation")
    if case != _load(folder / "case.json") or result != _load(folder / "result.json"):
        raise ValueError("metric input changed during validation")
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
    jobs = {j["job_id"]: j for j in case["jobs"]}
    if len(jobs) != len(case["jobs"]):
        raise ValueError("duplicate case job")
    completed = set(result["completed_job_ids"])
    if len(completed) != len(result["completed_job_ids"]) or not completed <= jobs.keys():
        raise ValueError("invalid completed job set")
    outcomes = []
    for name in ("completed_job_ids", "missed_job_ids", "unfinished_job_ids"):
        ids = result[name]
        if len(ids) != len(set(ids)) or not set(ids) <= jobs.keys():
            raise ValueError("invalid job outcome identities")
        outcomes.append(set(ids))
    if outcomes[0] & (outcomes[1] | outcomes[2]) or set.union(*outcomes) != jobs.keys():
        raise ValueError("job outcome coverage differs from case")
    per_job = accounting["per_job"]
    ids = [j["job_id"] for j in per_job]
    if len(ids) != len(set(ids)) or set(ids) != completed:
        raise ValueError("accounting job coverage differs from completed jobs")
    for record in per_job:
        job = jobs[record["job_id"]]
        start, end = record["start_slot"], record["end_slot"]
        if (
            type(start) is not int
            or type(end) is not int
            or not job["arrival_slot"] <= start < end <= min(30, job["deadline_slot"])
            or end - start != job["duration_slots"]
            or record["power_kw"] != job["power_kw"]
        ):
            raise ValueError("accounting interval or power differs from case")
    for name in ("pue", "slot_hours"):
        value = accounting[name]
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("invalid accounting scale")
    total = accounting["synthetic_impact_total"]
    if total is not None and (
        type(total) not in (int, float) or not math.isfinite(total) or total < 0
    ):
        raise ValueError("invalid producer impact")

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
        elif starts and "plan" in stage:
            selected = {
                s["job_id"]
                for s in stage["plan"]["starts"]
                if s["start_slot"] == decision["decision_index"]
            }
            actual = set(starts)
            if (
                actual != selected
                or len(actual) != len(starts)
                or decision["execution"]["status"] != "executed"
                or decision["execution"].get("simulator_rejection") is not None
            ):
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
        "bindings": dict(result["bindings"]),
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
            if recomputed is None or total is None
            else abs(recomputed - accounting["synthetic_impact_total"]) < 1e-9,
        },
    }


def equal_work(records: Sequence[Mapping]) -> list[dict]:
    """Per case, each non-baseline policy against Greedy A, or unavailable with a reason."""
    keys = [(r["case_id"], r["policy_id"]) for r in records]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate case/policy metric record")
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
        elif base["code_commit"] != record["code_commit"] or base["bindings"] != record["bindings"]:
            reason = "source_bindings_differ"
        elif any(r["status"] != "complete" for r in (base, record)):
            reason = "incomplete_run"
        elif any(r["execution_violations"] != 0 for r in (base, record)):
            reason = "recorded_execution_violation"
        elif any(r["synthetic_impact"]["matches_producer"] is not True for r in (base, record)):
            reason = "impact_unverified_or_mismatched"
        elif any(
            base[k] != record[k]
            for k in ("completed_job_ids", "missed_job_ids", "unfinished_job_ids")
        ):
            reason = "job_outcome_sets_differ"
        else:
            a = base["synthetic_impact"]["recomputed_total"]
            x = record["synthetic_impact"]["recomputed_total"]
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
    if not folders or len(folders) > 360:
        raise ValueError("metric report requires 1..360 supplied folders")
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
            "Artifact consistency is checked; external source authentication and independent metric acceptance remain separate.",
            "Execution violations count recorded gate/current-selection conflicts, not a new independent physical-safety verdict.",
        ],
    }
