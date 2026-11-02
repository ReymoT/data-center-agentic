"""Offline conditional source-footprint checks; no selection, source reads or defaults."""

from datetime import date, datetime, timezone


def footprint(day: date, *, history_hours: int, convention: str) -> tuple[set[int], set[int]]:
    """Return scoring and conservative read rows for a 30-hour Phoenix window.

    History is an explicit continuous lookback envelope, not an adopted forecast
    method. Both start/end hypotheses remain conditional while Q05 is unresolved.
    """
    if type(day) is not date or day.year != 2022:
        raise ValueError("an explicit 2022 date is required")
    if type(history_hours) is not int or history_hours < 0:
        raise ValueError("history_hours must be a nonnegative integer")
    if convention not in {"start", "end"}:
        raise ValueError("explicit start/end convention required")
    start = datetime(day.year, day.month, day.day, 7, tzinfo=timezone.utc)
    origin = datetime(2022, 1, 1, tzinfo=timezone.utc)
    first = int((start - origin).total_seconds() // 3600) + (convention == "end")
    if first - history_hours < 0 or first + 29 >= 8760:
        raise ValueError("source footprint exceeds available year; never wrap")
    scoring = set(range(first, first + 30))
    reads = set(range(first - history_hours, first + 30))
    return scoring, reads


def conflicts(
    development_days, held_out_days, *, history_hours: int, convention: str
) -> tuple[dict, ...]:
    """Detect scoring overlap and both directions of history-to-scoring leakage."""
    development_days, held_out_days = tuple(development_days), tuple(held_out_days)
    if not development_days or not held_out_days:
        raise ValueError("both explicit window sets are required")
    development = [
        (day, *footprint(day, history_hours=history_hours, convention=convention))
        for day in development_days
    ]
    held = [
        (day, *footprint(day, history_hours=history_hours, convention=convention))
        for day in held_out_days
    ]
    findings = []
    for dev_day, dev_score, dev_read in development:
        for held_day, held_score, held_read in held:
            overlap = (held_read & dev_score) | (dev_read & held_score)
            if overlap:
                findings.append(
                    {
                        "development": dev_day.isoformat(),
                        "held_out": held_day.isoformat(),
                        "overlap_rows": sorted(overlap),
                    }
                )
    return tuple(findings)
