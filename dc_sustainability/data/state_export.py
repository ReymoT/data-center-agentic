"""Bounded development state export primitives; no source loader, model or solver.

Operational use requires the supervised, separately authorized script. Low-level
functions also support explicitly synthetic tests. They do not grant permission.
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from time import monotonic

from dc_sustainability import schemas as s
from dc_sustainability.data.carbon_source import SHA256
from dc_sustainability.data.materialize_development import allocation
from dc_sustainability.runtime import ExecutionController, TraceStore
from dc_sustainability.simulator import SchedulingSimulator

MAX_INPUT = 128 * 1024 * 1024
MAX_OUTPUT = 32 * 1024 * 1024
TRAJECTORY = "new-no-start-controller-refusal-drain-v1"


def deadline_check(deadline):
    if monotonic() >= deadline:
        raise TimeoutError("state export deadline exceeded")


def payload(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def state_pair(state, snapshot):
    s.Context.build(state, snapshot, representation="flat")
    if any(j.arrival_slot > state.current_slot for j in state.waiting_jobs):
        raise ValueError("future arrival in visible state")
    return {"state": state.to_jsonable(), "snapshot": snapshot.to_jsonable()}


def validate_entries(entries, allowed, expected_hashes, *, deadline):
    """Recover without inventing missing states; bind each pair to approved provenance."""
    found = {}
    for entry in entries:
        deadline_check(deadline)
        if set(entry) != {"state", "snapshot"}:
            raise ValueError("state entry fields differ")
        state = s.VisibleState.from_jsonable(entry["state"])
        snap = s.ConstraintSnapshot.from_jsonable(entry["snapshot"])
        key = state.episode_id, state.current_slot
        if key[0] not in allowed or not 0 <= key[1] < 30 or key in found:
            raise ValueError("unauthorized or duplicate state position")
        if snap.canonical_hash() != allowed[key[0]]["constraint_snapshot_sha256"]:
            raise ValueError("snapshot differs from immutable development receipt")
        clean = state_pair(state, snap)
        if s.sha256_hex(clean) != expected_hashes.get(f"{key[0]}@{key[1]}"):
            raise ValueError("state differs from authenticated original provenance")
        found[key] = clean
    if len(found) != len(expected_hashes):
        raise ValueError("original provenance and supplied state coverage differ")
    return [found[k] for k in sorted(found)]


def decode_bundle(data, expected, allocation_row):
    """Decode already bounded bytes. Never load a CSV to fill absent forecasts."""
    if set(data) != {"episode", "slot0_utc", "forecasts_by_slot"}:
        raise ValueError("capture needs a pinned complete episode bundle")
    episode = s.PrivateEpisode.from_jsonable(data["episode"])
    origin = datetime.fromisoformat(data["slot0_utc"])
    if origin.utcoffset() != timedelta(0) or origin != datetime.fromisoformat(
        allocation_row["window"]["proposed_start_utc"]
    ):
        raise ValueError("UTC slot mapping differs from allocation")
    if (
        episode.split != "development"
        or episode.forecast_visibility != "persistence"
        or episode.canonical_hash() != expected["episode_canonical_sha256"]
    ):
        raise ValueError("episode differs from immutable development content")
    if episode.snapshot.canonical_hash() != expected["constraint_snapshot_sha256"]:
        raise ValueError("snapshot differs from receipt")
    forecasts = {}
    if set(data["forecasts_by_slot"]) != {str(i) for i in range(30)}:
        raise ValueError("all 30 forecast positions must be explicit")
    for key, facts in data["forecasts_by_slot"].items():
        slot = int(key)
        forecasts[slot] = tuple(s.CarbonForecast.from_jsonable(f) for f in facts)
        if any(f.issued_at_utc > origin + timedelta(hours=slot) for f in forecasts[slot]):
            raise ValueError("forecast issued after decision boundary")
        if any(
            f.forecast_kind != "persistence" or f.source_sha256 != SHA256 for f in forecasts[slot]
        ):
            raise ValueError("capture binds the legacy forecast only")
    return episode, forecasts


def capture_episode(episode, forecasts, traces, config_hash, *, deadline):
    """New no-start diagnostic history through the real controller refusal path.

    No ApprovedActions is constructed here. Every blocked intention calls the
    controller, which alone invokes S01 refusal-and-drain and persists the trace.
    This is not a Greedy A performance run despite using its non-model F02 channel.
    """
    if episode.split != "development":
        raise ValueError("development only")
    sim = SchedulingSimulator(allow_completion_starts=False)
    sim.reset(episode, forecasts_by_slot=forecasts)
    controller = ExecutionController(
        sim, lambda: episode.snapshot, TraceStore(traces), config_hash=config_hash
    )
    entries = []
    for slot in range(30):
        deadline_check(deadline)
        state = sim.state()
        if state.current_slot != slot:
            raise ValueError("capture trajectory advanced unexpectedly")
        entries.append(state_pair(state, episode.snapshot))
        rec = s.DecisionRecord(
            decision_id="DEC-" + s.sha256_hex([episode.episode_id, slot, config_hash])[:40],
            run_id="RUN-" + config_hash[:12],
            system="greedy_a",
            trial=None,
            episode_id=episode.episode_id,
            slot=slot,
            input_hash=s.Context.build(state, episode.snapshot, representation="flat").content_hash,
            final_status="blocked",
            not_applicable_stages=("initial", "repaired", "fallback"),
        )
        outcome = controller.execute_step(
            rec, stage=None, expected_state_version=state.state_version
        )
        if (
            outcome.replayed
            or outcome.record.executed_starts
            or outcome.record.final_status != "blocked"
        ):
            raise ValueError("no-start diagnostic controller invariant failed")
    return entries


def write_artifact(path, data, *, maximum=MAX_OUTPUT):
    raw = payload(data)
    if len(raw) > maximum:
        raise ValueError("state export output cap exceeded")
    with Path(path).open("xb") as handle:
        handle.write(raw)
    return hashlib.sha256(raw).hexdigest()


def public_cohort(root):
    """Only the existing public development allocation/content receipt is inspected."""
    rows = allocation()[0]["records"]
    receipt = json.loads(
        (Path(root) / "data/manifests/d04-development-content-112-v2/receipt.json").read_text()
    )
    bindings = {r["episode_id"]: r for r in receipt["entries"]}
    if len(rows) != 40 or len(bindings) != 40 or {r["episode_id"] for r in rows} != set(bindings):
        raise ValueError("public development cohort mismatch")
    return rows, bindings
