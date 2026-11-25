"""RULE-04 summary tables/plot: hand-built rollout output fixtures, no policy or simulator runs."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import prepare_rule_study_rollout as rollout
from scripts import rule04_summary_core as core

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts" / "build_rule04_summary.py"
STRATA = {
    "n1": "normal_feasible",
    "n2": "normal_feasible",
    "o1": "overloaded_impossible",
    "m1": "missing_forecast",
}
ORIGINAL_INPUTS = core._inputs
ORIGINAL_VALIDATE = core._validate_metric


@pytest.mark.parametrize("tamper", [False, True])
def test_suffix_pass_is_partial_global_coverage_and_bound_to_request(tmp_path, monkeypatch, tamper):
    metrics = [metric("n1", "rules-v1", 100)]
    run, cases = make_run(tmp_path, metrics)
    request = {"kind": rollout.SUFFIX_KIND, "parent": {"sha256": "fixture"}}
    path = run / "request-n1-rules-v1.json"
    path.write_text(json.dumps(request))
    result_path = run / "n1-rules-v1/pair-result.json"
    result = core._json(result_path)
    result["pair_request_sha256"] = core._sha(path)
    result_path.write_text(json.dumps(result))
    status_path = run / "rollout-report.json"
    status = core._json(status_path)
    status.update(
        scope_complete_only=True, selected_pairs=[["n1", "rules-v1"]], parent=request["parent"]
    )
    if tamper:
        status["selected_pairs"] = [["n2", "rules-v1"]]
    status_path.write_text(json.dumps(status))
    monkeypatch.setattr(rollout, "selection", lambda *a, **k: [("n1", "rules-v1")])
    if tamper:
        with pytest.raises(ValueError, match="authenticated suffix"):
            core.load_run(run, cases)
    else:
        data = core.load_run(run, cases)
        assert not data["complete"]
        assert core.summarize(data)["coverage_status"] == "PARTIAL"


@pytest.fixture(autouse=True)
def synthetic_reader(monkeypatch):
    """Only summary-math fixtures bypass trace/input validation, never CLI subprocesses."""
    monkeypatch.setattr(core, "_inputs", lambda path: (core._json(path), {}, {}))
    monkeypatch.setattr(core, "_validate_metric", lambda pair, record, inputs: record["metric"])


def metric(
    case_id,
    policy,
    impact,
    *,
    completed=("J1", "J2"),
    turnaround=(1, 1),
    delay=(0, 0),
    violations=0,
    fallback=0,
    blocked=0,
    matches=True,
):
    jobs = ("J1", "J2")
    missed = tuple(j for j in jobs if j not in completed)
    return {
        "case_id": case_id,
        "policy_id": policy,
        "case_sha256": f"sha-{case_id}",
        "code_commit": "abc",
        "bindings": {"code_commit": "abc"},
        "status": "complete",
        "decisions": 30,
        "checked_decisions": 30,
        "executed_starts": len(completed),
        "execution_violations": violations,
        "jobs": 2,
        "completed": len(completed),
        "missed": len(missed),
        "unfinished": len(missed),
        "completed_job_ids": sorted(completed),
        "missed_job_ids": sorted(missed),
        "unfinished_job_ids": sorted(missed),
        "turnaround_slots": {"values": sorted(turnaround), "count": len(turnaround)},
        "start_delay_slots": {"values": sorted(delay), "count": len(delay)},
        "fallback": {
            "attempted_stages": fallback,
            "selected": fallback,
            "blocked_decisions": blocked,
            "error_codes": {},
        },
        "synthetic_impact": {
            "unit": "u",
            "producer_total": impact,
            "recomputed_total": impact,
            "matches_producer": matches,
        },
    }


def default_metrics():
    out = []
    for case_id, (a, r, b) in {
        "n1": (1200, 800, 800),
        "n2": (1000, 900, 1000),
        "m1": (900, 900, 900),
    }.items():
        out += [
            metric(case_id, "greedy_a", a),
            metric(case_id, "rules-v1", r, turnaround=(1, 2), delay=(0, 1)),
            metric(case_id, "greedy_b", b),
        ]
    nothing = dict(completed=(), turnaround=(), delay=(), blocked=1)
    out += [metric("o1", p, 0, **nothing) for p in rollout.POLICIES]
    return out


def make_run(tmp_path, metrics, *, complete=True, failed=(), coverage=True, runs=None):
    cases = tmp_path / "cases.json"
    cases.write_text(
        json.dumps(
            {"set_id": "s", "cases": [{"case_id": c, "stratum": s} for c, s in STRATA.items()]}
        ),
        "utf-8",
    )
    run = tmp_path / "run"
    run.mkdir()
    for m in metrics:
        pair = run / f"{m['case_id']}-{m['policy_id']}"
        pair.mkdir()
        (pair / "pair-result.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "case_id": m["case_id"],
                    "policy_id": m["policy_id"],
                    "authenticated_request_sha256": "a" * 64,
                    "metric": m,
                }
            ),
            "utf-8",
        )
    for case_id, policy in failed:
        pair = run / f"{case_id}-{policy}"
        pair.mkdir()
        (pair / "pair-failure.json").write_text(
            json.dumps(
                {
                    "status": "FAIL_OR_INCOMPLETE",
                    "case_id": case_id,
                    "policy_id": policy,
                    "exception": "TimeoutError",
                }
            ),
            "utf-8",
        )
    status = {"runs" if complete else "completed_runs": len(metrics) if runs is None else runs}
    if coverage:
        status["coverage"] = rollout.coverage(metrics, STRATA)
    if complete:
        status["status"] = "PASS"
        (run / "rollout-report.json").write_text(json.dumps(status), "utf-8")
    else:
        status.update(status="FAIL_OR_INCOMPLETE", message="combined resource budget exhausted")
        (run / "rollout-failure.json").write_text(json.dumps(status), "utf-8")
    return run, cases


def summary_for(tmp_path, metrics=None, **kw):
    run, cases = make_run(tmp_path, default_metrics() if metrics is None else metrics, **kw)
    return core.summarize(core.load_run(run, cases))


def row(rows, stratum, policy):
    (match,) = [r for r in rows if r["stratum"] == stratum and r["policy_id"] == policy]
    return match


def test_complete_run_policy_rows(tmp_path):
    s = summary_for(tmp_path)
    assert s["coverage_status"] == "COMPLETE"
    r = row(s["policy_rows"], "normal_feasible", "rules-v1")
    assert (r["runs_completed"], r["runs_expected"]) == (2, 2)
    assert (r["completed"], r["missed"], r["execution_violations"]) == (4, 0, 0)
    assert r["turnaround_mean_slots"] == 1.5 and r["turnaround_count"] == 4
    assert r["start_delay_mean_slots"] == 0.5 and r["job_impact_total"] == 1700
    o = row(s["policy_rows"], "overloaded_impossible", "greedy_a")
    assert (o["completed"], o["missed"], o["runs_with_blocked_decision"]) == (0, 2, 1)
    assert o["turnaround_mean_slots"] is None and o["turnaround_count"] == 0


def test_comparisons_use_frozen_equal_work_and_never_show_zero_for_unavailable(tmp_path):
    s = summary_for(tmp_path)
    c = row(s["comparison_rows"], "normal_feasible", "rules-v1")
    assert (c["available"], c["rows"]) == (2, 2)
    assert c["reduction_median"] == round(((1200 - 800) / 1200 + (1000 - 900) / 1000) / 2, 4)
    assert c["turnaround_shift_mean_slots"] == 0.5 and c["turnaround_shift_count"] == 2
    o = row(s["comparison_rows"], "overloaded_impossible", "rules-v1")
    assert o["available"] == 0 and o["reduction_median"] is None
    assert o["unavailable_reasons"] == {"greedy_a_impact_not_positive": 1}
    tables = core.tables_markdown(s)
    assert "| overloaded_impossible | rules-v1 | 0/1 (0) | unavailable |" in tables
    assert "0.0 [" not in tables.split("overloaded_impossible | rules-v1")[1].splitlines()[0]


def test_missing_forecast_is_labelled_control_and_excluded_from_plot(tmp_path):
    s = summary_for(tmp_path)
    assert (
        row(s["comparison_rows"], "missing_forecast", "rules-v1")["role"] == "control_not_ranking"
    )
    assert "missing_forecast (control)" in core.tables_markdown(s)
    svg = core.plot_svg(s)
    assert "missing_forecast" not in svg
    assert "rules-v1 · normal_feasible (n=2)" in svg


def test_stopped_run_is_partial_with_failed_pair_listed(tmp_path):
    metrics = [m for m in default_metrics() if m["case_id"] != "n2"]
    s = summary_for(tmp_path, metrics, complete=False, failed=[("n2", "greedy_a")])
    assert s["coverage_status"] == "PARTIAL" and s["stop_message"]
    assert row(s["policy_rows"], "normal_feasible", "greedy_a")["runs_completed"] == 1
    assert s["failed_or_unfinished_pairs"] == [
        {"case_id": "n2", "policy_id": "greedy_a", "exception": "TimeoutError", "message": None}
    ]
    tables = core.tables_markdown(s)
    assert "Coverage: **PARTIAL**" in tables and "TimeoutError" in tables
    assert "PARTIAL coverage" in core.plot_svg(s)


def test_count_or_coverage_mismatch_with_the_run_record_is_refused(tmp_path):
    (tmp_path / "a").mkdir()
    with pytest.raises(ValueError, match="count|PASS requires|coverage"):
        summary_for(tmp_path / "a", runs=5)
    (tmp_path / "b").mkdir()
    run, cases = make_run(tmp_path / "b", default_metrics())
    status = json.loads((run / "rollout-report.json").read_text())
    status["coverage"]["normal_feasible"]["completed_runs"] = 99
    (run / "rollout-report.json").write_text(json.dumps(status))
    with pytest.raises(ValueError, match="coverage"):
        core.load_run(run, cases)


def test_non_pass_pair_and_ambiguous_status_are_refused(tmp_path):
    run, cases = make_run(tmp_path, default_metrics())
    pair = run / "n1-rules-v1" / "pair-result.json"
    record = json.loads(pair.read_text())
    record["status"] = "FAIL"
    pair.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="complete PASS"):
        core.load_run(run, cases)
    (run / "rollout-failure.json").write_text("{}")
    with pytest.raises(ValueError, match="failure status"):
        core.load_run(run, cases)


def test_summary_is_deterministic_and_outputs_never_overwrite(tmp_path):
    run, cases = make_run(tmp_path, default_metrics())
    first = core.summarize(core.load_run(run, cases))
    assert core.summarize(core.load_run(run, cases)) == first
    out = tmp_path / "out"
    names = sorted(p.name for p in core.write_outputs(first, out))
    assert names == ["RULE04_TABLES.md", "summary.json", "turnaround_vs_impact.svg"]
    with pytest.raises(FileExistsError):
        core.write_outputs(first, out)


def test_cli_builds_and_refuses_an_existing_output(tmp_path):
    from scripts import build_rule04_summary as cli

    run, cases = make_run(tmp_path, default_metrics())
    out = tmp_path / "summary"
    args = [
        sys.executable,
        str(SCRIPT),
        "--run-dir",
        str(run),
        "--cases",
        str(cases),
        "--out",
        str(out),
    ]
    # The real CLI must reject these synthetic math fixtures as scientific inputs.
    refused = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    assert refused.returncode == 1 and not out.exists()
    assert cli.main(args[2:]) == 0  # fixture-only helpers are explicitly patched in-process
    assert (out / "RULE04_TABLES.md").is_file()
    again = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    assert again.returncode != 0 and "already exists" in again.stderr


def test_empty_pass_is_never_complete(tmp_path):
    with pytest.raises(ValueError, match="PASS requires"):
        summary_for(tmp_path, metrics=[])


def test_unverified_pair_metrics_refused_by_real_validator(tmp_path, monkeypatch):
    run, cases = make_run(tmp_path, default_metrics())
    monkeypatch.setattr(core, "_validate_metric", ORIGINAL_VALIDATE)
    with pytest.raises((KeyError, ValueError)):
        core.load_run(run, cases)  # no actual retained trace exists


def test_custom_or_altered_cases_refused_by_real_input_gate(tmp_path, monkeypatch):
    run, cases = make_run(tmp_path, default_metrics())
    monkeypatch.setattr(core, "_inputs", ORIGINAL_INPUTS)
    with pytest.raises(ValueError, match="frozen retained"):
        core.load_run(run, cases)


def test_supervisor_failure_wins_over_truncated_or_pass_report(tmp_path):
    run, cases = make_run(tmp_path, default_metrics())
    (run / "rollout-failure.json").write_text('{"cut_off":')
    (run / "rollout-supervisor-failure.json").write_text(
        json.dumps(
            {"status": "FAIL_OR_INCOMPLETE", "completed_runs": 12, "message": "cleanup failed"}
        )
    )
    report = core.summarize(core.load_run(run, cases))
    assert report["coverage_status"] == "PARTIAL" and report["stop_message"] == "cleanup failed"


def test_checkpoint_lag_is_explicit_in_partial_recovery(tmp_path):
    run, cases = make_run(tmp_path, default_metrics(), complete=False, coverage=False)
    path = run / "rollout-failure.json"
    status = json.loads(path.read_text())
    status["completed_runs"] = 10
    path.write_text(json.dumps(status))
    s = core.summarize(core.load_run(run, cases))
    assert s["recovered_unacknowledged_pairs"] == 2 and s["coverage_status"] == "PARTIAL"


def test_plot_uses_the_same_matched_case_subset_for_both_axes():
    a = metric("n1", "greedy_a", 100, completed=(), turnaround=(), delay=())
    b = metric("n1", "rules-v1", 10, completed=(), turnaround=(), delay=())
    a2 = metric("n2", "greedy_a", 100)
    b2 = metric("n2", "rules-v1", 80, turnaround=(2, 2))
    summary = core.comparison_rows([a, b, a2, b2], STRATA)
    r = row(summary, "normal_feasible", "rules-v1")
    assert r["available"] == 2 and r["turnaround_shift_count"] == 1
    assert r["matched_turnaround_reduction_median"] == 0.2


def test_mixed_request_and_duplicate_json_refused(tmp_path):
    run, cases = make_run(tmp_path, default_metrics())
    p = run / "n1-rules-v1/pair-result.json"
    value = json.loads(p.read_text())
    value["authenticated_request_sha256"] = "b" * 64
    p.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="mixed authenticated"):
        core.load_run(run, cases)
    p.write_text('{"status":"PASS","status":"FAIL"}')
    with pytest.raises(ValueError, match="duplicate"):
        core.load_run(run, cases)


def test_real_retained_artifacts_recomputed_and_tampering_refused(tmp_path):
    """Read saved authored A only; no new policy, replay, checker or simulator call."""
    import hashlib
    import tarfile
    from pathlib import PurePosixPath

    from dc_sustainability.evaluation import rule_study_trace as tr

    pair = tmp_path / "A-greedy_a"
    trace = pair / "trace"
    prefix = "authored/greedy_a/A-greedy_a/"
    with tarfile.open(
        ROOT / "docs/evidence/rule03-nov23-native/authored-artifacts.tar.gz", "r:gz"
    ) as archive:
        for member in archive:
            if not member.name.startswith(prefix):
                continue
            relative = PurePosixPath(member.name[len("authored/") :])
            assert not relative.is_absolute() and ".." not in relative.parts and member.isfile()
            assert member.size < 1024 * 1024
            target = trace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
    folder = trace / "greedy_a/A-greedy_a"
    case, _, decisions = core.mc.load_run(folder)
    weights = case["scores"]
    expected = rollout._metric(folder, weights)
    record = {
        "case_id": "A",
        "policy_id": "greedy_a",
        "metric": expected,
        "trace_directory": "trace/greedy_a/A-greedy_a",
        "replay": {"overall": "PASS"},
        "execution_signature": hashlib.sha256(
            json.dumps(
                [d["execution"]["current_starts"] for d in decisions], sort_keys=True
            ).encode()
        ).hexdigest(),
    }
    inputs = ({}, {"cases": [{"case_id": "A", "weights": weights}]}, {"A": tr.case_from_dict(case)})
    assert ORIGINAL_VALIDATE(pair, record, inputs) == expected
    record["metric"]["synthetic_impact"]["producer_total"] += 1
    with pytest.raises(ValueError, match="differs from retained"):
        ORIGINAL_VALIDATE(pair, record, inputs)
