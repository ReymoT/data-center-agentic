"""Single-use authorization and fail-closed launcher controls; no live model calls."""

import copy
import json
import threading
from types import SimpleNamespace

import pytest

from dc_sustainability.llm.provider import Deployment, OllamaProvider
from scripts import run_i01_public_receiving as launch


def approval():
    candidate = {
        "candidate_config_hash": "c" * 64,
        "proposed_outer_controls_not_enforced_by_identity_alone": {"test": "SYNTHETIC ONLY"},
    }
    receipt = {
        "status": "approved",  # synthetic unit-test receipt, never a live approval
        "approved_by": "MattyAnd",
        "candidate_config_hash": "c" * 64,
        "bounds": candidate["proposed_outer_controls_not_enforced_by_identity_alone"],
        "single_use_id": "synthetic-test-not-real-authorization",
        "approval_ref": "SYNTHETIC TEST ONLY",
        "readiness_sha256": "r" * 64,
        "launcher_sha256": "l" * 64,
    }
    return receipt, candidate


@pytest.mark.parametrize(
    "field",
    [
        "status",
        "approved_by",
        "candidate_config_hash",
        "bounds",
        "approval_ref",
        "single_use_id",
        "readiness_sha256",
        "launcher_sha256",
    ],
)
def test_fresh_authorization_binds_every_required_input(field):
    receipt, candidate = approval()
    assert (
        launch.validate_authorization(receipt, candidate, "r" * 64, "l" * 64)
        == "SYNTHETIC TEST ONLY"
    )
    changed = copy.deepcopy(receipt)
    changed[field] = None
    with pytest.raises(RuntimeError, match="fresh approval"):
        launch.validate_authorization(changed, candidate, "r" * 64, "l" * 64)


def test_single_use_identity_cannot_be_consumed_again(tmp_path):
    receipt, _ = approval()
    launch.consume_authorization(receipt, "c" * 64, tmp_path / "consumed")
    with pytest.raises(FileExistsError):
        launch.consume_authorization(dict(receipt), "d" * 64, tmp_path / "consumed")


def provider(tmp_path):
    value = launch.StrictProvider(
        Deployment("http://127.0.0.1:1", "test", "a" * 64, 18, 1024, 1000, "test"),
        count_prompt_tokens=lambda request: 1,
        emergency_dir=tmp_path,
    )
    return value


def test_plain_six_cap_blocks_before_parent_dispatch(tmp_path, monkeypatch):
    value = provider(tmp_path)
    value._attempts = [None] * 6

    def forbidden(*args, **kwargs):
        raise AssertionError("must not dispatch")

    monkeypatch.setattr(OllamaProvider, "generate", forbidden)
    with pytest.raises(launch.StopRun, match="ceiling"):
        value.generate(system="plain_llm")


def test_uncertain_attempt_is_saved_then_stops_without_repair(tmp_path, monkeypatch):
    value = provider(tmp_path)
    attempt = SimpleNamespace(
        error=None, uncertain_outcome=True, client_trace_id="test", system="agent", slot=0
    )
    saved = []
    monkeypatch.setattr(OllamaProvider, "generate", lambda *args, **kwargs: attempt)
    monkeypatch.setattr(launch, "save_private_attempt", lambda path, item: saved.append(item))
    with pytest.raises(launch.StopRun, match="uncertain"):
        value.generate(system="agent")
    assert saved == [attempt]


def test_watchdog_terminates_only_its_retained_process():
    stopped = []
    owned = SimpleNamespace(poll=lambda: None, terminate=lambda: stopped.append("owned"))
    event = threading.Event()
    launch.terminate_owned_at_deadline(owned, event)
    assert event.is_set() and stopped == ["owned"]


@pytest.mark.parametrize("stale_code", [False, True])
def test_code_and_missing_approval_stop_before_any_runtime_start(tmp_path, monkeypatch, stale_code):
    fake = tmp_path / "input-file"
    fake.write_text("test-only placeholder; never loaded")
    out = tmp_path / "must-not-exist"
    root = launch.ROOT
    # Isolate the authorization gate from historical execution snapshots. This
    # temporary synthetic readiness is never an approved receipt or live evidence.
    ready = json.loads((root / "docs/evidence/i01-unified-readiness-2026-11-02.json").read_text())
    ready["execution_file_lf_sha256"] = {
        rel: launch.lf_sha256(root / rel) for rel in ready["execution_file_lf_sha256"]
    }
    if stale_code:
        ready["execution_file_lf_sha256"]["dc_sustainability/training/train.py"] = "0" * 64
    readiness_path = tmp_path / "synthetic-readiness.json"
    readiness_path.write_text(json.dumps(ready), encoding="utf-8")
    argv = [
        "launcher",
        "--runtime",
        str(fake),
        "--models",
        str(tmp_path),
        "--tokenizer",
        str(fake),
        "--tokenizer-packages",
        str(tmp_path),
        "--accepted-inventory",
        str(fake),
        "--candidate",
        str(root / "docs/evidence/i01-offline-config-2026-11-02.json"),
        "--readiness",
        str(readiness_path),
        "--tree",
        str(fake),
        "--forest",
        str(fake),
        "--out",
        str(out),
    ]
    monkeypatch.setattr(launch.sys, "argv", argv)
    monkeypatch.setattr(launch, "command", lambda *args: "")

    def forbidden(*args, **kwargs):
        raise AssertionError("must not start runtime without approval")

    monkeypatch.setattr(launch.subprocess, "Popen", forbidden)
    with pytest.raises(
        RuntimeError, match="execution code changed" if stale_code else "fresh Matty"
    ):
        launch.main()
    assert not out.exists()


def test_saved_result_must_match_independent_replay_before_success(tmp_path):
    import json

    from dc_sustainability.experiments import runner
    from tests.experiments.test_runner import config, write_bundle

    episode, path = write_bundle(tmp_path)
    cfg = config(path, episode, systems=("greedy_a",))
    statuses = runner.run(cfg, tmp_path / "runs")
    assert launch.verify_units(cfg, tmp_path / "runs", statuses, episode)[0]["traces"] == 30
    result_path = tmp_path / "runs" / cfg.run_id / "units" / statuses[0].unit.key / "result.json"
    data = json.loads(result_path.read_text())
    data["completed_job_ids"] = []
    result_path.write_text(json.dumps(data))
    with pytest.raises(launch.StopRun, match="replay"):
        launch.verify_units(cfg, tmp_path / "runs", statuses, episode)


def test_committed_template_is_unapproved_and_matches_exact_text_pins():
    import json

    from dc_sustainability.experiments.config import lf_sha256

    root = launch.ROOT
    template = json.loads(
        (root / "docs/evidence/i01-authorization-template-2026-11-02.json").read_text()
    )
    candidate = json.loads((root / "docs/evidence/i01-offline-config-2026-11-02.json").read_text())
    assert template["status"] == "pending_fresh_user_approval"
    assert template["approved_by"] is None and template["approval_ref"] is None
    assert template["launcher_sha256"] == lf_sha256(root / "scripts/run_i01_public_receiving.py")
    assert template["readiness_sha256"] == lf_sha256(
        root / "docs/evidence/i01-unified-readiness-2026-11-02.json"
    )
    with pytest.raises(RuntimeError, match="fresh approval"):
        launch.validate_authorization(
            template, candidate, template["readiness_sha256"], template["launcher_sha256"]
        )
