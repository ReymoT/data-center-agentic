"""Synthetic-only export mechanics; never touch real development/private inputs."""

import hashlib
import json
import os
import sys
from time import monotonic
from unittest.mock import patch

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data import state_export as ex
from dc_sustainability.runtime.bounded_worker import supervise
from scripts import export_development_states as cli
from tests.runtime.test_controller import setup


def fixture_entries(tmp_path):
    ep, _, _, _ = setup(tmp_path / "setup")
    entries = ex.capture_episode(ep, {}, tmp_path / "capture", "a" * 64, deadline=monotonic() + 20)
    return ep, entries


def test_capture_uses_real_controller_refusal_and_all_30_positions(tmp_path):
    ep, entries = fixture_entries(tmp_path)
    assert [e["state"]["current_slot"] for e in entries] == list(range(30))
    assert len(entries) == 30
    records = [
        s.DecisionRecord.from_json(p.read_text()) for p in (tmp_path / "capture").glob("*.json")
    ]
    assert len(records) == 30 and all(
        not r.executed_starts and r.final_status == "blocked" and not r.model_call_count
        for r in records
    )
    assert len([e for e in entries if e["state"]["current_slot"] >= 24]) == 6
    assert all(not e["state"]["running_jobs"] for e in entries)


def test_recovery_is_hash_bound_and_missing_states_remain_missing(tmp_path):
    ep, entries = fixture_entries(tmp_path)
    allowed = {ep.episode_id: {"constraint_snapshot_sha256": ep.snapshot.canonical_hash()}}
    sample = entries[:3]
    pins = {f"{ep.episode_id}@{x['state']['current_slot']}": s.sha256_hex(x) for x in sample}
    assert ex.validate_entries(sample, allowed, pins, deadline=monotonic() + 10) == sample
    with pytest.raises(ValueError, match="duplicate"):
        ex.validate_entries(sample + sample[:1], allowed, pins, deadline=monotonic() + 10)
    with pytest.raises(ValueError, match="provenance"):
        ex.validate_entries(entries[:2], allowed, pins, deadline=monotonic() + 10)
    pins[f"{ep.episode_id}@0"] = "0" * 64
    with pytest.raises(ValueError, match="provenance"):
        ex.validate_entries(sample, allowed, pins, deadline=monotonic() + 10)


def test_deadline_and_output_caps_preserve_existing_files(tmp_path):
    with pytest.raises(TimeoutError):
        ex.deadline_check(monotonic() - 1)
    p = tmp_path / "new.json"
    with pytest.raises(ValueError, match="cap"):
        ex.write_artifact(p, {"x": "a" * 100}, maximum=8)
    assert not p.exists()
    ex.write_artifact(p, {"x": 1})
    before = p.read_bytes()
    with pytest.raises(FileExistsError):
        ex.write_artifact(p, {"x": 2})
    assert p.read_bytes() == before


def test_pending_approval_cannot_open_private_inputs(tmp_path):
    with patch("pathlib.Path.open", side_effect=AssertionError("no private input open")):
        with pytest.raises(ValueError, match="fresh explicit"):
            cli.preflight(b'{"status":"pending"}', tmp_path / "out")


def recovery_setup(tmp_path, monkeypatch):
    ep, entries = fixture_entries(tmp_path)
    source = tmp_path / "original.json"
    source.write_bytes(ex.payload(entries[:3]))
    bindings = {ep.episode_id: {"constraint_snapshot_sha256": ep.snapshot.canonical_hash()}}
    rows = [
        {"episode_id": ep.episode_id, "window": {"proposed_start_utc": "2022-01-15T07:00:00+00:00"}}
    ]
    monkeypatch.setattr(cli.export, "public_cohort", lambda root: (rows, bindings))
    monkeypatch.setattr(cli, "clean_revision", lambda: "a" * 40)
    a = {
        "status": "approved",
        "approved_by": "MattyAnd",
        "scope": "cf60-development-state-export",
        "route": "recover",
        "source_sha256": cli.SHA256,
        "code_revision": "a" * 40,
        "code_sha256": cli.code_pins(),
        "maximum_input_bytes": ex.MAX_INPUT,
        "maximum_output_bytes": ex.MAX_OUTPUT,
        "time_limit_s": 30,
        "output_directory": str(tmp_path / "out"),
        "development_episode_ids": [ep.episode_id],
        "inputs": [
            {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
        ],
        "original_state_hashes": {
            f"{ep.episode_id}@{x['state']['current_slot']}": s.sha256_hex(x) for x in entries[:3]
        },
    }
    for name in (
        "approval_ref",
        "source_use_ref",
        "custody_ref",
        "executor",
        "machine",
        "storage_ref",
        "trajectory_agreement_ref",
        "provenance_ref",
        "authorization_id",
    ):
        a[name] = "SYNTHETIC-ONLY"
    raw = ex.payload(a)
    ledger = tmp_path / ".state-export-consumed-authorizations"
    ledger.mkdir()
    ex.write_artifact(
        ledger / (hashlib.sha256(a["authorization_id"].encode()).hexdigest() + ".json"),
        {"approval_sha256": hashlib.sha256(raw).hexdigest()},
    )
    return a, raw, source


def test_synthetic_recovery_records_coverage_and_refuses_repeat(tmp_path, monkeypatch):
    a, raw, _ = recovery_setup(tmp_path, monkeypatch)
    cli.work(raw, tmp_path / "out")
    result = json.loads((tmp_path / "out/provenance.json").read_text())
    assert result["coverage"] == 3 and result["missing"] == 1197
    assert (
        result["kind"] == "recovered_original"
        and result["receiving_status"] == "pending_independent_receiving"
    )
    assert result["scientific_compatibility"] is False
    with pytest.raises(ValueError, match="new exact private output"):
        cli.work(raw, tmp_path / "out")


def test_empty_recovery_is_refused_before_ledger_or_input_use(tmp_path, monkeypatch):
    a, _, source = recovery_setup(tmp_path, monkeypatch)
    source.write_bytes(b"[]")
    a["inputs"][0]["sha256"] = hashlib.sha256(b"[]").hexdigest()
    a["original_state_hashes"] = {}
    raw = ex.payload(a)
    reservation = (
        tmp_path
        / ".state-export-consumed-authorizations"
        / (hashlib.sha256(a["authorization_id"].encode()).hexdigest() + ".json")
    )
    reservation.write_bytes(ex.payload({"approval_sha256": hashlib.sha256(raw).hexdigest()}))
    with pytest.raises(ValueError, match="commitments required"):
        cli.work(raw, tmp_path / "out")
    assert not (tmp_path / ".state-export-worker-consumed-authorizations").exists()
    assert not (tmp_path / "out").exists()


def test_changed_input_is_preserved_as_failure_without_retry(tmp_path, monkeypatch):
    a, raw, source = recovery_setup(tmp_path, monkeypatch)
    source.write_text("[]")
    with pytest.raises(ValueError, match="checksum"):
        cli.work(raw, tmp_path / "out")
    assert json.loads((tmp_path / "out/failure.json").read_text())["no_retry"] is True
    assert not (tmp_path / "out/states.json").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("time_limit_s", 901),
        ("maximum_input_bytes", True),
        ("source_use_ref", None),
        ("code_sha256", {}),
        ("original_state_hashes", {}),
    ],
)
def test_approved_record_does_not_bypass_scope_gates(tmp_path, monkeypatch, field, value):
    a, _, _ = recovery_setup(tmp_path, monkeypatch)
    a[field] = value
    with pytest.raises(ValueError):
        cli.preflight(ex.payload(a), tmp_path / "out")


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object containment")
def test_real_gated_worker_success_and_process_tree_timeout():
    def command(body):
        return [
            sys.executable,
            "-c",
            "import sys; import time; assert sys.stdin.buffer.read(1)==b'G'; " + body,
        ]

    good = supervise(command("pass"), 5)
    assert good["status"] == "succeeded" and good["cleanup_verified"]
    bad = supervise(
        command(
            "import subprocess; subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)']); time.sleep(20)"
        ),
        0.4,
    )
    assert bad["status"] == "timed_out" and bad["cleanup_verified"]


def test_wall_bound_is_not_silently_unbounded():
    with pytest.raises(ValueError):
        supervise([], 901)


def test_missing_dispatch_prevents_any_state_input_read(tmp_path, monkeypatch):
    a, raw, source = recovery_setup(tmp_path, monkeypatch)
    ledger = tmp_path / ".state-export-consumed-authorizations"
    for path in ledger.iterdir():
        path.unlink()
    with pytest.raises(FileNotFoundError):
        cli.work(raw, tmp_path / "out")
    assert not (tmp_path / "out").exists() and source.exists()


def test_decode_requires_all_forecast_slots_and_rejects_wrong_mapping(tmp_path):
    ep, _ = fixture_entries(tmp_path)
    ep = ep.model_copy(update={"forecast_visibility": "persistence"})
    expected = {
        "episode_canonical_sha256": ep.canonical_hash(),
        "constraint_snapshot_sha256": ep.snapshot.canonical_hash(),
    }
    data = {
        "episode": ep.to_jsonable(),
        "slot0_utc": "2022-01-15T07:00:00+00:00",
        "forecasts_by_slot": {str(i): [] for i in range(30)},
    }
    row = {"window": {"proposed_start_utc": data["slot0_utc"]}}
    decoded, facts = ex.decode_bundle(data, expected, row)
    assert decoded == ep and len(facts) == 30
    data["forecasts_by_slot"].pop("29")
    with pytest.raises(ValueError, match="30 forecast"):
        ex.decode_bundle(data, expected, row)
    data["slot0_utc"] = "2022-01-15T08:00:00+00:00"
    with pytest.raises(ValueError, match="mapping"):
        ex.decode_bundle(data, expected, row)


def test_decode_rejects_future_forecast_issue(tmp_path):
    from datetime import datetime, timezone

    from tests.contracts.fixtures import forecasts

    ep, _ = fixture_entries(tmp_path)
    ep = ep.model_copy(update={"forecast_visibility": "persistence"})
    expected = {
        "episode_canonical_sha256": ep.canonical_hash(),
        "constraint_snapshot_sha256": ep.snapshot.canonical_hash(),
    }
    fact = forecasts()[0].model_copy(
        update={
            "issued_at_utc": datetime(2022, 1, 15, 8, tzinfo=timezone.utc),
            "forecast_kind": "persistence",
            "source_sha256": cli.SHA256,
        }
    )
    data = {
        "episode": ep.to_jsonable(),
        "slot0_utc": "2022-01-15T07:00:00+00:00",
        "forecasts_by_slot": {str(i): [] for i in range(30)},
    }
    data["forecasts_by_slot"]["0"] = [fact.to_jsonable()]
    with pytest.raises(ValueError, match="issued after"):
        ex.decode_bundle(data, expected, {"window": {"proposed_start_utc": data["slot0_utc"]}})


def test_oversize_input_is_refused_and_exact_bound_reads_once(tmp_path):
    path = tmp_path / "small.json"
    path.write_bytes(b"12345")
    with pytest.raises(ValueError, match="bounded file size"):
        cli.read_bounded(path, 4)
    assert cli.read_bounded(path, 5) == b"12345"


def test_published_pending_template_never_grants_a_dispatch(tmp_path):
    from pathlib import Path

    raw = (Path(cli.ROOT) / "docs/evidence/state-export-authorization-pending.json").read_bytes()
    with pytest.raises(ValueError, match="fresh explicit"):
        cli.preflight(raw, tmp_path / "out")
    assert not (tmp_path / "out").exists()
