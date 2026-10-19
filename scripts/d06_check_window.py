# #!/usr/bin/env python3
# """D06 independent check of the pinned Arizona carbon CSV and one UTC 24-hour window.

# Standalone on purpose: uses only the standard library and does NOT import the D01 adapter
# (unless --compare-adapter is given, which is a separate cross-check after the independent
# parse). Nothing is sorted, filled, dropped, rounded or rescaled. The window is a plain UTC
# calendar day, not the Phoenix-midnight episode mapping, and it makes no claim about whether
# a timestamp marks interval start or end.
# """

# from __future__ import annotations

# import argparse
# import csv
# import hashlib
# import json
# import math
# import platform
# import sys
# from datetime import datetime, timedelta, timezone
# from pathlib import Path

# PIN = "a92b4755aca560e34a98d14028dda629eb968482"
# REF_SHA256 = "e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4"
# REF_BLOB = "d5337a654e77c938d0909e76d56efdf3ad491e83"
# HEADER = ["timestamp", "WND", "SUN", "WAT", "OIL", "NG", "COL", "NUC", "OTH", "avg_CI"]
# # Prior-documentation reference values (targets to compare against, not evidence).
# REF_YEAR = {"min": 251.22162645218947, "max": 749.1955146635997, "mean": 575.0418721742574}
# REF_JAN1 = {
#     "first": 631.6617084572886,
#     "last": 541.7221627408993,
#     "min": 541.7221627408993,
#     "max": 672.2776436504105,
# }


# def check(path: Path, day: str) -> dict:
#     raw = path.read_bytes()
#     blob = hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()
#     problems: list[str] = []
#     lines = raw.decode("utf-8").splitlines()
#     header = next(csv.reader([lines[0]])) if lines else []
#     rows = list(csv.reader(lines[1:]))
#     if header != HEADER:
#         problems.append(f"header differs: {header}")
#     stamps, ci = [], []
#     for n, row in enumerate(rows, start=1):
#         if len(row) != len(HEADER):
#             problems.append(f"row {n}: {len(row)} fields")
#             continue
#         t = datetime.fromisoformat(row[0])
#         if t.tzinfo is None or t.utcoffset() != timedelta(0):
#             problems.append(f"row {n}: timestamp not explicit UTC")
#         for name, cell in zip(HEADER[1:], row[1:]):
#             v = float(cell)
#             if not math.isfinite(v) or v < 0:
#                 problems.append(f"row {n}: {name}={cell} not finite/nonnegative")
#         stamps.append(t.astimezone(timezone.utc))
#         ci.append(float(row[-1]))
#     dupes = len(stamps) - len(set(stamps))
#     gaps = [
#         (a.isoformat(), b.isoformat())
#         for a, b in zip(stamps, stamps[1:])
#         if b - a != timedelta(hours=1)
#     ]
#     year = {
#         "rows": len(rows),
#         "first": stamps[0].isoformat(),
#         "last": stamps[-1].isoformat(),
#         "duplicates": dupes,
#         "non_hourly_steps": len(gaps),
#         "gaps_sample": gaps[:5],
#         "starts_2022_01_01T00Z": stamps[0] == datetime(2022, 1, 1, tzinfo=timezone.utc),
#         "ends_2022_12_31T23Z": stamps[-1] == datetime(2022, 12, 31, 23, tzinfo=timezone.utc),
#         "min": min(ci),
#         "max": max(ci),
#         "mean": math.fsum(ci) / len(ci),
#     }
#     d0 = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
#     win = [(s, v) for s, v in zip(stamps, ci) if d0 <= s < d0 + timedelta(days=1)]
#     wv = [v for _, v in win]
#     window = {
#         "utc_day": day,
#         "rows": len(win),
#         "contiguous_hourly": all(b[0] - a[0] == timedelta(hours=1) for a, b in zip(win, win[1:])),
#         "expected_hours_present": [s for s, _ in win]
#         == [d0 + timedelta(hours=h) for h in range(24)],
#         "first": wv[0],
#         "last": wv[-1],
#         "min": min(wv),
#         "max": max(wv),
#         "mean": math.fsum(wv) / len(wv),
#         "observations": [{"timestamp": s.isoformat(), "avg_CI": v} for s, v in win],
#     }
#     return {
#         "checker": "scripts/d06_check_window.py (standalone)",
#         "file": str(path),
#         "size_bytes": len(raw),
#         "sha256": hashlib.sha256(raw).hexdigest(),
#         "git_blob_sha1": blob,
#         "sha256_matches_reference": hashlib.sha256(raw).hexdigest() == REF_SHA256,
#         "blob_matches_reference": blob == REF_BLOB,
#         "source_pin": PIN,
#         "run_utc": datetime.now(timezone.utc).isoformat(),
#         "python": sys.version.split()[0],
#         "platform": platform.platform(),
#         "year": year,
#         "window": window,
#         "problems": problems,
#         "reference_comparison": {
#             "year_exact_equal": {k: year[k] == v for k, v in REF_YEAR.items()},
#             "jan1_exact_equal": (
#                 {k: window[k] == v for k, v in REF_JAN1.items()}
#                 if day == "2022-01-01"
#                 else "n/a (not 2022-01-01)"
#             ),
#         },
#     }


# def compare_adapter(path: Path, result: dict) -> dict:
#     sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root
#     from dc_sustainability.data.carbon_source import load_source  # separate cross-check

#     pairs, _ = load_source(path)
#     by_ts = {t.isoformat(): v for t, v in pairs}
#     obs = result["window"]["observations"]
#     same = all(by_ts.get(o["timestamp"]) == o["avg_CI"] for o in obs)
#     return {"adapter_rows": len(pairs), "window_values_identical": same}


# def main() -> int:
#     p = argparse.ArgumentParser(description=__doc__)
#     p.add_argument("csv", type=Path)
#     p.add_argument("--day", default="2022-01-01", help="UTC calendar day, YYYY-MM-DD")
#     p.add_argument("--report", type=Path, required=True, help="new JSON output (no overwrite)")
#     p.add_argument("--compare-adapter", action="store_true")
#     a = p.parse_args()
#     if a.report.exists():
#         print(f"refusing to overwrite {a.report}", file=sys.stderr)
#         return 2
#     result = check(a.csv, a.day)
#     if a.compare_adapter:
#         result["adapter_comparison"] = compare_adapter(a.csv, result)
#     a.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
#     w, y = result["window"], result["year"]
#     print(f"sha256 {result['sha256']} (matches reference: {result['sha256_matches_reference']})")
#     print(f"git blob sha1 {result['git_blob_sha1']} (matches: {result['blob_matches_reference']})")
#     print(
#         f"year: rows={y['rows']} {y['first']} -> {y['last']} dup={y['duplicates']} "
#         f"non_hourly={y['non_hourly_steps']} min={y['min']!r} max={y['max']!r} mean={y['mean']!r}"
#     )
#     print(
#         f"window {w['utc_day']}: rows={w['rows']} contiguous={w['contiguous_hourly']} "
#         f"first={w['first']!r} last={w['last']!r} min={w['min']!r} max={w['max']!r} "
#         f"mean={w['mean']!r}"
#     )
#     for o in w["observations"]:
#         print(f"  {o['timestamp']}  {o['avg_CI']!r}")
#     print("problems:", result["problems"] or "none")
#     if "adapter_comparison" in result:
#         print("adapter comparison:", result["adapter_comparison"])
#     ok = (
#         not result["problems"]
#         and result["sha256_matches_reference"]
#         and y["rows"] == 8760
#         and y["duplicates"] == 0
#         and y["non_hourly_steps"] == 0
#         and w["rows"] == 24
#         and w["expected_hours_present"]
#     )
#     print("RESULT:", "PASS (structural)" if ok else "FAIL")
#     return 0 if ok else 1


# if __name__ == "__main__":
#     raise SystemExit(main())


#!/usr/bin/env python3
"""D06 independent check of the pinned Arizona carbon CSV and one UTC 24-hour window.

Standalone on purpose: uses only the standard library and does NOT import the D01 adapter
(unless --compare-adapter is given, which is a separate cross-check after the independent
parse). Nothing is sorted, filled, dropped, rounded or rescaled. The window is a plain UTC
calendar day, not the Phoenix-midnight episode mapping, and it makes no claim about whether
a timestamp marks interval start or end.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PIN = "a92b4755aca560e34a98d14028dda629eb968482"
REF_SHA256 = "e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4"
REF_BLOB = "d5337a654e77c938d0909e76d56efdf3ad491e83"
HEADER = [
    "timestamp",
    "WND",
    "SUN",
    "WAT",
    "OIL",
    "NG",
    "COL",
    "NUC",
    "OTH",
    "avg_CI",
]

# Prior-documentation reference values (targets to compare against, not evidence).
REF_YEAR = {
    "min": 251.22162645218947,
    "max": 749.1955146635997,
    "mean": 575.0418721742574,
}
REF_JAN1 = {
    "first": 631.6617084572886,
    "last": 541.7221627408993,
    "min": 541.7221627408993,
    "max": 672.2776436504105,
}


def _parse_utc_day(day: str) -> datetime:
    """Parse exactly YYYY-MM-DD as midnight UTC."""
    parsed = date.fromisoformat(day)
    if parsed.isoformat() != day:
        raise ValueError(day)
    return datetime.combine(parsed, datetime.min.time(), tzinfo=timezone.utc)


def check(path: Path, day: str) -> dict:
    raw = path.read_bytes()
    blob = hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()
    problems = []

    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        lines = []
        problems.append(f"CSV is not valid UTF-8: {exc}")

    try:
        header = next(csv.reader([lines[0]])) if lines else []
        rows = list(csv.reader(lines[1:]))
    except csv.Error as exc:
        header, rows = [], []
        problems.append(f"CSV parse error: {exc}")

    if header != HEADER:
        problems.append(f"header differs: {header}")

    stamps = []
    records = []
    ci_values = []

    for n, row in enumerate(rows, start=1):
        if len(row) != len(HEADER):
            problems.append(f"row {n}: {len(row)} fields")
            continue

        timestamp = None
        try:
            timestamp = datetime.fromisoformat(row[0])
        except ValueError:
            problems.append(f"row {n}: malformed timestamp: {row[0]!r}")

        if timestamp is not None:
            if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
                problems.append(f"row {n}: timestamp not explicit UTC")

            timestamp = timestamp.astimezone(timezone.utc)
            stamps.append(timestamp)

        numeric_values = {}

        for name, cell in zip(HEADER[1:], row[1:]):
            try:
                value = float(cell)
            except ValueError:
                problems.append(f"row {n}: {name} is not numeric: {cell!r}")
                continue

            numeric_values[name] = value

            if not math.isfinite(value) or value < 0:
                problems.append(f"row {n}: {name}={cell} not finite and nonnegative")

        # Keep observations aligned with valid timestamps and avg_CI values.
        if timestamp is not None and "avg_CI" in numeric_values:
            records.append((timestamp, numeric_values["avg_CI"]))

        if "avg_CI" in numeric_values:
            ci_values.append(numeric_values["avg_CI"])

    dupes = len(stamps) - len(set(stamps))

    gaps = [
        (a.isoformat(), b.isoformat())
        for a, b in zip(stamps, stamps[1:])
        if b - a != timedelta(hours=1)
    ]

    year = {
        "rows": len(rows),
        "valid_timestamp_rows": len(stamps),
        "first": stamps[0].isoformat() if stamps else None,
        "last": stamps[-1].isoformat() if stamps else None,
        "duplicates": dupes,
        "non_hourly_steps": len(gaps),
        "gaps_sample": gaps[:5],
        "starts_2022_01_01T00Z": (
            bool(stamps) and stamps[0] == datetime(2022, 1, 1, tzinfo=timezone.utc)
        ),
        "ends_2022_12_31T23Z": (
            bool(stamps) and stamps[-1] == datetime(2022, 12, 31, 23, tzinfo=timezone.utc)
        ),
        "min": min(ci_values) if ci_values else None,
        "max": max(ci_values) if ci_values else None,
        "mean": (math.fsum(ci_values) / len(ci_values) if ci_values else None),
    }

    try:
        d0 = _parse_utc_day(day)
    except ValueError:
        problems.append(f"invalid --day value: {day!r} (expected YYYY-MM-DD)")
        d0 = None

    if d0 is not None:
        win = [
            (timestamp, value)
            for timestamp, value in records
            if d0 <= timestamp < d0 + timedelta(days=1)
        ]
    else:
        win = []

    wv = [value for _, value in win]

    window = {
        "utc_day": day,
        "rows": len(win),
        "contiguous_hourly": all(b[0] - a[0] == timedelta(hours=1) for a, b in zip(win, win[1:])),
        "expected_hours_present": (
            d0 is not None
            and [timestamp for timestamp, _ in win] == [d0 + timedelta(hours=h) for h in range(24)]
        ),
        "first": wv[0] if wv else None,
        "last": wv[-1] if wv else None,
        "min": min(wv) if wv else None,
        "max": max(wv) if wv else None,
        "mean": (math.fsum(wv) / len(wv) if wv else None),
        "observations": [
            {
                "timestamp": timestamp.isoformat(),
                "avg_CI": value,
            }
            for timestamp, value in win
        ],
    }

    sha256 = hashlib.sha256(raw).hexdigest()

    return {
        "checker": "scripts/d06_check_window.py (standalone)",
        "file": str(path),
        "size_bytes": len(raw),
        "sha256": sha256,
        "git_blob_sha1": blob,
        "sha256_matches_reference": sha256 == REF_SHA256,
        "blob_matches_reference": blob == REF_BLOB,
        "source_pin": PIN,
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "year": year,
        "window": window,
        "problems": problems,
        "reference_comparison": {
            "year_exact_equal": {key: year[key] == value for key, value in REF_YEAR.items()},
            "jan1_exact_equal": (
                {key: window[key] == value for key, value in REF_JAN1.items()}
                if day == "2022-01-01"
                else "n/a (not 2022-01-01)"
            ),
        },
    }


def result_passes(
    result: dict,
    compare_adapter_requested: bool = False,
) -> bool:
    """Apply the D06 acceptance gates without requiring adapter comparison by default."""
    if result.get("problems"):
        return False

    if result.get("sha256_matches_reference") is not True:
        return False

    if result.get("blob_matches_reference") is not True:
        return False

    year = result.get("year", {})

    if (
        year.get("rows") != 8760
        or year.get("valid_timestamp_rows") != 8760
        or year.get("first") != "2022-01-01T00:00:00+00:00"
        or year.get("last") != "2022-12-31T23:00:00+00:00"
        or year.get("duplicates") != 0
        or year.get("non_hourly_steps") != 0
    ):
        return False

    window = result.get("window", {})

    if (
        window.get("rows") != 24
        or window.get("contiguous_hourly") is not True
        or window.get("expected_hours_present") is not True
    ):
        return False

    comparison = result.get("reference_comparison", {})
    year_comparison = comparison.get("year_exact_equal")

    if not isinstance(year_comparison, dict) or not year_comparison:
        return False

    if not all(value is True for value in year_comparison.values()):
        return False

    jan1_comparison = comparison.get("jan1_exact_equal")

    if window.get("utc_day") == "2022-01-01":
        if not isinstance(jan1_comparison, dict) or not jan1_comparison:
            return False

        if not all(value is True for value in jan1_comparison.values()):
            return False

    if compare_adapter_requested:
        adapter_comparison = result.get("adapter_comparison")

        if (
            not isinstance(adapter_comparison, dict)
            or adapter_comparison.get("window_values_identical") is not True
        ):
            return False

    return True


def compare_adapter(path: Path, result: dict) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    from dc_sustainability.data.carbon_source import load_source

    pairs, _ = load_source(path)
    by_ts = {timestamp.isoformat(): value for timestamp, value in pairs}

    observations = result["window"]["observations"]

    same = all(
        by_ts.get(observation["timestamp"]) == observation["avg_CI"] for observation in observations
    )

    return {
        "adapter_rows": len(pairs),
        "window_values_identical": same,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument(
        "--day",
        default="2022-01-01",
        help="UTC calendar day, YYYY-MM-DD",
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="new JSON output (no overwrite)",
    )
    parser.add_argument("--compare-adapter", action="store_true")
    args = parser.parse_args()

    if args.report.exists():
        print(f"refusing to overwrite {args.report}", file=sys.stderr)
        return 2

    try:
        result = check(args.csv, args.day)
    except (OSError, csv.Error) as exc:
        result = {
            "checker": "scripts/d06_check_window.py (standalone)",
            "file": str(args.csv),
            "source_pin": PIN,
            "problems": [f"could not read or parse source CSV: {exc}"],
        }

    if args.compare_adapter and not result.get("problems"):
        try:
            result["adapter_comparison"] = compare_adapter(args.csv, result)
        except Exception as exc:
            result["adapter_comparison"] = {
                "adapter_rows": None,
                "window_values_identical": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )

    window = result.get("window", {})
    year = result.get("year", {})

    print(
        f"sha256 {result.get('sha256')} "
        f"(matches reference: {result.get('sha256_matches_reference')})"
    )
    print(
        f"git blob sha1 {result.get('git_blob_sha1')} "
        f"(matches: {result.get('blob_matches_reference')})"
    )
    print(
        f"year: rows={year.get('rows')} "
        f"valid_timestamps={year.get('valid_timestamp_rows')} "
        f"{year.get('first')} -> {year.get('last')} "
        f"dup={year.get('duplicates')} "
        f"non_hourly={year.get('non_hourly_steps')} "
        f"min={year.get('min')!r} "
        f"max={year.get('max')!r} "
        f"mean={year.get('mean')!r}"
    )
    print(
        f"window {window.get('utc_day', args.day)}: "
        f"rows={window.get('rows')} "
        f"contiguous={window.get('contiguous_hourly')} "
        f"first={window.get('first')!r} "
        f"last={window.get('last')!r} "
        f"min={window.get('min')!r} "
        f"max={window.get('max')!r} "
        f"mean={window.get('mean')!r}"
    )

    for observation in window.get("observations", []):
        print(f"  {observation['timestamp']}  {observation['avg_CI']!r}")

    print("problems:", result.get("problems") or "none")

    if "adapter_comparison" in result:
        print("adapter comparison:", result["adapter_comparison"])

    ok = result_passes(
        result,
        compare_adapter_requested=args.compare_adapter,
    )

    print("RESULT:", "PASS (structural)" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
