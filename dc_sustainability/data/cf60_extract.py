"""Pure bounded CSV extraction, with no file/network/model or approval operations.

Real file access belongs to the separately authorized operational wrapper. Tests
supply synthetic bytes and their explicit synthetic digest.
"""

import csv
import hashlib
import io
import math
from datetime import datetime
from time import monotonic

from dc_sustainability.data.carbon_source import COLUMNS, HOUR, START

MAX_BYTES = 1024 * 1024
REQUIRED_ROWS = 8760
MAX_SECONDS = 120


def check_deadline(deadline):
    if monotonic() >= deadline:
        raise TimeoutError("extract deadline exceeded")


def validate_indices(indices):
    if (
        not isinstance(indices, list)
        or not indices
        or any(type(i) is not int or not 0 <= i < REQUIRED_ROWS for i in indices)
        or indices != sorted(set(indices))
    ):
        raise ValueError("indices must be sorted unique source row ordinals")


def extract_bytes(payload, indices, *, expected_sha256, deadline=None):
    """Hash and parse the identical bytes; validate all timestamps, export selected CI.

    All rows are decoded, and all timestamp fields interpreted. Unselected numeric
    fields are neither converted nor returned. Deadline checks are cooperative,
    including after caller I/O; a dispatch watchdog is needed for hard OS timeouts.
    """
    deadline = monotonic() + MAX_SECONDS if deadline is None else deadline
    check_deadline(deadline)
    validate_indices(indices)
    if not isinstance(payload, bytes) or len(payload) > MAX_BYTES:
        raise ValueError("source exceeds bounded byte input")
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise ValueError("source checksum mismatch")
    check_deadline(deadline)
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("source is not valid UTF-8") from exc
    selected, wanted = [], set(indices)
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        if tuple(next(reader, [])) != COLUMNS:
            raise ValueError("source header differs from canonical columns")
        count = 0
        for index, row in enumerate(reader):
            check_deadline(deadline)
            if index >= REQUIRED_ROWS:
                raise ValueError("source must have exactly 8760 data rows")
            if len(row) != len(COLUMNS) or any(not value.strip() for value in row):
                raise ValueError(f"invalid CSV structure at source index {index}")
            try:
                timestamp = datetime.fromisoformat(row[0])
            except ValueError as exc:
                raise ValueError(f"invalid timestamp at source index {index}") from exc
            if (
                timestamp.tzinfo is None
                or timestamp.utcoffset().total_seconds() != 0
                or timestamp != START + index * HOUR
            ):
                raise ValueError(f"timestamp/order mismatch at source index {index}")
            if index in wanted:
                try:
                    value = float(row[-1])
                except ValueError as exc:
                    raise ValueError(f"invalid selected avg_CI at source index {index}") from exc
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"invalid selected avg_CI at source index {index}")
                selected.append({"index": index, "value": value})
            count += 1
    except csv.Error as exc:
        raise ValueError("malformed CSV syntax") from exc
    if count != REQUIRED_ROWS:
        raise ValueError("source must have exactly 8760 data rows")
    if [row["index"] for row in selected] != indices:
        raise ValueError("selected source rows unavailable")
    check_deadline(deadline)
    return {"source_sha256": digest, "rows": selected}
