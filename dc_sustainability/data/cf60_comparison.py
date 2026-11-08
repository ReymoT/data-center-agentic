"""Offline forecast/feature comparison using an explicitly supplied row extract.

No source loader, simulator, solver, classifier or model is invoked. Saved
visible states hold the operational history fixed across the two forecasts.
"""

import json
from dataclasses import asdict
from datetime import datetime
from math import isfinite
from time import monotonic

from dc_sustainability import schemas as s
from dc_sustainability.data import carbon_source
from dc_sustainability.data.cf60_broker import (
    ORIGIN,
    H,
    RestrictedHistory,
    candidates,
    issue_forecast,
)
from dc_sustainability.data.cf60_receiving import development_footprints
from dc_sustainability.data.materialize_development import SEMANTICS
from dc_sustainability.training.features import candidate_features
from dc_sustainability.verification.rules import assess_forecasts


def compare(records, rows, saved_states=(), *, time_limit_s=1800, authorization="synthetic-only"):
    """Compare all 2,400 issue/hypothesis pairs on the fixed development cohort.

    Missing extract rows mean missing evidence. Extra rows are rejected. Each
    saved-state entry supplies F02 state and snapshot objects, never a policy
    callback. Missing saved states are counted rather than synthesized.
    """
    if (
        type(time_limit_s) not in (int, float)
        or not isfinite(time_limit_s)
        or not 0 < time_limit_s <= 1800
    ):
        raise ValueError("time limit must be positive and at most 1800 seconds")
    deadline = monotonic() + time_limit_s
    footprints = development_footprints(records)
    allowed = {
        index
        for footprint in footprints
        for name in ("legacy_reads", "start_cf60_reads", "end_cf60_reads")
        for index in footprint[name]
    }
    if any(type(index) is not int or index not in allowed for index in rows):
        raise ValueError("extract contains an unauthorized row")
    if any(type(v) not in (int, float) or not isfinite(v) or v < 0 for v in rows.values()):
        raise ValueError("invalid extract value")
    by_episode = {record["episode_id"]: record for record in records}
    if any(r["partition"] != "development" or r["withheld"] for r in records):
        raise ValueError("development records only")
    states = {}
    for entry in saved_states:
        state = s.VisibleState.from_jsonable(entry["state"])
        snapshot = s.ConstraintSnapshot.from_jsonable(entry["snapshot"])
        key = state.episode_id, state.current_slot
        if key[0] not in by_episode or key in states:
            raise ValueError("unknown or duplicate saved state")
        s.Context.build(state, snapshot, representation="flat")
        states[key] = state, snapshot
    source = s.SourceRef(
        source_id="SRC-D01",
        path=carbon_source.SOURCE_URL,
        sha256=carbon_source.SHA256,
        commit=carbon_source.COMMIT,
        redistribution_status="unresolved",
    )
    comparisons = []
    for record, footprint in zip(records, footprints, strict=True):
        anchor = datetime.fromisoformat(record["window"]["proposed_start_utc"])
        recorded = record["window"]["proposed_physical_indices"]
        if anchor != ORIGIN + recorded[0] * H:
            raise ValueError("recorded anchor mismatch")
        for slot in range(30):
            issue = anchor + slot * H
            legacy_index = footprint["legacy_reads"][slot]
            legacy_value = rows.get(legacy_index)
            for interpretation in ("start", "end"):
                if monotonic() >= deadline:
                    raise TimeoutError("comparison deadline exceeded")
                # Only this issue's three copied candidates reach the broker.
                labels = candidates(issue, interpretation)
                history = RestrictedHistory(
                    (
                        (label, rows[index])
                        for label in labels
                        if (index := int((label - ORIGIN) / H)) in rows
                    ),
                    issue=issue,
                    interpretation=interpretation,
                    source=source,
                    authorization=authorization,
                )
                result = issue_forecast(history, anchor=anchor, slot=slot, trusted_issue=issue)
                receipt = json.loads(result.receipt_json)
                cf_value = result.forecasts[0].value if result.forecasts else None
                row = {
                    "episode_id": record["episode_id"],
                    "slot": slot,
                    "interpretation": interpretation,
                    "legacy_index": legacy_index,
                    "legacy_value": legacy_value,
                    "cf60_value": cf_value,
                    "delta": None
                    if legacy_value is None or cf_value is None
                    else cf_value - legacy_value,
                    "legacy_missing": legacy_value is None,
                    "cf60_missing": cf_value is None,
                    "broker_receipt": receipt,
                    "features": None,
                }
                saved = states.get((record["episode_id"], slot))
                if saved is not None:
                    state, snapshot = saved
                    legacy = tuple(
                        s.CarbonForecast(
                            fact_id=f"FACT-D01-PERSIST-{slot}-{v}",
                            value=legacy_value,
                            unit="g/kWh",
                            source_id="SRC-D01",
                            source_sha256=carbon_source.SHA256,
                            valid_slot=v,
                            issued_at_utc=issue,
                            forecast_kind="persistence",
                            semantics=SEMANTICS,
                            quality_status="unvalidated",
                        )
                        for v in range(slot, min(slot + 24, 30))
                        if legacy_value is not None
                    )
                    row["features"] = {
                        "legacy": _features(state, snapshot, legacy, issue),
                        "cf60": _features(state, snapshot, result.forecasts, issue),
                    }
                comparisons.append(row)
    return {
        "scope": "fixed-state development forecast comparison; no rollout or compatibility verdict",
        "issue_hypothesis_count": len(comparisons),
        "saved_state_count": len(states),
        "missing_saved_state_count": 1200 - len(states),
        "read_footprints": footprints,
        "comparisons": comparisons,
        "model_calls": 0,
        "solver_calls": 0,
    }


def _features(state, snapshot, forecasts, issue):
    payload = state.to_jsonable()
    payload["carbon_facts"] = [fact.to_jsonable() for fact in forecasts]
    changed = s.VisibleState.from_jsonable(payload)
    context = s.Context.build(changed, snapshot, representation="flat")
    assessment = assess_forecasts(changed, snapshot, decision_time_utc=issue)
    features = candidate_features(changed, context, decision_time_utc=issue)
    return {
        "q04": {**asdict(assessment), "usable": assessment.usable},
        "candidate_rows": [
            {"job_id": row.job_id, "start_slot": row.start_slot, "values": row.values()}
            for row in features
        ],
    }
