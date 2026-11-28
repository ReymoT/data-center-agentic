"""Offline final-input preparation and trusted-host contained backend; no CLI release.

Generation and each evaluation stage require separate exact fresh approval. Never
draws the final seed during draft/inspection/tests. Scientific acceptance is not
inferred from JSON, producer checks, a URL or successful infrastructure tests.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prepare_rule_study_rollout as w  # noqa: E402
from scripts import rule04_final_receipts as receipts  # noqa: E402

KIND = "rule04_final_preparation_v1"
FIELDS = {
    "kind",
    "plan",
    "phase",
    "limits",
    "freeze_reference",
    "final_inputs",
    "receiving",
    "stage",
    "parent",
}
GEN_KEYS = {"wall_seconds", "output_bytes", "proposals", "feasibility_assignments"}
INPUT_ROLES = {"cases", "accounting", "generation_receipt"}


def bound(item):
    if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
        raise ValueError("exact path/hash binding required")
    if not isinstance(item["path"], str) or not Path(item["path"]).is_absolute():
        raise ValueError("absolute bound path required")
    if not isinstance(item["sha256"], str) or not re.fullmatch("[a-f0-9]{64}", item["sha256"]):
        raise ValueError("SHA-256 required")
    raw = w.pf.bounded_bytes(w.safe_path(item["path"]))
    if w.pf.sha(raw) != item["sha256"]:
        raise ValueError("bound input changed")
    return w.decode_json(raw)


def draft(phase):
    if phase not in {"generate", "evaluate"}:
        raise ValueError("fixed generation/evaluation phase required")
    source = w.draft()
    return dict(
        kind=KIND,
        phase=phase,
        plan=source["plan"],
        limits=dict.fromkeys(sorted(GEN_KEYS if phase == "generate" else w.LIMIT_KEYS)),
        freeze_reference=None,
        final_inputs=None,
        receiving=None,
        stage=None,
        parent=None,
    )


def validate_shape(request):
    if not isinstance(request, dict) or set(request) != FIELDS or request["kind"] != KIND:
        raise ValueError("exact final request fields required")
    if request["phase"] not in {"generate", "evaluate"}:
        raise ValueError("unknown phase")
    if request["phase"] == "generate":
        if any(request[k] is not None for k in ("final_inputs", "receiving", "stage", "parent")):
            raise ValueError("generation cannot accept final inputs, stage or receiving")
    elif type(request["stage"]) is not int or request["stage"] not in (0, 1):
        raise ValueError("fixed evaluation stage 0 or 1 required")


def generation_limits(limits):
    caps = dict(
        wall_seconds=900,
        output_bytes=256 * 1024 * 1024,
        proposals=30_000,
        feasibility_assignments=2_430_000,
    )
    if not isinstance(limits, dict) or set(limits) != GEN_KEYS:
        raise ValueError("explicit generation limits required")
    if any(type(limits[k]) is not int or not 0 < limits[k] <= v for k, v in caps.items()):
        raise ValueError("invalid generation ceiling")


def retained():
    return w.pair()


def pair(request):
    """Static identity/accounting/isolation checks; no policy or oracle search."""
    from dc_sustainability.evaluation import rule_study_accounting as ac
    from dc_sustainability.evaluation import rule_study_cases as cc
    from dc_sustainability.evaluation import rule_study_generator as g

    items = request["final_inputs"]
    if not isinstance(items, dict) or set(items) != INPUT_ROLES:
        raise ValueError("final visible/accounting/generation bindings required")
    if len({w.safe_path(v["path"]) for v in items.values()}) != 3:
        raise ValueError("distinct final artifacts required")
    cases, weights, receipt = (
        bound(items[k]) for k in ("cases", "accounting", "generation_receipt")
    )
    dev, _, _ = retained()
    if cases.get("set_id") != f"{g.STUDY_ID}-final" or len(cases.get("cases", [])) != 120:
        raise ValueError("exact final 120-case set required")
    metadata = cases.get("metadata", {})
    if metadata.get("seed_domain") != "final" or metadata.get("seed") != g.SEED_DOMAINS["final"]:
        raise ValueError("final seed namespace required")
    if metadata.get("per_stratum") != 40 or metadata.get("spec_sha256") != w.pf.SPEC_HASH:
        raise ValueError("final counts/specification changed")
    expected_ids = [f"final-{s}-{i:02d}" for s in g.STRATA for i in range(40)]
    if [c.get("case_id") for c in cases["cases"]] != expected_ids:
        raise ValueError("fixed final order/counts required")
    if any(
        c.get("stratum") != s
        for s in g.STRATA
        for c in cases["cases"]
        if c["case_id"].startswith(f"final-{s}-")
    ):
        raise ValueError("stratum/identity mismatch")
    parsed = {c["case_id"]: cc._case_from_dict(c) for c in cases["cases"]}
    for row in cases["cases"]:
        label = (
            "jointly_infeasible"
            if row["stratum"] == "overloaded_impossible"
            else "jointly_feasible"
        )
        if row.get("feasibility_label") != label or cc.predicate_findings(
            parsed[row["case_id"]], row["stratum"], label
        ):
            raise ValueError("final stratum predicate/label differs")
    dev_hashes = {g.canonical_sha256(cc.case_identity(cc._case_from_dict(c))) for c in dev["cases"]}
    authored = g.authored_full_identities(g.load_specification())
    identities = [g.canonical_sha256(cc.case_identity(c)) for c in parsed.values()]
    if len(set(identities)) != 120 or set(identities) & (dev_hashes | authored):
        raise ValueError("duplicate/development/authored full-case overlap")
    if ac.check_accounting(cases, weights)["overall"] != "PASS":
        raise ValueError("final accounting/visibility check failed")
    validate_metadata(cases, weights, receipt, request, parsed)
    if receipt.get("status") != "GENERATED_PENDING_INDEPENDENT_RECEIVING":
        raise ValueError("successful generation receipt required")
    if receipt.get("artifacts") != {k: items[k]["sha256"] for k in ("cases", "accounting")}:
        raise ValueError("generation artifact binding differs")
    if receipt.get("development_inputs") != request["plan"]["inputs"]:
        raise ValueError("generation retained-development exclusion differs")
    if (
        receipt.get("code_commit") != request["plan"]["code_commit"]
        or receipt.get("code_sha256") != request["plan"]["code_sha256"]
    ):
        raise ValueError("generation/evaluation freeze must be identical")
    if receipt.get("freeze_reference") != request["freeze_reference"]:
        raise ValueError("generation/evaluation freeze reference differs")
    receipts.authenticate_completed(
        ROOT, items["generation_receipt"]["path"], receipt, "generate", None
    )
    receiving = bound(request["receiving"])
    expected = {k: items[k]["sha256"] for k in INPUT_ROLES}
    if (
        receiving.get("artifact_sha256") != expected
        or receiving.get("reviewer") != "nkolekar-nk"
        or any(
            receiving.get(k) != "PASS"
            for k in (
                "case_predicates",
                "strata_counts",
                "no_full_case_overlap",
                "accounting_visibility",
            )
        )
    ):
        raise ValueError("actual independent isolation/accounting receiving required")
    # The host independently authenticates the person's actual record, not this JSON label.
    return cases, weights, parsed


def validate_metadata(cases, weights, receipt, request, parsed):
    """Static provenance/predicate checks only; oracle labels require receiving."""
    from collections import Counter

    from dc_sustainability.evaluation import rule_study_cases as cc
    from dc_sustainability.evaluation import rule_study_generator as g

    meta = cases["metadata"]
    pins = request["plan"]["code_sha256"]
    # Both source commitments explicitly normalize CRLF to LF.
    primitive = g.source_sha256()
    orchestrator = pins.get("scripts/rule04_final_generation.py")
    if (
        meta.get("generator_version") != "rule04-final-contained-v1"
        or meta.get("record_kind") != g.RECORD_KIND
        or meta.get("generator_source_sha256") != primitive
        or pins.get("dc_sustainability/evaluation/rule_study_generator.py") != primitive
        or weights.get("generator_source_sha256") != primitive
        or meta.get("orchestrator_source_sha256_lf") != orchestrator
        or meta.get("authorization") != receipt.get("authorization_id")
        or not isinstance(receipt.get("authorization_id"), str)
        or meta.get("max_attempts_per_stratum") != g.MAX_ATTEMPTS_PER_STRATUM
        or receipt.get("metadata_sha256") != receipts.digest(meta)
    ):
        raise ValueError("final generator provenance metadata differs")
    report = meta.get("report")
    if not isinstance(report, dict) or set(report) != set(g.STRATA):
        raise ValueError("complete generation metadata report required")
    total_attempts = 0
    for stratum in g.STRATA:
        rows = [c for c in cases["cases"] if c["stratum"] == stratum]
        stats = report[stratum]
        if not isinstance(stats, dict) or set(stats) != {
            "accepted",
            "attempts",
            "rejected",
            "distinct_full_case_hashes",
            "distinct_workload_hashes",
        }:
            raise ValueError("exact generation stratum statistics required")
        attempts = [c.get("generator_attempt") for c in rows]
        rejected = stats["rejected"]
        if (
            len(rows) != 40
            or any(type(a) is not int or not 1 <= a <= 10000 for a in attempts)
            or attempts != sorted(set(attempts))
            or type(stats["attempts"]) is not int
            or stats["attempts"] != attempts[-1]
            or stats["accepted"] != 40
            or not isinstance(rejected, dict)
            or set(rejected)
            - {
                "duplicate_full_case",
                "authored_overlap",
                "development_overlap",
                "jointly_feasible",
                "jointly_infeasible",
                "no_flexible_job",
                "constant_profile",
            }
            or any(type(v) is not int or v < 0 for v in rejected.values())
            or sum(rejected.values()) != stats["attempts"] - 40
        ):
            raise ValueError("generation attempts/rejections differ")
        full = Counter(g.canonical_sha256(cc.case_identity(parsed[c["case_id"]])) for c in rows)
        work = {g.canonical_sha256(cc.workload_identity(parsed[c["case_id"]])) for c in rows}
        if stats["distinct_full_case_hashes"] != len(full) or stats[
            "distinct_workload_hashes"
        ] != len(work):
            raise ValueError("generation diversity metadata differs")
        total_attempts += stats["attempts"]
    if receipt.get("counters", {}).get("proposals") != total_attempts:
        raise ValueError("generation attempt total differs")


def stage_pairs(loaded):
    """Fixed balanced halves: indices00-19 then20-39 in each stratum, no RNG."""
    from dc_sustainability.evaluation.rule_study_generator import STRATA

    rows, _, parsed = loaded
    groups = {s: [c["case_id"] for c in rows["cases"] if c["stratum"] == s] for s in STRATA}
    if (
        len(rows["cases"]) != 120
        or any(len(ids) != 40 for ids in groups.values())
        or len({c for ids in groups.values() for c in ids}) != 120
        or set(parsed) != {c for ids in groups.values() for c in ids}
    ):
        raise ValueError("balanced stages require exactly40 distinct cases per stratum")
    return [
        (case_id, policy)
        for half in (0, 1)
        for stratum in STRATA
        for case_id in groups[stratum][half * 20 : (half + 1) * 20]
        for policy in w.POLICIES
    ]


def selection(request, loaded=None, *, verify_parent_tree=True, deadline=None):
    loaded = pair(request) if loaded is None else loaded
    all_pairs = stage_pairs(loaded)
    if type(request["stage"]) is not int or request["stage"] not in (0, 1):
        raise ValueError("fixed stage required")
    stage = request["stage"]
    if stage == 0:
        if request["parent"] is not None:
            raise ValueError("first stage has no parent")
    else:
        validate_stage_receipt(
            request, request["parent"], 0, loaded, verify_tree=verify_parent_tree, deadline=deadline
        )
    return all_pairs[stage * 180 : (stage + 1) * 180]


def validate_stage_receipt(
    request, item, stage, loaded, *, first=None, verify_tree=True, deadline=None
):
    report = bound(item)
    rows = validate_stage_content(request, report, stage, loaded, first=first)
    receipts.verify_stage_tree(item["path"], report, verify_files=verify_tree, deadline=deadline)
    receipts.authenticate_completed(ROOT, item["path"], report, "evaluate", stage)
    return rows


def validate_stage_content(request, report, stage, loaded, *, first=None):
    expected = stage_pairs(loaded)[stage * 180 : (stage + 1) * 180]
    if (
        report.get("kind") != "rule04_complete_stage_receipt_v2"
        or report.get("status") != "PASS"
        or report.get("runs") != 180
        or report.get("stage") != stage
        or report.get("scope_complete_only") is not True
        or not receipts.is_digest(report.get("authenticated_request_sha256"))
        or report.get("selected_pairs") != [list(p) for p in expected]
        or report.get("charged_steps") != dict(states=10800, transitions=10800)
        or report.get("code_commit") != request["plan"]["code_commit"]
        or report.get("code_sha256") != request["plan"]["code_sha256"]
        or report.get("final_inputs") != request["final_inputs"]
        or report.get("receiving") != request["receiving"]
        or report.get("freeze_reference") != request["freeze_reference"]
        or report.get("limits") != request["limits"]
        or report.get("host_supervision", {}).get("status") != "succeeded"
        or report.get("host_supervision", {}).get("cleanup_verified") is not True
        or report.get("parent") != (None if stage == 0 else first)
    ):
        raise ValueError("authenticated complete same-freeze first stage/receipt required")
    groups = report.get("strata")
    if (
        not isinstance(groups, dict)
        or set(groups) != {"normal_feasible", "overloaded_impossible", "missing_forecast"}
        or any(not isinstance(rows, list) for rows in groups.values())
    ):
        raise ValueError("stage metric coverage/strata differs")
    rows = [m for group in groups.values() for m in group]
    observed = [(m.get("case_id"), m.get("policy_id")) for m in rows if isinstance(m, dict)]
    strata = {c["case_id"]: c["stratum"] for c in loaded[0]["cases"]}
    if (
        len(rows) != 180
        or len(set(observed)) != 180
        or set(observed) != set(expected)
        or any(strata.get(m.get("case_id")) != s for s, group in groups.items() for m in group)
    ):
        raise ValueError("stage metric coverage/identity differs")
    return rows


def join_stages(request, first, second):
    """Read-only numerical join of two complete pinned stages; no scientific run."""
    from scripts import rule_study_metrics_core as mc

    loaded = pair(request)
    metrics = []
    for stage, item in enumerate((first, second)):
        metrics.extend(validate_stage_receipt(request, item, stage, loaded, first=first))
    strata = {c["case_id"]: c["stratum"] for c in loaded[0]["cases"]}
    return dict(
        status="COMPLETE_SAVED_STAGE_JOIN_PENDING_INDEPENDENT_RECEIVING",
        scope="final synthetic observations only; not universal generalization",
        stages=[first, second],
        pairs=360,
        charged_steps=dict(states=21600, transitions=21600),
        metrics=metrics,
        equal_work_vs_greedy_a=w.comparison_rows(mc.equal_work(metrics), strata),
    )


def _assess(request, *, after=False, context=None, verify_parent_tree=True, deadline=None):
    if deadline is not None and monotonic() >= deadline:
        raise TimeoutError("final preflight deadline")
    validate_shape(request)
    plan = json.loads(json.dumps(request["plan"]))
    out = (
        w.safe_path(plan["output_directory"]) if isinstance(plan["output_directory"], str) else None
    )
    if after and out is not None:
        # Reuse source/input preflight while ignoring ONLY the expected owned output.
        plan["output_directory"] = str(out.with_name(out.name + "-preflight-unused"))
    problems = list(w.pf.assess(plan)["problems"])
    for role, (name, digest) in w.INPUTS.items():
        if request["plan"]["inputs"][role] != {
            "path": str(ROOT / "docs/evidence/rule04-dev-nov23" / name),
            "sha256": digest,
        }:
            raise ValueError("actual accepted retained development pair required")
    baseline = w.read_json(ROOT / "docs/rule_study/RULE03_VERIFICATION_BASELINE_NOV23.json")[
        "baseline_code_sha256"
    ]
    if any(
        w.pf.sha(w.pf.bounded_bytes(w.safe_path(ROOT / p)).replace(b"\r\n", b"\n")) != h
        for p, h in baseline.items()
    ):
        problems.append("accepted scientific baseline drift")
    if not isinstance(request["freeze_reference"], str) or not request["freeze_reference"].strip():
        problems.append("actual whole protocol freeze missing")
    try:
        if request["phase"] == "generate":
            retained()
            generation_limits(request["limits"])
        else:
            loaded = pair(request)
            selected = selection(
                request, loaded, verify_parent_tree=verify_parent_tree, deadline=deadline
            )
            if context is not None:
                context.update(loaded=loaded, selected=selected)
            w.validate_limits(request["limits"], 180)
            if any(request["limits"][k] != 10800 for k in ("states", "transitions")):
                problems.append("each fixed stage requires exactly 10800 states AND transitions")
            if w.artifact_path_length(str(out), list(loaded[2])) >= 260:
                problems.append("shorter output path required")
        if request["limits"]["wall_seconds"] != plan["proposed_limit_seconds"]:
            problems.append("wall limits differ")
    except (ValueError, TypeError, KeyError) as exc:
        problems.append(str(exc))
    return dict(
        status="BLOCKED" if problems else "PREPARED_NOT_AUTHORIZED",
        problems=problems,
        execution_authorized=False,
        phase=request["phase"],
    )


def assess(request, *, after=False, context=None, verify_parent_tree=True, deadline=None):
    """Read-only preflight always returns BLOCKED for malformed requests."""
    try:
        return _assess(
            request,
            after=after,
            context=context,
            verify_parent_tree=verify_parent_tree,
            deadline=deadline,
        )
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return dict(
            status="BLOCKED",
            problems=[str(exc)[:1000]],
            execution_authorized=False,
            phase=request.get("phase") if isinstance(request, dict) else None,
        )


def drift(request, *, deadline=None):
    if deadline is None and "RULE04_WORKER_DEADLINE" in os.environ:
        deadline = float(os.environ["RULE04_WORKER_DEADLINE"])
    return bool(assess(request, after=True, deadline=deadline)["problems"])


def command(path, digest, *, deadline=None, original_hash=None):
    value = w._command(path, digest, deadline=deadline, original_hash=original_hash)
    value[5] = value[5].replace(
        "from scripts.prepare_rule_study_rollout import execute_prepared",
        "from scripts.prepare_rule_study_final import execute_prepared",
    )
    return value


def receipt_context(request, authenticated_hash):
    return dict(
        authenticated_request_sha256=authenticated_hash,
        canonical_request_sha256=receipts.digest(request),
        authorization_id=request["plan"]["proposed_authorization_id"],
        freeze_reference=request["freeze_reference"],
        phase=request["phase"],
        stage=request["stage"],
        limits=request["limits"],
    )


def check_generation_output(out, request, authenticated_hash):
    """Producer publication checks only; does not replace Nisha's receiving."""
    from dc_sustainability.evaluation import rule_study_accounting as ac

    receipt = w.read_json(out / "generation-receipt.json")
    cases, weights = (w.read_json(out / n) for n in ("cases.json", "accounting.json"))
    expected = {
        k: w.pf.sha(w.pf.bounded_bytes(out / n))
        for k, n in (("cases", "cases.json"), ("accounting", "accounting.json"))
    }
    if (
        receipt.get("status") != "GENERATED_PENDING_INDEPENDENT_RECEIVING"
        or receipt.get("artifacts") != expected
        or receipt.get("development_inputs") != request["plan"]["inputs"]
        or receipt.get("code_commit") != request["plan"]["code_commit"]
        or receipt.get("code_sha256") != request["plan"]["code_sha256"]
        or len(cases.get("cases", [])) != 120
        or ac.check_accounting(cases, weights)["overall"] != "PASS"
        or any(receipt.get(k) != v for k, v in receipt_context(request, authenticated_hash).items())
        or receipt.get("metadata_sha256") != receipts.digest(cases.get("metadata"))
    ):
        raise ValueError("generation publication/result mismatch")
    from dc_sustainability.evaluation import rule_study_cases as cc

    parsed = {c["case_id"]: cc._case_from_dict(c) for c in cases["cases"]}
    validate_metadata(cases, weights, receipt, request, parsed)
    counters = receipt.get("counters", {})
    for name, limit in (
        ("proposals", "proposals"),
        ("feasibility_assignments_reserved", "feasibility_assignments"),
    ):
        if (
            type(counters.get(name)) is not int
            or not 0 <= counters[name] <= request["limits"][limit]
        ):
            raise ValueError("generation counter mismatch")
    return receipt


def execute_prepared(request):
    authenticated = receipts.worker_authority(ROOT, request)
    context = {}
    # One preflight/load per contained worker. Parent's full evidence tree is
    # checked by the host before release and after the batch; children retain
    # receipt/manifest/ledger hashes without rehashing its entire tree 180 times.
    if assess(request, after=True, context=context, verify_parent_tree=False)["problems"]:
        raise ValueError("final worker preflight refused")
    out = w.safe_path(request["plan"]["output_directory"])
    if request["phase"] == "generate":
        if "RULE04_WORKER_PAIR" in os.environ:
            raise ValueError("generation pair selector refused")
        import random

        from scripts.rule04_final_generation import build, g

        out.mkdir(exist_ok=False)
        # This authorized invocation constructs the public fixed-seed stream here.
        # It cannot prove that nobody else computed the deterministic cases earlier.
        cases, weights, counters = build(
            random.Random(g.SEED_DOMAINS["final"]),
            retained()[0],
            request["limits"],
            authorization_id=request["plan"]["proposed_authorization_id"],
        )
        for name, value in (("cases.json", cases), ("accounting.json", weights)):
            w._write(out / name, value)
        w._write(
            out / "generation-receipt.json",
            dict(
                status="GENERATED_PENDING_INDEPENDENT_RECEIVING",
                counters=counters,
                code_commit=request["plan"]["code_commit"],
                code_sha256=request["plan"]["code_sha256"],
                development_inputs=request["plan"]["inputs"],
                **receipt_context(request, authenticated),
                metadata_sha256=receipts.digest(cases["metadata"]),
                artifacts={
                    k: w.pf.sha(w.pf.bounded_bytes(out / n))
                    for k, n in (("cases", "cases.json"), ("accounting", "accounting.json"))
                },
            ),
        )
        return 0
    loaded = context["loaded"]
    if "RULE04_WORKER_PAIR" in os.environ:
        case_id, policy, states, transitions = json.loads(os.environ["RULE04_WORKER_PAIR"])
        if (case_id, policy) not in context["selected"]:
            raise ValueError("pair not in fixed stage")
        remaining = dict(states=states, transitions=transitions)
        if any(
            type(v) is not int or not 0 < v <= request["limits"][k] for k, v in remaining.items()
        ):
            raise ValueError("invalid remaining budget")
        directory = out / f"{case_id}-{policy}"
        directory.mkdir(exist_ok=False)
        w._one_pair(request, case_id, policy, directory, remaining, loaded=loaded, scope="final")
        return 0
    return w._batch(
        request, out, backend=sys.modules[__name__], prepared=(loaded, context["selected"])
    )


def dispatch_once(path, *, ledger, trusted_authorize=None):
    if not callable(trusted_authorize):
        raise PermissionError("fresh exact trusted host approval required")
    path = w.safe_path(path)
    raw = w.pf.bounded_bytes(path)
    request = w.decode_json(raw)
    if assess(request)["problems"]:
        raise ValueError("final preflight blocked")
    plan = request["plan"]
    environment = w.worker.environment_evidence()
    subject = dict(
        request_sha256=w.pf.sha(raw),
        code_commit=plan["code_commit"],
        authorization_id=plan["proposed_authorization_id"],
        phase=request["phase"],
        stage=request["stage"],
        limits=request["limits"],
        output_directory=plan["output_directory"],
        freeze_reference=request["freeze_reference"],
    )
    expected = dict(
        subject,
        actor="MattyAnd",
        decision="approved",
        protocol_freeze_authenticated=True,
        generation_and_isolation_receiving_authenticated=request["phase"] == "evaluate",
        parent_stage_authenticated=request["stage"] == 1,
    )
    if trusted_authorize(json.loads(json.dumps(subject))) != expected:
        raise PermissionError("exact host freeze/receiving/parent authority required")
    ledger, out = w.safe_path(ledger), w.safe_path(plan["output_directory"])
    if (
        ledger != ROOT.parent / "RuleStudy_Run_Ledger"
        or out.is_relative_to(ROOT)
        or out.is_relative_to(ledger)
        or ledger.is_relative_to(out)
    ):
        raise ValueError("canonical external ledger and separate output required")
    if any(
        k in os.environ
        for k in (
            "RULE04_WORKER_PAIR",
            "RULE04_WORKER_DEADLINE",
            "RULE04_AUTHENTICATED_REQUEST_SHA256",
            "RULE04_WORKER_REQUEST_SHA256",
        )
    ):
        raise ValueError("inherited worker controls refused")
    ledger.mkdir(exist_ok=True)
    entry = ledger / (w.pf.sha(subject["authorization_id"].encode()) + ".json")
    if entry.with_suffix(".result.json").exists():
        raise FileExistsError("consumed authorization")
    slot = receipts.slot_path(ROOT, request["phase"], request["stage"])
    if entry.exists() or entry.with_suffix(".result.json").exists():
        raise FileExistsError("consumed authorization")
    # A new ID cannot retry a failed phase/stage. Reserve before release; even a
    # crash between these two exclusive writes leaves the stage fail-closed.
    w._write(
        slot,
        dict(
            authorization_id=subject["authorization_id"],
            request_sha256=subject["request_sha256"],
            canonical_request_sha256=receipts.digest(request),
        ),
    )
    result = dict(status="failed_after_reservation", retry_allowed=False)
    id_reserved = False
    try:
        w._write(
            entry,
            {
                "receipt": expected,
                "environment": environment,
                "canonical_request_sha256": receipts.digest(request),
            },
        )
        id_reserved = True
        if (
            w.pf.sha(w.pf.bounded_bytes(path)) != subject["request_sha256"]
            or assess(request)["problems"]
            or w.worker.environment_evidence() != environment
        ):
            raise ValueError("request/input/source/environment drift after reservation")
        deadline = monotonic() + request["limits"]["wall_seconds"]
        result = w.supervisor.supervise(
            command(path, subject["request_sha256"], deadline=deadline),
            request["limits"]["wall_seconds"],
            output=out,
            limit_bytes=request["limits"]["output_bytes"],
            cwd=ROOT,
            deadline=deadline,
        )
        result.update(retry_allowed=False, authenticated_request_sha256=subject["request_sha256"])
        if (
            result["status"] == "succeeded"
            and result["cleanup_verified"]
            and not drift(request, deadline=deadline)
        ):
            if request["phase"] == "generate":
                check_generation_output(out, request, subject["request_sha256"])
                receipt_path = out / "generation-receipt.json"
            else:
                report = w.read_json(out / "rollout-report.json")
                if (
                    report.get("status") != "PASS"
                    or report.get("runs") != 180
                    or report.get("selected_pairs")
                    != [list(p) for p in selection(request, deadline=deadline)]
                    or report.get("authenticated_request_sha256") != subject["request_sha256"]
                ):
                    raise ValueError("incomplete stage result")
                inventory = receipts.inventory(out, deadline=deadline)
                w._write(out / "stage-manifest.json", inventory)
                receipt_path = out / "stage-receipt.json"
                w._write(
                    receipt_path,
                    dict(
                        report,
                        kind="rule04_complete_stage_receipt_v2",
                        final_inputs=request["final_inputs"],
                        receiving=request["receiving"],
                        code_commit=plan["code_commit"],
                        code_sha256=plan["code_sha256"],
                        host_supervision=dict(result),
                        pair_supervision=report.get("supervision"),
                        rollout_report_sha256=w.pf.sha(
                            w.pf.bounded_bytes(out / "rollout-report.json")
                        ),
                        output_inventory=dict(
                            path="stage-manifest.json",
                            sha256=w.pf.sha(w.pf.bounded_bytes(out / "stage-manifest.json")),
                        ),
                        **{
                            k: v
                            for k, v in receipt_context(request, subject["request_sha256"]).items()
                            if k not in report
                        },
                    ),
                )
                # Apply the same completeness and tree guards before calling the
                # host result successful (ledger authentication follows in finally).
                validate_stage_content(
                    request,
                    w.read_json(receipt_path),
                    request["stage"],
                    pair(request),
                    first=request["parent"],
                )
                receipts.verify_stage_tree(
                    receipt_path, w.read_json(receipt_path), deadline=deadline
                )
            if monotonic() >= deadline:
                raise TimeoutError("final publication validation exceeded total wall bound")
            if (
                w.supervisor.output_bytes(out, deadline=deadline)
                > request["limits"]["output_bytes"]
            ):
                raise ValueError("final publication exceeds observed output threshold")
            result["published_receipt_sha256"] = w.pf.sha(w.pf.bounded_bytes(receipt_path))
        else:
            result["status"] = "FAIL_OR_INCOMPLETE"
            result["additional_unmeasured_work"] = "unknown if killed; never assumed zero; no retry"
        return result
    except BaseException as exc:
        result.update(
            status="failed_after_reservation",
            exception=type(exc).__name__,
            message=str(exc)[:2000],
            retry_allowed=False,
        )
        raise
    finally:
        if id_reserved:
            w._write(entry.with_suffix(".result.json"), result)
        w._write(slot.with_suffix(".result.json"), result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("draft").add_argument("--phase", choices=("generate", "evaluate"), required=True)
    sub.add_parser("inspect").add_argument("request", type=Path)
    args = parser.parse_args(argv)
    try:
        value = draft(args.phase) if args.action == "draft" else assess(w.read_json(args.request))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        value = dict(status="BLOCKED", problems=[str(exc)[:1000]], execution_authorized=False)
    print(json.dumps(value, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
