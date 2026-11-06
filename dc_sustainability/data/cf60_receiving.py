"""Separate synthetic receiving procedure; no source acquisition or held-out selection.

Independent arithmetic and active forbidden-read probes exercise accessible data,
not just approved IDs in a producer log. Nisha must run/review it herself; its
producer-side PASS is not her independent acceptance.
"""

import json
from datetime import datetime, timedelta, timezone

from dc_sustainability import schemas as s
from dc_sustainability.data.cf60_broker import RestrictedHistory, code_hash, issue_forecast


def development_footprints(records):
    """Metadata only: retain recorded scoring and legacy plus both CF60 histories.

    No selection, nonce, values, source loader, fold rewrite or custody amendment.
    All forty fixed records must be supplied by the pinned allocation reader.
    """
    if len(records) != 40 or len({r["episode_id"] for r in records}) != 40:
        raise ValueError("exact forty development records required")
    origin = datetime(2022, 1, 1, tzinfo=timezone.utc)
    result = []
    for record in records:
        indices = record["window"]["proposed_physical_indices"]
        if len(indices) != 30 or indices != list(range(indices[0], indices[0] + 30)):
            raise ValueError("invalid recorded mapping")
        anchor = datetime.fromisoformat(record["window"]["date"]).replace(
            hour=7, tzinfo=timezone.utc
        )
        physical = int((anchor - origin).total_seconds() / 3600)
        entry = {
            "episode_id": record["episode_id"],
            "recorded_scoring": indices,
            "legacy_reads": [i - 1 for i in indices],
        }
        for name, shift in (("start", 0), ("end", 1)):
            entry[name + "_scoring"] = list(range(physical + shift, physical + shift + 30))
            # Independent union: issue=anchor+t; start labels t-5..t-3, end t-4..t-2.
            first = physical - (5 if name == "start" else 4)
            entry[name + "_cf60_reads"] = list(range(first, first + 32))
        rows = [v for k, xs in entry.items() if k != "episode_id" for v in xs]
        if any(type(v) is not int or not 0 <= v < 8760 for v in rows):
            raise ValueError("out-of-year footprint; no wrapping")
        entry["reserved_union"] = sorted(set(rows))
        result.append(entry)
    return result


def receive():
    origin = datetime(2022, 1, 1, tzinfo=timezone.utc)
    hour = timedelta(hours=1)
    anchor = origin + 100 * hour
    source = s.SourceRef(
        source_id="SRC-SYNTHETIC",
        path="synthetic://cf60-receiving",
        sha256="a" * 64,
        redistribution_status="permitted",
    )
    checks = []
    for interpretation in ("start", "end"):
        for slot in range(30):
            issue = anchor + slot * hour
            # Derive from physical interval completion and strict lag inequality.
            eligible = []
            for row in range(90, 140):
                label = origin + row * hour
                end = label + (hour if interpretation == "start" else 0 * hour)
                if end + hour < issue and issue - end <= 4 * hour:
                    eligible.append((label, 10000 + row))
            cap = RestrictedHistory(
                eligible,
                issue=issue,
                interpretation=interpretation,
                source=source,
                authorization="synthetic-only",
            )
            expected = max(eligible)[1]
            output = issue_forecast(cap, anchor=anchor, slot=slot, trusted_issue=issue)
            if any(f.value != expected for f in output.forecasts):
                raise ValueError("receiving value/selection mismatch")
            if tuple(f.valid_slot for f in output.forecasts) != tuple(
                range(slot, min(slot + 24, 30))
            ):
                raise ValueError("visible horizon mismatch")
            # Probe every row in the pinned synthetic year, including future and
            # older history; actual return/exception must agree, not merely logs.
            probe = RestrictedHistory(
                eligible,
                issue=issue,
                interpretation=interpretation,
                source=source,
                authorization="synthetic-only",
            )
            allowed = dict(eligible)
            denied = 0
            for row in range(8760):
                label = origin + row * hour
                try:
                    value = probe.read(label)
                except PermissionError:
                    if label in allowed:
                        raise ValueError("authorized row denied") from None
                    denied += 1
                else:
                    if label not in allowed or value != allowed[label]:
                        raise ValueError("unauthorized row accessible")
            if denied != 8757 or len(probe.footprint()) != 8760:
                raise ValueError("incomplete access footprint")
            checks.append(
                {
                    "interpretation": interpretation,
                    "slot": slot,
                    "accessible_rows": len(allowed),
                    "denied_reads": denied,
                    "output_sha256": s.sha256_hex(json.loads(output.receipt_json)),
                }
            )
    return {
        "scope": "synthetic receiving only",
        "broker_code_sha256": code_hash(),
        "checks": checks,
        "checks_sha256": s.sha256_hex(checks),
        "independent_acceptance": False,
    }


def main():
    from dc_sustainability.data.materialize_development import allocation

    manifest, _ = allocation()
    report = receive()
    footprints = development_footprints(manifest["records"])
    report["development_metadata"] = footprints
    report["development_metadata_sha256"] = s.sha256_hex(footprints)
    print(s.canonical_json(report))


if __name__ == "__main__":
    main()
