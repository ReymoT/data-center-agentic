"""Contained final-generation backend; imported only after exact host release.

No CLI. Tests use authored proposals and the known development RNG for equivalence,
never the final seed. Existing development generator and its accepted scientific pins stay intact.
"""

import hashlib
import math
from collections import Counter
from pathlib import Path
from time import monotonic

from dc_sustainability.evaluation import rule_study_generator as g


def build(rng, development, limits, *, draw=g.draw_proposal, authorization_id=None):
    """Use the accepted draw/predicate order with actual retained-set exclusion.

    Feasibility assignments are conservatively charged as the complete Cartesian
    product before each predicate call, even if its witness search returns early.
    An outer contained supervisor enforces wall/output stops independently.
    """
    authored = g.authored_full_identities(g.load_specification())
    # Identity must use the canonical job-list convention, not serialized dictionaries.
    excluded = set()
    for case in development["cases"]:
        jobs = tuple(g.Job(**j) for j in case["jobs"])
        scores = None if case["scores"] is None else tuple(case["scores"])
        excluded.add(
            g.canonical_sha256(
                g.full_case_identity(jobs, case["capacity_kw"], case["background_kw"], scores)
            )
        )
    counters = {"proposals": 0, "feasibility_assignments_reserved": 0}
    deadline = monotonic() + limits["wall_seconds"]
    seen, cases, weights, report = set(), [], [], {}
    for stratum in g.STRATA:
        rejected, accepted, attempts = Counter(), 0, 0
        stratum_full, stratum_workloads = set(), set()
        while accepted < 40:
            if (
                attempts >= g.MAX_ATTEMPTS_PER_STRATUM
                or counters["proposals"] >= limits["proposals"]
                or monotonic() >= deadline
            ):
                raise ValueError("generation proposal/time ceiling; no retry")
            proposal = draw(rng, stratum)
            attempts += 1
            counters["proposals"] += 1
            reserve = math.prod(len(j.legal_starts()) for j in proposal.jobs)
            counters["feasibility_assignments_reserved"] += reserve
            if counters["feasibility_assignments_reserved"] > limits["feasibility_assignments"]:
                raise ValueError("generation conservative feasibility ceiling; no retry")
            scores = g.visible_scores(proposal, stratum)
            full = g.canonical_sha256(
                g.full_case_identity(proposal.jobs, g.CAPACITY_KW, g.BACKGROUND_KW, scores)
            )
            reason = g.rejection_reason(proposal, stratum)
            if reason is None:
                reason = (
                    "duplicate_full_case"
                    if full in seen
                    else "authored_overlap"
                    if full in authored
                    else "development_overlap"
                    if full in excluded
                    else None
                )
            if reason:
                rejected[reason] += 1
                continue
            seen.add(full)
            workload = g.canonical_sha256(
                g.workload_identity(proposal.jobs, g.CAPACITY_KW, g.BACKGROUND_KW)
            )
            stratum_full.add(full)
            stratum_workloads.add(workload)
            ident = f"final-{stratum}-{accepted:02d}"
            cases.append(
                {
                    "case_id": ident,
                    "capacity_kw": g.CAPACITY_KW,
                    "background_kw": g.BACKGROUND_KW,
                    "jobs": [j.as_dict() for j in proposal.jobs],
                    "scores": None if scores is None else list(scores),
                    "stratum": stratum,
                    "feasibility_label": "jointly_infeasible"
                    if stratum == "overloaded_impossible"
                    else "jointly_feasible",
                    "generator_attempt": attempts,
                }
            )
            weights.append(
                {
                    "case_id": ident,
                    "full_case_sha256": full,
                    "workload_sha256": workload,
                    "weights": list(proposal.weights),
                    "weights_visible_to_policy": scores is not None,
                }
            )
            accepted += 1
        report[stratum] = {
            "accepted": accepted,
            "attempts": attempts,
            "rejected": dict(rejected),
            "distinct_full_case_hashes": len(stratum_full),
            "distinct_workload_hashes": len(stratum_workloads),
        }
    case_set = {
        "set_id": f"{g.STUDY_ID}-final",
        "cases": cases,
        "metadata": {
            "record_kind": g.RECORD_KIND,
            "seed_domain": "final",
            "seed": g.SEED_DOMAINS["final"],
            "per_stratum": 40,
            "spec_sha256": g.SUPPORTED_SPEC_SHA256,
            "generator_version": "rule04-final-contained-v1",
            "orchestrator_source_sha256_lf": hashlib.sha256(
                Path(__file__).read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest(),
            "authorization": authorization_id,
            "labels": "generator claims; independent check is RULE-03's case checker",
            "max_attempts_per_stratum": g.MAX_ATTEMPTS_PER_STRATUM,
            "report": report,
            "units": "artificial score weights; not g/kWh, not emissions",
        },
    }
    accounting = {
        "record_kind": g.ACCOUNTING_RECORD_KIND,
        "set_id": case_set["set_id"],
        "case_set_sha256": g.canonical_sha256(case_set),
        "generator_source_sha256": g.source_sha256(),
        "visibility": "evaluator-only; never supply to a policy",
        "units": "artificial score weights per slot; impact = power_kW x 1 h x PUE 1.0 x weight (score-kWh)",
        "cases": weights,
    }
    case_set["metadata"]["generator_source_sha256"] = g.source_sha256()
    accounting["case_set_sha256"] = g.canonical_sha256(case_set)
    return case_set, accounting, counters
