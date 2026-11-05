"""The refreshed approval must bind actual preparation, without authorizing dispatch."""

import json
from pathlib import Path

from dc_sustainability import schemas as s
from dc_sustainability.experiments.config import lf_sha256
from scripts import run_i01_public_receiving as launcher

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/evidence"


def read(name):
    return json.loads((EVIDENCE / name).read_text())


def test_current_authorization_binds_candidate_readiness_and_launcher():
    candidate = read("i01-offline-config-2026-11-02.json")
    ready = read("i01-unified-readiness-2026-11-02.json")
    approval = read("i01-authorization-template-2026-11-02.json")
    assert candidate["candidate_config_identity"]["code_revision"] == launcher.HEAD
    assert candidate["candidate_config_hash"] == s.sha256_hex(
        candidate["candidate_config_identity"]
    )
    assert (
        candidate["candidate_config_hash"]
        == ready["candidate_config_hash"]
        == approval["candidate_config_hash"]
    )
    assert approval["readiness_sha256"] == lf_sha256(
        EVIDENCE / "i01-unified-readiness-2026-11-02.json"
    )
    assert (
        approval["launcher_sha256"]
        == ready["launcher_lf_sha256"]
        == lf_sha256(Path(launcher.__file__))
    )
    assert (
        approval["bounds"]
        == ready["proposed_bounds"]
        == candidate["proposed_outer_controls_not_enforced_by_identity_alone"]
    )
    assert candidate["dispatch_authorized"] is False
    assert approval["status"] == "pending_fresh_user_approval"
    assert approval["approval_ref"] is approval["approved_by"] is None


def test_no_startup_dry_run_and_previous_candidate_are_retained():
    dry = read("i01-launcher-dry-run-2026-11-02.json")
    candidate = read("i01-offline-config-2026-11-02.json")
    old = read("i01-pre-nov04-2026-11-04/i01-offline-config-2026-11-02.json")
    assert dry["status"] == "dry_run_passed"
    assert dry["verified_on"] == "2026-11-04"
    assert dry["config_hash"] == candidate["candidate_config_hash"]
    assert (
        dry["runtime_started"] is dry["held_out_access"] is dry["output_directory_created"] is False
    )
    assert dry["model_requests"] == 0
    assert old["candidate_config_hash"] != candidate["candidate_config_hash"]
    assert any(
        entry["config_hash"] == old["candidate_config_hash"]
        for entry in candidate["candidate_history"]
    )
    assert (
        old["candidate_config_identity"]["trained"]
        == candidate["candidate_config_identity"]["trained"]
    )
    old_model = dict(old["candidate_config_identity"]["model"])
    current_model = dict(candidate["candidate_config_identity"]["model"])
    assert old_model.pop("plain_prompt_sha256") != current_model.pop("plain_prompt_sha256")
    assert old_model == current_model  # only the explicitly revised prompt pin changed
    assert (
        "dc_sustainability/evaluation/forecast_ties.py"
        in read("i01-unified-readiness-2026-11-02.json")["execution_file_lf_sha256"]
    )
