"""E04/E07 study rating packets built from saved Agent/Plain runs (public fixtures only)."""

import json

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import packets as pk
from dc_sustainability.evaluation import review
from dc_sustainability.evaluation.replay import executed_starts, replay_episode
from dc_sustainability.evaluation.sampling import Selection
from dc_sustainability.evaluation.validator import Q03_OPTION_B
from dc_sustainability.knowledge.retrieval import get_context
from tests.evaluation.test_study_tables import plan, plan_of, planned_item, record, run

PLANNED = plan_of(planned_item("EP-A"))
SEL = Selection("EP-A", "normal|persistence", 3, 0)


def units(agent="good", plain="late", trial=0, **fields):
    return {
        ("agent", "EP-A", trial): tuple(run("EP-A", "agent", trial, agent, **fields)),
        ("plain_llm", "EP-A", trial): tuple(run("EP-A", "plain_llm", trial, plain, **fields)),
    }


def build(selected=None, u=None, seed=7):
    selected = pk.items([SEL], []) if selected is None else selected
    return pk.build(
        selected, PLANNED, units() if u is None else u, order_seed=seed, protocol=Q03_OPTION_B
    )


def test_case_file_loads_and_carries_no_system_identity():
    cases, key = build()
    assert len(review.load_cases(cases)) == 1 and not key["missing"]
    text = json.dumps(cases)
    for hidden in ("agent", "plain_llm", "trial", "stratum", "boundary", "fallback", "repaired"):
        assert hidden not in text
    entry = key["cases"][0]
    assert sorted(entry["systems"].values()) == ["agent", "plain_llm"]
    assert (entry["episode_id"], entry["slot"], entry["trial"]) == ("EP-A", 3, 0)


def test_each_output_is_shown_with_its_own_systems_state():
    cases, key = build()
    entry = key["cases"][0]
    states = cases["cases"][0]["states"]
    assert states["X"] != states["Y"]  # the two trajectories differ by slot 3
    u = units()
    for out, system in entry["systems"].items():
        replay = replay_episode(
            PLANNED["EP-A"].episode, executed_starts(u[(system, "EP-A", 0)], "EP-A"), Q03_OPTION_B
        )
        assert s.VisibleState.from_jsonable(states[out]) == replay.state_at(3)


def test_a_missing_unit_is_listed_with_its_reason_not_dropped():
    u = units()
    del u[("agent", "EP-A", 0)]
    cases, key = build(u=u)
    assert cases["cases"] == []
    assert key["missing"] == [
        {
            "episode_id": "EP-A",
            "slot": 3,
            "trial": 0,
            "kinds": ["main"],
            "reason": "agent unit missing",
        }
    ]


def test_a_pair_in_both_samples_is_rated_once_with_both_kinds():
    selected = pk.items([SEL], [SEL])
    cases, key = build(selected)
    assert len(cases["cases"]) == 1 and key["cases"][0]["kinds"] == ["main", "boundary"]


def test_the_same_kind_twice_is_refused():
    with pytest.raises(ValueError, match="duplicate main"):
        pk.items([SEL, SEL], [])


def test_raters_see_the_last_stage_that_produced_a_plan():
    p0, p1, p2 = plan("EP-A", 0), plan("EP-A", 0, [("J1", 0)]), plan("EP-A", 0, [("J1", 1)])
    base = record("EP-A", 0, "agent", 0, p0, passed=False)
    stage = lambda p: s.StageRecord(plan=p, check=None)  # noqa: E731
    with_fallback = base.model_copy(
        update={"repaired": stage(p1), "fallback": stage(p2), "not_applicable_stages": ()}
    )
    assert pk.recommended(with_fallback) == ("fallback", p2)
    repaired_only = base.model_copy(
        update={"repaired": stage(p1), "not_applicable_stages": ("fallback",)}
    )
    assert pk.recommended(repaired_only) == ("repaired", p1)
    assert pk.recommended(base) == ("initial", p0)


def test_unreadable_output_shows_raw_text_and_no_plan():
    r = record("EP-A", 0, "plain_llm", 0).model_copy(update={"raw_response": "{ not json"})
    output, stage = pk.blind_output(r)
    assert output["output_status"] == "malformed" and output["plan"] is None
    assert output["raw_response"] == "{ not json" and stage is None


def test_a_readable_output_hides_its_raw_text():
    output, stage = pk.blind_output(
        record("EP-A", 0, "plain_llm", 0, plan("EP-A", 0)).model_copy(
            update={"raw_response": '{"plan": {}}'}
        )
    )
    assert output["output_status"] == "ok" and output["raw_response"] is None and stage == "initial"


def test_a_state_that_does_not_reproduce_the_saved_input_hash_is_withheld():
    cases, key = build(u=units(input_hash="0" * 64))
    assert cases["cases"] == []
    assert key["missing"][0]["reason"].endswith("does not reproduce the saved input hash")


def test_a_state_that_reproduces_the_saved_input_hash_is_verified():
    u = units()
    for k, records in u.items():
        replay = replay_episode(
            PLANNED["EP-A"].episode, executed_starts(records, "EP-A"), Q03_OPTION_B
        )
        u[k] = tuple(
            r.model_copy(
                update={
                    "input_hash": get_context(
                        replay.state_at(r.slot), PLANNED["EP-A"].episode.snapshot
                    ).content_hash
                }
            )
            if r.slot < s.PROPOSED_DECISION_SLOTS
            else r
            for r in records
        )
    cases, key = build(u=u)
    assert len(cases["cases"]) == 1
    assert key["cases"][0]["input_hash_verified"] == {"X": True, "Y": True}


def test_x_and_y_follow_the_recorded_seed():
    assert build(seed=1) == build(seed=1)
    orders = {build(seed=n)[1]["cases"][0]["systems"]["X"] for n in range(20)}
    assert orders == {"agent", "plain_llm"}


def test_a_case_gives_exactly_one_of_state_or_states():
    cases, _ = build()
    case = cases["cases"][0]
    with pytest.raises(ValueError, match="exactly one of"):
        review.load_cases({**cases, "cases": [{**case, "state": case["states"]["X"]}]})


def test_study_packet_renders_each_outputs_own_state():
    cases, _ = build()
    packet = review.render_packet(review.load_cases(cases), ("# study",))
    assert packet.count("State seen by output") == 2
    assert "agent" not in packet and "plain_llm" not in packet
