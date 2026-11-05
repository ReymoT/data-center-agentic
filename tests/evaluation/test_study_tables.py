"""E06 study table tests: hand episodes through scoring, pairing and reporting.

Each episode is the hand fixture under another ID. ``good`` runs follow the hand schedule
J1@0, J2@2, with an abstention from impossible J3, and emit 54.5 kg. ``late`` runs start
J1@2, J2@4 and emit 48.4 kg. ``idle`` runs plan nothing and complete no jobs.
"""

import ast
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.evaluation import paired
from dc_sustainability.evaluation import study_tables as t
from dc_sustainability.evaluation.validator import Q03_OPTION_B
from scripts import build_study_tables as cli
from tests.contracts import fixtures as f

END = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS
TRIALS = {"plain_llm": (0, 1), "agent": (0, 1), "greedy_a": (None,), "greedy_b": (None,)}
FAST = paired.Resampling(resamples=500)
SLOT0 = datetime(2022, 1, 15, 7, tzinfo=timezone.utc)
SCHEDULES = {
    "good": {
        0: [("J1", 0), ("J2", 2)],
        1: [("J2", 2)],
        2: [("J2", 2)],
    },
    "late": {
        0: [("J1", 2), ("J2", 4)],
        1: [("J1", 2), ("J2", 4)],
        2: [("J1", 2), ("J2", 4)],
        3: [("J2", 4)],
        4: [("J2", 4)],
    },
}


def plan(episode_id, slot, starts=(), abstain=()):
    return s.Plan(
        episode_id=episode_id,
        slot=slot,
        state_version=slot,
        starts=tuple(s.PlannedStart(job_id=j, start_slot=x) for j, x in starts),
        abstentions=tuple(
            s.Abstention(job_id=j, reason="infeasible_deadline", constraint_ids=("CON-DL-J3",))
            for j in abstain
        ),
        status="proposed",
    )


def record(episode_id, slot, system, trial, p=None, passed=True, **fields):
    stage = None if p is None else s.StageRecord(plan=p, check=f.check_pass(p) if passed else None)
    options = {"final_status": "blocked"}
    if stage is not None and passed:
        options = {
            "final_status": "executed",
            "execution_check": stage.check,
            "executed_starts": tuple(
                s.ApprovedStart(job_id=x.job_id, start_slot=x.start_slot) for x in p.current_starts
            ),
        }
    return s.DecisionRecord(
        decision_id=f"DEC-{episode_id[3:]}-{slot:02d}",
        system=system,
        run_id="RUN-HAND",
        episode_id=episode_id,
        trial=trial,
        slot=slot,
        initial=stage,
        not_applicable_stages=("repaired", "fallback"),
        **options,
        **fields,
    )


def run(episode_id, system, trial=None, kind="good", **fields):
    records = []
    for slot in range(END):
        if slot >= s.PROPOSED_DECISION_SLOTS:
            records.append(record(episode_id, slot, system, trial))
        elif kind == "idle":
            waiting = slot in (0, 1, 2, 3, 4)
            records.append(
                record(episode_id, slot, system, trial, plan(episode_id, slot), not waiting)
            )
        else:
            schedule = SCHEDULES[kind]
            if slot in schedule:
                p = plan(episode_id, slot, schedule[slot], ["J3"] if slot == 4 else ())
            elif slot == 4:
                p = plan(episode_id, slot, abstain=["J3"])
            else:
                p = plan(episode_id, slot)
            records.append(record(episode_id, slot, system, trial, p, **fields))
    return records


def planned_item(episode_id, scenario="normal", date="2022-01-15", visibility="persistence"):
    episode = f.private_episode().model_copy(
        update={
            "episode_id": episode_id,
            "scenario_id": scenario,
            "forecast_visibility": visibility,
        }
    )
    return t.PlannedEpisode(episode, date, {})


def plan_of(*items):
    return {item.episode.episode_id: item for item in items}


PLANNED = plan_of(
    planned_item("EP-A", date="2022-01-15"),
    planned_item("EP-B", "spike", date="2022-02-15"),
    planned_item("EP-W", date="2022-01-15", visibility="withheld"),
)


def scored(runs, planned=PLANNED):
    return t.score_runs(runs, planned, Q03_OPTION_B)


def pair_runs(plain="good", agent="good", episodes=("EP-A", "EP-B", "EP-W")):
    return [
        run(e, system, trial, kind)
        for e in episodes
        for system, kind in (("plain_llm", plain), ("agent", agent))
        for trial in (0, 1)
    ]


def rows(result, metric, cohort="core"):
    return next(r for r in result if r["metric"] == metric and r["cohort"] == cohort)


def paired_rows(runs):
    return t.paired_rows(scored(runs), PLANNED, "plain_llm", "agent", TRIALS, FAST)


def test_planned_date_is_the_phoenix_date_of_slot_zero():
    item = t.planned_episode(f.private_episode(), SLOT0, {})
    assert item.date == "2022-01-15"
    early = datetime(2022, 1, 15, 3, tzinfo=timezone.utc)
    assert t.planned_episode(f.private_episode(), early, {}).date == "2022-01-14"


def test_only_withheld_forecast_episodes_leave_the_core_cohort():
    assert PLANNED["EP-A"].cohort == "core"
    assert PLANNED["EP-W"].cohort == "withheld"


def test_observations_read_the_metric_and_keep_labels():
    result = t.observations(scored([run("EP-A", "greedy_a")]), PLANNED, "completed_jobs", "core")
    assert [(o.system, o.episode_id, o.scenario, o.date, o.value) for o in result] == [
        ("greedy_a", "EP-A", "normal", "2022-01-15", 2)
    ]


def test_withheld_runs_stay_out_of_core_observations():
    result = scored([run("EP-W", "greedy_a")])
    assert t.observations(result, PLANNED, "completed_jobs", "core") == ()
    assert len(t.observations(result, PLANNED, "completed_jobs", "withheld")) == 1


def test_core_and_withheld_are_reported_apart():
    result = paired_rows(pair_runs(plain="idle"))
    core, withheld = rows(result, "completed_jobs"), rows(result, "completed_jobs", "withheld")
    assert core["by_episode"]["episodes"] == 2
    assert withheld["by_episode"]["episodes"] == 1
    assert core["by_episode"]["estimate"] == 2.0  # candidate minus baseline


def test_a_planned_run_that_is_absent_stays_counted_as_missing():
    result = paired_rows(pair_runs(plain="idle", episodes=("EP-A", "EP-W")))
    row = rows(result, "completed_jobs")
    assert row["by_episode"]["episodes"] == 1
    assert row["excluded_by_reason"] == {"run_missing": 1}


def test_every_paired_row_has_episode_and_date_intervals():
    row = rows(paired_rows(pair_runs(plain="idle")), "decision_accuracy")
    assert row["by_episode"]["units"] == 2
    assert row["by_date"]["by"] == "date"
    assert row["by_date"]["units"] == 2


def test_both_unsafe_measures_are_reported_at_every_stage():
    names = {r["metric"] for r in paired_rows(pair_runs())}
    for stage in ("initial", "repaired", "fallback", "final"):
        assert f"unsafe_rate_{stage}" in names
        assert f"unsafe_rate_without_omissions_{stage}" in names


def test_omission_only_plans_separate_the_two_unsafe_measures():
    result = paired_rows(pair_runs(plain="idle"))
    broad = rows(result, "unsafe_rate_final")["by_episode"]["estimate"]
    narrow = rows(result, "unsafe_rate_without_omissions_final")["by_episode"]["estimate"]
    assert (broad, narrow) == (-1.0, 0.0)


def test_raw_emissions_are_never_paired_across_different_work():
    result = paired_rows(pair_runs(plain="idle"))
    assert "completed_job_emissions_kg" not in {r["metric"] for r in result}


def test_scenario_summaries_still_describe_emissions():
    result = t.scenario_rows(scored(pair_runs()), PLANNED)
    row = next(
        r
        for r in result
        if r["metric"] == "completed_job_emissions_kg"
        and (r["cohort"], r["system"], r["scenario"]) == ("core", "agent", "normal")
    )
    assert row["mean"] == pytest.approx(54.5)
    assert (row["runs"], row["missing"]) == (2, 0)


def savings(result):
    return t.savings_rows(result, PLANNED, "plain_llm", "agent", TRIALS, Q03_OPTION_B, FAST)


def test_savings_use_the_equal_work_rule_with_the_hand_value():
    runs = pair_runs(plain="good", agent="late")
    row = rows(savings(scored(runs)), "savings_kg")
    assert row["by_episode"]["estimate"] == pytest.approx(6.1)
    assert row["by_episode"]["episodes"] == 2


def test_different_work_blocks_savings_rather_than_reporting_a_difference():
    row = rows(savings(scored(pair_runs(plain="idle"))), "savings_kg")
    assert row["by_episode"]["estimate"] is None
    assert row["excluded_by_reason"] == {"comparison_blocked": 2}


def test_no_comparable_runs_at_all_is_counted_not_zero():
    row = rows(savings(scored([run("EP-A", "greedy_a")])), "savings_kg")
    assert row["by_episode"] is None
    assert row["excluded_by_reason"] == {"run_missing": 2}


def test_unequal_trial_savings_are_refused_until_the_rule_is_agreed():
    with pytest.raises(ValueError, match="unequal-trial"):
        t.savings_rows(scored([]), PLANNED, "greedy_a", "agent", TRIALS, Q03_OPTION_B, FAST)


def test_forecast_ties_read_greedy_b_runs_by_cohort():
    runs = [run("EP-A", "greedy_b"), run("EP-W", "greedy_b"), run("EP-B", "greedy_a")]
    result = t.tie_rows(scored(runs), PLANNED, Q03_OPTION_B)
    assert [(r["cohort"], r["runs"]) for r in result] == [("core", 1), ("withheld", 1)]
    assert result[0]["comparable"] == 0  # these planned episodes supply no forecasts
    assert result[0]["tie_rate"] is None


def test_a_flat_forecast_shows_as_ties_in_the_report_rows():
    flat = {
        slot: tuple(
            fact.model_copy(update={"value": 400.0})
            for fact in f.forecasts(slot)
            if fact.valid_slot >= slot
        )
        for slot in range(24)
    }
    item = planned_item("EP-A")
    planned = plan_of(t.PlannedEpisode(item.episode, item.date, flat))
    result = t.tie_rows(scored([run("EP-A", "greedy_b")], planned), planned, Q03_OPTION_B)
    assert result[0]["tied"] > 0
    assert result[0]["tie_rate"] == 1.0


def test_a_saved_run_e03_refuses_is_listed_and_not_dropped():
    broken = run("EP-A", "greedy_a")[:-1]
    result = scored([broken])
    assert not result.runs
    assert "exactly one decision record" in result.unscored[("greedy_a", "EP-A", None)]


@pytest.mark.parametrize(
    "runs, message",
    [
        ([[]], "no decision records"),
        ([run("EP-Z", "greedy_a")], "not a planned episode"),
        ([run("EP-A", "greedy_a"), run("EP-A", "greedy_a")], "more than one saved run"),
    ],
)
def test_defective_run_sets_are_refused(runs, message):
    with pytest.raises(ValueError, match=message):
        scored(runs)


def report(runs=None, planned=PLANNED):
    return t.study_report(
        pair_runs(plain="idle") if runs is None else runs,
        planned,
        TRIALS,
        Q03_OPTION_B,
        settings=FAST,
    )


def test_the_report_states_its_split_and_that_it_is_not_frozen():
    result = report()
    assert (result["split"], result["status"]) == ("development", "not_a_frozen_result")
    assert result["protocol"] == Q03_OPTION_B.name
    assert result["planned_episodes"] == {"core": 2, "withheld": 1}


def test_default_settings_are_the_recorded_analysis_settings():
    assert paired.Resampling() == paired.Resampling(10_000, 0.95, 20261113)


def test_a_report_cannot_mix_development_and_held_out_episodes():
    other = planned_item("EP-H")
    held = t.PlannedEpisode(other.episode.model_copy(update={"split": "held_out"}), other.date, {})
    with pytest.raises(ValueError, match="mix"):
        report([], plan_of(planned_item("EP-A"), held))


def test_a_report_needs_planned_episodes():
    with pytest.raises(ValueError, match="mix"):
        report([], {})


def test_the_report_is_json_ready_and_lists_unscored_runs():
    runs = [*pair_runs(plain="idle"), run("EP-A", "greedy_a")[:-1]]
    result = report(runs)
    assert json.loads(json.dumps(result)) == result
    assert result["unscored_runs"][0]["system"] == "greedy_a"


def test_the_script_skips_unfinished_units_and_never_overwrites(tmp_path):
    finished = tmp_path / "unit"
    (finished / "traces").mkdir(parents=True)
    (finished / "result.json").write_text("{}", encoding="utf-8")
    for index, item in enumerate(run("EP-A", "greedy_a")):
        (finished / "traces" / f"{index}.json").write_text(item.to_json(), encoding="utf-8")
    partial = tmp_path / "partial"
    (partial / "traces").mkdir(parents=True)
    assert len(cli.load_unit(finished)) == END
    assert cli.load_unit(partial) is None

    bundle = Path(__file__).resolve().parents[2] / "docs/evidence/ep-hand1-episode-bundle.json"
    out = tmp_path / "report.json"
    arguments = ["--bundle", str(bundle), "--unit-dir", str(partial), "--out", str(out)]
    assert cli.main(arguments) == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert (written["scored_runs"], written["units_without_result"]) == (0, 1)
    with pytest.raises(FileExistsError):
        cli.main(arguments)


def test_the_module_stays_independent_of_policies_and_production_checks():
    tree = ast.parse(Path(t.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(
        name.startswith(
            (
                "dc_sustainability.policies",
                "dc_sustainability.verification",
                "dc_sustainability.simulator",
                "dc_sustainability.experiments",
            )
        )
        for name in imported
    )
