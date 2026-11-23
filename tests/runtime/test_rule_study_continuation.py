"""Narrow continuation controls; fixtures never authorize a real scientific run."""

import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from scripts import prepare_rule_study_continuation as w


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(w.preflight, "snapshot", lambda: ("fixture", {"source": "fixture"}))
    monkeypatch.setattr(w, "receiving_plan", lambda: {"status": "NOT_RUN", "fixture": True})
    monkeypatch.setattr(w.worker, "environment_evidence", lambda: {"fixture": True})
    data = w.draft()
    data.update(
        output_directory=str(tmp_path / "out"), proposed_authorization_id="unit-only-continuation"
    )
    path = tmp_path / "request.json"
    path.write_text(json.dumps(data))
    return data, path, tmp_path / "ledger"


def authority(subject):
    # Used only with mocked supervision, never a real person decision.
    return dict(subject, actor="MattyAnd", decision="approved")


def test_bootstrap_never_imports_or_reads_without_containment(tmp_path):
    r = subprocess.run(
        [sys.executable, "-c", w.BOOTSTRAP, str(tmp_path), str(tmp_path / "missing"), "0" * 64],
        input=b"",
        capture_output=True,
    )
    assert r.returncode == 90 and not r.stderr and not list(tmp_path.iterdir())


def test_bootstrap_changed_request_is_refused_before_import(tmp_path):
    p = tmp_path / "request.json"
    p.write_bytes(b"changed")
    r = subprocess.run(
        [sys.executable, "-c", w.BOOTSTRAP, str(tmp_path), str(p), "0" * 64],
        input=b"G",
        capture_output=True,
    )
    assert r.returncode == 91 and not r.stderr


@pytest.mark.parametrize("extra", ["approved", "command", "module", "authorization"])
def test_request_cannot_supply_approval_or_code(prepared, extra):
    d, _, _ = prepared
    d[extra] = True
    with pytest.raises(ValueError, match="exact receiving fields"):
        w.assess(d)


@pytest.mark.parametrize(
    "key,value",
    [
        ("states", True),
        ("states", 10001),
        ("wall_seconds", 601),
        ("new_case_policy_runs", 11),
        ("saved_trace_replays", 52),
    ],
)
def test_limits_cannot_expand_or_use_bool_alias(prepared, key, value):
    d, _, _ = prepared
    d["limits"][key] = value
    with pytest.raises(ValueError, match="fixed combined continuation"):
        w.assess(d)


def test_original_consumed_id_is_rejected(prepared):
    d, _, _ = prepared
    d["proposed_authorization_id"] = w.CONSUMED_ID
    assert "original authorization ID is consumed" in w.assess(d)["problems"]


def test_no_authority_never_reads_or_reserves(tmp_path):
    with pytest.raises(PermissionError):
        w.dispatch_once(tmp_path / "missing", ledger=tmp_path / "ledger")
    assert not list(tmp_path.iterdir())


def test_wrong_exact_authority_never_consumes_id(prepared):
    _, path, ledger = prepared
    with pytest.raises(PermissionError):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=lambda subject: True)
    assert not ledger.exists()


def test_timeout_consumes_only_new_id_and_does_not_retry(prepared, monkeypatch):
    from dc_sustainability.runtime import bounded_worker

    _, path, ledger = prepared
    calls = []

    def fail(command, seconds, **kwargs):
        calls.append(seconds)
        return {"status": "timed_out", "cleanup_verified": True}

    monkeypatch.setattr(bounded_worker, "supervise", fail)
    assert w.dispatch_once(path, ledger=ledger, trusted_authorize=authority)["status"] == "failed"
    with pytest.raises(FileExistsError):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=authority)
    assert calls == [600]


def test_drift_after_reservation_prevents_release(prepared):
    _, path, ledger = prepared

    def changed(subject):
        path.write_text("changed")
        return authority(subject)

    with pytest.raises(ValueError):
        w.dispatch_once(path, ledger=ledger, trusted_authorize=changed)
    assert len(list(ledger.glob("*.result.json"))) == 1


def archive_fixture(tmp_path, monkeypatch, members, expected=None):
    archive = tmp_path / "archive.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name, raw, kind in members:
            m = tarfile.TarInfo(name)
            m.size = len(raw)
            m.type = kind
            if kind == tarfile.SYMTYPE:
                m.linkname = "../outside"
            tar.addfile(m, io.BytesIO(raw))
    expected = (
        expected
        if expected is not None
        else {n: w.hashlib.sha256(raw).hexdigest() for n, raw, k in members}
    )
    manifest = "".join(d + "  " + n + "\n" for n, d in expected.items()).encode()
    monkeypatch.setattr(w, "ROOT", tmp_path)
    monkeypatch.setattr(w, "ARCHIVE", "archive.tar.gz")
    monkeypatch.setattr(w, "FILE_COUNT", len(expected))
    monkeypatch.setattr(w, "EXPANDED_BYTES", sum(len(raw) for n, raw, k in members))
    blobs = {"archive.tar.gz": archive.read_bytes(), w.EVIDENCE + "SHA256SUMS.txt": manifest}
    monkeypatch.setattr(w, "EVIDENCE_PATHS", tuple(blobs))
    monkeypatch.setattr(w, "_evidence_bytes", lambda path: blobs[path])
    return {p: w.hashlib.sha256(raw).hexdigest() for p, raw in blobs.items()}


def budget():
    from dc_sustainability.evaluation.rule_study_verifier import Budget

    return Budget()


def test_exact_regular_archive_extracts_to_new_directory(tmp_path, monkeypatch):
    hashes = archive_fixture(tmp_path, monkeypatch, [("traces/case.json", b"{}", tarfile.REGTYPE)])
    w.extract_verified(tmp_path / "new", hashes, budget())
    assert (tmp_path / "new/traces/case.json").read_bytes() == b"{}"
    with pytest.raises(FileExistsError):
        w.extract_verified(tmp_path / "new", hashes, budget())


@pytest.mark.parametrize("name", ["../outside", "/absolute", "C:/outside", "traces\\outside"])
def test_archive_paths_never_escape(tmp_path, monkeypatch, name):
    hashes = archive_fixture(tmp_path, monkeypatch, [(name, b"x", tarfile.REGTYPE)])
    with pytest.raises(ValueError, match="unsafe"):
        w.extract_verified(tmp_path / "new", hashes, budget())
    assert not (tmp_path / "outside").exists()


def test_archive_link_is_refused(tmp_path, monkeypatch):
    hashes = archive_fixture(tmp_path, monkeypatch, [("link", b"", tarfile.SYMTYPE)])
    with pytest.raises(ValueError, match="unsafe"):
        w.extract_verified(tmp_path / "new", hashes, budget())


def test_duplicate_member_is_refused(tmp_path, monkeypatch):
    hashes = archive_fixture(
        tmp_path, monkeypatch, [("case", b"x", tarfile.REGTYPE), ("case", b"x", tarfile.REGTYPE)]
    )
    with pytest.raises(ValueError, match="unsafe"):
        w.extract_verified(tmp_path / "new", hashes, budget())


def test_changed_artifact_is_refused(tmp_path, monkeypatch):
    hashes = archive_fixture(
        tmp_path, monkeypatch, [("case", b"x", tarfile.REGTYPE)], {"case": "0" * 64}
    )
    with pytest.raises(ValueError, match="hash differs"):
        w.extract_verified(tmp_path / "new", hashes, budget())


def test_expansion_limit_is_enforced(tmp_path, monkeypatch):
    hashes = archive_fixture(tmp_path, monkeypatch, [("case", b"xx", tarfile.REGTYPE)])
    monkeypatch.setattr(w, "EXPANDED_BYTES", 1)
    with pytest.raises(ValueError, match="expansion"):
        w.extract_verified(tmp_path / "new", hashes, budget())


def test_expired_budget_stops_extraction_without_policy(tmp_path, monkeypatch):
    hashes = archive_fixture(tmp_path, monkeypatch, [("case", b"x", tarfile.REGTYPE)])
    b = budget()
    b.exhausted = "seconds"
    with pytest.raises(TimeoutError):
        w.extract_verified(tmp_path / "new", hashes, b)


def test_real_source_and_retained_metadata_are_reconstructed_without_execution():
    p = w.receiving_plan()
    assert p["status"] == "NOT_RUN" and len(p["saved_replay_records"]) == 51
    assert p["saved_producer_pin"]["code_commit"] == w.FROZEN_COMMIT
    assert p["authored_plan"]["domains"]["authored"]["runs"] == 10


def backend_fixture(prepared, monkeypatch, status="PASS"):
    from dc_sustainability.evaluation import rule_study_receiving as rv

    d, path, ledger = prepared
    d["receiving_plan"] = {
        "status": "NOT_RUN",
        "evidence_sha256": {},
        "original_state_count": 10000,
        "original_transition_count": 10000,
        "saved_producer_pin": {"code_commit": "original-fixture"},
        "authored_plan": {"pin": {"code_commit": "new-fixture"}},
        "saved_replay_records": [
            {
                "case_id": "fixture",
                "folder": "fixture",
                "result_sha256": w.hashlib.sha256(b"{}").hexdigest(),
            }
        ],
    }
    monkeypatch.setattr(w, "receiving_plan", lambda: d["receiving_plan"])

    def extract(dest, hashes, b):
        (dest / "fixture").mkdir(parents=True)
        (dest / "fixture/result.json").write_bytes(b"{}")

    monkeypatch.setattr(w, "extract_verified", extract)
    observed = []

    def authored(domains, policies, out, root, spec, *, budget):
        observed.append(budget)
        assert domains == ["authored"]
        assert policies == ["rules-v1", "greedy_a", "greedy_b"]
        budget.take_state("authored_fixture")
        return {"overall": status}

    def receive(name, count, folders, errors, pin, spec, *, budget):
        observed.append(budget)
        assert count == 51 and pin["code_commit"] == "original-fixture"
        budget.take_state("saved_fixture")
        return {"overall": "PASS"}

    monkeypatch.setattr(rv, "run_receiving", authored)
    monkeypatch.setattr(rv, "_receive_folders", receive)
    return d, observed


def test_only_authored_executes_and_saved_replay_shares_budget(prepared, monkeypatch):
    d, seen = backend_fixture(prepared, monkeypatch)
    assert w.execute_prepared(d) == 0
    r = json.loads((Path(d["output_directory"]) / "continuation-report.json").read_bytes())
    assert seen[0] is seen[1] and r["new_primary_executions"] == 0
    assert r["original_attempt_overall"] == "INCOMPLETE" and r["cumulative_charged_states"] == 10002
    assert r["saved_producer_pin"]["code_commit"] != "new-fixture"
    assert r["scientific_freeze_accepted"] is False


@pytest.mark.parametrize("status", ["FAIL", "INCOMPLETE"])
def test_authored_failure_stops_later_replay(prepared, monkeypatch, status):
    d, seen = backend_fixture(prepared, monkeypatch, status)
    assert w.execute_prepared(d) == 7 and len(seen) == 1
    r = json.loads((Path(d["output_directory"]) / "continuation-report.json").read_bytes())
    assert r["overall"] == status and "saved_greedy_b" not in r["phases"]


def test_existing_output_race_is_never_modified(prepared, monkeypatch):
    d, seen = backend_fixture(prepared, monkeypatch)
    out = Path(d["output_directory"])
    out.mkdir()
    marker = out / "original"
    marker.write_text("preserve")
    monkeypatch.setattr(w, "assess", lambda request: {"problems": []})
    with pytest.raises(FileExistsError):
        w.execute_prepared(d)
    assert list(out.iterdir()) == [marker] and not seen


def test_archive_evidence_drift_stops_before_destination(tmp_path, monkeypatch):
    hashes = archive_fixture(tmp_path, monkeypatch, [("case", b"x", tarfile.REGTYPE)])
    hashes["archive.tar.gz"] = "0" * 64
    with pytest.raises(ValueError, match="evidence drift"):
        w.extract_verified(tmp_path / "new", hashes, budget())
    assert not (tmp_path / "new").exists()


def test_scientific_source_change_blocks_plan(monkeypatch):
    from dc_sustainability.evaluation import rule_study_receiving as rv

    original = rv.reconstruct_pin

    def changed(root):
        p = original(root)
        p["adapter_source_sha256"] = "0" * 64
        return p

    monkeypatch.setattr(rv, "reconstruct_pin", changed)
    with pytest.raises(ValueError, match="scientific source differs"):
        w.receiving_plan()


def test_changed_original_report_blocks_plan(monkeypatch):
    original = w._evidence_bytes
    monkeypatch.setattr(
        w,
        "_evidence_bytes",
        lambda p: b"{}" if p == w.EVIDENCE + "receiving-report.json" else original(p),
    )
    with pytest.raises(ValueError, match="original report changed"):
        w.receiving_plan()


def test_bootstrap_evidence_drift_stops_before_project_import(tmp_path):
    for d in ("scripts", "dc_sustainability", "requirements", "docs/rule_study"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    code = tmp_path / "scripts/prepare_rule_study_continuation.py"
    code.write_text("raise RuntimeError('must not import')")
    lock = tmp_path / "requirements/requirements-windows-py312.lock.txt"
    lock.write_text("fixture")
    spec = tmp_path / "docs/rule_study/specification.json"
    spec.write_text("{}")
    pins = {
        p.relative_to(tmp_path).as_posix(): w.hashlib.sha256(
            p.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for p in (code, lock, spec)
    }
    evidence = {}
    for relative in w.EVIDENCE_PATHS:
        p = tmp_path / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"fixture")
        evidence[relative] = w.hashlib.sha256(b"fixture").hexdigest()
    evidence[w.EVIDENCE + "receiving-report.json"] = "0" * 64
    raw = json.dumps(
        {"code_sha256": pins, "receiving_plan": {"evidence_sha256": evidence}}
    ).encode()
    request = tmp_path / "request.json"
    request.write_bytes(raw)
    r = subprocess.run(
        [
            sys.executable,
            "-c",
            w.BOOTSTRAP,
            str(tmp_path),
            str(request),
            w.hashlib.sha256(raw).hexdigest(),
        ],
        input=b"G",
        capture_output=True,
    )
    assert r.returncode == 94 and not r.stderr
