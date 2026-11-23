"""Contained receiving wiring tests. No real receiving study or human approval."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import prepare_rule_study_receiving as w


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(w.preflight, "snapshot", lambda: ("fixture", {"source": "fixture"}))
    monkeypatch.setattr(w, "receiving_plan", lambda: {"status": "NOT_RUN", "fixture": True})
    monkeypatch.setattr(w.worker, "environment_evidence", lambda: {"fixture": True})
    data = w.draft()
    data.update(
        output_directory=str(tmp_path / "output"),
        proposed_authorization_id="unit-only-not-human-approval",
    )
    path = tmp_path / "request.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return data, path, tmp_path / "ledger"


def authority(subject):
    # Fixture authority only; every test mocks actual research supervision.
    return dict(subject, actor="MattyAnd", decision="approved")


def test_bootstrap_closed_stdin_does_not_import_or_read(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", w.BOOTSTRAP, str(tmp_path), str(tmp_path / "absent"), "0" * 64],
        input=b"",
        capture_output=True,
    )
    assert result.returncode == 90 and not result.stderr
    assert not list(tmp_path.iterdir())


def test_bootstrap_changed_bytes_stop_before_import(tmp_path):
    p = tmp_path / "request.json"
    p.write_text("changed")
    result = subprocess.run(
        [sys.executable, "-c", w.BOOTSTRAP, str(tmp_path), str(p), "0" * 64],
        input=b"G",
        capture_output=True,
    )
    assert result.returncode == 91 and not result.stderr


@pytest.mark.parametrize("extra", ["approved", "module", "command", "authorization"])
def test_untrusted_fields_never_grant_execution(prepared, extra):
    data, _, _ = prepared
    data[extra] = True
    with pytest.raises(ValueError, match="exact receiving fields"):
        w.assess(data)


@pytest.mark.parametrize(
    "key,value", [("states", True), ("states", 10001), ("wall_seconds", 601), ("runs", 203)]
)
def test_no_request_can_expand_combined_limits(prepared, key, value):
    data, _, _ = prepared
    data["limits"][key] = value
    with pytest.raises(ValueError, match="fixed combined"):
        w.assess(data)


def test_source_and_domain_drift_block(prepared):
    data, _, _ = prepared
    data["code_sha256"] = {}
    data["receiving_plan"] = {"extended": "not authorized"}
    report = w.assess(data)
    assert report["status"] == "BLOCKED" and len(report["problems"]) == 2


def test_no_authority_never_touches_request_or_ledger(tmp_path):
    with pytest.raises(PermissionError):
        w.dispatch_once(tmp_path / "absent", ledger=tmp_path / "ledger")
    assert not list(tmp_path.iterdir())


def test_wrong_exact_approval_does_not_consume_id(prepared):
    _, path, ledger = prepared
    with pytest.raises(PermissionError):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=lambda subject: True)
    assert not ledger.exists()


def test_changed_request_after_approval_retains_used_id(prepared):
    _, path, ledger = prepared

    def changed(subject):
        path.write_text("changed")
        return authority(subject)

    with pytest.raises(ValueError):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=changed)
    report = json.loads(next(ledger.glob("*.result.json")).read_text())
    assert report["retry_allowed"] is False and report["status"] == "stopped_after_reservation"


def test_timeout_does_not_retry_and_id_is_single_use(prepared, monkeypatch):
    from dc_sustainability.runtime import bounded_worker

    _, path, ledger = prepared
    calls = []

    def timeout(command, seconds, **kwargs):
        calls.append(seconds)
        return {"status": "timed_out", "cleanup_verified": True}

    monkeypatch.setattr(bounded_worker, "supervise", timeout)
    assert w.dispatch_once(path, ledger=ledger, trusted_authorize=authority)["status"] == "failed"
    with pytest.raises(FileExistsError):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=authority)
    assert calls == [600]


@pytest.mark.parametrize("overall", [None, "FAIL", "INCOMPLETE", "PASS"])
def test_exit_zero_needs_retained_pass_report(prepared, monkeypatch, overall):
    from dc_sustainability.runtime import bounded_worker

    data, path, ledger = prepared

    def success(*args, **kwargs):
        if overall:
            out = Path(data["output_directory"])
            out.mkdir()
            (out / "receiving-report.json").write_text(json.dumps({"overall": overall}))
        return {"status": "succeeded", "cleanup_verified": True}

    monkeypatch.setattr(bounded_worker, "supervise", success)
    r = w.dispatch_once(path, ledger=ledger, trusted_authorize=authority)
    assert (r["status"] == "completed") is (overall == "PASS")


def test_receiving_backend_uses_one_budget_and_retains_incomplete(prepared, monkeypatch):
    from dc_sustainability.evaluation import rule_study_receiving as rv

    data, _, _ = prepared

    def incomplete(domains, policies, out, root, spec, *, budget):
        assert domains == ["primary", "authored"]
        assert policies == ["rules-v1", "greedy_a", "greedy_b"]
        assert (budget.max_states, budget.max_transitions, budget.max_seconds) == (
            10000,
            50000,
            600,
        )
        out.mkdir()
        return {"overall": "INCOMPLETE", "fixture": True}

    monkeypatch.setattr(rv, "run_receiving", incomplete)
    assert w.execute_prepared(data) == 7
    assert (
        json.loads((Path(data["output_directory"]) / "receiving-report.json").read_text())[
            "overall"
        ]
        == "INCOMPLETE"
    )


def test_failure_evidence_survives_backend_exception(prepared, monkeypatch):
    from dc_sustainability.evaluation import rule_study_receiving as rv

    data, _, _ = prepared

    def fail(*args, **kwargs):
        Path(data["output_directory"]).mkdir()
        raise RuntimeError("fixture failure")

    monkeypatch.setattr(rv, "run_receiving", fail)
    with pytest.raises(RuntimeError):
        w.execute_prepared(data)
    evidence = Path(data["output_directory"]) / "receiving-failure.json"
    assert json.loads(evidence.read_text())["retry_allowed"] is False


def test_inspection_is_only_a_report_and_output_reuse_is_refused(prepared, tmp_path):
    data, path, ledger = prepared
    report_path = tmp_path / "inspection.json"
    assert w.main(["--inspect", str(path), "--out", str(report_path)]) == 0
    assert json.loads(report_path.read_text())["release_allowed"] is False
    assert not ledger.exists() and not Path(data["output_directory"]).exists()
    with pytest.raises(SystemExit):
        w.main(["--inspect", str(path), "--out", str(report_path)])
    Path(data["output_directory"]).mkdir()
    assert w.assess(data)["status"] == "BLOCKED"


def test_cleanup_failure_cannot_complete_receiving(prepared, monkeypatch):
    from dc_sustainability.runtime import bounded_worker

    data, path, ledger = prepared
    out = Path(data["output_directory"])

    def failed_cleanup(*args, **kwargs):
        out.mkdir()
        (out / "receiving-report.json").write_text(json.dumps({"overall": "PASS"}))
        return {"status": "succeeded", "cleanup_verified": False}

    monkeypatch.setattr(bounded_worker, "supervise", failed_cleanup)
    assert w.dispatch_once(path, ledger=ledger, trusted_authorize=authority)["status"] == "failed"


def test_receiving_bootstrap_rejects_code_drift_before_import(tmp_path):
    for folder in ("requirements", "docs/rule_study", "scripts", "dc_sustainability"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    (tmp_path / "requirements/requirements-windows-py312.lock.txt").write_text("fixture")
    (tmp_path / "docs/rule_study/specification.json").write_text("{}")
    (tmp_path / "scripts/prepare_rule_study_receiving.py").write_text(
        "raise RuntimeError('must not import')"
    )
    raw = json.dumps({"code_sha256": {}}).encode()
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
    assert result.returncode == 93 and not result.stderr
