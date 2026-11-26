"""Prepare fixed development-only RULE04 dispatch; public CLI never executes it.

Trusted-host dispatch requires fresh exact authority, including protocol freeze.
No final generator, model, arbitrary command or alternate input set is supported.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prepare_rule_study_dispatch as pf  # noqa: E402
from scripts import prepare_rule_study_worker as worker  # noqa: E402
from scripts import rule_rollout_supervisor as supervisor  # noqa: E402

KIND = "rule04_development_rollout_preparation_v1"
SUFFIX_KIND = "rule04_development_suffix_preparation_v1"
POLICIES = ("rules-v1", "greedy_a", "greedy_b")
INPUTS = {
    "development_cases": (
        "development.cases.json",
        "08942727f68a995e386a37f23ab0e651fa905ba911ea487bc917c7ebf58bd716",
    ),
    "development_accounting": (
        "development.accounting.json",
        "c35c8dd98f7aaf66ba4e5549626a02551141cb418d5d4ca0b42fb9b4593b8599",
    ),
}
FIELDS = {"kind", "plan", "limits", "freeze_reference"}
LIMIT_KEYS = {"states", "transitions", "wall_seconds", "case_policy_seconds", "output_bytes"}
BOOTSTRAP = worker.BOOTSTRAP.replace(
    "from scripts.prepare_rule_study_worker import execute_prepared",
    "from scripts.prepare_rule_study_rollout import execute_prepared",
)


def decode_json(raw):
    """Strictly parse the same bounded bytes a caller has just authenticated."""

    def pairs(items):
        value = {}
        for k, v in items:
            if k in value:
                raise ValueError("duplicate JSON key")
            value[k] = v
        return value

    def nonfinite(_):
        raise ValueError("nonfinite JSON")

    if not isinstance(raw, bytes) or len(raw) > 8 * 1024 * 1024:
        raise ValueError("bounded JSON bytes required")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def read_json(path):
    return decode_json(pf.bounded_bytes(safe_path(path)))


class ResourceStop(ValueError):
    def __init__(self, reason):
        self.stop_reason = reason
        message = {
            "wall_time_reserve": "wall-time reserve budget exhausted before next pair and cleanup",
            "state_transition_budget": "combined state/transition budget exhausted",
        }[reason]
        super().__init__(message)


def safe_path(path):
    path = Path(path).absolute()
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError("linked path refused")
    return path


def pair():
    """Read accepted retained files only; no generator or feasibility search."""
    from dc_sustainability.evaluation import rule_study_accounting as ac
    from dc_sustainability.evaluation import rule_study_cases as cc

    loaded = {}
    for role, (name, digest) in INPUTS.items():
        path = ROOT / "docs/evidence/rule04-dev-nov23" / name
        if pf.sha(pf.bounded_bytes(safe_path(path))) != digest:
            raise ValueError("retained development input hash changed")
        loaded[role] = read_json(path)
    cases, sidecar = loaded["development_cases"], loaded["development_accounting"]
    if len(cases["cases"]) != 120 or ac.check_accounting(cases, sidecar)["overall"] != "PASS":
        raise ValueError("accepted 120-case accounting pair required")
    parsed = {c["case_id"]: cc._case_from_dict(c) for c in cases["cases"]}
    if len(parsed) != 120:
        raise ValueError("duplicate development case")
    episode_ids = set()
    for visible in parsed.values():
        mapped = development_case_spec(visible)
        mapped.episode()  # Schema construction only; no runner, search or simulator.
        if mapped.episode_id in episode_ids:
            raise ValueError("development episode identity collision")
        episode_ids.add(mapped.episode_id)
    return cases, sidecar, parsed


def development_case_spec(visible):
    """Map retained cases without putting descriptive split labels into episode IDs.

    Keep the accepted receiving implementation and case facts unchanged. Only its
    temporary identity input is opaque; restore the exact retained case ID before
    computing bindings or constructing the episode. Hex contains no split tokens.
    """
    from dc_sustainability.evaluation import rule_study_receiving as rv

    neutral_id = "Q" + hashlib.sha256(visible.case_id.encode("utf-8")).hexdigest()[:24]
    mapped = rv.case_spec_for(replace(visible, case_id=neutral_id))
    return replace(mapped, case_id=visible.case_id)


def validate_limits(limits, runs=360):
    if not isinstance(limits, dict) or set(limits) != LIMIT_KEYS:
        raise ValueError("exact explicit rollout limits required")
    ceilings = {
        "states": 5_000_000,
        "transitions": 5_000_000,
        "wall_seconds": 900,
        "case_policy_seconds": 60,
        "output_bytes": 256 * 1024 * 1024,
    }
    for k, cap in ceilings.items():
        if type(limits[k]) is not int or not 0 < limits[k] <= cap:
            raise ValueError(f"unsupported or absent limit: {k}")
    if type(runs) is not int or not 1 <= runs <= 360:
        raise ValueError("bounded fixed pair count required")
    if min(limits["states"], limits["transitions"]) < runs * 60:
        raise ValueError(
            f"execution plus replay needs at least {runs * 60} charged steps; eligibility also uses wall time"
        )
    if limits["case_policy_seconds"] > limits["wall_seconds"]:
        raise ValueError("per-pair time exceeds combined wall bound")


def draft():
    plan = pf.draft()
    for role, (name, digest) in INPUTS.items():
        plan["inputs"][role] = {
            "path": str(ROOT / "docs/evidence/rule04-dev-nov23" / name),
            "sha256": digest,
        }
    plan["receiving_references"] = {
        "rule_adapter": "https://github.com/ReymoT/data-center-agentic/pull/257",
        "verifier_freeze": "docs/rule_study/RULE03_VERIFICATION_BASELINE_NOV23.json (component only)",
        "independent_accounting": "https://github.com/ReymoT/data-center-agentic/issues/242#issuecomment-7121894902",
    }
    return {
        "kind": KIND,
        "plan": plan,
        "limits": {k: None for k in sorted(LIMIT_KEYS)},
        "freeze_reference": None,
    }


def assess(request):
    if not isinstance(request, dict):
        raise ValueError("fixed development rollout request required")
    selected = selection(request)
    report = pf.assess(request["plan"])
    problems = list(report["problems"])
    try:
        validate_limits(request["limits"], len(selected))
    except ValueError as exc:
        problems.append(str(exc))
    if not isinstance(request["freeze_reference"], str) or not request["freeze_reference"].strip():
        problems.append(
            "whole protocol freeze reference missing (component baseline is insufficient)"
        )
    plan = request["plan"]
    for role, (name, digest) in INPUTS.items():
        expected = ROOT / "docs/evidence/rule04-dev-nov23" / name
        item = plan["inputs"][role]
        if item["sha256"] != digest or item["path"] != str(expected):
            raise ValueError("alternate/final input set refused")
        safe_path(expected)
    if request["limits"]["wall_seconds"] != plan["proposed_limit_seconds"]:
        problems.append("plan and rollout wall limits differ")
    # Preserve the accepted scientific component exactly, including file set.
    baseline = read_json(ROOT / "docs/rule_study/RULE03_VERIFICATION_BASELINE_NOV23.json")
    pins = baseline["baseline_code_sha256"]
    current_package = {
        p.relative_to(ROOT).as_posix() for p in (ROOT / "dc_sustainability").rglob("*.py")
    }
    expected_package = {p for p in pins if p.startswith("dc_sustainability/")}
    if current_package != expected_package or any(
        pf.sha(pf.bounded_bytes(safe_path(ROOT / p)).replace(b"\r\n", b"\n")) != digest
        for p, digest in pins.items()
    ):
        problems.append("accepted verification component drift")
    case_file, _, _ = pair()
    if isinstance(plan["output_directory"], str):
        if (
            artifact_path_length(
                plan["output_directory"], [c["case_id"] for c in case_file["cases"]]
            )
            >= 260
        ):
            problems.append(
                "output artifact path reaches Windows MAX_PATH; choose a shorter output"
            )
    return {
        "status": "BLOCKED" if problems else "PREPARED_NOT_AUTHORIZED",
        "problems": problems,
        "execution_authorized": False,
        "runs": len(selected),
        "final_generation_supported": False,
    }


def selection(request, *, full=False, loaded=None):
    from scripts.rule04_suffix import selection as fixed_selection

    return fixed_selection(request, full=full, loaded=loaded)


def suffix_controls(request, loaded):
    from scripts.rule04_suffix import controls

    return controls(request, loaded) if request.get("kind") == SUFFIX_KIND else {}


def _write(path, value):
    with safe_path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def _command(path, expected_hash, *, deadline=None, original_hash=None):
    prefix = (
        "import os; os.environ['RULE04_AUTHENTICATED_REQUEST_SHA256']="
        + repr(original_hash or expected_hash)
        + "; os.environ['RULE04_WORKER_REQUEST_SHA256']="
        + repr(expected_hash)
        + ";\n"
    )
    if deadline is not None:
        prefix += "import os; os.environ['RULE04_WORKER_DEADLINE']=" + repr(str(deadline)) + ";\n"
    return [
        sys.executable,
        "-B",
        "-X",
        "utf8",
        "-c",
        prefix + BOOTSTRAP,
        str(ROOT),
        str(path),
        expected_hash,
    ]


def _metric(folder, weights):
    from scripts import rule_study_metrics_core as mc

    case, result, decisions = mc.load_run(folder)
    metric = mc.run_metrics(case, result, decisions)
    # Evaluator-only weights never enter case.json or the policy-visible forecast.
    recomputed = mc._impact(dict(case, scores=weights), result["accounting"]["per_job"], 1, 1)
    if recomputed != result["accounting"]["synthetic_impact_total"]:
        raise ValueError("evaluator-only impact does not match actual execution accounting")
    metric["synthetic_impact"].update(recomputed_total=recomputed, matches_producer=True)
    metric["synthetic_impact"]["scope"] = "job_only"
    background = case["background_kw"] * sum(weights)
    metric["background_synthetic_impact"] = {"total": background, "unit": mc.IMPACT_UNIT}
    metric["site_synthetic_impact"] = {"total": recomputed + background, "unit": mc.IMPACT_UNIT}
    metric["accounting_weights_visibility"] = (
        "visible" if case["scores"] is not None else "evaluator_only"
    )
    return metric


def _one_pair(request, case_id, policy, directory, remaining, *, loaded=None):
    from dc_sustainability.evaluation import rule_study_receiving as rv
    from dc_sustainability.evaluation import rule_study_verifier as v
    from dc_sustainability.rule_study import runner, scheduler

    _, sidecar, parsed = pair() if loaded is None else loaded
    visible = parsed[case_id]
    weights = next(e["weights"] for e in sidecar["cases"] if e["case_id"] == case_id)
    case = replace(development_case_spec(visible), first_scores=tuple(weights))
    if visible.scores is None and (
        case.case_json()["scores"] is not None or case.forecasts_by_slot()
    ):
        raise ValueError("hidden forecast leaked")
    budget = v.Budget(
        max_states=remaining["states"],
        max_transitions=remaining["transitions"],
        max_seconds=request["limits"]["case_policy_seconds"],
    )
    bindings = runner.make_bindings(case, ROOT)
    folder = rv._run_bounded_case(
        budget,
        "development",
        directory / "trace",
        case,
        policy,
        bindings=bindings,
        score_convention=scheduler.ScoreKwhConvention(),
        fault_injection=None,
    )
    spec = read_json(ROOT / "docs/rule_study/specification.json")
    received = rv._receive_folders(
        "development",
        1,
        [(case_id, policy, folder)],
        [],
        rv.reconstruct_pin(ROOT),
        spec,
        budget=budget,
    )
    if received["overall"] != "PASS":
        _write(directory / "replay.json", received)
        raise ValueError("independent replay failed or incomplete; stop without retry")
    metric = _metric(folder, weights)
    from scripts import rule_study_metrics_core as mc

    _, _, decisions = mc.load_run(folder)
    execution_signature = pf.sha(
        json.dumps([d["execution"]["current_starts"] for d in decisions], sort_keys=True).encode()
    )
    if metric["status"] != "complete" or metric["execution_violations"]:
        raise ValueError("incomplete or unsafe execution")
    _write(
        directory / "pair-result.json",
        {
            "status": "PASS",
            "case_id": case_id,
            "policy_id": policy,
            "authenticated_request_sha256": os.environ.get("RULE04_AUTHENTICATED_REQUEST_SHA256"),
            "pair_request_sha256": os.environ.get("RULE04_WORKER_REQUEST_SHA256"),
            "trace_directory": folder.relative_to(directory).as_posix(),
            "execution_signature": execution_signature,
            "metric": metric,
            "budget": budget.summary(),
            "replay": received,
        },
    )


def execute_prepared(request):
    """Fixed contained worker. Called only after authenticated host release, not by CLI."""
    out = safe_path(request["plan"]["output_directory"])
    mode = os.environ.get("RULE04_WORKER_PAIR")
    # Pair selection is supplied by fixed parent code, never an arbitrary command.
    if mode is not None:
        case_id, policy, states, transitions = json.loads(mode)
        loaded = pair()
        selected = selection(request, loaded=loaded)
        validate_limits(request["limits"], len(selected))
        if (case_id, policy) not in selected:
            raise ValueError("unknown pair")
        if any(
            type(n) is not int or not 0 < n <= request["limits"][k]
            for k, n in (("states", states), ("transitions", transitions))
        ):
            raise ValueError("invalid remaining pair budget")
        directory = out / f"{case_id}-{policy}"
        directory.mkdir(exist_ok=False)
        try:
            if assess_after_run(request):
                raise ValueError("pair source/input request refused")
            _one_pair(
                request,
                case_id,
                policy,
                directory,
                {"states": states, "transitions": transitions},
                loaded=loaded,
            )
        except BaseException as exc:
            _write(
                directory / "pair-failure.json",
                {
                    "status": "FAIL_OR_INCOMPLETE",
                    "case_id": case_id,
                    "policy_id": policy,
                    "authenticated_request_sha256": os.environ.get(
                        "RULE04_AUTHENTICATED_REQUEST_SHA256"
                    ),
                    "pair_request_sha256": os.environ.get("RULE04_WORKER_REQUEST_SHA256"),
                    "exception": type(exc).__name__,
                    "message": str(exc)[:2000],
                    "reserved_remaining_budget": {"states": states, "transitions": transitions},
                    "charged_steps": "unknown if execution did not return; bounded by reserved remaining budget",
                    "retry_allowed": False,
                },
            )
            raise
        return 0
    if assess(request)["problems"]:
        raise ValueError("rollout preparation blocked after containment")
    return _batch(request, out)


def _batch(request, out):
    """Serial contained pair workers, shared resource counters, no retries."""
    from scripts import rule_study_metrics_core as mc

    out.mkdir(exist_ok=False)
    started = monotonic()
    limits = request["limits"]
    deadline = min(
        started + limits["wall_seconds"],
        float(os.environ.get("RULE04_WORKER_DEADLINE", started + limits["wall_seconds"])),
    )
    # Leave time for pair cleanup and a durable failure summary before the outer kill.
    write_margin = 1
    used = {"states": 0, "transitions": 0}
    metrics, reports, control_signatures = [], [], {}
    strata = {}
    try:
        loaded = pair()
        case_file, _, parsed = loaded
        strata = {c["case_id"]: c["stratum"] for c in case_file["cases"]}
        selected = selection(request, loaded=loaded)
        control_signatures = suffix_controls(request, loaded)
        for case_id in parsed:
            for policy in POLICIES:
                if (case_id, policy) not in selected:
                    continue
                remaining = {k: limits[k] - used[k] for k in used}
                seconds = limits["case_policy_seconds"]
                if min(remaining.values()) <= 0:
                    raise ResourceStop("state_transition_budget")
                if deadline - monotonic() < seconds + 3 + write_margin:
                    raise ResourceStop("wall_time_reserve")
                task = out / "pair-request.json"
                # One immutable request per pair; no overwrites or retries.
                task = task.with_name(f"request-{case_id}-{policy}.json")
                _write(task, request)
                selector = json.dumps(
                    [case_id, policy, remaining["states"], remaining["transitions"]]
                )
                command = _command(
                    task,
                    pf.sha(pf.bounded_bytes(task)),
                    original_hash=os.environ.get("RULE04_AUTHENTICATED_REQUEST_SHA256"),
                )
                # Fixed selector bound in the child command, never inherited from the host.
                command[5] = (
                    "import os; os.environ['RULE04_WORKER_PAIR']="
                    + repr(selector)
                    + ";\n"
                    + command[5]
                )
                result = supervisor.supervise(
                    command,
                    seconds,
                    output=out / f"{case_id}-{policy}",
                    limit_bytes=limits["output_bytes"],
                    cwd=ROOT,
                )
                reports.append({"case_id": case_id, "policy_id": policy, "supervision": result})
                if result["status"] != "succeeded" or not result["cleanup_verified"]:
                    raise ValueError("pair timeout/output/cleanup/failure; no retry")
                received = read_json(out / f"{case_id}-{policy}" / "pair-result.json")
                for k in used:
                    value = received["budget"][k + "_used"]
                    if type(value) is not int or not 0 <= value <= remaining[k]:
                        raise ValueError("invalid resource counter")
                    used[k] += value
                metrics.append(received["metric"])
                if parsed[case_id].scores is None:
                    signature = received["execution_signature"]
                    if case_id in control_signatures and control_signatures[case_id] != signature:
                        raise ValueError(
                            "missing-forecast control differs across policies; investigate, do not rank"
                        )
                    control_signatures[case_id] = signature
                checkpoint = out / f"checkpoint-{len(metrics):04d}.json"
                pending = checkpoint.with_suffix(".pending")
                _write(
                    pending,
                    {
                        "completed_runs": len(metrics),
                        "charged_steps_completed_pairs_only": dict(used),
                        "last_completed_pair": {"case_id": case_id, "policy_id": policy},
                        "last_supervision": result,
                        "coverage": coverage(metrics, strata),
                        "authenticated_request_sha256": os.environ.get(
                            "RULE04_AUTHENTICATED_REQUEST_SHA256"
                        ),
                    },
                )
                pending.replace(checkpoint)
        if assess_after_run(request):
            raise ValueError("source/input drift after batch")
        grouped = {
            s: [dict(m, stratum=s) for m in metrics if strata[m["case_id"]] == s]
            for s in sorted(set(strata.values()))
        }
        _write(
            out / "rollout-report.json",
            {
                "status": "PASS",
                "scope": "development only; not unseen generalization",
                "selected_pairs": [list(p) for p in selected],
                "parent": request.get("parent"),
                "scope_complete_only": request["kind"] == SUFFIX_KIND,
                "authenticated_request_sha256": os.environ.get(
                    "RULE04_AUTHENTICATED_REQUEST_SHA256"
                ),
                "runs": len(metrics),
                "charged_steps": used,
                "eligibility_budget_semantics": "existing kernel checks wall time; eligibility assignments are not charged as states/transitions",
                "strata": grouped,
                "equal_work_vs_greedy_a": comparison_rows(mc.equal_work(metrics), strata),
                "supervision": reports,
                "independent_person_receiving": "PENDING",
                "final_cases_generated": 0,
            },
        )
        return 0
    except BaseException as exc:
        _write(
            out / "rollout-failure.json",
            {
                "status": "FAIL_OR_INCOMPLETE",
                "exception": type(exc).__name__,
                "message": str(exc)[:2000],
                "stop_reason": getattr(exc, "stop_reason", "other_failure"),
                "completed_runs": len(metrics),
                "coverage": coverage(metrics, strata),
                "coverage_scope": "completed validated pairs only; active/failed pair may have uncounted partial work",
                "authenticated_request_sha256": os.environ.get(
                    "RULE04_AUTHENTICATED_REQUEST_SHA256"
                ),
                "charged_steps_completed_pairs_only": used,
                "failed_pair_additional_work": "unknown if killed; bounded by remaining budget reserved for that pair",
                "supervision": reports,
                "retry_allowed": False,
            },
        )
        raise


def assess_after_run(request):
    """Actual source/input drift check without treating existing output as a new invocation."""
    commit, pins = pf.snapshot()
    return (
        commit != request["plan"]["code_commit"]
        or pins != request["plan"]["code_sha256"]
        or any(
            pf.sha(pf.bounded_bytes(Path(request["plan"]["inputs"][r]["path"]))) != d
            for r, (_, d) in INPUTS.items()
        )
    )


def comparison_rows(rows, strata):
    return [
        dict(
            row,
            stratum=strata[row["case_id"]],
            comparison_role="control_not_ranking"
            if strata[row["case_id"]] == "missing_forecast"
            else "development_comparison",
        )
        for row in rows
    ]


def artifact_path_length(output, case_ids):
    """Include BOTH pair and runner nesting, hashed names and longest directory."""
    return max(
        len(
            str(
                Path(output)
                / f"{case_id}-{policy}"
                / "trace"
                / policy
                / f"{case_id}-{policy}"
                / "snapshots"
                / ("f" * 64 + ".json")
            )
        )
        for case_id in case_ids
        for policy in POLICIES
    )


def coverage(metrics, strata):
    return {
        s: {
            "expected_runs": sum(value == s for value in strata.values()) * len(POLICIES),
            "completed_runs": sum(strata[m["case_id"]] == s for m in metrics),
            "completed_by_policy": {
                p: sum(strata[m["case_id"]] == s and m["policy_id"] == p for m in metrics)
                for p in POLICIES
            },
        }
        for s in sorted(set(strata.values()))
    }


def dispatch_once(path, *, ledger, trusted_authorize=None):
    """Host-only hook. Exact authority must authenticate both freeze and run approval."""
    if not callable(trusted_authorize):
        raise PermissionError("fresh exact host authorization required")
    path = safe_path(path)
    request = read_json(path)
    if assess(request)["problems"]:
        raise ValueError("rollout preflight blocked")
    selected = selection(request, full=True)
    environment = worker.environment_evidence()
    plan = request["plan"]
    subject = {
        "request_sha256": pf.sha(pf.bounded_bytes(path)),
        "code_commit": plan["code_commit"],
        "authorization_id": plan["proposed_authorization_id"],
        "limits": request["limits"],
        "output_directory": plan["output_directory"],
        "freeze_reference": request["freeze_reference"],
        "operation": "120_development_cases_three_policies_execution_and_replay"
        if request["kind"] == KIND
        else "retained_development_unexecuted_suffix_execution_and_replay",
    }
    expected = dict(
        subject, actor="MattyAnd", decision="approved", protocol_freeze_authenticated=True
    )
    if trusted_authorize(json.loads(json.dumps(subject))) != expected:
        raise PermissionError("exact freeze and rollout authority not authenticated")
    ledger = safe_path(ledger)
    canonical = ROOT.parent / "RuleStudy_Run_Ledger"
    out = safe_path(plan["output_directory"])
    if (
        ledger != canonical
        or out.is_relative_to(ROOT)
        or out.is_relative_to(ledger)
        or ledger.is_relative_to(out)
    ):
        raise ValueError("canonical external one-use ledger and separate output required")
    if any(
        k in os.environ
        for k in (
            "RULE04_WORKER_PAIR",
            "RULE04_WORKER_DEADLINE",
            "RULE04_AUTHENTICATED_REQUEST_SHA256",
            "RULE04_WORKER_REQUEST_SHA256",
        )
    ):
        raise ValueError("inherited pair selector or deadline refused")
    ledger.mkdir(exist_ok=True)
    entry = ledger / (pf.sha(subject["authorization_id"].encode()) + ".json")
    if entry.with_suffix(".result.json").exists():
        raise FileExistsError("authorization ID already has a result marker")
    with entry.open("x", encoding="utf-8") as f:
        json.dump({"receipt": expected, "environment": environment}, f, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    result = {"status": "stopped_after_reservation", "retry_allowed": False}
    try:
        if (
            pf.sha(pf.bounded_bytes(path)) != subject["request_sha256"]
            or assess(request)["problems"]
            or selection(request, full=True) != selected
        ):
            raise ValueError("request/source/input drift after ID reservation")
        if worker.environment_evidence() != environment:
            raise ValueError("environment changed after reservation")
        deadline = monotonic() + request["limits"]["wall_seconds"]
        result = supervisor.supervise(
            _command(path, subject["request_sha256"], deadline=deadline),
            request["limits"]["wall_seconds"],
            output=out,
            limit_bytes=request["limits"]["output_bytes"],
            cwd=ROOT,
            deadline=deadline,
        )
        result["retry_allowed"] = False
        result["authenticated_request_sha256"] = subject["request_sha256"]
        if not result["cleanup_verified"]:
            result["status"] = "failed_cleanup"
        if result["status"] == "succeeded" and result["cleanup_verified"]:
            report = read_json(out / "rollout-report.json")
            if (
                report["status"] != "PASS"
                or report["runs"] != len(selected)
                or selection(request, full=True) != selected
                or assess_after_run(request)
                or (
                    request["kind"] == SUFFIX_KIND
                    and (
                        report.get("scope_complete_only") is not True
                        or report.get("selected_pairs") != [list(p) for p in selected]
                        or report.get("parent") != request["parent"]
                    )
                )
            ):
                result["status"] = "failed_result_or_drift"
        if result["status"] != "succeeded":
            _supervisor_failure(out, result)
        return result
    except BaseException as exc:
        result["status"] = "failed_after_reservation"
        result["exception"] = type(exc).__name__
        result["message"] = str(exc)[:2000]
        raise
    finally:
        _write(entry.with_suffix(".result.json"), result)


def _supervisor_failure(out, result):
    """Host fallback after child cleanup, including a hard kill before its summary."""
    out = safe_path(out)
    if not out.exists():
        return
    target = out / "rollout-failure.json"
    if target.exists():
        try:
            read_json(target)
        except (ValueError, UnicodeError):
            # Preserve a child summary truncated by termination, but retain a
            # separate complete host record rather than treating existence as PASS.
            target = out / "rollout-supervisor-failure.json"
        else:
            return
    checkpoints = sorted(out.glob("checkpoint-*.json"))
    if len(checkpoints) > 360:
        raise ValueError("excessive checkpoint inventory")
    latest = (
        read_json(checkpoints[-1])
        if checkpoints
        else {
            "completed_runs": 0,
            "charged_steps_completed_pairs_only": {"states": 0, "transitions": 0},
            "coverage": {
                s: {
                    "expected_runs": 120,
                    "completed_runs": 0,
                    "completed_by_policy": dict.fromkeys(POLICIES, 0),
                }
                for s in ("normal_feasible", "overloaded_impossible", "missing_forecast")
            },
        }
    )
    _write(
        target,
        dict(
            latest,
            status="FAIL_OR_INCOMPLETE",
            summary_origin="host_after_supervisor_stop",
            supervision=result,
            authenticated_request_sha256=result.get("authenticated_request_sha256"),
            retry_allowed=False,
            failed_pair_additional_work="unknown if killed; bounded by remaining budget reserved for that pair",
        ),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--draft", action="store_true")
    group.add_argument("--inspect", type=Path)
    parser.add_argument("--parent-receipt", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.parent_receipt and not args.draft:
        parser.error("--parent-receipt is only a draft binding, never an execution option")
    try:
        value = draft() if args.draft else assess(read_json(args.inspect))
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        subprocess.SubprocessError,
    ) as exc:
        if not args.inspect:
            raise
        value = {
            "status": "BLOCKED",
            "problems": [f"{type(exc).__name__}: {str(exc)[:2000]}"],
            "execution_authorized": False,
            "final_generation_supported": False,
        }
        _write(args.out, value)
        return 2
    if args.parent_receipt:
        parent = safe_path(args.parent_receipt)
        value.update(
            kind=SUFFIX_KIND,
            parent={"path": str(parent), "sha256": pf.sha(pf.bounded_bytes(parent))},
        )
    _write(args.out, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
