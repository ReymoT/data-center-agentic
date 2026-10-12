"""D01 source inspection; not an adopted CarbonFact or policy-facing interface."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import statistics
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

COMMIT = "a92b4755aca560e34a98d14028dda629eb968482"
SOURCE_PATH = "data/CarbonIntensity/AZPS_NG_&_avgCI.csv"
SOURCE_URL = (
    f"https://raw.githubusercontent.com/HewlettPackard/dc-rl/{COMMIT}/"
    "data/CarbonIntensity/AZPS_NG_%26_avgCI.csv"
)
SHA256 = "e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4"
COLUMNS = ("timestamp", "WND", "SUN", "WAT", "OIL", "NG", "COL", "NUC", "OTH", "avg_CI")
START = datetime(2022, 1, 1, tzinfo=timezone.utc)
HOUR = timedelta(hours=1)
BLOCKERS = (
    "Q05: CO2 versus CO2e conflicts within upstream calculation documentation.",
    "Q05: source timestamp interval-start versus interval-end convention unverified.",
    "Q05: dataset-specific redistribution rights unverified; repository has mixed licensing.",
    "Annual eGRID magnitude comparison is regional only; AZPS factor alignment unverified.",
    "F02 schemas/consumer validation and Ved independent 24-hour reproduction pending.",
)


def inspect_csv(payload: bytes, *, require_pinned: bool = True) -> dict:
    """Validate the complete source without sorting, filling, trimming or resampling.

    The optional unpinned mode is for diagnostic tests, not source acquisition.
    Bounds are a broad numerical screen, not an empirical emission-factor claim.
    """
    digest = hashlib.sha256(payload).hexdigest()
    errors = []
    if require_pinned and digest != SHA256:
        errors.append("checksum differs from inspected pinned source")
    try:
        reader = csv.reader(io.StringIO(payload.decode("utf-8")), strict=True)
        header = next(reader, [])
        rows = list(reader)
    except (UnicodeError, csv.Error) as exc:
        return {"sha256": digest, "errors": [*errors, f"invalid CSV encoding/syntax: {exc}"]}
    if tuple(header) != COLUMNS:
        errors.append(f"unexpected schema: {header!r}")
    if len(rows) != 8760:
        errors.append(f"expected 8760 records, observed {len(rows)}")
    values = []
    timestamps = []
    seen = set()
    previous = None
    if tuple(header) == COLUMNS:
        for index, row in enumerate(rows):
            label = f"record {index + 1}"
            if len(row) != len(COLUMNS):
                errors.append(f"{label}: incorrect field count")
                continue
            if any(not field.strip() for field in row):
                errors.append(f"{label}: missing value")
            try:
                timestamp = datetime.fromisoformat(row[0])
                if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
                    raise ValueError("timestamp must explicitly use UTC")
                timestamp = timestamp.astimezone(timezone.utc)
                if timestamp in seen:
                    errors.append(f"{label}: duplicate timestamp")
                if previous is not None and timestamp - previous != HOUR:
                    errors.append(f"{label}: hourly continuity/order failure")
                if timestamp != START + index * HOUR:
                    errors.append(f"{label}: timestamp differs from expected 2022 UTC hour")
                seen.add(timestamp)
                previous = timestamp
                timestamps.append(timestamp.isoformat())
            except ValueError as exc:
                errors.append(f"{label}: invalid timestamp: {exc}")
            for column, field in zip(COLUMNS[1:], row[1:]):
                try:
                    value = float(field)
                    if not math.isfinite(value) or value < 0:
                        raise ValueError("must be finite and nonnegative")
                    if column == "avg_CI":
                        if value > 2000:
                            raise ValueError("exceeds broad 2000 g/kWh screening bound")
                        values.append(value)
                except ValueError as exc:
                    errors.append(f"{label}: invalid {column}: {exc}")
    return {
        "sha256": digest,
        "pinned_checksum_matches": digest == SHA256,
        "columns": header,
        "row_count": len(rows),
        "first_timestamp_utc": timestamps[0] if timestamps else None,
        "last_timestamp_utc": timestamps[-1] if timestamps else None,
        "avg_CI_min": min(values) if values else None,
        "avg_CI_max": max(values) if values else None,
        "avg_CI_mean": statistics.fmean(values) if values else None,
        "errors": errors,
    }


def load_source(path: Path) -> tuple[tuple[tuple[datetime, float], ...], dict]:
    """Return immutable UTC/value pairs privately; no adopted shared schema.

    Only accept exact pinned bytes. These pairs are source observations, not
    verified interval/forecast facts; Q05 still blocks scientific acceptance.
    """
    payload = path.read_bytes()
    report = inspect_csv(payload)
    if report["errors"]:
        raise ValueError("; ".join(report["errors"][:10]))
    rows = csv.DictReader(io.StringIO(payload.decode("utf-8")))
    observations = tuple(
        (datetime.fromisoformat(row["timestamp"]).astimezone(timezone.utc), float(row["avg_CI"]))
        for row in rows
    )
    return observations, report


def retrieve_source(destination: Path) -> dict:
    """Fetch only the pinned URL; validate before an exclusive, non-overwriting save."""
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
        payload = response.read()
    report = inspect_csv(payload)
    if report["errors"]:
        raise ValueError("; ".join(report["errors"][:10]))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as output:
        output.write(payload)
    return report


def episode_indices(day: date, *, interval_convention: str) -> tuple[int, ...]:
    """Private data lookup only; caller must explicitly select a verified convention.

    This implements a proposed interval-start mapping, not evidence that the
    original source uses it. It creates no forecasts, jobs or policy state.
    """
    if interval_convention != "start":
        raise ValueError("only explicit interval-start mapping is implemented; Q05 is open")
    start = datetime(day.year, day.month, day.day, 7, tzinfo=timezone.utc)
    index = int((start - START) / HOUR)
    if index < 0 or index + 30 > 8760:
        raise ValueError("30-hour episode lies outside the source year; no wrapping")
    return tuple(range(index, index + 30))


def provenance(report: dict, *, acquisition_time_utc: str | None) -> dict:
    """Local D01 evidence report, not a versioned shared scientific record."""
    base = f"https://github.com/HewlettPackard/dc-rl/blob/{COMMIT}/"
    return {
        "task": "D01",
        "source_url": SOURCE_URL,
        "source_commit": COMMIT,
        "source_path": SOURCE_PATH,
        "acquisition_time_utc": acquisition_time_utc,
        "inspection_time_utc": datetime.now(timezone.utc).isoformat(),
        "validation": report,
        "meaning": "average carbon intensity associated with electricity consumption",
        "numerical_unit": "g/kWh",
        "unit_evidence": base + "envs/bat_env_fwd_view.py#L218-L243",
        "unit_evidence_status": "upstream kWh multiplication; CO2/CO2e label conflicts",
        "pollutant_basis": None,
        "timestamp_timezone": "UTC",
        "source_interval_convention": None,
        "meaning_evidence": base + "README.md#L342-L370",
        "license_evidence": [base + "LICENSE", base + "README.md#L577-L591"],
        "dataset_redistribution_verified": False,
        "transformations": ["UTF-8/CSV parsing", "UTC-aware parsing", "numeric parsing"],
        "source_values_modified": False,
        "excluded_records": 0,
        "annual_magnitude_comparison": {
            "source": "https://www.epa.gov/system/files/documents/2024-01/"
            "egrid2022_summary_tables.pdf",
            "table": "1, page 2, AZNM WECC Southwest total output emission rates",
            "year": 2022,
            "co2_lb_per_mwh": 776.0,
            "co2e_lb_per_mwh": 779.4,
            "conversion_g_per_kwh_per_lb_per_mwh": 0.45359237,
            "co2_g_per_kwh": 776.0 * 0.45359237,
            "co2e_g_per_kwh": 779.4 * 0.45359237,
            "interpretation": "Same order of magnitude only; not an acceptance threshold.",
            "limits": "AZNM region differs from AZPS; unweighted hourly source mean differs "
            "from generation-weighted annual eGRID; source pollutant basis unresolved. "
            "No transmission-loss adjustment, marginal factor, or source rescaling applied.",
        },
        "acceptance_complete": False,
        "blockers": list(BLOCKERS),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="local CSV, or download destination")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise FileExistsError(args.report)
    if args.source.resolve() == args.report.resolve():
        raise ValueError("source and report paths must differ")
    acquired = None
    if args.download:
        report = retrieve_source(args.source)
        acquired = datetime.now(timezone.utc).isoformat()
    else:
        report = inspect_csv(args.source.read_bytes())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(provenance(report, acquisition_time_utc=acquired), output, indent=2)
        output.write("\n")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
