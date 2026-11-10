"""Synthetic values on public allocation metadata, never real source observations."""

import hashlib
import json

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data.cf60_comparison import compare
from dc_sustainability.data.cf60_receiving import development_footprints
from dc_sustainability.data.materialize_development import allocation, snapshot
from scripts.compare_cf60_development import ROOT, run
from tests.contracts import fixtures as f


def inputs():
    records = allocation()[0]["records"]
    footprints = development_footprints(records)
    indices = {
        index
        for footprint in footprints
        for key in ("legacy_reads", "start_cf60_reads", "end_cf60_reads")
        for index in footprint[key]
    }
    return records, {index: float(index) for index in indices}


def test_projection_q04_features_and_missing_state_counts():
    records, rows = inputs()
    site = snapshot()
    state = s.VisibleState.from_snapshot(
        site,
        episode_id=records[0]["episode_id"],
        current_slot=0,
        state_version=0,
        waiting_jobs=tuple(job for job in f.jobs().values() if job.arrival_slot == 0),
    )
    result = compare(
        records, rows, [{"state": state.to_jsonable(), "snapshot": site.to_jsonable()}]
    )
    assert result["issue_hypothesis_count"] == 2400
    assert result["saved_state_count"] == 1
    assert result["missing_saved_state_count"] == 1199
    for row in result["comparisons"]:
        assert row["delta"] == (-2 if row["interpretation"] == "start" else -1)
    first = result["comparisons"][0]["features"]
    assert first["legacy"]["q04"]["usable"] == first["cf60"]["q04"]["usable"]
    old = first["legacy"]["candidate_rows"]
    new = first["cf60"]["candidate_rows"]
    assert old and len(old) == len(new)
    assert old[0]["values"][:-2] == new[0]["values"][:-2]
    assert old[0]["values"][-1] - new[0]["values"][-1] == 2


@pytest.mark.parametrize("slot", [30, 45])
def test_saved_state_outside_compared_slots_is_rejected(slot):
    records, rows = inputs()
    site = snapshot()
    state = s.VisibleState.from_snapshot(
        site, episode_id=records[0]["episode_id"], current_slot=slot, state_version=0
    )
    entry = {"state": state.to_jsonable(), "snapshot": site.to_jsonable()}
    with pytest.raises(ValueError, match="outside the 30 compared issues"):
        compare(records, rows, [entry])


def test_missing_history_is_not_zero():
    records, _ = inputs()
    result = compare(records, {})
    assert all(
        r["legacy_missing"] and r["cf60_missing"] and r["delta"] is None
        for r in result["comparisons"]
    )


def test_reject_extra_rows_and_invalid_budget():
    records, rows = inputs()
    with pytest.raises(ValueError, match="unauthorized"):
        compare(records, {**rows, 8760: 0})
    with pytest.raises(ValueError, match="time limit"):
        compare(records, rows, time_limit_s=1801)


def test_cli_rejects_pin_and_output_reuse(tmp_path, monkeypatch):
    from scripts import compare_cf60_development as driver

    monkeypatch.setattr(driver, "checkout_revision", lambda: "1" * 40)
    records, rows = inputs()
    from dc_sustainability.data.carbon_source import SHA256

    extract = tmp_path / "synthetic.json"
    extract.write_text(
        json.dumps(
            {"source_sha256": SHA256, "rows": [{"index": i, "value": v} for i, v in rows.items()]}
        )
    )
    pins = {
        name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in (
            "scripts/compare_cf60_development.py",
            "dc_sustainability/data/cf60_comparison.py",
            "dc_sustainability/data/cf60_broker.py",
        )
    }
    approval = {
        "authorization_id": "synthetic-first",
        "code_revision": "1" * 40,
        "status": "approved",
        "scope": "cf60-development-forecast-features-only",
        "source_sha256": SHA256,
        "code_sha256": dict(pins),
        "extract_sha256": hashlib.sha256(extract.read_bytes()).hexdigest(),
        "permitted_indices": sorted(rows),
        "time_limit_s": 1800,
        "extract_path": str(extract),
        "output_path": str(tmp_path / "out"),
    }
    auth = tmp_path / "synthetic-approval.json"
    auth.write_text(json.dumps(approval))
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="path mismatch"):
        run(extract, auth, tmp_path / "wrong-path")
    assert run(extract, auth, output)["issue_hypothesis_count"] == 2400
    with pytest.raises(FileExistsError):
        run(extract, auth, output)
    # Changing the output in a copied record cannot reuse its consumed ID.
    approval["output_path"] = str(tmp_path / "retry")
    auth.write_text(json.dumps(approval))
    with pytest.raises(FileExistsError):
        run(extract, auth, tmp_path / "retry")
    approval["code_sha256"]["dc_sustainability/data/cf60_broker.py"] = "0" * 64
    auth.write_text(json.dumps(approval))
    with pytest.raises(ValueError, match="code pin mismatch"):
        run(extract, auth, tmp_path / "wrong-pin")
    approval["code_sha256"]["dc_sustainability/data/cf60_broker.py"] = pins[
        "dc_sustainability/data/cf60_broker.py"
    ]
    damaged = json.loads(extract.read_text())
    damaged["rows"][0]["value"] = -1
    extract.write_text(json.dumps(damaged))
    approval["extract_sha256"] = hashlib.sha256(extract.read_bytes()).hexdigest()
    approval["authorization_id"] = "synthetic-failure"
    approval["output_path"] = str(tmp_path / "failed")
    auth.write_text(json.dumps(approval))
    failed = tmp_path / "failed"
    with pytest.raises(ValueError, match="invalid extract value"):
        run(extract, auth, failed)
    assert (failed / "failure.json").is_file()
    assert not (failed / "comparison.json").exists()
    extract.write_text("{}")
    approval["authorization_id"] = "synthetic-checksum"
    approval["output_path"] = str(tmp_path / "unused")
    auth.write_text(json.dumps(approval))
    with pytest.raises(ValueError, match="checksum mismatch"):
        run(extract, auth, tmp_path / "unused")


@pytest.mark.parametrize(
    "field,value",
    [
        ("extract_sha256", None),
        ("extract_sha256", "bad"),
        ("time_limit_s", True),
        ("time_limit_s", 1801),
        ("permitted_indices", []),
        ("code_revision", None),
    ],
)
def test_invalid_authorization_is_rejected_before_consumption(tmp_path, monkeypatch, field, value):
    from dc_sustainability.data.carbon_source import SHA256
    from scripts import compare_cf60_development as driver

    _, rows = inputs()
    extract = tmp_path / "synthetic.json"
    extract.write_text("{}")
    output = tmp_path / "out"
    monkeypatch.setattr(driver, "checkout_revision", lambda: "1" * 40)
    pins = {
        name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in (
            "scripts/compare_cf60_development.py",
            "dc_sustainability/data/cf60_comparison.py",
            "dc_sustainability/data/cf60_broker.py",
        )
    }
    approval = {
        "status": "approved",
        "scope": "cf60-development-forecast-features-only",
        "source_sha256": SHA256,
        "authorization_id": "SYNTHETIC-preflight",
        "code_revision": "1" * 40,
        "code_sha256": pins,
        "extract_sha256": hashlib.sha256(extract.read_bytes()).hexdigest(),
        "extract_path": str(extract),
        "output_path": str(output),
        "permitted_indices": sorted(rows),
        "time_limit_s": 1800,
    }
    approval[field] = value
    auth = tmp_path / "approval.json"
    auth.write_text(json.dumps(approval))
    monkeypatch.setattr(driver, "pinned_json", lambda *a: pytest.fail("must not open input"))
    with pytest.raises(ValueError):
        driver.run(extract, auth, output)
    assert not output.exists()
    assert not (tmp_path / ".cf60-consumed-authorizations").exists()
