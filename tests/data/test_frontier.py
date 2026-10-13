"""Labeled synthetic job-table fixtures, not observations of Frontier's actual schema."""

from dataclasses import replace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from dc_sustainability.data.frontier import (
    FieldMapping,
    calibration_statistics,
    inspect_parquet,
    proposed_mapping,
    quantile,
    validate_rows,
)
from dc_sustainability.schemas import Job, parse_record

FIELDS = FieldMapping(
    "id",
    "run",
    "nodes",
    "power",
    "wall",
    "seconds",
    "minutes",
    "W",
    "job_total",
    "synthetic fixture dictionary only",
)


def fixture(job_id="a", **changes):
    return {"id": job_id, "run": 3600, "nodes": 2, "power": 20000, "wall": 120, **changes}


def test_units_and_power_scope():
    rows, report = validate_rows([fixture()], FIELDS)
    assert (rows[0].runtime_seconds, rows[0].requested_walltime_seconds, rows[0].job_power_kw) == (
        3600,
        7200,
        20,
    )
    assert report["accepted_rows"] == 1
    nodes, _ = validate_rows([fixture()], replace(FIELDS, power_scope="per_node_mean"))
    assert nodes[0].job_power_kw == 40
    hours, _ = validate_rows(
        [fixture(run=2, wall=3, power=0.02)],
        replace(FIELDS, runtime_unit="hours", walltime_unit="hours", power_unit="MW"),
    )
    assert (
        hours[0].runtime_seconds,
        hours[0].requested_walltime_seconds,
        hours[0].job_power_kw,
    ) == (7200, 10800, 20)


@pytest.mark.parametrize(
    "column,reason",
    [("run", "runtime"), ("wall", "walltime"), ("power", "power"), ("nodes", "nodes")],
)
@pytest.mark.parametrize("bad", [None, True, 0, -1, float("nan"), float("inf"), "bad"])
def test_invalid_values(column, reason, bad):
    rows, report = validate_rows([fixture(**{column: bad})], FIELDS)
    assert not rows
    assert report["reason_counts"] == {f"invalid_{reason}": 1}


def test_multiple_reasons_duplicates_and_fractional_nodes():
    rows, report = validate_rows([fixture(), fixture(run=-1), fixture("b", nodes=1.5)], FIELDS)
    assert not rows
    assert report["excluded_rows"] == 3
    assert report["reason_counts"] == {
        "duplicate_job_id": 2,
        "invalid_nodes": 1,
        "invalid_runtime": 1,
    }
    assert report["exclusions"][0]["row_index"] == 0


def test_schema_and_semantics_fail_closed():
    with pytest.raises(ValueError, match="missing configured"):
        validate_rows([{"id": "x"}], FIELDS)
    for changes in (
        {"power_unit": "unknown"},
        {"runtime_unit": "unknown"},
        {"walltime_unit": "unknown"},
        {"power_scope": "unknown"},
        {"evidence": ""},
        {"runtime": "id"},
    ):
        with pytest.raises(ValueError):
            replace(FIELDS, **changes)


def test_statistics_mapping_and_f02_compatibility():
    rows, _ = validate_rows(
        [fixture(str(i), run=i * 3600, power=i * 10000) for i in range(1, 5)], FIELDS
    )
    stats = calibration_statistics(rows)
    assert stats["runtime_seconds"]["mean"] == 9000
    assert stats["job_power_kw"]["quantiles"]["0.5"] == 25
    assert stats["requested_walltime_seconds"]["min"] == 7200
    assert quantile([10, 20, 30, 40], 0.25) == 17.5
    for row in rows:
        mapped = proposed_mapping(row, rows)
        assert mapped == proposed_mapping(row, tuple(reversed(rows)))
        job = Job(
            job_id="J1",
            arrival_slot=0,
            deadline_slot=6,
            flexible=True,
            duration_slots=mapped["duration_slots"],
            power_kw=mapped["power_kw"],
        )
        assert 1 <= job.duration_slots <= 4 and 10 <= job.power_kw <= 40
        assert parse_record(job.model_dump()) == job
    assert proposed_mapping(rows[0], rows)["duration_slots"] == 1
    assert proposed_mapping(rows[-1], rows)["duration_slots"] == 4
    with pytest.raises(ValueError, match="degenerate"):
        proposed_mapping(rows[0], [rows[0]])
    with pytest.raises(ValueError):
        calibration_statistics([])
    with pytest.raises(ValueError):
        quantile([1], 2)


def test_parquet_provenance_and_checksum(tmp_path):
    import hashlib

    path = tmp_path / "synthetic.parquet"
    pq.write_table(pa.Table.from_pylist([fixture(), fixture("b", power=-1)]), path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    args = {
        "expected_sha256": digest,
        "source_version": "synthetic-test",
        "acquired_at_utc": "2026-10-13T00:00:00Z",
    }
    rows, report = inspect_parquet(path, FIELDS, **args)
    assert len(rows) == 1 and report["excluded_rows"] == 1
    assert report["source"]["sha256"] == digest
    assert report["source"]["schema_version"] == "1.0.0"
    with pytest.raises(ValueError, match="checksum"):
        inspect_parquet(path, FIELDS, **{**args, "expected_sha256": "0" * 64})
    with pytest.raises(ValueError, match="UTC"):
        inspect_parquet(path, FIELDS, **{**args, "acquired_at_utc": "2026-10-13"})
    with pytest.raises(ValueError, match="absent"):
        inspect_parquet(path, replace(FIELDS, runtime="absent"), **args)
