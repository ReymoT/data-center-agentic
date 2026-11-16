"""Pure legacy-bundle assembly from explicit JSON inputs. No filesystem/source loader.

Authenticating permissions, hashes and execution scope belongs to the caller.
This preserves the existing development persistence rule, not CF60 adoption.
"""

import math
from datetime import datetime

from dc_sustainability import schemas as s
from dc_sustainability.data.carbon_source import HOUR, SHA256, START
from dc_sustainability.data.cf60_receiving import development_footprints
from dc_sustainability.data.materialize_development import SEMANTICS
from dc_sustainability.data.state_export import deadline_check, decode_bundle


def permitted_indices(records):
    return sorted(
        {
            i
            for footprint in development_footprints(records)
            for name in ("legacy_reads", "start_cf60_reads", "end_cf60_reads")
            for i in footprint[name]
        }
    )


def assemble(episodes, extract, *, records, commitments, deadline):
    """Build all40 existing capture-shaped bundles; never generate an episode/state."""
    deadline_check(deadline)
    ids = {r["episode_id"] for r in records}
    if len(records) != 40 or len(ids) != 40 or set(commitments) != ids:
        raise ValueError("exact fixed development cohort required")
    if not isinstance(episodes, dict) or set(episodes) != ids:
        raise ValueError("complete unique episode JSON mapping required")
    if set(extract) != {"source_sha256", "rows"} or extract["source_sha256"] != SHA256:
        raise ValueError("pinned explicit extract required")
    allowed = permitted_indices(records)
    rows = extract["rows"]
    if not isinstance(rows, list) or len(rows) != len(allowed):
        raise ValueError("exact permitted row set required")
    values = {}
    for row in rows:
        deadline_check(deadline)
        if not isinstance(row, dict) or set(row) != {"index", "value"}:
            raise ValueError("invalid extract row")
        index, value = row["index"], row["value"]
        if (
            type(index) is not int
            or index in values
            or type(value) not in (int, float)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError("invalid or duplicate extract value")
        values[index] = value
    if list(values) != allowed:
        raise ValueError("extract indices must match exact sorted permitted set")
    bundles = {}
    for record in records:
        deadline_check(deadline)
        eid = record["episode_id"]
        indices = record["window"]["proposed_physical_indices"]
        origin = START + indices[0] * HOUR
        if origin != datetime.fromisoformat(record["window"]["proposed_start_utc"]):
            raise ValueError("recorded UTC anchor differs")
        schedule = {}
        for slot, current in enumerate(indices):
            deadline_check(deadline)
            schedule[str(slot)] = [
                s.CarbonForecast(
                    fact_id=f"FACT-D01-PERSIST-{slot}-{valid}",
                    value=values[current - 1],
                    unit="g/kWh",
                    source_id="SRC-D01",
                    source_sha256=SHA256,
                    valid_slot=valid,
                    issued_at_utc=START + current * HOUR,
                    forecast_kind="persistence",
                    semantics=SEMANTICS,
                    quality_status="unvalidated",
                ).to_jsonable()
                for valid in range(slot, min(slot + s.PROPOSED_DECISION_SLOTS, 30))
            ]
        bundle = {
            "episode": episodes[eid],
            "slot0_utc": origin.isoformat(),
            "forecasts_by_slot": schedule,
        }
        episode, _ = decode_bundle(bundle, commitments[eid], record)
        if episode.episode_id != eid:
            raise ValueError("episode identity differs from allocation")
        bundles[eid] = bundle
    deadline_check(deadline)
    return bundles
