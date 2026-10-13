"""D02 private calibration tooling; field meanings must be supplied from source evidence.

No source field names or units are guessed. No episodes or public schemas are generated.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

DOI = "https://doi.org/10.13139/OLCF/3013979"
QUANTILES = (0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1.0)
TIME_FACTORS = {"seconds": 1.0, "minutes": 60.0, "hours": 3600.0}
POWER_FACTORS = {"W": 0.001, "kW": 1.0, "MW": 1000.0}


@dataclass(frozen=True)
class FieldMapping:
    """Adapter configuration, not an F02 exchanged record or verified source dictionary."""

    job_id: str
    runtime: str
    nodes: str
    mean_power: str
    requested_walltime: str
    runtime_unit: str
    walltime_unit: str
    power_unit: str
    power_scope: str  # job_total or per_node_mean, explicitly evidenced
    evidence: str

    def __post_init__(self):
        if self.runtime_unit not in TIME_FACTORS or self.walltime_unit not in TIME_FACTORS:
            raise ValueError("time units must be explicitly seconds, minutes, or hours")
        if self.power_unit not in POWER_FACTORS:
            raise ValueError("power unit must be explicitly W, kW, or MW")
        if self.power_scope not in ("job_total", "per_node_mean"):
            raise ValueError("power scope must be job_total or per_node_mean")
        if not self.evidence.strip():
            raise ValueError("source dictionary evidence is required (synthetic for fixtures)")
        if any(not isinstance(c, str) or not c.strip() for c in self.columns):
            raise ValueError("field names must be nonempty strings")
        if len(set(self.columns)) != 5:
            raise ValueError("five distinct fields are required")

    @property
    def columns(self):
        return (self.job_id, self.runtime, self.nodes, self.mean_power, self.requested_walltime)


@dataclass(frozen=True)
class CalibrationRow:
    source_job_id: str
    runtime_seconds: float
    node_count: int
    job_power_kw: float
    requested_walltime_seconds: float


def _positive(value):
    if isinstance(value, bool) or value is None or isinstance(value, (list, dict, tuple)):
        raise ValueError("not a numeric scalar")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError("not positive finite")
    return result


def validate_rows(rows: Iterable[Mapping], fields: FieldMapping):
    """Exclude bad rows with all reasons; duplicate IDs exclude every occurrence.

    Structural missing fields fail the entire table rather than looking like row exclusions.
    No upper outlier cutoff, runtime/walltime inequality, or success-status filter is inferred.
    """
    candidates = []
    exclusions = []
    ids = Counter()
    total = 0
    for index, row in enumerate(rows):
        total += 1
        if not isinstance(row, Mapping) or any(c not in row for c in fields.columns):
            raise ValueError(f"row {index}: missing configured fields or nonmapping row")
        reasons = []
        raw_id = row[fields.job_id]
        if (
            isinstance(raw_id, bool)
            or not isinstance(raw_id, (str, int))
            or not str(raw_id).strip()
        ):
            reasons.append("invalid_job_id")
            job_id = None
        else:
            job_id = str(raw_id)
            ids[job_id] += 1
        values = {}
        for name, column, factor in (
            ("runtime", fields.runtime, TIME_FACTORS[fields.runtime_unit]),
            ("nodes", fields.nodes, 1.0),
            ("power", fields.mean_power, POWER_FACTORS[fields.power_unit]),
            ("walltime", fields.requested_walltime, TIME_FACTORS[fields.walltime_unit]),
        ):
            try:
                value = _positive(row[column]) * factor
                if not math.isfinite(value) or (name == "nodes" and not value.is_integer()):
                    raise ValueError("invalid converted value")
                values[name] = value
            except (TypeError, ValueError, OverflowError):
                reasons.append(f"invalid_{name}")
        if not reasons and fields.power_scope == "per_node_mean":
            values["power"] *= values["nodes"]
            if not math.isfinite(values["power"]):
                reasons.append("invalid_power")
        candidates.append((index, job_id, values, reasons))
    accepted = []
    for index, job_id, values, reasons in candidates:
        if job_id is not None and ids[job_id] > 1:
            reasons.append("duplicate_job_id")
        if reasons:
            exclusions.append({"row_index": index, "reasons": sorted(reasons)})
        else:
            accepted.append(
                CalibrationRow(
                    job_id,
                    values["runtime"],
                    int(values["nodes"]),
                    values["power"],
                    values["walltime"],
                )
            )
    counts = Counter(reason for item in exclusions for reason in item["reasons"])
    return tuple(accepted), {
        "input_rows": total,
        "accepted_rows": len(accepted),
        "excluded_rows": len(exclusions),
        "reason_counts": dict(sorted(counts.items())),
        "exclusions": exclusions,
        "field_mapping": asdict(fields),
        "row_index_base": 0,
    }


def quantile(values, probability):
    """Linear interpolation at (n-1)*p, equivalent to Hyndman-Fan type 7."""
    ordered = sorted(values)
    if not ordered or any(not math.isfinite(v) for v in ordered):
        raise ValueError("quantiles require nonempty finite values")
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("probability must be in [0,1]")
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    weight = position - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def distribution(values):
    values = tuple(values)
    if not values or any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError("distribution requires positive finite values")
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "population_stddev": statistics.pstdev(values),
        "min": min(values),
        "max": max(values),
        "quantiles": {str(p): quantile(values, p) for p in QUANTILES},
        "quantile_method": "Hyndman-Fan type 7",
    }


def calibration_statistics(rows):
    rows = tuple(rows)
    return {
        "runtime_seconds": distribution(r.runtime_seconds for r in rows),
        "job_power_kw": distribution(r.job_power_kw for r in rows),
        "requested_walltime_seconds": distribution(r.requested_walltime_seconds for r in rows),
    }


def proposed_mapping(row: CalibrationRow, population):
    """Unapproved Q06 design only: clip each marginal to p05/p95, scale linearly.

    Degenerate ranges fail explicitly. Caller must preserve row pairing and obtain agreement
    before adopting this function in D03. Requested walltime does not become a deadline.
    """
    population = tuple(population)
    outputs = []
    for value, values, lower, upper in (
        (row.runtime_seconds, [r.runtime_seconds for r in population], 1, 4),
        (row.job_power_kw, [r.job_power_kw for r in population], 10, 40),
    ):
        lo, hi = quantile(values, 0.05), quantile(values, 0.95)
        if hi <= lo:
            raise ValueError("degenerate calibration range requires an approved alternative")
        fraction = max(0.0, min(1.0, (value - lo) / (hi - lo)))
        outputs.append(lower + (upper - lower) * fraction)
    # Round half upward; do not use Python's ties-to-even rounding.
    return {
        "duration_slots": math.floor(outputs[0] + 0.5),
        "power_kw": outputs[1],
        "mapping_status": "proposed_requires_Q06_agreement",
    }


def inspect_parquet(
    path: Path,
    fields: FieldMapping,
    *,
    expected_sha256: str,
    source_version: str,
    acquired_at_utc: str,
):
    """Read only the configured job-table columns, after checking the pinned bytes.

    pyarrow is an existing project dependency. No telemetry traversal or network request.
    Acquisition date/version are caller evidence, not fabricated filesystem timestamps.
    """
    import pyarrow.parquet as pq

    from dc_sustainability.schemas import SourceRef

    if not source_version.strip() or not acquired_at_utc.strip():
        raise ValueError("source version and acquisition timestamp are required")
    from datetime import datetime, timedelta

    stamp = datetime.fromisoformat(acquired_at_utc.replace("Z", "+00:00"))
    if stamp.utcoffset() != timedelta(0):
        raise ValueError("acquisition timestamp must be UTC-aware")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != expected_sha256:
        raise ValueError("source checksum mismatch")
    schema = pq.read_schema(path)
    if len(set(schema.names)) != len(schema.names):
        raise ValueError("duplicate Parquet field names")
    if any(c not in schema.names for c in fields.columns):
        raise ValueError("configured columns absent from Parquet schema")
    table = pq.read_table(path, columns=list(fields.columns))
    rows, report = validate_rows(table.to_pylist(), fields)
    report.update(
        {
            "source": SourceRef(
                source_id="frontier-job-table",
                path=DOI,
                sha256=digest,
                redistribution_status="unresolved",
            ).model_dump(),
            "source_version": source_version,
            "acquired_at_utc": acquired_at_utc,
            "observed_schema": str(schema),
            "file_bytes": path.stat().st_size,
            "statistics": calibration_statistics(rows) if rows else None,
            "accepted_rows_sha256": hashlib.sha256(
                json.dumps(
                    [asdict(row) for row in sorted(rows, key=lambda r: r.source_job_id)],
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest(),
            "status": "inspected_not_approved_calibration",
        }
    )
    return rows, report
