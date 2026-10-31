"""Offline tests for the production Agent proposal renderer; no model calls."""

import json

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.agent.renderers import (
    messages_sha256,
    proposal_template_sha256,
    render_proposal,
)
from tests.contracts import fixtures as f


def context(representation="graph"):
    state = f.visible_state()
    return state, s.Context.build(state, f.snapshot(), representation)


def test_proposal_renderer_contains_exact_identity_and_visible_context_only():
    state, graph = context()
    messages = render_proposal(graph)
    assert [message["role"] for message in messages] == ["system", "user"]
    user = messages[1]["content"]
    assert f'record_type "Plan", schema_version "{s.SCHEMA_VERSION}"' in user
    assert f'episode_id "{state.episode_id}"' in user
    assert f"slot {state.current_slot}, state_version {state.state_version}" in user
    facts = json.loads(user[user.index("{") :])
    assert facts == graph.content.to_jsonable()
    s.assert_no_private_keys(facts)
    for evidence_id in graph.content.evidence_ids:
        assert evidence_id in user
    assert "J3" not in user


def test_renderer_does_not_claim_tools_checks_repairs_fallback_or_execution():
    _, graph = context()
    rendered = "\n".join(message["content"] for message in render_proposal(graph)).lower()
    assert "do not claim" in rendered
    for text in ("check", "tool", "repair", "fallback", "execution"):
        assert text in rendered
    assert "return only one proposed plan" in rendered


def test_renderer_requires_revalidated_graph_context():
    _, flat = context("flat")
    with pytest.raises(ValueError, match="graph context"):
        render_proposal(flat)
    _, graph = context()
    broken = graph.model_copy(update={"content_hash": "0" * 64})
    with pytest.raises(ValueError, match="content_hash"):
        render_proposal(broken)


def test_renderer_and_message_hashes_are_deterministic_and_distinct():
    _, graph = context()
    first = render_proposal(graph)
    assert first == render_proposal(graph)
    assert len(proposal_template_sha256()) == 64
    assert len(messages_sha256(first)) == 64
    assert proposal_template_sha256() != messages_sha256(first)
