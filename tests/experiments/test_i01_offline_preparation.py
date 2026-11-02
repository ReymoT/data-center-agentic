"""Pin normalization regression; never dispatch the candidate."""

import json
from pathlib import Path

from dc_sustainability import schemas as s
from dc_sustainability.experiments.config import lf_sha256

ROOT = Path(__file__).resolve().parents[2]


def test_candidate_pins_cli_normalized_lock_and_keeps_its_identity_consistent():
    candidate = json.loads((ROOT / "docs/evidence/i01-offline-config-2026-11-02.json").read_text())
    identity = candidate["candidate_config_identity"]
    assert identity["lock_sha256"] == lf_sha256(
        ROOT / "requirements/requirements-windows-py312.lock.txt"
    )
    digest = s.sha256_hex(identity)
    assert candidate["candidate_config_hash"] == digest
    assert candidate["candidate_run_id"] == "RUN-" + digest[:12]
    assert candidate["dispatch_authorized"] is False
    assert candidate["model_calls"] == candidate["runtime_requests"] == 0
    assert candidate["superseded_offline_candidate"]["run_id"] == "RUN-7806c94f563e"
