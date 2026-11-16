"""Synthetic-only bundle assembly. No real source, retained episode or model access."""

import copy
import hashlib
import json
from time import monotonic
from unittest.mock import patch

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data import development_bundles as b
from dc_sustainability.data import materialize_development as m
from dc_sustainability.data import state_export as ex
from scripts import extract_cf60_development as producer
from scripts import prepare_development_bundles as cli
from tests.data.test_cf60_extract import payload as synthetic_csv


@pytest.fixture
def synthetic(monkeypatch):
    # Explicit diagnostic source double; the real loader is never invoked.
    observations = tuple((m.carbon.START + i * m.carbon.HOUR, float(i)) for i in range(8760))
    monkeypatch.setattr(m.carbon, "load_source", lambda _: (observations, {}))
    records = m.allocation()[0]["records"]
    corpus = m.episodes(None)
    expected = {e.episode_id: m.persistence_forecasts(None, e.episode_id) for e in corpus}
    monkeypatch.setattr(m.carbon, "load_source", lambda _: pytest.fail("CSV loader must not run"))
    episodes = {e.episode_id: e.to_jsonable() for e in corpus}
    commitments = {
        e.episode_id: {
            "episode_canonical_sha256": e.canonical_hash(),
            "constraint_snapshot_sha256": e.snapshot.canonical_hash(),
            "file_sha256": hashlib.sha256(ex.payload(e.to_jsonable())).hexdigest(),
        }
        for e in corpus
    }
    extract = {
        "source_sha256": m.carbon.SHA256,
        "rows": [{"index": i, "value": float(i)} for i in b.permitted_indices(records)],
    }
    return records, episodes, commitments, extract, expected


def assemble(data, **kwargs):
    records, episodes, commitments, extract, _ = data
    return b.assemble(
        episodes,
        extract,
        records=records,
        commitments=commitments,
        deadline=monotonic() + 30,
        **kwargs,
    )


def test_full_cohort_matches_existing_legacy_forecasts_and_capture_decoder(synthetic):
    records, _, commitments, _, expected = synthetic
    assert len(b.permitted_indices(records)) == 340
    bundles = assemble(synthetic)
    assert len(bundles) == 40
    for row in records:
        eid = row["episode_id"]
        ep, forecasts = ex.decode_bundle(bundles[eid], commitments[eid], row)
        assert ep.episode_id == eid
        assert forecasts == expected[eid]
        assert set(bundles[eid]["forecasts_by_slot"]) == {str(i) for i in range(30)}
        # Distinct row-index values prove prior-row use at every issue, not a constant stub.
        for slot, facts in forecasts.items():
            assert all(
                f.value == row["window"]["proposed_physical_indices"][slot] - 1 for f in facts
            )


@pytest.mark.parametrize(
    "fault",
    [
        "missing_row",
        "extra_row",
        "duplicate_row",
        "boolean_value",
        "nonfinite",
        "wrong_source",
        "changed_episode",
        "missing_episode",
        "wrong_anchor",
    ],
)
def test_malformed_or_incomplete_inputs_fail_closed(synthetic, fault):
    data = copy.deepcopy(synthetic)
    records, episodes, _, extract, _ = data
    if fault == "missing_row":
        extract["rows"].pop()
    elif fault == "extra_row":
        extract["rows"].append({"index": 8759, "value": 0})
    elif fault == "duplicate_row":
        extract["rows"][1] = extract["rows"][0]
    elif fault == "boolean_value":
        extract["rows"][0]["value"] = True
    elif fault == "nonfinite":
        extract["rows"][0]["value"] = float("nan")
    elif fault == "wrong_source":
        extract["source_sha256"] = "0" * 64
    elif fault == "changed_episode":
        episodes[records[0]["episode_id"]]["seed"] += 1
    elif fault == "missing_episode":
        episodes.pop(records[0]["episode_id"])
    elif fault == "wrong_anchor":
        records[0]["window"]["proposed_start_utc"] = "2022-01-01T00:00:00+00:00"
    with pytest.raises(ValueError):
        assemble(data)


def test_deadline_refused(synthetic):
    records, episodes, commitments, extract, _ = synthetic
    with pytest.raises(TimeoutError):
        b.assemble(
            episodes, extract, records=records, commitments=commitments, deadline=monotonic() - 1
        )


def test_pending_record_never_opens_any_input(tmp_path):
    with patch("pathlib.Path.open", side_effect=AssertionError("no input access")):
        with pytest.raises(ValueError, match="fresh explicit"):
            cli.preflight(b'{"status":"pending"}', tmp_path / "out")


def test_published_pending_template_refuses_before_input_access(tmp_path):
    raw = (cli.ROOT / "docs/evidence/development-bundle-authorization-pending.json").read_bytes()
    with patch("pathlib.Path.open", side_effect=AssertionError("no input access")):
        with pytest.raises(ValueError, match="fresh explicit"):
            cli.preflight(raw, tmp_path / "out")


def approval_fixture(data, tmp_path, monkeypatch, *, extract_path=None):
    records, episodes, commitments, extract, _ = data
    monkeypatch.setattr(cli.export, "public_cohort", lambda _: (records, commitments))
    monkeypatch.setattr(cli, "clean_revision", lambda: "a" * 40)
    items = []
    for eid, ep in episodes.items():
        path = tmp_path / (eid + ".json")
        path.write_bytes(ex.payload(ep))
        items.append(
            {"episode_id": eid, "path": str(path), "sha256": commitments[eid]["file_sha256"]}
        )
    source = tmp_path / "synthetic-extract.json" if extract_path is None else extract_path
    if extract_path is None:
        source.write_bytes(ex.payload(extract))
    a = {
        "status": "approved",
        "approved_by": "MattyAnd",
        "scope": cli.SCOPE,
        "source_sha256": m.carbon.SHA256,
        "code_revision": "a" * 40,
        "code_sha256": cli.code_pins(),
        "episodes": items,
        "extract_path": str(source),
        "extract_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "permitted_indices": b.permitted_indices(records),
        "output_directory": str(tmp_path / "out"),
        "maximum_input_bytes": ex.MAX_INPUT,
        "maximum_output_bytes": ex.MAX_OUTPUT,
        "time_limit_s": 30,
    }
    for name in (
        "approval_ref",
        "authorization_id",
        "source_use_ref",
        "full_episode_access_ref",
        "extract_provenance_ref",
        "custody_ref",
        "executor",
        "machine",
        "storage_ref",
    ):
        a[name] = "SYNTHETIC-ONLY-NOT-REAL-APPROVAL"
    raw = ex.payload(a)
    ledger = tmp_path / ".bundle-consumed"
    ledger.mkdir()
    ex.write_artifact(
        ledger / (hashlib.sha256(a["authorization_id"].encode()).hexdigest() + ".json"),
        {"approval_sha256": hashlib.sha256(raw).hexdigest()},
    )
    return a, raw, source


def test_synthetic_worker_full40_hash_bound_outputs_and_no_repeat(synthetic, tmp_path, monkeypatch):
    a, raw, _ = approval_fixture(synthetic, tmp_path, monkeypatch)
    cli.work(raw, tmp_path / "out")
    p = json.loads((tmp_path / "out/provenance.json").read_text())
    assert len(p["bundles"]) == 40 and p["receiving_status"] == "pending_independent_receiving"
    assert (
        p["source_csv_reads"] == p["simulator_steps"] == p["model_calls"] == p["solver_calls"] == 0
    )
    for name, digest in p["bundles"].items():
        assert hashlib.sha256((tmp_path / "out" / name).read_bytes()).hexdigest() == digest
    assert p["approval_sha256"] == hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match="new exact output"):
        cli.work(raw, tmp_path / "out")


@pytest.mark.parametrize(
    "fault", ["scope", "references", "code", "duplicate", "oversize", "csv", "indices"]
)
def test_authorization_and_named_input_gates(synthetic, tmp_path, monkeypatch, fault):
    a, _, _ = approval_fixture(synthetic, tmp_path, monkeypatch)
    if fault == "scope":
        a["scope"] = "other"
    elif fault == "references":
        a["full_episode_access_ref"] = None
    elif fault == "code":
        a["code_sha256"] = {}
    elif fault == "duplicate":
        a["episodes"][1] = a["episodes"][0]
    elif fault == "oversize":
        a["maximum_input_bytes"] = 1
    elif fault == "csv":
        a["extract_path"] = str(tmp_path / "source.csv")
    elif fault == "indices":
        a["permitted_indices"] = []
    with pytest.raises(ValueError):
        cli.preflight(ex.payload(a), tmp_path / "out")
    assert not (tmp_path / ".bundle-worker-consumed").exists()


def test_changed_input_failure_is_preserved(synthetic, tmp_path, monkeypatch):
    _, raw, source = approval_fixture(synthetic, tmp_path, monkeypatch)
    source.write_text("{}")
    with pytest.raises(ValueError, match="input checksum"):
        cli.work(raw, tmp_path / "out")
    assert json.loads((tmp_path / "out/failure.json").read_text())["no_retry"]
    assert not (tmp_path / "out/provenance.json").exists()


@pytest.mark.parametrize("tamper", [False, True])
def test_launcher_binding_verification_and_single_use(synthetic, tmp_path, monkeypatch, tamper):
    if cli.os.name != "nt":
        pytest.skip("launcher requires Windows; containment primitive tested separately")
    a, raw, _ = approval_fixture(synthetic, tmp_path, monkeypatch)
    # The fixture pre-reserved worker tests; give this independent launch a new ID.
    a["authorization_id"] = "SYNTHETIC-LAUNCH-ONLY"
    raw = ex.payload(a)
    auth = tmp_path / "approval.json"
    auth.write_bytes(raw)

    def supervised_double(command, limit, cwd):
        # Test wrapper wiring only. Real Job Object behavior is tested elsewhere.
        assert 0 < limit <= a["time_limit_s"] and cwd == cli.ROOT
        assert "--worker" in command and command[-1] == hashlib.sha256(raw).hexdigest()
        cli.work(raw, tmp_path / "out")
        if tamper:
            (tmp_path / "out" / (a["episodes"][0]["episode_id"] + ".json")).write_text("{}")
        return {"status": "succeeded", "cleanup_verified": True}

    monkeypatch.setattr(cli, "supervise", supervised_double)
    result = cli.launch(auth, tmp_path / "out")
    assert result["status"] == ("output_unverified" if tamper else "succeeded")
    assert (tmp_path / "out.dispatch/authorization.json").read_bytes() == raw
    with pytest.raises(ValueError, match="new exact output"):
        cli.launch(auth, tmp_path / "out")


def test_worker_requires_dispatch_reservation(synthetic, tmp_path, monkeypatch):
    a, _, _ = approval_fixture(synthetic, tmp_path, monkeypatch)
    a["authorization_id"] = "UNRESERVED-SYNTHETIC-ID"
    with pytest.raises(FileNotFoundError):
        cli.work(ex.payload(a), tmp_path / "out")
    assert not (tmp_path / ".bundle-worker-consumed").exists()


def test_output_cap_preserves_failure_without_bundle_publication(synthetic, tmp_path, monkeypatch):
    a, _, _ = approval_fixture(synthetic, tmp_path, monkeypatch)
    a["maximum_output_bytes"] = 1
    raw = ex.payload(a)
    reservation = (
        tmp_path
        / ".bundle-consumed"
        / (hashlib.sha256(a["authorization_id"].encode()).hexdigest() + ".json")
    )
    reservation.write_bytes(ex.payload({"approval_sha256": hashlib.sha256(raw).hexdigest()}))
    with pytest.raises(ValueError, match="aggregate output cap"):
        cli.work(raw, tmp_path / "out")
    assert json.loads((tmp_path / "out/failure.json").read_text())["no_retry"]
    assert list((tmp_path / "out").glob("EP-*.json")) == []


def test_real_extractor_record_flows_into_bundle_worker(synthetic, tmp_path, monkeypatch):
    # Real producer/consumer functions, synthetic inputs and test-only approvals.
    # This is an in-process offline seam test, not real source/run acceptance.
    records, episodes, commitments, _, expected = copy.deepcopy(synthetic)
    data = synthetic_csv()
    synthetic_sha = hashlib.sha256(data).hexdigest()
    original_sha = m.carbon.SHA256
    for eid, value in episodes.items():
        ep = s.PrivateEpisode.from_jsonable(
            json.loads(json.dumps(value).replace(original_sha, synthetic_sha))
        )
        episodes[eid] = ep.to_jsonable()
        commitments[eid] = {
            "episode_canonical_sha256": ep.canonical_hash(),
            "constraint_snapshot_sha256": ep.snapshot.canonical_hash(),
            "file_sha256": hashlib.sha256(ex.payload(ep.to_jsonable())).hexdigest(),
        }
    for module in (producer, cli, b, ex, m.carbon):
        monkeypatch.setattr(module, "SHA256", synthetic_sha)
    monkeypatch.setattr(producer, "revision", lambda: "a" * 40)
    source = tmp_path / "synthetic-diagnostic.csv"
    source.write_bytes(data)
    output = tmp_path / "producer-extract.json"
    a = {
        "status": "approved",
        "approved_by": "MattyAnd",
        "scope": "cf60-development-row-extract-only",
        "source_sha256": synthetic_sha,
        "code_sha256": producer.code_pins(),
        "code_revision": "a" * 40,
        "source_path": str(source),
        "output_path": str(output),
        "nonce_relation": "before_nonce",
        "physical_read_scope": "whole-file-bytes-all-timestamps-selected-numeric-only",
        "maximum_bytes": producer.MAX_BYTES,
        "required_data_rows": producer.REQUIRED_ROWS,
        "time_limit_s": 30,
        "permitted_indices": b.permitted_indices(records),
    }
    for field in (
        "approval_ref",
        "source_use_ref",
        "custody_disposition_ref",
        "nonce_timing_ref",
        "executor",
        "machine",
        "storage_ref",
        "authorization_id",
    ):
        a[field] = "SYNTHETIC-SEAM-ONLY"
    producer.run(source, tmp_path / "unused-approval.json", output, approval_bytes=ex.payload(a))
    extract = json.loads(output.read_bytes())
    before = output.read_bytes()
    assert set(extract) == {"source_sha256", "rows", "ingestion", "extractor_code_sha256"}
    assert extract["ingestion"]["selected_numeric_values"] == 340
    synthetic_input_dir = tmp_path / "consumer"
    synthetic_input_dir.mkdir()
    fixture = (records, episodes, commitments, extract, expected)
    _, raw, _ = approval_fixture(fixture, synthetic_input_dir, monkeypatch, extract_path=output)
    cli.work(raw, synthetic_input_dir / "out")
    provenance = json.loads((synthetic_input_dir / "out/provenance.json").read_bytes())
    assert len(provenance["bundles"]) == 40
    assert provenance["input_sha256"][0] == hashlib.sha256(before).hexdigest()
    assert output.read_bytes() == before


@pytest.mark.parametrize(
    "fields",
    [{"unexpected": {}}, {"ingestion": {}}, {"ingestion": [], "extractor_code_sha256": {}}],
)
def test_unrecognized_or_incomplete_producer_metadata_is_rejected(synthetic, fields):
    data = copy.deepcopy(synthetic)
    data[3].update(fields)
    with pytest.raises(ValueError, match="extract"):
        assemble(data)
