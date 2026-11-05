"""Offline shared instructions and unchanged semantic rejection; no model inference."""

import json
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.agent.renderers import render_proposal, render_repair
from dc_sustainability.llm.plain import render_messages
from tests.contracts import fixtures as f
from tests.llm.test_ollama_provider import generate, provider
from tests.llm.test_ollama_provider import server as server


@pytest.mark.parametrize("path", ["plain", "proposal", "repair"])
def test_same_action_choice_contract_reaches_all_planning_paths(path):
    state = f.visible_state()
    rules = (
        (Path(__file__).resolve().parents[2] / "prompts/shared/task_rules.md")
        .read_text(encoding="utf-8")
        .strip()
    )
    flat = s.Context.build(state, f.snapshot(), "flat")
    graph = s.Context.build(state, f.snapshot(), "graph")
    if path == "plain":
        messages = render_messages(flat)
    elif path == "proposal":
        messages = render_proposal(graph)
    else:
        messages = render_repair(graph, None, ("synthetic invalid initial response",))
        assert "complete replacement, not an addition" in messages[1]["content"]
    assert messages[0]["content"].startswith(rules)
    assert "exactly one action in exactly one category" in rules
    assert "A current or future start belongs only in starts" in rules
    assert "when returning a Plan or the plan inside PolicyOutput" in rules


@pytest.mark.parametrize("system,model", [("agent", s.Plan), ("plain_llm", s.PolicyOutput)])
def test_explicit_but_conflicting_actions_stay_failed_and_retained(server, system, model):
    plan = json.loads(f.plan().to_json())
    plan["abstentions"] = [{"job_id": "J2", "reason": "constraint_violation"}]
    if model is s.Plan:
        content = plan
    else:
        content = json.loads(f.policy_output().to_json())
        content["system"] = system
        content["explanation"]["source"] = "llm"
        content["plan"] = plan
    server.body["message"]["content"] = json.dumps(content)
    client = provider(server)
    attempt = generate(client, system=system, response_model=model)
    assert attempt.output is None and "jobs both started and deferred/abstained" in attempt.error
    assert attempt.raw_response and attempt.http_status == 200
    assert len(client.attempts) == len(server.requests) == 1
    assert not attempt.uncertain_outcome
    # Neither the model's start nor its abstention was silently removed to parse it.
    original = json.loads(json.loads(attempt.raw_response)["message"]["content"])
    original_plan = original.get("plan", original)
    assert original_plan["starts"] == plan["starts"]
    assert original_plan["abstentions"] == plan["abstentions"]


@pytest.mark.parametrize("choice", ["start", "abstain"])
def test_selecting_one_category_is_structurally_valid_without_rewriting_outputs(choice):
    plan = json.loads(f.plan().to_json())
    if choice == "abstain":
        plan["starts"] = [entry for entry in plan["starts"] if entry["job_id"] != "J2"]
        plan["abstentions"] = [{"job_id": "J2", "reason": "constraint_violation"}]
    parsed = s.Plan.from_json(json.dumps(plan))
    assert not ({entry.job_id for entry in parsed.starts} & {a.job_id for a in parsed.abstentions})
    # Structural validity does not certify the abstention, schedule or explanation.
