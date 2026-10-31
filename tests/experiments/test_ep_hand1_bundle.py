"""The frozen public EP-HAND1 bundle: generated, faithful to the fixture and runnable.

The model test uses the synthetic loopback responder from test_model_units; it is not
inference and says nothing about model quality.
"""

import pytest

from dc_sustainability.evaluation import replay as r
from dc_sustainability.evaluation.validator import Q03_OPTION_B
from dc_sustainability.experiments import runner
from dc_sustainability.experiments.config import RunConfig, lf_sha256, load_bundle
from scripts import build_ep_hand1_bundle as build
from tests.contracts import fixtures as f
from tests.experiments.test_model_units import inputs, model_config
from tests.experiments.test_model_units import model as model  # noqa: F401
from tests.experiments.test_runner import result, traces
from tests.llm.test_ollama_provider import server as server  # noqa: F401

BUNDLE = build.OUT


def test_committed_bundle_matches_the_generator():
    assert BUNDLE.read_text(encoding="utf-8") == build.build(), "run build_ep_hand1_bundle.py"


def test_bundle_is_the_public_hand_example_with_only_issued_forecasts():
    bundle = load_bundle(BUNDLE)
    assert bundle.episode == f.private_episode()
    assert bundle.episode.split == "development" and bundle.slot0_utc == f.SLOT0_UTC
    assert sorted(bundle.forecasts_by_slot) == list(range(30))
    for slot, facts in bundle.forecasts_by_slot.items():
        assert all(x.valid_slot >= slot for x in facts)  # nothing from the past
        assert {x.issued_at_utc for x in facts} <= {f.forecasts(issued_slot=slot)[0].issued_at_utc}


def test_deterministic_units_run_and_replay_on_the_bundle(tmp_path):
    ep = load_bundle(BUNDLE).episode
    config = RunConfig(
        "ep-hand1",
        ("greedy_a", "greedy_b"),
        ((ep.episode_id, str(BUNDLE), lf_sha256(BUNDLE)),),
        code_revision="test",
    )
    statuses = runner.run(config, tmp_path / "out")
    assert [st.status for st in statuses] == ["completed", "completed"]
    root = tmp_path / "out" / config.run_id / "units"
    for st in statuses:
        records = traces(root, st.unit)
        assert [d.slot for d in records] == list(range(30))
        res = result(root, st.unit)
        assert res.completed_job_ids == ("J1", "J2")
        assert res.deadline_missed_job_ids == ("J3",)  # the intentionally impossible job
        rep = r.replay_episode(ep, r.executed_starts(records, ep.episode_id), Q03_OPTION_B)
        assert rep.valid and r.compare_result(rep, res) == ()


def test_plain_and_agent_units_run_on_the_same_bundle(tmp_path, model):
    ep = load_bundle(BUNDLE).episode
    config = model_config(BUNDLE, ep, model)
    statuses = runner.run(config, tmp_path / "out", inputs(model))
    assert [st.status for st in statuses] == ["completed", "completed"]
    root = tmp_path / "out" / config.run_id / "units"
    for st in statuses:
        records = traces(root, st.unit)
        assert [d.slot for d in records] == list(range(30))
        assert records[0].model_call_count >= 1  # slot 0 has waiting jobs
    assert len(model.requests) == sum(
        d.model_call_count for st in statuses for d in traces(root, st.unit)
    )


@pytest.mark.parametrize("overlap", [False, True])
def test_receiving_bounds_admit_both_units_within_24_requests(tmp_path, model, overlap):
    """The agreed EP-HAND1 budget admits both units, including the repair path."""
    model.overlap = overlap
    ep = load_bundle(BUNDLE).episode
    config = model_config(BUNDLE, ep, model, max_total=24, max_run_attempts=18)
    plain, agent = runner.run(config, tmp_path / "out", inputs(model, max_run_attempts=18))
    assert (plain.status, agent.status) == ("completed", "completed"), agent.detail
    root = tmp_path / "out" / config.run_id / "units"
    calls = {
        st.unit.system: sum(d.model_call_count for d in traces(root, st.unit))
        for st in (plain, agent)
    }
    assert calls["plain_llm"] <= 5 and calls["agent"] <= 18
    assert len(model.requests) == sum(calls.values()) <= 24


def test_a_smaller_total_still_refuses_the_agent_unit(tmp_path, model):
    """The ledger-aware admission rule does not weaken the global run budget."""
    ep = load_bundle(BUNDLE).episode
    config = model_config(BUNDLE, ep, model, max_total=20, max_run_attempts=18)
    plain, agent = runner.run(config, tmp_path / "out", inputs(model, max_run_attempts=18))
    assert plain.status == "completed"
    assert agent.status == "pending" and "unit may need 18" in agent.detail
