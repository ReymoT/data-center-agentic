"""RULE-03: independent check of synthetic case sets before evaluation (#241, #242).

RULE-01 review-2 decision 6 asks Nisha to verify, independently of Edison's generator:

- each case's feasibility label, using the verifier's own brute-force joint-assignment
  oracle and, within a budget, the legal-action-graph oracle as a cross-check;
- that each case meets its stratum's acceptance predicate from the specification;
- per-stratum counts, full-case diversity and workload-only diversity (actual counts,
  never assumed);
- no overlap between the final set, the development set and the authored examples.

Generator labels are claims to be checked, never a safety oracle. Standard library only;
no generator, scheduler, checker or simulator import.

Input shape (this checker's assumption until RULE-04 publishes its format): a JSON object
``{"set_id": str, "cases": [case, ...]}`` where each case has the trace reader's case
fields (``case_id``, ``capacity_kw``, ``background_kw``, ``jobs``, and ``scores`` (null when
no forecast is visible) or ``first_scores`` + ``remaining_score``) plus ``stratum`` and
``feasibility_label`` (``jointly_feasible`` or ``jointly_infeasible``). Only explicitly
named metadata fields are ignored; unsupported semantic fields are refused.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

from dc_sustainability.evaluation import rule_study_trace as tr
from dc_sustainability.evaluation import rule_study_verifier as v

RECORD_KIND = "rule_study_case_set_check_v1"
SUPPORTED_SPEC_SHA256 = "9597931fcee09bc895605b65401483c9c3658da9e0bdf7c954f8669dfa8542bd"
# Reader resource limits, not new scientific sample counts or execution permission.
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_SETS = 2
MAX_CASES_PER_SET = 120
CASE_FIELDS = frozenset(
    {
        "case_id",
        "capacity_kw",
        "background_kw",
        "jobs",
        "scores",
        "first_scores",
        "remaining_score",
        "fault_starts",
        "stratum",
        "feasibility_label",
        "metadata",
        "generator_attempt",
    }
)
JOB_FIELDS = frozenset(
    {"job_id", "power_kw", "duration_slots", "arrival_slot", "deadline_slot", "flexible"}
)
STRATA = ("normal_feasible", "overloaded_impossible", "missing_forecast")
LABELS = ("jointly_feasible", "jointly_infeasible")
AUTHORED_SLOTS = 6  # scores for slots 0-5 are drawn; later slots use the drain score

# Review-2 generator proposal (RULE01_SPECIFICATION.md, specification.json).
SITE = {"capacity_kw": 60, "background_kw": 20}
POWERS = frozenset({10, 20, 30})
DURATIONS = frozenset({1, 2})
ARRIVALS = frozenset({0, 1, 2})
SLACKS = frozenset({0, 1, 2})
MAX_DEADLINE = 6
SCORE_VALUES = frozenset({100, 200, 300})
DRAIN_SCORE = 200
JOB_COUNTS = {
    "normal_feasible": frozenset({2, 3, 4}),
    "overloaded_impossible": frozenset({3, 4}),
    "missing_forecast": frozenset({2, 3, 4}),
}
CONFLICT_PAIR = (("J1", 30, 1, 0, 1, False), ("J2", 30, 1, 0, 1, False))


def _job_tuple(job: v.Job) -> tuple:
    return (
        job.job_id,
        job.power_kw,
        job.duration_slots,
        job.arrival_slot,
        job.deadline_slot,
        job.flexible,
    )


def workload_identity(case: v.Case) -> dict:
    """Physical workload only: sorted jobs plus site and horizon, no scores or IDs of case."""
    return {
        "capacity_kw": case.capacity_kw,
        "background_kw": case.background_kw,
        "horizon": v.HORIZON,
        "jobs": [list(_job_tuple(j)) for j in sorted(case.jobs, key=lambda j: j.job_id)],
    }


def case_identity(case: v.Case) -> dict:
    """Workload plus the visible synthetic profile (None when no forecast is visible)."""
    return {**workload_identity(case), "scores": None if case.scores is None else list(case.scores)}


def oracle_label(case: v.Case, budget: v.Budget) -> str:
    witness, _ = v.completion_witness(case, v.initial_state(), budget=budget)
    return "jointly_feasible" if witness is not None else "jointly_infeasible"


def _validate_budget(budget: v.Budget) -> None:
    if budget.max_states > 10_000 or budget.max_transitions > 50_000 or budget.max_seconds > 600:
        raise ValueError("budget exceeds prospective combined 10000/50000/600 ceilings")


def _validate_set(data: Mapping) -> None:
    if not isinstance(data, Mapping) or not isinstance(data.get("cases"), list):
        raise ValueError("case set must be an object with a cases list")
    if set(data) - {"set_id", "cases", "metadata"}:
        raise ValueError("unsupported case-set fields")
    if not isinstance(data.get("set_id"), str) or not data["set_id"].strip():
        raise ValueError("case set needs a nonempty set_id")
    if len(data["cases"]) > MAX_CASES_PER_SET:
        raise ValueError("case-set reader limit exceeded")


def _case_from_dict(raw: Mapping) -> v.Case:
    if not isinstance(raw, Mapping) or set(raw) - CASE_FIELDS:
        raise ValueError("unsupported case fields")
    if not isinstance(raw.get("case_id"), str) or not raw["case_id"].strip():
        raise ValueError("nonempty case_id required")
    if "scores" in raw and ("first_scores" in raw or "remaining_score" in raw):
        raise ValueError("conflicting score encodings")
    if "scores" not in raw:
        if (
            not isinstance(raw.get("first_scores"), list)
            or not 1 <= len(raw["first_scores"]) <= v.HORIZON
        ):
            raise ValueError("invalid compact score profile")
    elif raw["scores"] is not None and not isinstance(raw["scores"], list):
        raise ValueError("scores must be a list or null")
    if not isinstance(raw.get("jobs"), list) or not 1 <= len(raw["jobs"]) <= 4:
        raise ValueError("jobs must contain one to four entries")
    if any(not isinstance(j, Mapping) or set(j) != JOB_FIELDS for j in raw["jobs"]):
        raise ValueError("unsupported or missing job fields")
    if "fault_starts" in raw and not isinstance(raw["fault_starts"], list):
        raise ValueError("fault_starts must be a list")
    return tr.case_from_dict(raw)


def predicate_findings(case: v.Case, stratum: str, label: str) -> list[str]:
    """Spec acceptance predicate for the case's stratum; empty list means it conforms."""
    out = []
    if {"capacity_kw": case.capacity_kw, "background_kw": case.background_kw} != SITE:
        out.append("site_parameters")
    if len(case.jobs) not in JOB_COUNTS[stratum]:
        out.append("job_count")
    jobs = sorted(case.jobs, key=lambda j: j.job_id)
    expected_ids = [f"J{i}" for i in range(1, len(jobs) + 1)]
    if [j.job_id for j in jobs] != expected_ids:
        out.append("job_ids")
    conflict = stratum == "overloaded_impossible"
    for job in jobs:
        if conflict and _job_tuple(job) in CONFLICT_PAIR:
            continue
        if job.power_kw not in POWERS or job.duration_slots not in DURATIONS:
            out.append(f"job_values:{job.job_id}")
        elif job.arrival_slot not in ARRIVALS:
            out.append(f"arrival:{job.job_id}")
        else:
            slack_ok = any(
                job.deadline_slot == min(MAX_DEADLINE, job.arrival_slot + job.duration_slots + s)
                for s in SLACKS
            )
            if not slack_ok:
                out.append(f"deadline:{job.job_id}")
    if conflict:
        present = {_job_tuple(j) for j in jobs}
        if not all(pair in present for pair in CONFLICT_PAIR):
            out.append("missing_conflict_pair")
    if stratum == "missing_forecast":
        if case.scores is not None:
            out.append("forecast_visible")
    else:
        if case.scores is None:
            out.append("forecast_missing")
        else:
            head, tail = case.scores[:AUTHORED_SLOTS], case.scores[AUTHORED_SLOTS:]
            if not set(head) <= SCORE_VALUES or any(s != DRAIN_SCORE for s in tail):
                out.append("score_values")
            if stratum == "normal_feasible" and len(set(head)) == 1:
                out.append("constant_profile")
    if stratum in ("normal_feasible", "missing_forecast"):
        if not any(j.flexible for j in jobs):
            out.append("no_flexible_job")
        if label != "jointly_feasible":
            out.append("stratum_requires_feasible")
    if stratum == "overloaded_impossible" and label != "jointly_infeasible":
        out.append("stratum_requires_infeasible")
    if case.fault_injected:
        out.append("fault_injection_in_evaluation_case")
    return out


def check_case_set(
    data: Mapping,
    *,
    expected_per_stratum: int | None = 40,
    graph_budget: v.Budget | None = None,
) -> dict:
    """Check one case set; returns its section of the report (without overlap)."""
    _validate_set(data)
    set_id = data["set_id"]
    if expected_per_stratum is not None and (
        type(expected_per_stratum) is not int or not 1 <= expected_per_stratum <= 40
    ):
        raise ValueError("expected count must be a positive integer at most 40 or None")
    graph_budget = graph_budget if graph_budget is not None else v.Budget()
    _validate_budget(graph_budget)
    rows, malformed = [], []
    for n, raw in enumerate(data["cases"]):
        try:
            if raw.get("stratum") not in STRATA:
                raise ValueError(f"stratum {raw.get('stratum')!r}")
            if raw.get("feasibility_label") not in LABELS:
                raise ValueError(f"feasibility_label {raw.get('feasibility_label')!r}")
            case = _case_from_dict(raw)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            malformed.append({"index": n, "case_id": _safe_id(raw), "reason": str(exc)})
            continue
        rows.append((raw, case))

    label_mismatches, predicate_failures, crosscheck = [], [], Counter()
    unchecked_labels, crosscheck_mismatches = [], []
    by_stratum: dict[str, dict] = {
        s: {"cases": 0, "full": set(), "workload": set()} for s in STRATA
    }
    full_hashes, workload_hashes, ids = Counter(), Counter(), Counter()
    for raw, case in rows:
        stratum = raw["stratum"]
        ids[case.case_id] += 1
        # Refuse out-of-domain inputs before expensive enumeration. Labels here
        # remain claims; the independently computed label is checked below.
        findings = predicate_findings(case, stratum, raw["feasibility_label"])
        if findings:
            predicate_failures.append(
                {"case_id": case.case_id, "stratum": stratum, "findings": findings}
            )
        invalid_domain = set(findings) - {
            "stratum_requires_feasible",
            "stratum_requires_infeasible",
        }
        if invalid_domain:
            unchecked_labels.append(case.case_id)
            crosscheck["not_run_invalid_predicate"] += 1
        elif graph_budget.max_seconds == 0 or not graph_budget.check_time():
            unchecked_labels.append(case.case_id)
            crosscheck["incomplete"] += 1
        else:
            try:
                label = oracle_label(case, graph_budget)
            except v.BudgetStopped:
                unchecked_labels.append(case.case_id)
                crosscheck["incomplete"] += 1
            else:
                if label != raw["feasibility_label"]:
                    label_mismatches.append(
                        {
                            "case_id": case.case_id,
                            "generator": raw["feasibility_label"],
                            "oracle": label,
                        }
                    )
                # Stratum feasibility must agree with the computed oracle too.
                actual = predicate_findings(case, stratum, label)
                if actual:
                    predicate_failures.append(
                        {"case_id": case.case_id, "stratum": stratum, "findings": actual}
                    )
                _, graph_done, complete = v.explore_legal_graph(
                    case, graph_budget, f"{set_id}/labels"
                )
                if not complete:
                    crosscheck["incomplete"] += 1
                elif graph_done == (label == "jointly_feasible"):
                    crosscheck["agreements"] += 1
                else:
                    crosscheck["mismatches"] += 1
                    crosscheck_mismatches.append(case.case_id)
        full = v.canonical_sha256(case_identity(case))
        work = v.canonical_sha256(workload_identity(case))
        full_hashes[full] += 1
        workload_hashes[work] += 1
        bucket = by_stratum[stratum]
        bucket["cases"] += 1
        bucket["full"].add(full)
        bucket["workload"].add(work)

    strata = {
        s: {
            "cases": b["cases"],
            "distinct_full_cases": len(b["full"]),
            "distinct_workloads": len(b["workload"]),
            "expected": expected_per_stratum,
        }
        for s, b in by_stratum.items()
    }
    count_failures = [
        s
        for s, row in strata.items()
        if expected_per_stratum is not None and row["cases"] != expected_per_stratum
    ]
    duplicates = sorted(h for h, n in full_hashes.items() if n > 1)
    duplicate_ids = sorted(i for i, n in ids.items() if n > 1)
    checks = {
        "well_formed": _verdict(not malformed, len(data["cases"])),
        "feasibility_labels": {"status": "FAIL", "checked": len(rows) - len(unchecked_labels)}
        if label_mismatches
        else {"status": "INCOMPLETE", "reason": "unexamined labels"}
        if unchecked_labels
        else _verdict(True, len(rows)),
        "stratum_predicates": _verdict(not predicate_failures, len(rows)),
        "stratum_counts": _verdict(not count_failures, len(STRATA))
        if expected_per_stratum is not None
        else {"status": "NOT_RUN", "reason": "no expected count given"},
        "no_duplicate_cases": _verdict(not duplicates and not duplicate_ids, len(rows)),
        "oracle_crosscheck": (
            {"status": "FAIL", "checked": len(rows)}
            if crosscheck["mismatches"]
            else {"status": "INCOMPLETE", "reason": "legal-graph budget hit"}
            if crosscheck["incomplete"] or unchecked_labels
            else _verdict(True, len(rows))
        ),
    }
    return {
        "set_id": set_id,
        "input_sha256": v.canonical_sha256(data),
        "cases": len(data["cases"]),
        "strata": strata,
        "distinct_workloads_total": len(workload_hashes),
        "checks": checks,
        "malformed": malformed,
        "label_mismatches": label_mismatches,
        "predicate_failures": predicate_failures,
        "duplicate_full_case_hashes": duplicates,
        "duplicate_case_ids": duplicate_ids,
        "oracle_crosscheck_counts": dict(crosscheck),
        "oracle_crosscheck_mismatched_case_ids": crosscheck_mismatches,
        "unexamined_label_case_ids": unchecked_labels,
        "_full": set(full_hashes),
        "_workload": set(workload_hashes),
    }


def _verdict(ok: bool, checked: int) -> dict:
    if checked == 0:
        return {"status": "NOT_RUN", "reason": "nothing to check", "checked": 0}
    return {"status": "PASS" if ok else "FAIL", "checked": checked}


def _safe_id(raw) -> str | None:
    return raw.get("case_id") if isinstance(raw, Mapping) else None


def authored_identities(spec: Mapping) -> tuple[set[str], set[str]]:
    cases = [c for c in v.authored_cases(spec) if not c.fault_injected]
    return (
        {v.canonical_sha256(case_identity(c)) for c in cases},
        {v.canonical_sha256(workload_identity(c)) for c in cases},
    )


def check_case_sets(
    sets: Sequence[Mapping],
    *,
    spec: Mapping,
    expected_per_stratum: Mapping[str, int | None] | None = None,
    graph_budget: v.Budget | None = None,
) -> dict:
    """Check each set, then cross-set and authored-example overlap. Any full overlap fails."""
    if v.canonical_sha256(spec) != SUPPORTED_SPEC_SHA256:
        raise ValueError("unsupported specification revision; review checker assumptions first")
    if not isinstance(sets, (list, tuple)) or not 1 <= len(sets) <= MAX_SETS:
        raise ValueError("supply one or two case sets")
    for data in sets:
        _validate_set(data)
    ids = [s["set_id"] for s in sets]
    if len(set(ids)) != len(ids):
        raise ValueError("set_id values must be distinct")
    expected_per_stratum = expected_per_stratum if expected_per_stratum is not None else {}
    if not isinstance(expected_per_stratum, Mapping) or set(expected_per_stratum) - set(ids):
        raise ValueError("expected counts reference unknown set IDs")
    graph_budget = graph_budget if graph_budget is not None else v.Budget()
    _validate_budget(graph_budget)
    sections = [
        check_case_set(
            s,
            expected_per_stratum=expected_per_stratum.get(s["set_id"], 40),
            graph_budget=graph_budget,
        )
        for s in sets
    ]
    authored_full, authored_work = authored_identities(spec)
    overlaps = []
    for i, a in enumerate(sections):
        others = [("authored", authored_full, authored_work)] + [
            (b["set_id"], b["_full"], b["_workload"]) for b in sections[i + 1 :]
        ]
        for name, full, work in others:
            overlaps.append(
                {
                    "pair": [a["set_id"], name],
                    "full_case_overlap": len(a["_full"] & full),
                    "workload_overlap": len(a["_workload"] & work),
                }
            )
    ids = [s["set_id"] for s in sections]
    if len(set(ids)) != len(ids):
        raise ValueError("set_id values must be distinct")
    for s in sections:
        s.pop("_full")
        s.pop("_workload")
    full_overlap = any(o["full_case_overlap"] for o in overlaps)
    report = {
        "record_kind": RECORD_KIND,
        "checker_source_sha256": _own_sha256(),
        "verifier_source_sha256": v.source_sha256(),
        "parser_source_sha256": hashlib.sha256(
            Path(tr.__file__).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest(),
        "spec_sha256": v.canonical_sha256(spec),
        "sets": sections,
        "budget": graph_budget.summary(),
        "study_acceptance": "NOT_ESTABLISHED",
        "scope": "supplied cases and supplied-set pairs only; not seed/provenance/freeze or generator acceptance",
        "unseen_isolation": "INCOMPLETE: no second set supplied"
        if len(sets) < 2
        else "supplied-pair content overlap checked; roles and provenance not authenticated",
        "missing_forecast_accounting": "not checked: visible scores are null; private evaluator-only weights not supplied or authenticated",
        "overlap": overlaps,
        "checks": {
            "no_full_case_overlap": {
                "status": "FAIL" if full_overlap else "PASS",
                "pairs": len(overlaps),
            },
            "workload_overlap": {
                "status": "REPORTED",
                "note": "shared workloads with different profiles are reported, not rejected",
            },
        },
        "overall": "PASS"
        if not full_overlap
        and all(c["status"] == "PASS" for s in sections for c in s["checks"].values())
        else (
            "FAIL"
            if full_overlap
            or any(c["status"] == "FAIL" for s in sections for c in s["checks"].values())
            else "INCOMPLETE"
        ),
        "notes": [
            "Labels come from the independent brute-force oracle; generator labels are claims.",
            "Predicates follow the review-2 generator proposal; a later accepted protocol "
            "revision needs a matching checker revision.",
            "Scores are artificial weights; nothing here concerns emissions.",
        ],
    }
    return report


def load_case_set(path: Path) -> Mapping:
    with Path(path).open("rb") as handle:
        raw = handle.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("case-set input byte limit exceeded")

    def pairs(items):
        data = {}
        for key, value in items:
            if key in data:
                raise ValueError("duplicate JSON key")
            data[key] = value
        return data

    def reject_constant(value):
        raise ValueError("nonfinite JSON number")

    data = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)
    _validate_set(data)
    return data


def _own_sha256() -> str:
    import hashlib

    return hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
