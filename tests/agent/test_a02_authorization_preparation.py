"""Offline guardrails for the A02 episode-authorization preparation; no model calls."""

import json
from pathlib import Path

from dc_sustainability.agent.renderers import (
    proposal_template_sha256,
    repair_template_sha256,
)
from dc_sustainability.experiments.config import lf_sha256
from dc_sustainability.explanations.agent import explanation_template_sha256
from dc_sustainability.llm.plain import prompt_template_sha256

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


def test_episode_and_all_renderers_are_frozen_without_inventing_bounds():
    data = load_manifest()
    assert data["episode"]["episode_id"] == "EP-HAND1"
    assert data["episode"]["plain_and_agent_must_match"] is True
    bundle = ROOT / data["episode"]["bundle_path"]
    assert lf_sha256(bundle) == data["episode"]["bundle_sha256"]
    freeze = data["renderer_freeze"]
    assert freeze["status"] == "frozen_offline"
    assert freeze["exact_commit"] == "8a98996be6b497cf1065bdfaec8bbd1ce9f4b58b"
    assert freeze["plain_prompt_template_sha256"] == prompt_template_sha256()
    assert freeze["proposal_template_sha256"] == proposal_template_sha256()
    assert freeze["repair_template_sha256"] == repair_template_sha256()
    assert freeze["explanation_template_sha256"] == explanation_template_sha256()
    for field in (
        "plain_maximum_requests",
        "agent_maximum_requests",
        "per_request_seconds",
        "paired_total_seconds",
    ):
        assert data["bounds"][field] is None
    assert data["bounds"]["retries"] == 0


def test_a01_transport_evidence_does_not_authorize_a02():
    data = load_manifest()
    assert data["a01_prerequisite"]["status"] == "passed_for_bounded_transport_only"
    assert data["a01_prerequisite"]["model_calls"] == 2
    assert data["a01_prerequisite"]["retries"] == 0
    assert data["authorization"]["status"] == "not_recorded"
    assert data["ready_for_dispatch"] is False
