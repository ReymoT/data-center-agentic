"""Offline tests for the L02 Agent explanation renderer; no real model is called."""

import json
import shutil

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.agent import AgentHarness
from dc_sustainability.explanations import agent as ex
from dc_sustainability.verification.checker import check_schedule
from tests.agent.test_harness import decide, messages, plan, response, setup
from tests.contracts import fixtures as f
from tests.llm.test_ollama_provider import server as server  # noqa: F401


def context(representation="graph"):
    state = f.visible_state()
    return state, s.Context.build(state, f.snapshot(), representation)


def passing_stage():
    state = f.visible_state()
    good = f.plan()
    return s.StageRecord(plan=good, check=check_schedule(good, state, f.snapshot()))


def test_renders_the_fixed_plan_its_check_and_visible_context_only():
    state, graph = context()
    selected = passing_stage()
    messages_ = ex.render_explanation(graph, selected)
    assert [m["role"] for m in messages_] == ["system", "user"]
    user = messages_[1]["content"]
    assert f'episode_id "{state.episode_id}", slot {state.current_slot}' in user
    assert selected.plan.to_json() in user and selected.check.to_json() in user
    facts = json.loads(user[user.rindex("\n{") + 1 :])
    assert facts == graph.content.to_jsonable()
    s.assert_no_private_keys(facts)
    assert "J3" not in user  # not visible at slot 0


def test_prompt_states_the_l02_boundaries():
    _, graph = context()
    text = "\n".join(m["content"] for m in ex.render_explanation(graph, passing_stage()))
    assert "Explanation rules:" in text  # the shared rules Plain also receives
    for phrase in (
        "do not change, add or remove any start",
        "has not executed",
        "do not say that any job started, that emissions were saved",
        "Do not say how the plan was produced",
        "Cite only IDs from the evidence_ids list",
    ):
        assert phrase in text, phrase


def test_refuses_anything_but_a_checked_passing_stage_for_this_context():
    state, graph = context()
    _, flat = context("flat")
    with pytest.raises(ValueError, match="graph context"):
        ex.render_explanation(flat, passing_stage())
    with pytest.raises(ValueError, match="checked, passing"):
        ex.render_explanation(graph, s.StageRecord(plan=f.plan()))
    overlap = s.Plan(
        episode_id=state.episode_id,
        slot=0,
        state_version=0,
        status="proposed",
        starts=(
            s.PlannedStart(job_id="J1", start_slot=0),
            s.PlannedStart(job_id="J2", start_slot=0),
        ),
    )
    failing = s.StageRecord(plan=overlap, check=check_schedule(overlap, state, f.snapshot()))
    assert failing.check.status == "fail"
    with pytest.raises(ValueError, match="checked, passing"):
        ex.render_explanation(graph, failing)
    later = state.model_copy(update={"state_version": 1})
    other = s.Context.build(
        s.VisibleState.model_validate(later.model_dump()), f.snapshot(), "graph"
    )
    with pytest.raises(ValueError, match="does not match"):
        ex.render_explanation(other, passing_stage())


def test_template_hash_is_deterministic_and_tracks_every_prompt_file(tmp_path, monkeypatch):
    _, graph = context()
    stage = passing_stage()  # each check has its own ID, so reuse one stage
    assert ex.render_explanation(graph, stage) == ex.render_explanation(graph, stage)
    original, source = ex.explanation_template_sha256(), ex.PROMPT_DIR
    used = (  # every file render_explanation reads, named here rather than taken from ex
        "shared/task_rules.md",
        "shared/explanation_rules.md",
        "agent/explanation_system.md",
        "agent/explanation.md",
    )
    for i, name in enumerate(used):
        root = tmp_path / f"prompts{i}"
        shutil.copytree(source, root)
        (root / name).write_text((root / name).read_text(encoding="utf-8") + "\nchanged\n")
        monkeypatch.setattr(ex, "PROMPT_DIR", root)
        assert ex.explanation_template_sha256() != original, name
    monkeypatch.undo()
    assert ex.explanation_template_sha256() == original


def test_harness_explains_the_approved_plan_without_changing_it(server, tmp_path):
    ep, sim, _, controller, client = setup(server, tmp_path)
    good = plan(sim.state())
    response(server, good)
    seen = []

    def explain(context, selected):
        rendered = ex.render_explanation(context, selected)
        seen.append(rendered)
        response(server, s.Explanation(summary="Synthetic test explanation.", source="llm"))
        return rendered

    harness = AgentHarness(
        client, controller, proposal_messages=messages, explanation_messages=explain
    )
    record = decide(harness, sim, ep).execution.record
    assert record.final_status == "executed" and record.execution_check.plan_hash == good.plan_hash
    assert record.model_call_count == len(server.requests) == 2
    assert server.requests[1]["messages"] == seen[0]
    assert server.requests[1]["format"]["title"] == "Explanation"
    assert record.explanation.summary == "Synthetic test explanation."
