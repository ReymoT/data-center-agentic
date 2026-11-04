"""Keep the human receipt immutable and its limited acceptance distinct from freeze."""

import hashlib
import json
from pathlib import Path

from scripts.validate_i02_freeze_manifest import validate_manifest

ROOT = Path(__file__).resolve().parents[2]


def test_original_receipt_bytes_and_supplement_scope_are_retained():
    report = ROOT / "docs/evidence/I01_RECEIVING_NISHA_2026-11-03.txt"
    digest = hashlib.sha256(report.read_bytes()).hexdigest()
    assert digest == "900e67598cdb9c4e8aab6f927d94a4407980a55bc21d52780e1ca890c6c9d588"
    supplement = json.loads(
        (ROOT / "docs/evidence/I01_RECEIVING_MANAGER_CORROBORATION_2026-11-04.json").read_text()
    )
    assert supplement["human_report_raw_sha256"] == digest
    assert supplement["evidence_files_verified"] == 186 and supplement["zip_entries"] == 187
    assert supplement["model_requests"] == 0
    assert supplement["held_out_access"] is supplement["originals_modified"] is False
    units = supplement["units"]
    assert {u["system"] for u in units} == {
        "greedy_a",
        "greedy_b",
        "decision_tree_c",
        "random_forest_d",
        "agent",
        "plain_llm",
    }
    assert len({u["unit_id"] for u in units}) == 6
    assert sum(u["traces"] for u in units) == 180
    for unit in units:
        assert unit["traces"] == 30
        assert unit["replay_findings"] == unit["result_mismatches"] == 0
        assert unit["completed_work"]["status"] == "absent"
        assert unit["completed_work"]["recorded"] is None
        assert unit["manager_manifest_hash_check"] == "pass"
        assert unit["nisha_manifest_hash_check"] == "not_performed_packet_omitted_manifests"
        model = unit["system"] in {"agent", "plain_llm"}
        assert unit["trial"] == (0 if model else None)
        assert unit["completed_work"]["derived_kwh"] == (
            0.0 if unit["system"] == "plain_llm" else 140.0
        )


def test_receiving_acceptance_does_not_freeze_the_matrix_or_authorize_runs():
    manifest = json.loads((ROOT / "docs/i02/freeze-manifest.json").read_text())
    assert validate_manifest(manifest) == []
    assert manifest["run_matrix"]["total_runs"] == 300
    assert manifest["freeze"]["commit"] is None
    assert not any(item["status"] == "frozen" for item in manifest["items"])
    blockers = validate_manifest(manifest, require_ready=True)
    assert any("study-forecast: blocked" in blocker for blocker in blockers)
    assert any("pre-freeze-acceptance: blocked" in blocker for blocker in blockers)
    candidate = json.loads((ROOT / "docs/evidence/i01-offline-config-2026-11-02.json").read_text())
    approval = json.loads(
        (ROOT / "docs/evidence/i01-authorization-template-2026-11-02.json").read_text()
    )
    assert candidate["dispatch_authorized"] is False
    assert approval["status"] == "pending_fresh_user_approval"
    assert approval["approved_by"] is approval["approval_ref"] is None
