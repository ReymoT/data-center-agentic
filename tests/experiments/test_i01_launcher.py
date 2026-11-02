"""Single-use authorization and fail-closed launcher controls; no live model calls."""

import copy
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
