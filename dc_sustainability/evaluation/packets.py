"""E04/E07 study rating packets: selected Agent/Plain pairs from saved runs, blinded.

For each selected (episode, slot, trial) the two reviewed systems' saved decision records
are found, each system's own visible state at that slot is rebuilt by replaying its
executed starts (the systems follow different trajectories), and both outputs are shown
to raters as X and Y in a seeded random order.

Two products are kept apart, as Q10 requires: the rater case file (no system, stage,
trial, stratum or sample kind) and the private unblinding key. A selected pair whose run
unit or decision record is missing is listed in the key with its reason, never dropped
quietly and never replaced.

Raters see each system's *recommended* plan: the last stage that produced a plan
(fallback, else repaired, else initial). That stage is recorded in the key only.
"""

import random
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import review, sampling
from dc_sustainability.evaluation.replay import executed_starts, replay_episode
from dc_sustainability.evaluation.study_tables import PlannedEpisode
from dc_sustainability.evaluation.validator import Protocol
from dc_sustainability.knowledge.retrieval import get_context

PACKET_VERSION = "e04-study-packets-v1"
STAGE_ORDER = ("fallback", "repaired", "initial")
UnitKey = tuple[str, str, int]  # system, episode ID, trial


@dataclass(frozen=True)
class Item:
    """One sampled pair; ``kinds`` is ('main',), ('boundary',) or both."""

    selection: sampling.Selection
    kinds: tuple[str, ...]


def items(main: Iterable[sampling.Selection], boundary: Iterable[sampling.Selection]) -> list:
    """Merge the two samples. An identical episode/slot/trial in both is rated once."""
    merged: dict[tuple[str, int, int], list] = {}
    for kind, selections in (("main", main), ("boundary", boundary)):
        for sel in selections:
            key = (sel.episode_id, sel.slot, sel.trial)
            if key in merged and kind in merged[key][1]:
                raise ValueError(f"duplicate {kind} selection {key}")
            merged.setdefault(key, [sel, []])[1].append(kind)
    return [Item(sel, tuple(kinds)) for sel, kinds in (merged[k] for k in sorted(merged))]


def recommended(record: s.DecisionRecord) -> tuple[str | None, s.Plan | None]:
    """The plan the system put forward last, and the stage it came from."""
    for stage in STAGE_ORDER:
        stage_record = getattr(record, stage)
        if stage_record is not None and stage_record.plan is not None:
            return stage, stage_record.plan
    return None, None


def blind_output(record: s.DecisionRecord) -> tuple[dict, str | None]:
    """The rater-facing output (no system identity) and the private stage label."""
    stage, plan = recommended(record)
    if plan is not None:
        status = "ok"
    elif record.raw_response:
        status = "malformed"
    elif record.errors:
        status = "error"
    else:
        status = "no_output"
    return (
        {
            "output_status": status,
            "plan": None if plan is None else plan.to_jsonable(),
            "explanation": None if record.explanation is None else record.explanation.to_jsonable(),
            # Raw text is shown only when no plan could be read from it (rule 11.7).
            "raw_response": None if plan is not None else (record.raw_response or None),
        },
        stage,
    )


def build(
    selected: Iterable[Item],
    planned: Mapping[str, PlannedEpisode],
    units: Mapping[UnitKey, tuple[s.DecisionRecord, ...]],
    *,
    order_seed: int,
    protocol: Protocol,
) -> tuple[dict, dict]:
    """Return (rater case file, private key). The case file passes ``review.load_cases``."""
    rng = random.Random(order_seed)
    selected = list(selected)
    rng.shuffle(selected)  # case order carries no episode, stratum or trial order
    cases, key_cases, missing = [], [], []
    replays: dict[UnitKey, object] = {}
    for item in selected:
        sel = item.selection
        where = {"episode_id": sel.episode_id, "slot": sel.slot, "trial": sel.trial}
        if sel.episode_id not in planned:
            missing.append({**where, "kinds": list(item.kinds), "reason": "episode not planned"})
            continue
        plan_ep = planned[sel.episode_id]
        records, states, problem = {}, {}, None
        for system in sampling.REVIEWED_SYSTEMS:
            unit = units.get((system, sel.episode_id, sel.trial))
            if unit is None:
                problem = f"{system} unit missing"
                break
            at_slot = [r for r in unit if r.slot == sel.slot]
            if len(at_slot) != 1:
                problem = f"{system} has {len(at_slot)} records at the slot"
                break
            ukey = (system, sel.episode_id, sel.trial)
            if ukey not in replays:
                replays[ukey] = replay_episode(
                    plan_ep.episode, executed_starts(unit, sel.episode_id), protocol
                )
            record = at_slot[0]
            state = replays[ukey].state_at(
                sel.slot, tuple(plan_ep.forecasts_by_slot.get(sel.slot, ()))
            )
            # Raters must see exactly what the model saw: the replayed state's Context must
            # reproduce the saved input hash (graph and flat Contexts hash identically).
            if record.input_hash is not None and (
                get_context(state, plan_ep.episode.snapshot).content_hash != record.input_hash
            ):
                problem = f"{system} replayed state does not reproduce the saved input hash"
                break
            records[system], states[system] = record, state
        if problem:
            missing.append({**where, "kinds": list(item.kinds), "reason": problem})
            continue
        pair = sampling.pair_record(sel, states)
        order = list(sampling.REVIEWED_SYSTEMS)
        rng.shuffle(order)
        assignment = dict(zip(review.OUTPUT_KEYS, order, strict=True))
        case_id = f"S{len(cases) + 1:03d}"
        outputs, stages = {}, {}
        for k, system in assignment.items():
            outputs[k], stages[k] = blind_output(records[system])
        cases.append(
            {
                "case_id": case_id,
                "snapshot": plan_ep.episode.snapshot.to_jsonable(),
                "states": {k: states[system].to_jsonable() for k, system in assignment.items()},
                "outputs": outputs,
            }
        )
        key_cases.append(
            {
                "case_id": case_id,
                **where,
                "stratum": sel.stratum,
                "kinds": list(item.kinds),
                "systems": assignment,
                "stages": stages,
                "decision_ids": {
                    k: records[system].decision_id for k, system in assignment.items()
                },
                "input_hash_verified": {
                    k: records[system].input_hash is not None for k, system in assignment.items()
                },
                "state_hashes": dict(pair.state_hashes),
                "queue_counts": dict(pair.queue_counts),
                "not_applicable": list(pair.not_applicable),
            }
        )
    case_file = {
        "rubric_version": review.RUBRIC_VERSION,
        "packet_version": PACKET_VERSION,
        "cases": cases,
    }
    review.load_cases(case_file)  # refuse to write anything raters could not load
    key = {
        "packet_version": PACKET_VERSION,
        "order_seed": order_seed,
        "case_file_sha256": s.sha256_hex(case_file),
        "selected": len(selected),
        "cases": key_cases,
        "missing": missing,
    }
    return case_file, key
