import copy
import json
from pathlib import Path

from scripts.validate_a01_bounded_manifest import validate_manifest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/evidence/a01-bounded-validation-manifest-2026-10-30.json"


def load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_checked_in_manifest_is_valid_blocked_offline_preparation():
    manifest = load()
    assert validate_manifest(manifest) == []
    assert manifest["preparation_model_calls"] == 0
    assert manifest["preparation_runtime_requests"] == 0
    assert not manifest["ready_for_dispatch"]


def test_readiness_refuses_missing_agreement_authorization_and_freeze():
    blockers = validate_manifest(load(), require_ready=True)
    assert any("nisha" in item for item in blockers)
    assert any("ved" in item for item in blockers)
    assert any("authorization" in item for item in blockers)
    assert any("exact run commit" in item for item in blockers)
    assert any("prompt hash" in item for item in blockers)
    assert any("renderer" in item for item in blockers)


def test_false_ready_flag_is_rejected_without_dispatch_gates():
    manifest = load()
    manifest["ready_for_dispatch"] = True
    assert "blocked preparation manifest cannot claim dispatch readiness" in validate_manifest(
        manifest
    )


def test_deadline_and_authorization_records_require_exact_owners():
    manifest = load()
    manifest["deadline_proposal"]["status"] = "accepted"
    assert any("both referenced agreements" in item for item in validate_manifest(manifest))

    manifest = load()
    manifest["run_authorization"] = {
        "status": "recorded",
        "reference": "https://example.invalid/authorization",
        "authorized_by": "someone-else",
    }
    assert any("MattyAnd" in item for item in validate_manifest(manifest))


def test_identity_settings_and_measurement_drift_are_rejected():
    mutations = (
        ("accepted_identity", "runtime_version", "0.40.6"),
        ("accepted_generation_settings", "temperature", 0.3),
        ("response_bounds", "largest_tokens", 1263),
    )
    for section, key, value in mutations:
        manifest = load()
        manifest[section][key] = value
        assert validate_manifest(manifest)


def test_third_request_retry_warmup_or_action_is_rejected():
    for key, value in (
        ("maximum_serial_requests", 3),
        ("retries", 1),
        ("warmup_calls", 1),
        ("tool_calls", 1),
        ("simulator_actions", 1),
        ("study_runs", 1),
    ):
        manifest = load()
        manifest["bounded_sequence"][key] = value
        assert validate_manifest(manifest)


def test_complete_referenced_gate_records_can_validate_ready_copy():
    manifest = copy.deepcopy(load())
    manifest["deadline_proposal"]["status"] = "accepted"
    for owner in ("nisha", "ved"):
        manifest["affected_owner_agreement"][owner] = {
            "status": "accepted",
            "reference": f"https://example.invalid/{owner}-agreement",
        }
    manifest["run_authorization"] = {
        "status": "recorded",
        "reference": "https://example.invalid/fresh-authorization",
        "authorized_by": "MattyAnd",
    }
    manifest["run_freeze"] = {
        "exact_commit": "a" * 40,
        "plain_prompt_sha256": "b" * 64,
        "agent_renderer_ref": "commit:path@sha256",
    }
    manifest["ready_for_dispatch"] = True
    assert validate_manifest(manifest, require_ready=True) == []
