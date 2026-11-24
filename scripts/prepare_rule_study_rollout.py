"""Prepare fixed development-only RULE04 dispatch; public CLI never executes it.

Trusted-host dispatch requires fresh exact authority, including protocol freeze.
No final generator, model, arbitrary command or alternate input set is supported.
"""

import argparse
import json
import os
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


def read_json(path):
    def pairs(items):
        value = {}
        for k, v in items:
            if k in value:
                raise ValueError("duplicate JSON key")
            value[k] = v
        return value

    def nonfinite(_):
        raise ValueError("nonfinite JSON")

    path = safe_path(path)
    return json.loads(pf.bounded_bytes(path), object_pairs_hook=pairs, parse_constant=nonfinite)


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
    return cases, sidecar, parsed


def validate_limits(limits):
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
    if min(limits["states"], limits["transitions"]) < 21600:
        raise ValueError(
            "full execution plus replay needs at least 21600 charged steps, plus oracle work"
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
    if not isinstance(request, dict) or set(request) != FIELDS or request["kind"] != KIND:
        raise ValueError("fixed development rollout request required")
    report = pf.assess(request["plan"])
    problems = list(report["problems"])
    try:
        validate_limits(request["limits"])
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
    pair()
    return {
        "status": "BLOCKED" if problems else "PREPARED_NOT_AUTHORIZED",
        "problems": problems,
        "execution_authorized": False,
        "runs": 360,
        "final_generation_supported": False,
    }


def _write(path, value):
    with safe_path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def _command(path):
    return [
        sys.executable,
        "-B",
        "-X",
        "utf8",
        "-c",
        BOOTSTRAP,
        str(ROOT),
        str(path),
        pf.sha(pf.bounded_bytes(path)),
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


def _one_pair(request, case_id, policy, directory, remaining):
    from dc_sustainability.evaluation import rule_study_receiving as rv
    from dc_sustainability.evaluation import rule_study_verifier as v
    from dc_sustainability.rule_study import runner, scheduler

    _, sidecar, parsed = pair()
    visible = parsed[case_id]
    weights = next(e["weights"] for e in sidecar["cases"] if e["case_id"] == case_id)
    case = replace(rv.case_spec_for(visible), first_scores=tuple(weights))
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
        if set(request) != FIELDS or request["kind"] != KIND or assess_after_run(request):
            raise ValueError("pair source/input request refused")
        validate_limits(request["limits"])
        case_id, policy, states, transitions = json.loads(mode)
        if case_id not in pair()[2] or policy not in POLICIES:
            raise ValueError("unknown pair")
        if any(
            type(n) is not int or not 0 < n <= request["limits"][k]
            for k, n in (("states", states), ("transitions", transitions))
        ):
            raise ValueError("invalid remaining pair budget")
        directory = out / f"{case_id}-{policy}"
        directory.mkdir(exist_ok=False)
        _one_pair(
            request, case_id, policy, directory, {"states": states, "transitions": transitions}
        )
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
    used = {"states": 0, "transitions": 0}
    metrics, reports, control_signatures = [], [], {}
    try:
        for case_id in pair()[2]:
            for policy in POLICIES:
                remaining = {k: limits[k] - used[k] for k in used}
                seconds = min(
                    limits["case_policy_seconds"], limits["wall_seconds"] - (monotonic() - started)
                )
                if min(remaining.values()) <= 0 or seconds <= 0:
                    raise ValueError("combined resource budget exhausted")
                task = out / "pair-request.json"
                # One immutable request per pair; no overwrites or retries.
                task = task.with_name(f"request-{case_id}-{policy}.json")
                _write(task, request)
                selector = json.dumps(
                    [case_id, policy, remaining["states"], remaining["transitions"]]
                )
                command = _command(task)
                # Fixed selector bound in the child command, never inherited from the host.
                command[5] = (
                    "import os; os.environ['RULE04_WORKER_PAIR']="
                    + repr(selector)
                    + ";\n"
                    + BOOTSTRAP
                )
                result = supervisor.supervise(
                    command, seconds, output=out, limit_bytes=limits["output_bytes"], cwd=ROOT
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
                if pair()[2][case_id].scores is None:
                    signature = received["execution_signature"]
                    if case_id in control_signatures and control_signatures[case_id] != signature:
                        raise ValueError(
                            "missing-forecast control differs across policies; investigate, do not rank"
                        )
                    control_signatures[case_id] = signature
        if assess_after_run(request):
            raise ValueError("source/input drift after batch")
        strata = {c["case_id"]: c["stratum"] for c in pair()[0]["cases"]}
        grouped = {
            s: [dict(m, stratum=s) for m in metrics if strata[m["case_id"]] == s]
            for s in sorted(set(strata.values()))
        }
        _write(
            out / "rollout-report.json",
            {
                "status": "PASS",
                "scope": "development only; not unseen generalization",
                "runs": len(metrics),
                "charged_steps": used,
                "strata": grouped,
                "equal_work_vs_greedy_a": mc.equal_work(metrics),
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
                "completed_runs": len(metrics),
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


def dispatch_once(path, *, ledger, trusted_authorize=None):
    """Host-only hook. Exact authority must authenticate both freeze and run approval."""
    if not callable(trusted_authorize):
        raise PermissionError("fresh exact host authorization required")
    path = safe_path(path)
    request = read_json(path)
    if assess(request)["problems"]:
        raise ValueError("rollout preflight blocked")
    environment = worker.environment_evidence()
    plan = request["plan"]
    subject = {
        "request_sha256": pf.sha(pf.bounded_bytes(path)),
        "code_commit": plan["code_commit"],
        "authorization_id": plan["proposed_authorization_id"],
        "limits": request["limits"],
        "output_directory": plan["output_directory"],
        "freeze_reference": request["freeze_reference"],
        "operation": "120_development_cases_three_policies_execution_and_replay",
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
    if "RULE04_WORKER_PAIR" in os.environ:
        raise ValueError("inherited pair selector refused")
    ledger.mkdir(exist_ok=True)
    entry = ledger / (pf.sha(subject["authorization_id"].encode()) + ".json")
    with entry.open("x", encoding="utf-8") as f:
        json.dump({"receipt": expected, "environment": environment}, f, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    result = {"status": "stopped_after_reservation", "retry_allowed": False}
    try:
        if (
            pf.sha(pf.bounded_bytes(path)) != subject["request_sha256"]
            or assess(request)["problems"]
        ):
            raise ValueError("request/source/input drift after ID reservation")
        if worker.environment_evidence() != environment:
            raise ValueError("environment changed after reservation")
        result = supervisor.supervise(
            _command(path),
            request["limits"]["wall_seconds"],
            output=out,
            limit_bytes=request["limits"]["output_bytes"],
            cwd=ROOT,
        )
        result["retry_allowed"] = False
        if not result["cleanup_verified"]:
            result["status"] = "failed_cleanup"
        if result["status"] == "succeeded" and result["cleanup_verified"]:
            report = read_json(out / "rollout-report.json")
            if report["status"] != "PASS" or report["runs"] != 360 or assess_after_run(request):
                result["status"] = "failed_result_or_drift"
        return result
    except BaseException as exc:
        result["status"] = "failed_after_reservation"
        result["exception"] = type(exc).__name__
        raise
    finally:
        _write(entry.with_suffix(".result.json"), result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--draft", action="store_true")
    group.add_argument("--inspect", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    value = draft() if args.draft else assess(read_json(args.inspect))
    _write(args.out, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
