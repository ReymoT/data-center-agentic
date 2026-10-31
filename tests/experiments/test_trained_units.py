"""E02-c trained C/D units on the frozen EP-HAND1 bundle with a synthetic classifier.

The classifier here is a test double, not Edison's P04 model: it only exercises the
runner, P03 schedule constructor, checker and controller path.
"""

import json

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import replay as r
from dc_sustainability.evaluation.validator import Q03_OPTION_B
from dc_sustainability.experiments import runner
from dc_sustainability.experiments import trained as t
from dc_sustainability.experiments.config import (
    RunConfig,
    TrainedSettings,
    lf_sha256,
    load_bundle,
)
from scripts import build_ep_hand1_bundle as build
from tests.experiments.test_runner import result, traces

BUNDLE = build.OUT
DT, RF = "d" * 64, "f" * 64


class EarlierIsLikelier:
    """Synthetic scores: earlier starts are likelier; not a trained model."""

    def selection_probability(self, job, start_slot):
        return 1 / (1 + start_slot)


def inputs(seen=None, classifier=EarlierIsLikelier, **hashes):
    def factory(state, context):
        if seen is not None:
            seen.append((state, context))
        return classifier()

    digests = {"decision_tree_c": DT, "random_forest_d": RF} | hashes
    return t.TrainedInputs(
        {system: t.TrainedPolicy(digest, factory) for system, digest in digests.items()}
    )


def config(systems=("decision_tree_c", "random_forest_d"), **changes):
    ep = load_bundle(BUNDLE).episode
    pins = {"decision_tree_c": DT, "random_forest_d": RF}
    return RunConfig(
        "test",
        systems,
        ((ep.episode_id, str(BUNDLE), lf_sha256(BUNDLE)),),
        code_revision="test",
        trained=TrainedSettings(tuple((x, pins[x]) for x in systems)),
        **changes,
    )


def test_trained_units_run_whole_episodes_through_the_controller(tmp_path):
    cfg = config()
    statuses = runner.run(cfg, tmp_path / "out", trained=inputs())
    assert [st.status for st in statuses] == ["completed", "completed"]
    assert [st.unit.trial for st in statuses] == [None, None]  # one run each, no trials
    ep = load_bundle(BUNDLE).episode
    root = tmp_path / "out" / cfg.run_id / "units"
    for st in statuses:
        records = traces(root, st.unit)
        assert [d.slot for d in records] == list(range(30))
        assert all(d.system == st.unit.system and d.model_call_count == 0 for d in records)
        res = result(root, st.unit)
        assert res.completed_job_ids == ("J1", "J2")
        rep = r.replay_episode(ep, r.executed_starts(records, ep.episode_id), Q03_OPTION_B)
        assert rep.valid and r.compare_result(rep, res) == ()


def test_classifier_sees_only_the_visible_state_and_flat_context(tmp_path):
    seen = []
    runner.run(config(("decision_tree_c",)), tmp_path / "out", trained=inputs(seen))
    assert seen and all(isinstance(state, s.VisibleState) for state, _ in seen)
    for state, context in seen:
        assert context.representation == "flat"
        assert context.content.current_slot == state.current_slot
        s.assert_no_private_keys(context.content.to_jsonable())
        assert all(j.arrival_slot <= state.current_slot for j in state.waiting_jobs)


@pytest.mark.parametrize("bad", ["raises", "out_of_range"])
def test_classifier_failure_is_a_recorded_failed_output_not_a_fallback(tmp_path, bad):
    class Broken:
        def selection_probability(self, job, start_slot):
            if bad == "raises":
                raise RuntimeError("synthetic classifier failure")
            return 1.5

    cfg = config(("decision_tree_c",))
    [st] = runner.run(cfg, tmp_path / "out", trained=inputs(classifier=Broken))
    assert st.status == "completed"
    root = tmp_path / "out" / cfg.run_id / "units"
    records = traces(root, st.unit)
    assert not any(d.executed_starts for d in records)  # nothing substitutes for the model
    # Slots 0-4 hold waiting jobs, so the classifier is asked and fails; from slot 5
    # the queue is empty and the no-op plan needs no classifier.
    assert [d.slot for d in records if d.final_status == "blocked"][:5] == [0, 1, 2, 3, 4]
    errors = json.loads((root / st.unit.key / "policy_errors.json").read_text(encoding="utf-8"))
    assert [e.split(":")[0] for e in errors] == [f"slot {i}" for i in range(5)]


def test_trained_systems_refuse_without_matching_inputs_before_writing(tmp_path):
    out = tmp_path / "out"
    cfg = config()
    with pytest.raises(NotImplementedError, match="decision_tree_c"):
        runner.run(cfg, out)
    with pytest.raises(ValueError, match="artifact differs"):
        runner.run(cfg, out, trained=inputs(random_forest_d="0" * 64))
    missing = t.TrainedInputs({"decision_tree_c": inputs().policies["decision_tree_c"]})
    with pytest.raises(ValueError, match="random_forest_d needs"):
        runner.run(cfg, out, trained=missing)
    ab = RunConfig("test", ("greedy_a",), cfg.episodes, code_revision="test")
    with pytest.raises(ValueError, match="without trained systems"):
        runner.run(ab, out, trained=inputs())
    assert not out.exists()


def test_trained_settings_are_required_validated_and_in_the_run_identity():
    episodes = config().episodes
    with pytest.raises(ValueError, match="trained settings"):
        RunConfig("test", ("decision_tree_c",), episodes)
    with pytest.raises(ValueError, match="trained settings"):
        RunConfig(
            "test", ("greedy_a",), episodes, trained=TrainedSettings((("decision_tree_c", DT),))
        )
    with pytest.raises(ValueError, match="exactly the listed"):
        RunConfig("test", ("decision_tree_c",), episodes, trained=TrainedSettings(
            (("decision_tree_c", DT), ("random_forest_d", RF))))  # fmt: skip
    with pytest.raises(ValueError, match="SHA256"):
        TrainedSettings((("decision_tree_c", "abc"),))
    with pytest.raises(ValueError, match="not a trained system"):
        TrainedSettings((("greedy_a", DT),))
    a, b = config(), config()
    other = RunConfig(**{**a.__dict__, "trained": TrainedSettings(
        (("decision_tree_c", "e" * 64), ("random_forest_d", RF)))})  # fmt: skip
    assert a.run_id == b.run_id != other.run_id  # a retrained model is a different run
    assert a.identity()["trained"] == {"artifacts": {"decision_tree_c": DT, "random_forest_d": RF}}
    assert "trained" not in RunConfig("test", ("greedy_a",), episodes).identity()
