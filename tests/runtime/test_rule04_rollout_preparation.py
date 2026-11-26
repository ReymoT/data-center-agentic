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


def test_all_retained_development_cases_construct_opaque_episodes_without_execution(monkeypatch):
    from dc_sustainability.evaluation import rule_study_receiving as rv
    from dc_sustainability.rule_study import runner

    def forbidden(*args, **kwargs):
        pytest.fail("static mapping must not execute a policy or simulator")

    monkeypatch.setattr(rv, "_run_bounded_case", forbidden)
    monkeypatch.setattr(runner, "make_bindings", forbidden)
    cases, _, parsed = w.pair()
    identities = []
    for original in cases["cases"]:
        visible = parsed[original["case_id"]]
        mapped = w.development_case_spec(visible)
        assert mapped.case_id == visible.case_id
        assert mapped.case_json() == {key: original[key] for key in mapped.case_json()}
        assert mapped.episode().episode_id == mapped.episode_id
        assert mapped.episode_id == w.development_case_spec(visible).episode_id
        assert all(token not in mapped.episode_id.lower() for token in ("dev", "test", "held"))
        assert mapped.forecast_present == (visible.scores is not None)
        if visible.scores is None:
            assert mapped.case_json()["scores"] is None
            assert mapped.forecasts_by_slot() is None
        identities.append(mapped.episode_id)
    assert len(set(identities)) == len(identities) == 120


def test_mapping_does_not_collapse_truncated_or_sanitized_case_names():
    from dc_sustainability.evaluation import rule_study_verifier as v

    template = v.authored_cases(w.read_json(w.ROOT / "docs/rule_study/specification.json"))[0]
    ids = ["development-normal_feasible-00", "development-normal-feasible-00"]
    ids += ["development-" + "a" * 40 + suffix for suffix in ("1", "2")]
    mapped = [w.development_case_spec(replace(template, case_id=name)) for name in ids]
    assert len({case.episode_id for case in mapped}) == len(ids)
    assert [case.case_id for case in mapped] == ids


@pytest.mark.parametrize("mode", ["invalid_id", "collision"])
def test_retained_preflight_rejects_mapping_errors_without_dispatch(monkeypatch, mode):
    original = w.development_case_spec

    def broken(visible):
        return replace(
            original(visible),
            episode_id="EP-development" if mode == "invalid_id" else "EP-Q123",
        )

    monkeypatch.setattr(w, "development_case_spec", broken)
    with pytest.raises(ValueError, match="opaque|collision"):
        w.pair()


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
    assert result["status"] == "succeeded" and result["cleanup_verified"], result


@pytest.mark.parametrize("hidden", [False, True])
@pytest.mark.parametrize("policy", w.POLICIES)
@pytest.mark.parametrize("job_count", [2, 3, 4])
def test_one_authored_fixture_pair_uses_real_runner_and_independent_replay(
    tmp_path, monkeypatch, hidden, policy, job_count
):
    from dc_sustainability.evaluation import rule_study_receiving as rv
    from dc_sustainability.evaluation import rule_study_trace as tr
    from dc_sustainability.rule_study import cases, runner

    fixture = replace(cases.CASE_A, forecast_present=not hidden)
    if job_count > 2:
        fixture = replace(
            fixture,
            jobs=fixture.jobs
            + tuple(cases._job(f"J{i}", 20, 3, True) for i in range(3, job_count + 1)),
            capacity_kw=100,
        )
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
    # These verify runner/replay semantics, not a 10-second CI speed target.
    # Use the already supported production pair ceiling; stop-control tests
    # retain their separate short dummy bounds.
    try:
        w._one_pair(
            {"limits": dict(limits(), case_policy_seconds=60)},
            "A",
            policy,
            directory,
            {"states": 50000, "transitions": 50000},
        )
    except ValueError:
        replay = directory / "replay.json"
        if replay.is_file():
            pytest.fail("Fixture independent replay detail: " + replay.read_text(encoding="utf-8"))
        raise
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
    monkeypatch.setattr(w, "selection", lambda *a, **k: [(str(i), "fixture") for i in range(360)])
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
    monkeypatch.setattr(w, "selection", lambda *a, **k: [("A", "rules-v1")])
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


def test_command_keeps_authorized_hash_when_request_swapped(tmp_path):
    path = tmp_path / "request.json"
    path.write_text('{"changed":true}')
    command = w._command(path, "a" * 64, deadline=123.5)
    assert command[-1] == "a" * 64
    assert "RULE04_WORKER_DEADLINE" in command[5] and "123.5" in command[5]
    done = subprocess.run(command, input=b"G", capture_output=True)
    assert done.returncode == 91  # refuses swapped bytes before project import


def test_host_summary_after_kill_retains_last_complete_checkpoint(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    w._write(
        out / "checkpoint-0001.json",
        {
            "completed_runs": 1,
            "charged_steps_completed_pairs_only": {"states": 60, "transitions": 60},
        },
    )
    (out / "checkpoint-0002.pending").write_text('{"incomplete":')
    w._supervisor_failure(out, {"status": "timed_out", "cleanup_verified": True})
    result = w.read_json(out / "rollout-failure.json")
    assert (
        result["completed_runs"] == 1
        and result["charged_steps_completed_pairs_only"]["states"] == 60
    )
    assert result["supervision"]["status"] == "timed_out" and not result["retry_allowed"]
    original = (out / "rollout-failure.json").read_bytes()
    w._supervisor_failure(out, {"status": "failed"})
    assert (out / "rollout-failure.json").read_bytes() == original
    (out / "rollout-failure.json").write_text('{"cut_off":')
    w._supervisor_failure(out, {"status": "timed_out"})
    assert w.read_json(out / "rollout-supervisor-failure.json")["completed_runs"] == 1
    assert (out / "rollout-failure.json").read_text() == '{"cut_off":'


def test_pair_exception_message_survives_devnull(tmp_path, monkeypatch):
    request = {
        "kind": w.KIND,
        "plan": {"output_directory": str(tmp_path)},
        "limits": limits(),
        "freeze_reference": "fixture",
    }
    monkeypatch.setenv("RULE04_WORKER_PAIR", json.dumps(["A", "rules-v1", 100, 100]))
    monkeypatch.setattr(w, "pair", lambda: ({}, {}, {"A": object()}))
    monkeypatch.setattr(w, "assess_after_run", lambda req: False)

    def fail(*args, **kwargs):
        raise ValueError("specific metric mismatch fixture")

    monkeypatch.setattr(w, "_one_pair", fail)
    with pytest.raises(ValueError, match="specific metric"):
        w.execute_prepared(request)
    failure = w.read_json(tmp_path / "A-rules-v1/pair-failure.json")
    assert failure["message"] == "specific metric mismatch fixture"
    assert failure["reserved_remaining_budget"] == {"states": 100, "transitions": 100}


def test_inventory_deadline_checked_during_traversal(tmp_path, monkeypatch):
    (tmp_path / "one").write_text("a")
    ticks = iter([0, 2])
    monkeypatch.setattr(sup, "monotonic", lambda: next(ticks))
    with pytest.raises(TimeoutError, match="inventory deadline"):
        sup.output_bytes(tmp_path, deadline=1)


def test_original_and_pair_request_hashes_are_distinguished(tmp_path):
    command = w._command(tmp_path / "missing", "b" * 64, original_hash="a" * 64)
    assert "'" + "a" * 64 + "'" in command[5]
    assert "'" + "b" * 64 + "'" in command[5]
    assert command[-1] == "b" * 64


def test_partial_coverage_preserves_unexecuted_control_stratum():
    strata = {"a": "normal_feasible", "b": "overloaded_impossible", "c": "missing_forecast"}
    result = w.coverage([{"case_id": "a", "policy_id": "rules-v1"}], strata)
    assert result["normal_feasible"]["completed_runs"] == 1
    assert result["missing_forecast"] == {
        "expected_runs": 3,
        "completed_runs": 0,
        "completed_by_policy": dict.fromkeys(w.POLICIES, 0),
    }


def test_child_accounting_pair_is_loaded_once(tmp_path, monkeypatch):
    calls = []

    def load():
        calls.append(True)
        return ({}, {}, {"A": object()})

    monkeypatch.setattr(w, "pair", load)
    monkeypatch.setattr(w, "assess_after_run", lambda r: False)
    monkeypatch.setenv("RULE04_WORKER_PAIR", json.dumps(["A", "rules-v1", 100, 100]))

    def checked(*a, loaded=None):
        assert loaded[2]["A"] is not None

    monkeypatch.setattr(w, "_one_pair", checked)
    w.execute_prepared(
        {
            "kind": w.KIND,
            "plan": {"output_directory": str(tmp_path)},
            "limits": limits(),
            "freeze_reference": "fixture",
        }
    )
    assert len(calls) == 1


def test_full_nested_path_layout_on_native_short_parent():
    if os.name != "nt":
        pytest.skip("Windows MAX_PATH layout fixture")
    import tempfile

    home = Path.home().resolve()
    with tempfile.TemporaryDirectory(prefix="R4T_", dir=home) as temporary:
        base = Path(temporary).resolve()
        assert base.is_relative_to(home) and base.name.startswith("R4T_")
        case_id = "development-overloaded_impossible-39"
        assert w.artifact_path_length(base, [case_id]) < 260
        for policy in w.POLICIES:
            p = (
                base
                / f"{case_id}-{policy}"
                / "trace"
                / policy
                / f"{case_id}-{policy}"
                / "snapshots"
                / ("f" * 64 + ".json")
            )
            p.parent.mkdir(parents=True)
            p.write_text("{}")
            assert p.read_text() == "{}"
        # A deliberately deep root reproduces the defect independent of CI's
        # shorter checkout location. This path is calculated, never created.
        assert w.artifact_path_length(home / ("x" * 85), [case_id]) >= 260


def test_batch_reserves_cleanup_margin_before_starting_pair(tmp_path, monkeypatch):
    monkeypatch.setattr(w, "selection", lambda *a, **k: [("A", "rules-v1")])
    monkeypatch.setattr(w, "monotonic", lambda: 10.0)
    monkeypatch.setenv("RULE04_WORKER_DEADLINE", "20.0")
    monkeypatch.setattr(
        w,
        "pair",
        lambda: ({"cases": [{"case_id": "A", "stratum": "fixture"}]}, {}, {"A": object()}),
    )
    monkeypatch.setattr(w.supervisor, "supervise", lambda *a, **k: pytest.fail("no pair may start"))
    with pytest.raises(ValueError, match="budget exhausted"):
        w._batch({"limits": limits()}, tmp_path / "out")
    assert w.read_json(tmp_path / "out/rollout-failure.json")["completed_runs"] == 0


def test_missing_forecast_comparisons_explicitly_labeled_control():
    rows = w.comparison_rows(
        [{"case_id": "hidden", "reduction": 0.0}, {"case_id": "normal", "reduction": 0.2}],
        {"hidden": "missing_forecast", "normal": "normal_feasible"},
    )
    assert rows[0]["comparison_role"] == "control_not_ranking"
    assert rows[1]["comparison_role"] == "development_comparison"


def test_expired_supervisor_deadline_never_starts_process(tmp_path, monkeypatch):
    monkeypatch.setattr(sup.subprocess, "Popen", lambda *a, **k: pytest.fail("expired launch"))
    with pytest.raises(ValueError, match="expired"):
        sup.supervise([], 1, output=tmp_path, limit_bytes=1024, cwd=w.ROOT, deadline=0)


@pytest.mark.parametrize("job_count", [2, 3, 4])
def test_contained_authored_fixture_resource_sample(tmp_path, job_count, record_property):
    """Native-host ordinary fixture only, not a study or capacity guarantee."""
    if os.name != "nt":
        pytest.skip("Windows Job Object resource sample")
    code = (
        "import sys,importlib.util,pathlib,pytest; assert sys.stdin.buffer.read(1)==b'G'; "
        f"s=importlib.util.spec_from_file_location('fixture_test',{__file__!r}); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "mp=pytest.MonkeyPatch(); "
        f"m.test_one_authored_fixture_pair_uses_real_runner_and_independent_replay(pathlib.Path({str(tmp_path)!r}),mp,False,'rules-v1',{job_count}); "
        "mp.undo()"
    )
    result = sup.supervise(
        [sys.executable, "-B", "-c", code],
        30,
        output=tmp_path,
        limit_bytes=8 * 1024 * 1024,
        cwd=w.ROOT,
    )
    assert result["status"] == "succeeded" and result["cleanup_verified"], result
    record_property(
        "scope", "ordinary authored fixture; no bootstrap/development-batch feasibility claim"
    )
    record_property("jobs", job_count)
    record_property("native_contained_elapsed_s", result["elapsed_total_s"])
    record_property("fixture_output_bytes", sup.output_bytes(tmp_path))


def test_output_inventory_survives_vanished_publish_temp(tmp_path, monkeypatch):
    stable = tmp_path / "published.json"
    stable.write_bytes(b"abc")

    class VanishedTemporary:
        def is_symlink(self):
            return False

        def is_junction(self):
            return False

        def is_file(self):
            return True

        def stat(self, *a, **k):
            raise FileNotFoundError("temporary publication entry disappeared")

        lstat = stat

    monkeypatch.setattr(Path, "rglob", lambda *a: iter([VanishedTemporary(), stable]))
    assert sup.output_bytes(tmp_path) == 3


def test_output_inventory_other_stat_errors_remain_fail_closed(tmp_path, monkeypatch):
    class Unreadable:
        def is_symlink(self):
            return False

        def is_junction(self):
            return False

        def is_file(self):
            return True

        def stat(self, *a, **k):
            raise PermissionError("unreadable output")

        lstat = stat

    monkeypatch.setattr(Path, "rglob", lambda *a: iter([Unreadable()]))
    with pytest.raises(PermissionError):
        sup.output_bytes(tmp_path)


@pytest.mark.parametrize("reparse", [False, True])
def test_output_inventory_nonfollowing_snapshot_rejects_links(tmp_path, monkeypatch, reparse):
    import stat
    from types import SimpleNamespace

    class Linked:
        def lstat(self):
            return SimpleNamespace(
                st_mode=stat.S_IFDIR if reparse else stat.S_IFLNK,
                st_file_attributes=0x400 if reparse else 0,
                st_size=0,
            )

    monkeypatch.setattr(Path, "rglob", lambda *a: iter([Linked()]))
    with pytest.raises(ValueError, match="unsafe"):
        sup.output_bytes(tmp_path)
