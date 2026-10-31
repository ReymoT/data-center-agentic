"""Offline guardrails for the A02 episode-authorization preparation; no model calls."""

import json
from pathlib import Path

from dc_sustainability.agent.renderers import (
    proposal_template_sha256,
    repair_template_sha256,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/evidence/a02-episode-authorization-preparation-2026-10-30.json"


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_preparation_is_explicitly_offline_and_not_authorized():
    data = load_manifest()
    assert data["evidence_kind"] == "offline_preparation_not_inference"
    assert data["preparation_model_calls"] == 0
    assert data["preparation_runtime_requests"] == 0
    assert data["authorization"] == {
        "status": "not_recorded",
        "authorized_by": None,
        "reference": None,
    }
    assert data["ready_for_dispatch"] is False


def test_episode_alignment_and_unknown_bounds_are_not_invented():
    data = load_manifest()
    assert data["episode"]["episode_id"] == "EP-HAND1"
    assert data["episode"]["plain_and_agent_must_match"] is True
    assert data["episode"]["bundle_path"] is None
    assert data["episode"]["bundle_sha256"] is None
    for field in (
        "plain_maximum_requests",
        "agent_maximum_requests",
        "per_request_seconds",
        "paired_total_seconds",
    ):
        assert data["bounds"][field] is None
    assert data["bounds"]["retries"] == 0


def test_current_renderers_are_hashable_before_commit_freeze():
    data = load_manifest()
    assert len(proposal_template_sha256()) == 64
    assert len(repair_template_sha256()) == 64
    assert data["renderer_freeze"]["exact_commit"] is None
    assert data["renderer_freeze"]["explanation_renderer_ref"] is None
