"""E02-a runner tests: real simulator, checker, controller and trace store; no model calls.

Episodes are the hand fixture (J1 40 kW × 2, J2 30 kW × 2, deadline 6) with forecasts
issued at every slot, or none to make Greedy B fall back to checked Greedy A.
"""

import json
import re

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import replay as r
from dc_sustainability.evaluation.validator import Q03_OPTION_B
from dc_sustainability.experiments import __main__ as cli
from dc_sustainability.experiments import runner
from dc_sustainability.experiments.config import (
    EpisodeBundle,
    RunConfig,
    TrainedSettings,
    bundle_to_json,
    decision_id,
    lf_sha256,
    load_bundle,
)
from dc_sustainability.runtime import TraceStore
from tests.contracts import fixtures as f
from tests.simulator.test_core import episode


def write_bundle(tmp_path, *, withheld=False, name="ep.json"):
    ep = episode((f.jobs()["J1"], f.jobs()["J2"]), withheld=withheld)
    forecasts = (
        {}
        if withheld
        else {
            slot: tuple(x for x in f.forecasts(issued_slot=slot) if x.valid_slot >= slot)
            for slot in range(30)
        }
    )
    path = tmp_path / name
    path.write_text(bundle_to_json(EpisodeBundle(ep, f.SLOT0_UTC, forecasts)), encoding="utf-8")
    return ep, path


def config(path, ep, systems=("greedy_a", "greedy_b"), revision="test"):
    return RunConfig("test", systems, ((ep.episode_id, str(path), lf_sha256(path)),),
                     code_revision=revision)  # fmt: skip


def traces(root, unit):
    folder = root / unit.key / "traces"
    return sorted(
        (s.DecisionRecord.from_json(p.read_text(encoding="utf-8")) for p in folder.glob("*.json")),
        key=lambda d: d.slot,
    )


def result(root, unit):
    return s.EpisodeResult.from_json((root / unit.key / "result.json").read_text(encoding="utf-8"))


# ----------------------------------------------------------------- full episodes
@pytest.mark.parametrize("system", ["greedy_a", "greedy_b"])
def test_full_episode_runs_all_30_slots_through_the_controller(tmp_path, system):
    ep, path = write_bundle(tmp_path)
    cfg = config(path, ep, systems=(system,))
    [status] = runner.run(cfg, tmp_path / "out")
    assert status.status == "completed"
    root = tmp_path / "out" / cfg.run_id / "units"
    records = traces(root, status.unit)
    assert [d.slot for d in records] == list(range(30))
    assert all(d.system == system and d.run_id == cfg.run_id for d in records)
    assert all(d.model_call_count == 0 for d in records)
    completion = records[24:]
    assert all(d.final_status == "blocked" and not d.executed_starts for d in completion)
    res = result(root, status.unit)
    assert res.completed_job_ids == ("J1", "J2") and res.trial is None


def test_saved_traces_agree_with_the_independent_e01_replay(tmp_path):
    ep, path = write_bundle(tmp_path)
    cfg = config(path, ep)
    root = tmp_path / "out" / cfg.run_id / "units"
    for status in runner.run(cfg, tmp_path / "out"):
        records = traces(root, status.unit)
        rep = r.replay_episode(ep, r.executed_starts(records, ep.episode_id), Q03_OPTION_B)
        assert rep.valid, rep.findings
        assert r.compare_result(rep, result(root, status.unit)) == ()


def test_greedy_b_without_forecasts_keeps_its_identity_and_falls_back(tmp_path):
    ep, path = write_bundle(tmp_path, withheld=True)
    cfg = config(path, ep, systems=("greedy_b",))
    [status] = runner.run(cfg, tmp_path / "out")
    records = traces(tmp_path / "out" / cfg.run_id / "units", status.unit)
    assert status.status == "completed"
    assert all(d.system == "greedy_b" for d in records)
    assert any(d.fallback is not None for d in records[:24])


# ----------------------------------------------------------------- resume and retention
def test_rerun_skips_completed_units_without_touching_them(tmp_path):
    ep, path = write_bundle(tmp_path)
    cfg = config(path, ep)
    runner.run(cfg, tmp_path / "out")
    root = tmp_path / "out" / cfg.run_id / "units"
    before = {p: p.stat().st_mtime_ns for p in root.rglob("*.json")}
    statuses = runner.run(cfg, tmp_path / "out")
    assert [x.status for x in statuses] == ["completed", "completed"]
    assert {p: p.stat().st_mtime_ns for p in root.rglob("*.json")} == before


def test_interrupted_unit_needs_reconciliation_and_is_not_rerun(tmp_path):
    ep, path = write_bundle(tmp_path)
    cfg = config(path, ep, systems=("greedy_a",))
    [unit] = runner.units(cfg)
    folder = tmp_path / "out" / cfg.run_id / "units" / unit.key
    # A trace left behind with no final result, as after a crash mid-episode.
    store = TraceStore(folder / "traces")
    store.write(
        s.DecisionRecord(
            decision_id=decision_id(cfg, "greedy_a", ep.episode_id, None, 0),
            run_id=cfg.run_id,
            system="greedy_a",
            episode_id=ep.episode_id,
            slot=0,
            final_status="blocked",
            not_applicable_stages=("initial", "repaired", "fallback"),
        )
    )
    [status] = runner.run(cfg, tmp_path / "out")
    assert status.status == "needs_reconciliation"
    assert not (folder / "result.json").exists()
    assert len(list((folder / "traces").glob("*.json"))) == 1  # nothing added


def test_failed_unit_is_kept_and_counted_not_rerun(tmp_path, monkeypatch):
    ep, path = write_bundle(tmp_path)
    cfg = config(path, ep, systems=("greedy_a",))

    def broken(*args):
        raise RuntimeError("disk full")

    monkeypatch.setattr(runner, "_drive_episode", broken)
    [first] = runner.run(cfg, tmp_path / "out")
    assert (first.status, first.detail) == ("failed", "RuntimeError: disk full")
    monkeypatch.undo()
    [again] = runner.run(cfg, tmp_path / "out")
    assert again.status == "failed"  # retained, never silently replaced


def test_policy_exception_is_a_recorded_failed_decision(tmp_path, monkeypatch):
    ep, path = write_bundle(tmp_path)
    cfg = config(path, ep, systems=("greedy_a",))
    original = runner.propose

    def flaky(view, context, **kwargs):
        if view.current_slot == 0:
            raise ValueError("bad input")
        return original(view, context, **kwargs)

    monkeypatch.setattr(runner, "propose", flaky)
    [status] = runner.run(cfg, tmp_path / "out")
    folder = tmp_path / "out" / cfg.run_id / "units" / status.unit.key
    assert status.status == "completed"
    assert traces(folder.parent, status.unit)[0].final_status == "blocked"
    errors = json.loads((folder / "policy_errors.json").read_text(encoding="utf-8"))
    assert errors == ["slot 0: ValueError: bad input"]


# ----------------------------------------------------------------- config, IDs and custody
def test_unavailable_system_is_refused_before_anything_is_written(tmp_path):
    ep, path = write_bundle(tmp_path)
    cfg = RunConfig(
        "test",
        ("greedy_a", "decision_tree_c"),
        ((ep.episode_id, str(path), lf_sha256(path)),),
        trained=TrainedSettings((("decision_tree_c", "a" * 64),)),
    )
    with pytest.raises(NotImplementedError, match="decision_tree_c"):  # no trained inputs
        runner.run(cfg, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_changed_bundle_or_tampered_manifest_is_refused(tmp_path):
    ep, path = write_bundle(tmp_path)
    cfg = config(path, ep, systems=("greedy_a",))
    runner.run(cfg, tmp_path / "out")
    manifest = tmp_path / "out" / cfg.run_id / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["systems"] = ["greedy_b"]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="different run configuration"):
        runner.run(cfg, tmp_path / "out")
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")  # one more byte
    with pytest.raises(ValueError, match="changed since"):
        runner.run(cfg, tmp_path / "other")


def test_ids_are_stable_valid_and_tied_to_the_config(tmp_path):
    ep, path = write_bundle(tmp_path)
    a, b = config(path, ep), config(path, ep)
    assert a.run_id == b.run_id and a.config_hash == b.config_hash
    assert config(path, ep, revision="other").run_id != a.run_id
    ids = {decision_id(a, sys, ep.episode_id, t, slot)
           for sys in ("greedy_a", "greedy_b", "plain_llm") for t in (None, 0, 2)
           for slot in range(30)}  # fmt: skip
    assert len(ids) == 3 * 3 * 30
    assert all(re.fullmatch(r"DEC-[A-Za-z0-9][A-Za-z0-9_.:-]{0,59}", i) for i in ids)  # F02


def test_policy_sees_only_visible_state_and_context(tmp_path, monkeypatch):
    ep, path = write_bundle(tmp_path)
    cfg = config(path, ep, systems=("greedy_a",))
    seen = []
    original = runner.propose

    def spy(view, context, **kwargs):
        seen.append((type(view), type(context), set(kwargs)))
        return original(view, context, **kwargs)

    monkeypatch.setattr(runner, "propose", spy)
    runner.run(cfg, tmp_path / "out")
    assert len(seen) == 24  # decision slots only
    assert {x[:2] for x in seen} == {(s.VisibleState, s.Context)}
    assert {frozenset(x[2]) for x in seen} == {frozenset({"system", "decision_time_utc"})}


def test_bundle_round_trip(tmp_path):
    ep, path = write_bundle(tmp_path)
    bundle = load_bundle(path)
    assert bundle.episode == ep and bundle.slot0_utc == f.SLOT0_UTC
    assert sorted(bundle.forecasts_by_slot) == list(range(30))


def test_command_line_run_and_status(tmp_path, capsys):
    ep, path = write_bundle(tmp_path)
    run_file = tmp_path / "run.json"
    run_file.write_text(
        json.dumps({"name": "cli", "systems": ["greedy_a", "greedy_b"], "episodes": ["ep.json"]}),
        encoding="utf-8",
    )
    args = ["--config", str(run_file), "--out", str(tmp_path / "out")]
    assert cli.main(["status", *args]) == 1  # pending before running
    assert cli.main(["run", *args]) == 0
    assert cli.main(["status", *args]) == 0
    assert "completed" in capsys.readouterr().out
