"""E02-c trained C/D units through P05 learned inference on the frozen EP-HAND1 bundle.

The models are small real tree/forest artifacts fitted on synthetic feature rows
(the P05 test construction), loaded through ``learned.load_verified``. They are
not Edison's development models and say nothing about policy quality.
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
    bundle_to_json,
    lf_sha256,
    load_bundle,
)
from dc_sustainability.policies import learned
from scripts import build_ep_hand1_bundle as build
from tests.experiments.test_runner import result, traces, write_bundle
from tests.policies.test_learned import _fit_tree

BUNDLE = build.OUT
SYSTEMS = ("decision_tree_c", "random_forest_d")
DT, RF = "d" * 64, "f" * 64  # identity-only pins for the settings test


@pytest.fixture(scope="module")
def artifacts(tmp_path_factory):
    folder = tmp_path_factory.mktemp("artifacts")
    loaded = {}
    for system in SYSTEMS:
        path, digest, _ = _fit_tree(folder, system)
        loaded[system] = learned.load_verified(path, expected_sha256=digest)
    return loaded


def inputs(artifacts, systems=SYSTEMS):
    return t.TrainedInputs({x: t.TrainedPolicy(artifacts[x]) for x in systems})


def config(artifacts, systems=SYSTEMS, bundle=BUNDLE, **pins):
    ep = load_bundle(bundle).episode
    digests = {x: artifacts[x].artifact_sha256 for x in SYSTEMS} | pins
    return RunConfig(
        "test",
        systems,
        ((ep.episode_id, str(bundle), lf_sha256(bundle)),),
        code_revision="test",
        trained=TrainedSettings(tuple((x, digests[x]) for x in systems)),
    )


def check_units(cfg, statuses, root, bundle=BUNDLE):
    ep = load_bundle(bundle).episode
    out = {}
    for st in statuses:
        records = traces(root, st.unit)
        assert [d.slot for d in records] == list(range(30))
        assert all(d.system == st.unit.system and d.model_call_count == 0 for d in records)
        res = result(root, st.unit)
        rep = r.replay_episode(ep, r.executed_starts(records, ep.episode_id), Q03_OPTION_B)
        assert rep.valid and r.compare_result(rep, res) == ()
        out[st.unit.system] = (records, res)
    return out


def test_c_and_d_run_through_p05_with_measured_artifact_hashes(tmp_path, artifacts):
    cfg = config(artifacts)
    assert cfg.identity()["trained"]["artifacts"] == {
        x: artifacts[x].artifact_sha256 for x in SYSTEMS
    }
    statuses = runner.run(cfg, tmp_path / "out", trained=inputs(artifacts))
    assert [st.status for st in statuses] == ["completed", "completed"]
    assert [st.unit.trial for st in statuses] == [None, None]
    units = check_units(cfg, statuses, tmp_path / "out" / cfg.run_id / "units")
    for records, res in units.values():
        assert res.completed_job_ids == ("J1", "J2")
        assert any(d.initial is not None for d in records)  # learned probabilities chose


def test_missing_forecasts_take_the_checked_greedy_a_fallback_stage(tmp_path, artifacts):
    _, withheld = write_bundle(tmp_path, withheld=True, name="withheld.json")
    cfg = config(artifacts, bundle=withheld)
    statuses = runner.run(cfg, tmp_path / "out", trained=inputs(artifacts))
    assert [st.status for st in statuses] == ["completed", "completed"]
    units = check_units(cfg, statuses, tmp_path / "out" / cfg.run_id / "units", withheld)
    for system, (records, res) in units.items():
        decided = [d for d in records if d.slot < 24 and d.fallback is not None]
        assert decided, system
        for d in decided:
            assert d.initial is None and d.fallback.check.status == "pass"
            assert d.explanation.summary.startswith("learned_fallback:")
            assert d.system == system  # the comparison identity is kept
        assert res.completed_job_ids == ("J1", "J2")


def test_policy_sees_only_the_visible_state_and_flat_context(tmp_path, artifacts, monkeypatch):
    seen, original = [], learned.propose

    def spy(state, context, **kwargs):
        seen.append((state, context, kwargs))
        return original(state, context, **kwargs)

    monkeypatch.setattr(learned, "propose", spy)
    cfg = config(artifacts, ("decision_tree_c",))
    runner.run(cfg, tmp_path / "out", trained=inputs(artifacts, ("decision_tree_c",)))
    bundle = load_bundle(BUNDLE)
    assert len(seen) == 24
    for state, context, kwargs in seen:
        assert isinstance(state, s.VisibleState) and context.representation == "flat"
        assert context.content.current_slot == state.current_slot
        s.assert_no_private_keys(context.content.to_jsonable())
        assert all(j.arrival_slot <= state.current_slot for j in state.waiting_jobs)
        assert kwargs["artifact"].artifact_sha256 == artifacts["decision_tree_c"].artifact_sha256
        assert kwargs["artifact"] is not artifacts["decision_tree_c"]  # boundary reload
        hours = kwargs["decision_time_utc"] - bundle.slot0_utc
        assert hours.total_seconds() == 3600 * state.current_slot  # trusted slot clock


def test_policy_failure_is_a_recorded_failed_output_not_a_substitute(
    tmp_path, artifacts, monkeypatch
):
    def broken(*args, **kwargs):
        raise RuntimeError("synthetic learned-policy failure")

    monkeypatch.setattr(learned, "propose", broken)
    cfg = config(artifacts, ("decision_tree_c",))
    [st] = runner.run(cfg, tmp_path / "out", trained=inputs(artifacts, ("decision_tree_c",)))
    assert st.status == "completed"
    root = tmp_path / "out" / cfg.run_id / "units"
    records = traces(root, st.unit)
    assert not any(d.executed_starts for d in records)
    assert all(d.final_status == "blocked" for d in records[:24])
    assert all(d.initial is None and d.fallback is None for d in records)
    errors = json.loads((root / st.unit.key / "policy_errors.json").read_text(encoding="utf-8"))
    assert len(errors) == 24 and "synthetic learned-policy failure" in errors[0]


def test_trained_systems_refuse_without_matching_inputs_before_writing(tmp_path, artifacts):
    out = tmp_path / "out"
    cfg = config(artifacts)
    with pytest.raises(NotImplementedError, match="decision_tree_c"):
        runner.run(cfg, out)
    with pytest.raises(ValueError, match="artifact differs"):
        runner.run(config(artifacts, random_forest_d="0" * 64), out, trained=inputs(artifacts))
    swapped = t.TrainedInputs(
        {
            "decision_tree_c": t.TrainedPolicy(artifacts["decision_tree_c"]),
            "random_forest_d": t.TrainedPolicy(artifacts["decision_tree_c"]),
        }
    )
    with pytest.raises(ValueError, match="holds a decision_tree_c artifact"):
        runner.run(cfg, out, trained=swapped)
    unverified = t.TrainedInputs(
        {x: t.TrainedPolicy(object()) for x in SYSTEMS}  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="verified P05 LearnedArtifact"):
        runner.run(cfg, out, trained=unverified)
    missing = inputs(artifacts, ("decision_tree_c",))
    with pytest.raises(ValueError, match="missing=.*random_forest_d"):
        runner.run(cfg, out, trained=missing)
    extra = t.TrainedInputs(
        inputs(artifacts).policies | {"unfrozen": t.TrainedPolicy(artifacts["decision_tree_c"])}
    )
    with pytest.raises(ValueError, match="extra=.*unfrozen"):
        runner.run(cfg, out, trained=extra)
    ab = RunConfig("test", ("greedy_a",), cfg.episodes, code_revision="test")
    with pytest.raises(ValueError, match="without trained systems"):
        runner.run(ab, out, trained=inputs(artifacts))
    assert not out.exists()


def test_trained_settings_are_required_validated_and_in_the_run_identity():
    episodes = ((("EP-HAND1", str(BUNDLE), lf_sha256(BUNDLE))),)
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
    pins = TrainedSettings((("decision_tree_c", DT), ("random_forest_d", RF)))
    a = RunConfig("test", SYSTEMS, episodes, trained=pins)
    other = RunConfig("test", SYSTEMS, episodes, trained=TrainedSettings(
        (("decision_tree_c", "e" * 64), ("random_forest_d", RF))))  # fmt: skip
    assert a.run_id != other.run_id  # a retrained model is a different run
    assert a.identity()["trained"] == {"artifacts": {"decision_tree_c": DT, "random_forest_d": RF}}
    assert "trained" not in RunConfig("test", ("greedy_a",), episodes).identity()


@pytest.mark.parametrize("system", ["decision_tree_c", "random_forest_d"])
def test_reloaded_model_missing_forecast_fallback_is_recorded_by_real_runner(tmp_path, system):
    from dataclasses import replace

    from dc_sustainability.policies import learned
    from tests.policies.test_learned import _fit_tree

    path, digest, _ = _fit_tree(tmp_path, system)
    artifact = learned.load_verified(path, expected_sha256=digest)
    original = load_bundle(BUNDLE)
    bundle = replace(original, forecasts_by_slot={})
    bundle_path = tmp_path / "withheld.json"
    bundle_path.write_text(bundle_to_json(bundle), encoding="utf-8")
    cfg = RunConfig(
        "p05-reloaded-withheld-test",
        (system,),
        ((bundle.episode.episode_id, str(bundle_path), lf_sha256(bundle_path)),),
        code_revision="synthetic-regression-not-study",
        trained=TrainedSettings(((system, digest),)),
    )
    policy = t.TrainedPolicy(artifact)
    [status] = runner.run(cfg, tmp_path / "out", trained=t.TrainedInputs({system: policy}))
    assert status.status == "completed"
    root = tmp_path / "out" / cfg.run_id / "units"
    records = traces(root, status.unit)
    fallback = [d for d in records if d.fallback is not None]
    assert fallback and all(d.system == system for d in records)
    assert all(d.fallback.check.status == "pass" for d in fallback)
    assert all(d.model_call_count == 0 for d in records)
    replay = r.replay_episode(
        bundle.episode, r.executed_starts(records, bundle.episode.episode_id), Q03_OPTION_B
    )
    assert replay.valid and r.compare_result(replay, result(root, status.unit)) == ()


def test_claimed_digest_cannot_mask_changed_artifact_bytes(tmp_path, artifacts):
    from dataclasses import replace

    bogus = tmp_path / "changed.joblib"
    bogus.write_bytes(b"not the pinned artifact")
    forged = replace(artifacts["decision_tree_c"], path=bogus)
    supplied = t.TrainedInputs({"decision_tree_c": t.TrainedPolicy(forged)})
    with pytest.raises(ValueError, match="digest mismatch"):
        runner.run(config(artifacts, ("decision_tree_c",)), tmp_path / "out", trained=supplied)
    assert not (tmp_path / "out").exists()


def test_runner_uses_verified_bytes_not_supplied_fitted_object(tmp_path, artifacts):
    from dataclasses import replace

    forged = replace(artifacts["decision_tree_c"], fitted=object())
    supplied = t.TrainedInputs({"decision_tree_c": t.TrainedPolicy(forged)})
    cfg = config(artifacts, ("decision_tree_c",))
    [status] = runner.run(cfg, tmp_path / "out", trained=supplied)
    assert status.status == "completed"
    assert result(tmp_path / "out" / cfg.run_id / "units", status.unit).completed_job_ids == (
        "J1",
        "J2",
    )
