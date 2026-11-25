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
    assert "| overloaded_impossible | rules-v1 | 0/1 | unavailable |" in tables
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
        {"case_id": "n2", "policy_id": "greedy_a", "exception": "TimeoutError"}
    ]
    tables = core.tables_markdown(s)
    assert "Coverage: **PARTIAL**" in tables and "TimeoutError" in tables
    assert "PARTIAL coverage" in core.plot_svg(s)


def test_count_or_coverage_mismatch_with_the_run_record_is_refused(tmp_path):
    (tmp_path / "a").mkdir()
    with pytest.raises(ValueError, match="count"):
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
    with pytest.raises(ValueError, match="exactly one"):
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
    done = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    assert done.returncode == 0, done.stderr
    assert "coverage: COMPLETE" in done.stdout and (out / "RULE04_TABLES.md").is_file()
    again = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    assert again.returncode != 0 and "already exists" in again.stderr
