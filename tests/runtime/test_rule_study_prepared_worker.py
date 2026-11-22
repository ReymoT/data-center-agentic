"""Offline worker plumbing; test fixtures are not real approval or study results."""

import json
import subprocess
import sys

import pytest

from scripts import prepare_rule_study_worker as w


def request(tmp_path):
    return {
        "kind": w.KIND,
        "case_id": "A",
        "policy_id": "rules-v1",
        "plan": {"output_directory": str(tmp_path / "output")},
    }


def ready_fixture(monkeypatch):
    # Approval is not being mocked: this is byte/shape readiness, explicitly not approval.
    monkeypatch.setattr(
        w.preflight,
        "assess",
        lambda plan: {"status": "HASH_PREFLIGHT_READY_NOT_AUTHORIZATION", "problems": []},
    )


def test_closed_stdin_does_not_read_request_or_import_project_code(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", w.BOOTSTRAP, str(tmp_path), str(tmp_path / "absent.json"), "unused"],
        input=b"",
        capture_output=True,
    )
    assert result.returncode == 90
    assert not result.stderr and not list(tmp_path.iterdir())


def test_changed_request_stops_before_project_import(tmp_path):
    path = tmp_path / "request.json"
    path.write_bytes(b"changed")
    result = subprocess.run(
        [sys.executable, "-c", w.BOOTSTRAP, str(tmp_path), str(path), "0" * 64],
        input=b"G",
        capture_output=True,
    )
    assert result.returncode == 91
    assert not result.stderr


def test_changed_code_pins_stop_before_project_import(tmp_path):
    for folder in ("requirements", "docs/rule_study", "scripts", "dc_sustainability"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    (tmp_path / "requirements/requirements-windows-py312.lock.txt").write_bytes(b"fixture")
    (tmp_path / "docs/rule_study/specification.json").write_bytes(b"{}")
    (tmp_path / "scripts/prepare_rule_study_worker.py").write_text(
        "raise RuntimeError('must not import this fixture')", encoding="utf-8"
    )
    raw = json.dumps({"plan": {"code_sha256": {}}}).encode()
    path = tmp_path / "request.json"
    path.write_bytes(raw)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            w.BOOTSTRAP,
            str(tmp_path),
            str(path),
            w.hashlib.sha256(raw).hexdigest(),
        ],
        input=b"G",
        capture_output=True,
    )
    assert result.returncode == 93
    assert not result.stderr


def test_missing_preflight_never_prepares_a_command(tmp_path, monkeypatch):
    monkeypatch.setattr(
        w.preflight,
        "assess",
        lambda plan: {"status": "BLOCKED", "problems": ["verifier freeze absent"]},
    )
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request(tmp_path)))
    with pytest.raises(ValueError, match="preflight blocked"):
        w.contained_command(path)
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("extra", ["approved", "authorization", "command", "module"])
def test_json_cannot_add_an_approval_or_arbitrary_command(tmp_path, extra):
    data = request(tmp_path)
    data[extra] = True
    with pytest.raises(ValueError, match="exact prepared-worker fields"):
        w.validate_request(data)


def test_inspection_never_releases_or_consumes_authorization(tmp_path, monkeypatch):
    ready_fixture(monkeypatch)
    data = request(tmp_path)
    path = tmp_path / "request.json"
    path.write_text(json.dumps(data))
    report = w.describe(data, path)
    assert report["status"] == "WORKER_PREPARED_NOT_AUTHORIZED"
    assert report["release_allowed"] is False
    assert report["real_authorization_consumed"] is False
    command = w.contained_command(path)
    assert command[:5] == [sys.executable, "-X", "utf8", "-c", w.BOOTSTRAP]
    assert not (tmp_path / "output").exists()


def test_actual_case_runner_is_wired_on_a_unit_fixture_only(tmp_path, monkeypatch):
    from dc_sustainability.rule_study import runner
    from tests.rule_study.helpers import TEST_ONLY_COMMIT

    ready_fixture(monkeypatch)
    original = runner.make_bindings
    monkeypatch.setattr(
        runner,
        "make_bindings",
        lambda case, root: original(case, root, code_commit=TEST_ONLY_COMMIT),
    )
    assert w.execute_prepared(request(tmp_path)) == 0
    result = json.loads((tmp_path / "output/worker-result.json").read_text())
    assert result["decisions_recorded"] == 30 and result["model_calls"] == 0
    assert result["scope"] == "authored_case_execution_not_independent_verification"
    with pytest.raises(FileExistsError):
        w.execute_prepared(request(tmp_path))


def test_backend_failure_is_retained_without_retry(tmp_path, monkeypatch):
    from dc_sustainability.rule_study import runner

    ready_fixture(monkeypatch)
    monkeypatch.setattr(runner, "make_bindings", lambda *args: object())

    def fail(*args, **kwargs):
        raise RuntimeError("unit fixture failure")

    monkeypatch.setattr(runner, "run_case", fail)
    with pytest.raises(RuntimeError, match="unit fixture failure"):
        w.execute_prepared(request(tmp_path))
    evidence = json.loads((tmp_path / "output/worker-failure.json").read_text())
    assert evidence["retry_allowed"] is False


def test_fault_case_cannot_be_mislabelled_as_a_baseline(tmp_path):
    data = request(tmp_path)
    data.update(case_id="B-fault", policy_id="greedy_a")
    with pytest.raises(ValueError, match="rules-v1 fixture"):
        w.validate_request(data)


def dispatch_fixture(tmp_path, monkeypatch):
    ready_fixture(monkeypatch)
    data = request(tmp_path)
    data["plan"].update(
        proposed_authorization_id="unit-fixture-never-human-approval",
        code_commit="test-only-not-a-frozen-commit",
        proposed_limit_seconds=1,
    )
    path = tmp_path / "request.json"
    path.write_text(json.dumps(data))
    monkeypatch.setattr(w, "environment_evidence", lambda: {"scope": "unit_fixture_only"})
    return path, tmp_path / "ledger"


def fixture_authority(subject):
    # Only used with mocked supervision and temporary files; never a human receipt.
    return dict(subject, actor="MattyAnd", decision="approved")


def test_no_authority_does_not_consume_id_or_touch_outputs(tmp_path):
    with pytest.raises(PermissionError, match="fresh trusted"):
        w.dispatch_once(tmp_path / "absent", ledger=tmp_path / "ledger")
    assert not list(tmp_path.iterdir())


def test_wrong_authority_envelope_does_not_reserve_id(tmp_path, monkeypatch):
    path, ledger = dispatch_fixture(tmp_path, monkeypatch)
    with pytest.raises(PermissionError, match="exact worker envelope"):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=lambda subject: True)
    assert not ledger.exists() and not (tmp_path / "output").exists()


def test_authority_drift_is_stopped_after_reservation_without_launch(tmp_path, monkeypatch):
    path, ledger = dispatch_fixture(tmp_path, monkeypatch)

    def changed(subject):
        path.write_text("changed request")
        return fixture_authority(subject)

    with pytest.raises(ValueError, match="changed after"):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=changed)
    files = list(ledger.glob("*.result.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text())["retry_allowed"] is False
    assert not (tmp_path / "output").exists()


def test_same_fixture_id_cannot_dispatch_twice(tmp_path, monkeypatch):
    from dc_sustainability.runtime import bounded_worker

    path, ledger = dispatch_fixture(tmp_path, monkeypatch)
    launches = []

    def fail(command, seconds, **kwargs):
        launches.append(command)
        return {"status": "timed_out", "cleanup_verified": True}

    monkeypatch.setattr(bounded_worker, "supervise", fail)
    first = w.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)
    assert first["status"] == "failed" and first["retry_allowed"] is False
    with pytest.raises(FileExistsError):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)
    assert len(launches) == 1 and not (tmp_path / "output").exists()


def test_zero_exit_without_worker_result_is_not_success(tmp_path, monkeypatch):
    from dc_sustainability.runtime import bounded_worker

    path, ledger = dispatch_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        bounded_worker,
        "supervise",
        lambda *a, **k: {"status": "succeeded", "cleanup_verified": True},
    )
    result = w.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)
    assert result["status"] == "failed_missing_worker_result"
