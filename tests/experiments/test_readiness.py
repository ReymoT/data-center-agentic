import copy
import json
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.experiments.readiness import prepare
from dc_sustainability.llm.provider import OllamaProvider
from tests.policies.test_learned import _fit_tree

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def inputs(tmp_path):
    candidate = json.loads((ROOT / "docs/evidence/i01-offline-config-2026-11-02.json").read_text())
    paths = {}
    for system in ("decision_tree_c", "random_forest_d"):
        path, digest, _ = _fit_tree(tmp_path, system)
        paths[system] = path
        candidate["candidate_config_identity"]["trained"]["artifacts"][system] = digest
    identity_hash = s.sha256_hex(candidate["candidate_config_identity"])
    candidate.update(
        candidate_config_hash=identity_hash, candidate_run_id="RUN-" + identity_hash[:12]
    )
    return candidate, paths


def test_offline_readiness_verifies_actual_bytes_without_constructing_provider(inputs, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline preparation must not construct a provider")

    monkeypatch.setattr(OllamaProvider, "__init__", forbidden)
    candidate, paths = inputs
    report = prepare(candidate, paths, ROOT)
    assert report["status"] == "offline_pins_verified_dispatch_blocked"
    assert report["model_requests"] == 0 and report["held_out_access"] is False
    assert (
        report["verified_artifact_sha256"]
        == candidate["candidate_config_identity"]["trained"]["artifacts"]
    )
    assert report["remaining_dispatch_gates"]
    assert "dc_sustainability/schemas.py" in report["execution_file_lf_sha256"]


@pytest.mark.parametrize("problem", ["authorization", "lock", "identity", "budget", "artifact"])
def test_invalid_readiness_is_refused_before_dispatch(inputs, problem):
    candidate, paths = copy.deepcopy(inputs)
    if problem == "authorization":
        candidate["dispatch_authorized"] = True
    elif problem == "lock":
        candidate["candidate_config_identity"]["lock_sha256"] = "0" * 64
    elif problem == "identity":
        candidate["candidate_config_hash"] = "0" * 64
    elif problem == "budget":
        candidate["proposed_outer_controls_not_enforced_by_identity_alone"][
            "maximum_unit_attempts"
        ]["plain_llm"] = 7
    else:
        paths["decision_tree_c"].write_bytes(b"changed bytes")
    with pytest.raises(ValueError):
        prepare(candidate, paths, ROOT)
