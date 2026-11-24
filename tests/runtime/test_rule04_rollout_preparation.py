"""Offline fixture plumbing only; no real approval or development batch."""

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from scripts import prepare_rule_study_rollout as w
from scripts import rule_rollout_supervisor as sup


def limits():
    # Dummy test envelope, not a proposed/approved scientific budget.
    return {
        "states": 50000,
        "transitions": 50000,
        "wall_seconds": 30,
        "case_policy_seconds": 10,
        "output_bytes": 1024 * 1024,
    }


@pytest.mark.parametrize(
    "key,value",
    [
        ("states", 10000),
        ("transitions", 10000),
        ("wall_seconds", 901),
        ("case_policy_seconds", 61),
        ("output_bytes", True),
        ("states", None),
        ("states", 5_000_001),
    ],
)
def test_invalid_or_reused_verification_budget_refused(key, value):
    data = limits()
    data[key] = value
    with pytest.raises(ValueError):
        w.validate_limits(data)


def test_preparation_cli_has_no_execute_option():
    done = subprocess.run([sys.executable, str(Path(w.__file__)), "--execute"], capture_output=True)
    assert done.returncode != 0


def test_closed_gate_never_reads_request(tmp_path):
    done = subprocess.run(
        [sys.executable, "-c", w.BOOTSTRAP, str(tmp_path), "missing", "0" * 64],
        input=b"",
        capture_output=True,
    )
    assert done.returncode == 90 and not list(tmp_path.iterdir())


def test_altered_request_fails_before_project_import(tmp_path):
    p = tmp_path / "request.json"
    p.write_text("{}")
    done = subprocess.run(
        [sys.executable, "-c", w.BOOTSTRAP, str(tmp_path), str(p), "0" * 64],
        input=b"G",
        capture_output=True,
    )
    assert done.returncode == 91


def test_no_authority_does_not_touch_id_or_output(tmp_path):
    with pytest.raises(PermissionError):
        w.dispatch_once(tmp_path / "missing", ledger=tmp_path / "ledger")
    assert not list(tmp_path.iterdir())


def test_json_duplicate_and_link_refusal(tmp_path):
    p = tmp_path / "duplicate.json"
    p.write_text('{"x":1,"x":2}')
    with pytest.raises(ValueError, match="duplicate"):
        w.read_json(p)


@pytest.mark.parametrize(
    "mode,expected",
    [("ok", "succeeded"), ("fail", "failed"), ("timeout", "timed_out"), ("output", "output_limit")],
)
def test_real_dummy_process_stop_controls(tmp_path, mode, expected):
    if os.name != "nt":
        pytest.skip("Windows Job Object control")
    code = "import sys,time,pathlib; assert sys.stdin.buffer.read(1)==b'G'; "
    if mode == "fail":
        code += "raise SystemExit(7)"
    elif mode == "timeout":
        code += "time.sleep(10)"
    elif mode == "output":
        code += f"pathlib.Path({str(tmp_path / 'big')!r}).write_bytes(b'x'*4096); time.sleep(10)"
    else:
        code += "pass"
    result = sup.supervise(
        [sys.executable, "-c", code],
        0.8 if mode == "timeout" else 5,
        output=tmp_path,
        limit_bytes=1024,
        cwd=w.ROOT,
    )
    assert result["status"] == expected and result["cleanup_verified"]


def test_descendant_left_after_parent_stops_is_killed(tmp_path):
    if os.name != "nt":
        pytest.skip("Windows Job Object control")
    code = "import sys,subprocess; assert sys.stdin.buffer.read(1)==b'G'; subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'])"
    result = sup.supervise(
        [sys.executable, "-c", code], 5, output=tmp_path, limit_bytes=1024, cwd=w.ROOT
    )
    assert result["status"] == "descendants_left_running" and result["cleanup_verified"]


def test_nested_job_containment_for_dummy_pair(tmp_path):
    if os.name != "nt":
        pytest.skip("Windows Job Object control")
    inner = "import sys; assert sys.stdin.buffer.read(1)==b'G'"
    code = (
        "import sys; assert sys.stdin.buffer.read(1)==b'G'; "
        "from scripts.rule_rollout_supervisor import supervise; "
        f"r=supervise([sys.executable,'-c',{inner!r}],3,output={str(tmp_path)!r},limit_bytes=1024,cwd={str(w.ROOT)!r}); "
        "assert r['status']=='succeeded' and r['cleanup_verified']"
    )
    result = sup.supervise(
        [sys.executable, "-c", code], 8, output=tmp_path, limit_bytes=1024, cwd=w.ROOT
    )
    assert result["status"] == "succeeded" and result["cleanup_verified"]


@pytest.mark.parametrize("hidden", [False, True])
@pytest.mark.parametrize("policy", w.POLICIES)
def test_one_authored_fixture_pair_uses_real_runner_and_independent_replay(
    tmp_path, monkeypatch, hidden, policy
):
    from dc_sustainability.evaluation import rule_study_receiving as rv
    from dc_sustainability.evaluation import rule_study_trace as tr
    from dc_sustainability.rule_study import cases, runner

    fixture = replace(cases.CASE_A, forecast_present=not hidden)
    weights = list(fixture.score_profile)
    parsed = tr.case_from_dict(fixture.case_json())
    monkeypatch.setattr(
        w, "pair", lambda: ({}, {"cases": [{"case_id": "A", "weights": weights}]}, {"A": parsed})
    )
    fixture_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=w.ROOT, text=True
    ).strip()
    original = runner.make_bindings
    monkeypatch.setattr(
        runner, "make_bindings", lambda case, root: original(case, root, code_commit=fixture_commit)
    )
    original_pin = rv.reconstruct_pin
    # Test pin is expressly fixture-only, not real clean/merged evidence or authority.
    monkeypatch.setattr(
        rv,
        "reconstruct_pin",
        lambda root: dict(
            original_pin(root, code_commit=fixture_commit),
            commit_source="git",
            clean_tree=True,
            merged_main=True,
        ),
    )
    directory = tmp_path / "fixture"
    directory.mkdir()
    w._one_pair(
        {"limits": limits()}, "A", policy, directory, {"states": 50000, "transitions": 50000}
    )
    result = w.read_json(directory / "pair-result.json")
    assert result["status"] == "PASS"
    assert result["budget"]["states_used"] >= 60 and result["budget"]["transitions_used"] >= 60
    trace_root = directory / result["trace_directory"]
    trace = w.read_json(trace_root / "case.json")
    assert (trace["scores"] is None) == hidden
    assert result["metric"]["synthetic_impact"]["matches_producer"]
    background = fixture.background_kw * sum(weights)
    assert result["metric"]["background_synthetic_impact"]["total"] == background
    assert (
        result["metric"]["site_synthetic_impact"]["total"]
        == background + result["metric"]["synthetic_impact"]["producer_total"]
    )
    if hidden:
        state_files = list((trace_root / "states").glob("*.json"))
        assert state_files
        for p in state_files:
            assert not json.loads(p.read_text())["carbon_facts"]


def dispatch_fixture(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(w, "ROOT", repo)
    monkeypatch.setattr(w, "assess", lambda r: {"problems": []})
    monkeypatch.setattr(w, "assess_after_run", lambda r: False)
    monkeypatch.setattr(w.worker, "environment_evidence", lambda: {"fixture": True})
    request = {
        "kind": w.KIND,
        "plan": {
            "code_commit": "unit-fixture",
            "proposed_authorization_id": "dummy-unit-only",
            "output_directory": str(tmp_path / "output"),
        },
        "limits": limits(),
        "freeze_reference": "unit fixture only",
    }
    path = tmp_path / "request.json"
    w._write(path, request)
    return path, tmp_path / "RuleStudy_Run_Ledger", request


def fixture_authority(subject):
    return dict(subject, actor="MattyAnd", decision="approved", protocol_freeze_authenticated=True)


def test_wrong_exact_authority_never_reserves(tmp_path, monkeypatch):
    path, ledger, _ = dispatch_fixture(tmp_path, monkeypatch)
    with pytest.raises(PermissionError):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=lambda s: {})
    assert not ledger.exists()


def test_one_use_id_and_verified_result_gate(tmp_path, monkeypatch):
    path, ledger, req = dispatch_fixture(tmp_path, monkeypatch)

    def done(*args, **kwargs):
        out = Path(req["plan"]["output_directory"])
        out.mkdir()
        w._write(out / "rollout-report.json", {"status": "PASS", "runs": 360})
        return {"status": "succeeded", "cleanup_verified": True}

    monkeypatch.setattr(w.supervisor, "supervise", done)
    result = w.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)
    assert result["status"] == "succeeded"
    with pytest.raises(FileExistsError):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)


def test_cleanup_failure_cannot_return_success(tmp_path, monkeypatch):
    path, ledger, _ = dispatch_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        w.supervisor,
        "supervise",
        lambda *a, **k: {"status": "succeeded", "cleanup_verified": False},
    )
    assert (
        w.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)["status"]
        == "failed_cleanup"
    )


def test_request_drift_consumes_id_but_does_not_release(tmp_path, monkeypatch):
    path, ledger, _ = dispatch_fixture(tmp_path, monkeypatch)

    def mutate(subject):
        path.write_text("{}")
        return fixture_authority(subject)

    with pytest.raises(ValueError, match="drift"):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=mutate)
    assert len(list(ledger.glob("*.json"))) == 2
    assert any(
        w.read_json(p).get("status") == "failed_after_reservation" for p in ledger.glob("*.json")
    )


def test_inherited_pair_selector_refused(tmp_path, monkeypatch):
    path, ledger, _ = dispatch_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("RULE04_WORKER_PAIR", "untrusted")
    with pytest.raises(ValueError, match="inherited"):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)
    assert not ledger.exists()


def test_result_marker_alone_also_refuses_id_reuse(tmp_path, monkeypatch):
    path, ledger, req = dispatch_fixture(tmp_path, monkeypatch)
    ledger.mkdir()
    name = w.pf.sha(req["plan"]["proposed_authorization_id"].encode()) + ".result.json"
    w._write(ledger / name, {"status": "historical fixture result"})
    with pytest.raises(FileExistsError, match="result marker"):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)
    assert len(list(ledger.iterdir())) == 1


def test_batch_stops_on_first_failed_pair_and_preserves_failure(tmp_path, monkeypatch):
    out = tmp_path / "out"
    request = {"plan": {"output_directory": str(out)}, "limits": limits()}
    monkeypatch.setattr(
        w,
        "pair",
        lambda: ({"cases": [{"case_id": "A", "stratum": "fixture"}]}, {}, {"A": object()}),
    )
    calls = []

    def fail(*args, **kwargs):
        calls.append(args[0])
        return {"status": "timed_out", "cleanup_verified": True}

    monkeypatch.setattr(w.supervisor, "supervise", fail)
    with pytest.raises(ValueError, match="no retry"):
        w._batch(request, out)
    assert len(calls) == 1 and (out / "rollout-failure.json").is_file()
    report = w.read_json(out / "rollout-failure.json")
    assert report["completed_runs"] == 0 and report["failed_pair_additional_work"].startswith(
        "unknown"
    )
    # The fixed Python source remains at -c's argument, not in the ROOT argument.
    assert calls[0][4] == "-c" and "RULE04_WORKER_PAIR" in calls[0][5]
    assert calls[0][6] == str(w.ROOT)
