"""Offline D04 materialization fault tests; synthetic loader double, never real carbon.

Real pinned-input and consumer verification is scripts/check_d04_materialization.py.
No source bytes are embedded or acquired by ordinary CI.
"""

import json
import os
import shutil
from datetime import timedelta

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data import materialize_development as m
from dc_sustainability.data import scenarios
from dc_sustainability.reference import labels
from dc_sustainability.simulator import SchedulingSimulator
from dc_sustainability.training.collect import collect_decisions


@pytest.fixture
def fake_source(monkeypatch, tmp_path):
    # Explicit diagnostic double to exercise serialization/IO without redistributing CSV.
    observations = tuple((m.carbon.START + i * m.carbon.HOUR, 100.0) for i in range(8760))
    monkeypatch.setattr(m.carbon, "load_source", lambda _: (observations, {}))
    return tmp_path / "diagnostic-double-not-a-source.csv"


def test_exact_allocation_round_trips_and_metadata(fake_source):
    manifest, folds = m.allocation()
    corpus = m.episodes(fake_source)
    assert len(corpus) == len({e.episode_id for e in corpus}) == 40
    assert {e.episode_id for e in corpus} == set(folds)
    assert [list(folds.values()).count(i) for i in range(3)] == [16, 12, 12]
    records = {r["episode_id"]: r for r in manifest["records"]}
    for e in corpus:
        r = records[e.episode_id]
        assert s.PrivateEpisode.from_jsonable(e.to_jsonable()) == e
        assert (e.scenario_id, e.seed, e.split) == (r["scenario"], r["seed"], "development")
        assert e.jobs == scenarios.generate_jobs(r["scenario"], seed=r["seed"], split="development")
        assert (e.n_decision_slots, e.n_completion_slots) == (24, 6)
        assert [o.valid_slot for o in e.realized_carbon] == list(range(30))
        assert all(o.source_sha256 == m.carbon.SHA256 for o in e.realized_carbon)
        assert all(o.valid_from_utc is o.valid_to_utc is None for o in e.realized_carbon)
        assert all(o.semantics == m.SEMANTICS for o in e.realized_carbon)
        assert not any(c.applies_to_jobs for c in e.snapshot.constraints)
        assert e.snapshot.capacity_kw == 100
        assert e.snapshot.site.background_kw == 40
        assert e.snapshot.site.pue == 1.2
        if e.scenario_id == "infeasible":
            assert sum(j.intentionally_infeasible for j in e.jobs) == 1
            assert any(j.job.slack_slots < 0 for j in e.jobs)


def test_exclusive_deterministic_content_receipts_and_verifier(fake_source, tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    a = m.materialize(fake_source, first, revision="test-revision")
    b = m.materialize(fake_source, second, revision="test-revision")
    assert a == b
    assert len(a["entries"]) == 40
    public = m.public_receipt(a, custody_id="authorized-local-test")
    assert public["private_receipt_sha256"] == m.sha(m.serialize(a))
    assert "source_timestamps" not in json.dumps(public)
    assert "realized_carbon" not in json.dumps(public)
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()
        assert b"\r" not in path.read_bytes()
        # Windows chmod exposes read/write bits, not a POSIX ACL. Authorized
        # custody on Windows additionally requires the parent directory ACL.
        expected_mode = 0o666 if os.name == "nt" else 0o600
        assert path.stat().st_mode & 0o777 == expected_mode
    assert len(m.verify(fake_source, first, revision="test-revision")) == 40
    with pytest.raises(FileExistsError):
        m.materialize(fake_source, first, revision="test-revision")
    for e in a["entries"]:
        payload = (first / e["content_path"]).read_bytes()
        assert m.sha(payload) == e["file_sha256"]
        assert (
            s.PrivateEpisode.from_json(payload.decode()).canonical_hash()
            == e["episode_canonical_sha256"]
        )
        assert e["allocation_sha256"] == e["allocation"]["allocation_sha256"]


@pytest.mark.parametrize("damage", ["corrupt", "missing", "extra", "receipt", "symlink"])
def test_corrupted_partial_or_unexpected_corpus_rejected(fake_source, tmp_path, damage):
    out = tmp_path / "corpus"
    m.materialize(fake_source, out, revision="test-revision")
    target = next(p for p in out.iterdir() if p.name.startswith("EP-"))
    if damage == "corrupt":
        target.write_bytes(b"{}\n")
    elif damage == "missing":
        target.unlink()
    elif damage == "extra":
        (out / "EP-unexpected.json").write_bytes(b"{}")
    elif damage == "receipt":
        (out / "content-receipt.json").write_bytes(b"{}")
    else:
        saved = tmp_path / "saved"
        target.rename(saved)
        target.symlink_to(saved)
    with pytest.raises(ValueError):
        m.verify(fake_source, out, revision="test-revision")


@pytest.mark.parametrize("damage", ["seed", "id", "fold", "index"])
def test_allocation_mutations_rejected(tmp_path, damage):
    copy = tmp_path / "allocation"
    shutil.copytree(m.ALLOCATION, copy)
    path = copy / "manifest.json"
    manifest = json.loads(path.read_bytes())
    if damage == "seed":
        manifest["records"][0]["seed"] += 1
    elif damage == "id":
        manifest["records"][0]["episode_id"] = "EP-unexpected"
    elif damage == "fold":
        manifest["records"][0]["fold"] = 2
    else:
        manifest["records"][0]["window"]["proposed_physical_indices"].pop()
    path.write_bytes(m.serialize(manifest))
    with pytest.raises(ValueError, match="pinned allocation changed"):
        m.allocation(copy)


@pytest.mark.parametrize("payload", [b"", b"timestamp,avg_CI\n", b"not pinned source bytes"])
def test_missing_or_changed_source_fails_before_output(tmp_path, payload):
    source = tmp_path / "bad.csv"
    source.write_bytes(payload)
    destination = tmp_path / "absent"
    with pytest.raises(ValueError, match="checksum"):
        m.materialize(source, destination, revision="test-revision")
    assert not destination.exists()


def test_missing_source_fails_before_output(tmp_path):
    with pytest.raises(FileNotFoundError):
        m.materialize(tmp_path / "missing.csv", tmp_path / "absent", revision="test-revision")
    assert not (tmp_path / "absent").exists()


def empty_approve(state, context):
    return s.ApprovedActions(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        plan_hash="a" * 64,
        check_id="CHK-D04-BOUNDARY",
        starts=(),
    )


def test_simulator_collection_and_missing_forecast_boundary(fake_source):
    for e in m.episodes(fake_source):
        simulator = SchedulingSimulator(allow_completion_starts=False)
        simulator.reset(e)
        for _ in range(30):
            state = simulator.state()
            s.assert_no_private_keys(state.to_jsonable())
            assert all(j.arrival_slot <= state.current_slot for j in state.waiting_jobs)
            assert not state.carbon_facts
            simulator.step(empty_approve(state, None))
        assert simulator.state().current_slot == 30
    e = m.episodes(fake_source)[0]
    start = e.realized_carbon[0].observed_at_utc
    decisions = collect_decisions(
        e,
        decision_time_utc=lambda slot: start + timedelta(hours=slot),
        approve=empty_approve,
    )
    assert len(decisions) == 30
    assert all(not d.rows for d in decisions)  # unavailable evidence, not training readiness
    result = labels.label_episode(decisions[:1], time_limit_s=0.1)
    assert len(result) == 1 and not result[0].training_rows()


def test_valid_callback_forecast_interface_and_unknown_labels(fake_source, monkeypatch):
    # TEST-ONLY forecasts demonstrate interface compatibility. This invented test
    # schedule is deliberately not exported as the D01 development forecast protocol.
    e = m.episodes(fake_source)[0]
    start = e.realized_carbon[0].observed_at_utc
    forecasts = {
        t: tuple(
            s.CarbonForecast(
                fact_id=f"FACT-TEST-{t}-{slot}",
                value=100,
                unit="g/kWh",
                source_id="SRC-D01",
                valid_slot=slot,
                issued_at_utc=start + timedelta(hours=t),
                forecast_kind="perfect_foresight",
                semantics=m.SEMANTICS,
                quality_status="unvalidated",
            )
            for slot in range(t, min(t + 24, 30))
        )
        for t in range(30)
    }
    decisions = collect_decisions(
        e,
        decision_time_utc=lambda t: start + timedelta(hours=t),
        approve=empty_approve,
        forecasts_by_slot=forecasts,
    )
    decision = next(d for d in decisions if d.rows)
    # Real solver called on a bounded collected development workload.
    actual = labels.label_episode((decision,), time_limit_s=0.1)
    assert len(actual[0].labels) == len(decision.rows)
    if actual[0].solver_result.status != "certified_optimal":
        assert all(label.label is None for label in actual[0].labels)
    result = actual[0].solver_result.model_copy(update={"status": "unresolved"})
    monkeypatch.setattr(labels, "solve_visible", lambda *args, **kwargs: result)
    unknown = labels.label_episode((decision,), time_limit_s=0.1)[0]
    assert unknown.labels and all(label.label is None for label in unknown.labels)
    assert not unknown.training_rows()
