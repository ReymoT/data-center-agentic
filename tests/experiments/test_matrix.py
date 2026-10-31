"""The planned 300-run held-out matrix, on 30 synthetic stand-in bundles.

The bundles are the public hand fixture relabeled as held-out cells; they are not
D04 episodes and carry no held-out data.
"""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.experiments import matrix
from dc_sustainability.experiments.config import (
    EpisodeBundle,
    ModelSettings,
    RunConfig,
    TrainedSettings,
    bundle_to_json,
)
from dc_sustainability.llm.plain import prompt_template_sha256
from tests.contracts import fixtures as f

DATES = [date(2022, m, 3) for m in (2, 4, 6, 8, 10, 12)]


def bundle(
    tmp_path,
    episode_id,
    day,
    scenario,
    *,
    withheld=False,
    split="held_out",
    leak=False,
    future_issue=False,
):
    base = f.private_episode().model_dump(mode="python")
    base.update(
        episode_id=episode_id,
        scenario_id=scenario,
        split=split,
        forecast_visibility="withheld" if withheld else "perfect_foresight",
    )
    for job in base["jobs"]:
        job.update(scenario_id=scenario, split=split)
    episode = s.PrivateEpisode.model_validate(base)
    slot0 = datetime.combine(day, time(7), tzinfo=timezone.utc)
    forecasts = {
        slot: () if withheld and not leak else tuple(
            x.model_copy(
                update={
                    "issued_at_utc": slot0
                    + timedelta(hours=slot + (1 if future_issue else 0))
                }
            )
            for x in f.forecasts(issued_slot=slot) if x.valid_slot >= slot)
        for slot in range(30)
    }  # fmt: skip
    path = tmp_path / f"{episode_id}.json"
    path.write_text(bundle_to_json(EpisodeBundle(episode, slot0, forecasts)), encoding="utf-8")
    return path


def planned(tmp_path):
    paths = []
    for d, day in enumerate(DATES):
        for scenario in matrix.SCENARIOS:
            paths.append(bundle(tmp_path, f"EP-HO{d}{scenario}", day, scenario))
        paths.append(bundle(tmp_path, f"EP-HO{d}missing", day, "normal", withheld=True))
    return paths


def model(**changes):
    values = dict(
        seeds=((0, 101), (1, 102), (2, 103)),
        decision_seconds=480,
        max_total_attempts=8640,
        deployment={"max_run_attempts": 72, "runtime_version": "0.40.5"},
        plain_prompt_sha256=prompt_template_sha256(),
        agent_renderer_ref="dc_sustainability.agent.renderers",
    )
    return ModelSettings(**(values | changes))


TRAINED = TrainedSettings((("decision_tree_c", "d" * 64), ("random_forest_d", "f" * 64)))


def build(paths, **changes):
    return matrix.build(
        "held-out-matrix",
        paths,
        model=changes.get("model", model()),
        trained=TRAINED,
        code_revision="0" * 40,
        lock_sha256="1" * 64,
    )


def test_the_planned_matrix_is_300_runs_and_passes(tmp_path):
    config = build(planned(tmp_path))
    assert matrix.check(config) == []
    units = matrix.runner.units(config)
    assert len(units) == 300
    assert sum(u.system == "agent" for u in units) == sum(u.system == "plain_llm" for u in units)
    assert {u.trial for u in units if u.system == "agent"} == {0, 1, 2}
    identity = config.identity()
    assert identity["model"]["max_total_attempts"] == 8640 and "trained" in identity
    assert len({e for e, _, _ in config.episodes}) == 30


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda p, t: p[:-1], "29 episodes"),
        (lambda p, t: p[:-1] + [bundle(t, "EP-X1", DATES[0], "normal")], "6 dates x 4"),
        (lambda p, t: [bundle(t, "EP-X1", DATES[0], "normal", split="development")] + p[1:],
         "not held_out"),
        (lambda p, t: p[:4] + [bundle(t, "EP-X1", DATES[0], "spike", withheld=True)] + p[5:],
         "missing-forecast"),
        (lambda p, t: p[:4] + [bundle(t, "EP-X1", DATES[0], "normal", withheld=True, leak=True)]
         + p[5:], "exposes forecasts"),
        (lambda p, t: [bundle(t, "EP-X1", DATES[0], "infeasible", future_issue=True)]
         + p[1:], "after its decision time"),
    ],
)  # fmt: skip
def test_episode_design_deviations_are_refused(tmp_path, change, message):
    paths = change(planned(tmp_path), tmp_path / "x")
    assert any(message in problem for problem in matrix.check(build(paths)))


@pytest.fixture(autouse=True)
def _stand_in_folder(tmp_path):
    (tmp_path / "x").mkdir()


@pytest.mark.parametrize(
    "settings, message",
    [
        (model(max_total_attempts=8000), "8,640"),
        (model(deployment={"max_run_attempts": 18}), "trim agent"),
    ],
)
def test_budget_and_ledger_reductions_are_refused(tmp_path, settings, message):
    assert any(message in p for p in matrix.check(build(planned(tmp_path), model=settings)))


def test_systems_trials_and_changed_bundles_are_refused(tmp_path):
    paths = planned(tmp_path)
    good = build(paths)
    fewer = RunConfig(**{**good.__dict__, "model_trials": (0, 1), "model": model(
        seeds=((0, 101), (1, 102)))})  # fmt: skip
    problems = matrix.check(fewer)
    assert any("0, 1, 2" in p for p in problems) and any("runs; the plan" in p for p in problems)
    no_d = RunConfig(**{**good.__dict__, "systems": matrix.SYSTEMS[:3] + matrix.SYSTEMS[4:],
                        "trained": TrainedSettings((("decision_tree_c", "d" * 64),))})  # fmt: skip
    assert any("systems must be exactly" in p for p in matrix.check(no_d))
    paths[0].write_text(paths[0].read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert any("bundle changed" in p for p in matrix.check(good))
