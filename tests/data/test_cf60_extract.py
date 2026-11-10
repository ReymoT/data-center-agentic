"""Synthetic CSVs only; never opens the real source or model artifacts."""

import csv
import hashlib
import io
import json
from datetime import timedelta

import pytest

from dc_sustainability.data.carbon_source import COLUMNS, START
from dc_sustainability.data.cf60_extract import MAX_BYTES, extract_bytes
from dc_sustainability.data.cf60_receiving import development_footprints
from dc_sustainability.data.materialize_development import allocation
from scripts import extract_cf60_development as cli


def payload(*, count=8760, change=None, header=COLUMNS):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(header)
    for index in range(count):
        row = [(START + timedelta(hours=index)).isoformat()] + ["x"] * 8 + [str(index)]
        if change is not None:
            row = change(index, row)
        writer.writerow(row)
    return stream.getvalue().encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def test_selected_values_and_all_timestamp_validation():
    # Unselected avg_CI and every other numeric column need not be parsed as numbers.
    data = payload(change=lambda i, row: row if i in [0, 29, 8759] else row[:-1] + ["unparsed"])
    result = extract_bytes(data, [0, 29, 8759], expected_sha256=digest(data))
    assert result["rows"] == [{"index": i, "value": float(i)} for i in [0, 29, 8759]]
    bad = payload(
        change=lambda i, row: ["2022-01-01T00:00:00+00:00"] + row[1:] if i == 500 else row
    )
    with pytest.raises(ValueError, match="timestamp/order"):
        extract_bytes(bad, [0], expected_sha256=digest(bad))


@pytest.mark.parametrize("count", [8759, 8761])
def test_exact_annual_row_count(count):
    data = payload(count=count)
    with pytest.raises(ValueError, match="exactly 8760"):
        extract_bytes(data, [0], expected_sha256=digest(data))


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "not-a-number"])
def test_invalid_selected_value_is_not_echoed(value):
    data = payload(change=lambda i, row: row[:-1] + [value] if i == 1 else row)
    with pytest.raises(ValueError, match="invalid selected avg_CI at source index 1"):
        extract_bytes(data, [1], expected_sha256=digest(data))


def test_bad_header_hash_and_byte_limit():
    data = payload(header=COLUMNS[::-1])
    with pytest.raises(ValueError, match="header"):
        extract_bytes(data, [0], expected_sha256=digest(data))
    data = payload()
    with pytest.raises(ValueError, match="checksum"):
        extract_bytes(data, [0], expected_sha256="0" * 64)
    with pytest.raises(ValueError, match="bounded byte"):
        extract_bytes(b"x" * (MAX_BYTES + 1), [0], expected_sha256="0" * 64)
    with pytest.raises(TimeoutError, match="deadline"):
        extract_bytes(data, [0], expected_sha256=digest(data), deadline=0)


@pytest.mark.parametrize("indices", [[True], [0, 0], [1, 0], [-1], [8760], []])
def test_invalid_index_requests(indices):
    data = b"synthetic only"
    with pytest.raises(ValueError, match="indices"):
        extract_bytes(data, indices, expected_sha256=digest(data))


def approval_fixture(tmp_path, monkeypatch):
    data = payload()
    source = tmp_path / "synthetic.csv"
    source.write_bytes(data)
    output = tmp_path / "extract.json"
    # Explicitly synthetic authorization and source pin, not real source access.
    monkeypatch.setattr(cli, "SHA256", digest(data))
    monkeypatch.setattr(cli, "revision", lambda: "1" * 40)
    rows = development_footprints(allocation()[0]["records"])
    indices = sorted(
        {
            i
            for row in rows
            for key in ("legacy_reads", "start_cf60_reads", "end_cf60_reads")
            for i in row[key]
        }
    )
    approval = {
        "status": "approved",
        "approved_by": "MattyAnd",
        "scope": "cf60-development-row-extract-only",
        "source_sha256": digest(data),
        "source_path": str(source),
        "output_path": str(output),
        "code_sha256": cli.code_pins(),
        "code_revision": "1" * 40,
        "permitted_indices": indices,
        "maximum_bytes": MAX_BYTES,
        "required_data_rows": 8760,
        "time_limit_s": 120,
        "physical_read_scope": "whole-file-bytes-all-timestamps-selected-numeric-only",
        "nonce_relation": "before_nonce",
    }
    for key in (
        "approval_ref",
        "source_use_ref",
        "custody_disposition_ref",
        "nonce_timing_ref",
        "executor",
        "machine",
        "storage_ref",
        "authorization_id",
    ):
        approval[key] = "SYNTHETIC-ONLY-" + key
    auth = tmp_path / "synthetic-approval.json"
    auth.write_text(json.dumps(approval))
    return source, auth, output, approval


def test_cli_one_shot_hashes_exact_read_and_exports_only_selected(tmp_path, monkeypatch):
    source, auth, output, approval = approval_fixture(tmp_path, monkeypatch)
    result = cli.run(source, auth, output)
    assert len(result["rows"]) == 340
    assert result["source_sha256"] == digest(source.read_bytes())
    assert result["extractor_code_sha256"] == cli.code_pins()
    assert result["ingestion"]["timestamps_interpreted"] == 8760
    assert result["ingestion"]["unselected_numeric_values_retained"] is False
    assert set(result) == {"source_sha256", "rows", "extractor_code_sha256", "ingestion"}
    with pytest.raises(FileExistsError):
        cli.run(source, auth, output)
    # An output rename cannot reuse a consumed ID.
    renamed = tmp_path / "second.json"
    approval["output_path"] = str(renamed)
    auth.write_text(json.dumps(approval))
    with pytest.raises(FileExistsError):
        cli.run(source, auth, renamed)
    assert not renamed.exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "pending"),
        ("custody_disposition_ref", None),
        ("nonce_relation", None),
        ("code_sha256", {}),
        ("time_limit_s", True),
        ("required_data_rows", 8759),
    ],
)
def test_bad_approval_stops_before_read_or_consumption(tmp_path, monkeypatch, field, value):
    source, auth, output, approval = approval_fixture(tmp_path, monkeypatch)
    approval[field] = value
    auth.write_text(json.dumps(approval))
    monkeypatch.setattr(cli, "extract_bytes", lambda *a, **k: pytest.fail("must not parse input"))
    with pytest.raises(ValueError):
        cli.run(source, auth, output)
    assert not output.exists()
    assert not (tmp_path / ".cf60-extract-consumed-authorizations").exists()


def test_failure_is_preserved_and_id_cannot_be_reused(tmp_path, monkeypatch):
    source, auth, output, approval = approval_fixture(tmp_path, monkeypatch)
    source.write_bytes(b"changed bytes after authorization")
    with pytest.raises(ValueError, match="checksum"):
        cli.run(source, auth, output)
    assert not output.exists()
    assert (
        json.loads(output.with_name(output.name + ".failure.json").read_text())[
            "authorization_consumed"
        ]
        is True
    )
    with pytest.raises(FileExistsError):
        cli.run(source, auth, output)
