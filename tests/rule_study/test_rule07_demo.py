"""RULE-07 demo driver: reuses the merged RULE-02 pipeline, expected vs observed, disk replay."""

import json
import subprocess
import sys

import pytest

from dc_sustainability import rule_demo as d
from dc_sustainability.rule_study import cases as c
from dc_sustainability.rule_study import records as r
from dc_sustainability.rule_study import runner as merged_runner
from tests.rule_study.helpers import REPO_ROOT, TEST_ONLY_COMMIT


def run_main(args, capsys):
    code = d.main(args, code_commit=TEST_ONLY_COMMIT)
    return code, capsys.readouterr()


@pytest.fixture(scope="module")
def all_runs(tmp_path_factory):
    out = tmp_path_factory.mktemp("rule07") / "run"
    runs = [d.run_scenario(n, "rules-v1", out, code_commit=TEST_ONLY_COMMIT) for n in d.SCENARIOS]
    return out, {sr.scenario: sr for sr in runs}


def starts_of(sr):
    return {j: int(k) for k, v in sr.observed["executed_starts_by_slot"].items() for j in v}


# ------------------------------------------------------------------ reuse of the merged code
def test_driver_reuses_the_merged_pipeline_without_redefining_it():
    assert d.run_case is merged_runner.run_case
    assert d.RuleStudyRunner is merged_runner.RuleStudyRunner
    assert d.AUTHORED_CASES is c.AUTHORED_CASES
    for name in ("decide", "propose_rules_v1", "recheck_schedule", "check_schedule"):
        assert not hasattr(d, name)


def test_real_scheduler_checker_and_fallback_are_invoked(tmp_path, monkeypatch):
    calls = {"check": 0, "recheck": 0, "rules": 0, "greedy": []}
    real_check, real_recheck = merged_runner.check_schedule, merged_runner.recheck_schedule
    real_rules, real_greedy = merged_runner.sch.propose_rules_v1, merged_runner.greedy.propose

    def check(*a, **k):
        calls["check"] += 1
        return real_check(*a, **k)

    def recheck(*a, **k):
        calls["recheck"] += 1
        return real_recheck(*a, **k)

    def rules(*a, **k):
        calls["rules"] += 1
        return real_rules(*a, **k)

    def greedy(state, context, *, system, **k):
        calls["greedy"].append(system)
        return real_greedy(state, context, system=system, **k)

    monkeypatch.setattr(merged_runner, "check_schedule", check)
    monkeypatch.setattr(merged_runner, "recheck_schedule", recheck)
    monkeypatch.setattr(merged_runner.sch, "propose_rules_v1", rules)
    monkeypatch.setattr(merged_runner.greedy, "propose", greedy)
    d.run_scenario("B", "rules-v1", tmp_path / "o", code_commit=TEST_ONLY_COMMIT)
    assert calls["rules"] > 0 and calls["check"] > 0
    assert "greedy_a" in calls["greedy"]  # the fallback was actually built (and then checked)
    d.run_scenario("A", "rules-v1", tmp_path / "o2", code_commit=TEST_ONLY_COMMIT)
    assert calls["recheck"] > 0  # a passed proposal is re-checked against the latest state


def test_expectations_come_from_the_specification_file():
    spec = json.loads((REPO_ROOT / "docs" / "rule_study" / "specification.json").read_text("utf-8"))
    entries = spec["scenarios"]
    entries = entries if isinstance(entries, list) else list(entries.values())
    expected = d.load_expectations()
    assert expected["A"] == next(e for e in entries if e["id"] == "A")["expected_not_measured"]
    assert expected["B"] == next(e for e in entries if e["id"] == "B")["expected_not_measured"]


# ------------------------------------------------------------------ the four scenarios
def test_scenario_a_executes_only_the_current_start_and_keeps_the_future_one_advisory(all_runs):
    _, runs = all_runs
    sr = runs["A"]
    d0 = sr.observed["decision_0"]
    assert d0["current_starts"] == ["J2"] and d0["advisory_future_placements"] == ["J1@1"]
    assert starts_of(sr) == {"J2": 0, "J1": 1}
    assert sr.observed["only_approved_current_slot_starts_executed"] is True
    assert sr.observed["completed"] == ["J1", "J2"] and sr.observed["missed"] == []
    assert all(row["verdict"] == "MATCH" for row in d.compare_with_expectation("A", sr.observed))


def test_scenario_b_stays_blocked_with_the_rejections_visible(all_runs):
    _, runs = all_runs
    obs = runs["B"].observed
    stages = obs["decision_0"]["stages"]
    assert [s["origin"] for s in stages] == ["rules-v1", "greedy_a_fallback"]
    assert [s["production_check"] for s in stages] == ["fail", "fail"]
    assert stages[1]["fallback_reason"] == "invalid_proposal"
    assert any("abstention" in text for text in stages[0]["check_violations"])
    assert obs["decision_0"]["selected_stage_id"] is None
    assert (
        obs["decision_0"]["execution_status"] == "blocked" and obs["executed_starts_by_slot"] == {}
    )
    assert obs["completed"] == [] and obs["missed"] == ["J1", "J2"]
    verdicts = [row["verdict"] for row in d.compare_with_expectation("B", obs)]
    assert verdicts == ["BOUND-MET-LITERAL", "BLOCKED"]


def test_scenario_b_fault_refuses_the_injected_plan_and_shows_the_overload(all_runs):
    _, runs = all_runs
    stages = runs["B-fault"].observed["decision_0"]["stages"]
    assert stages[0]["origin"] == "fault_injection" and stages[0]["production_check"] == "fail"
    overload = [a for a in stages[0]["capacity_arithmetic"] if a["outcome"] == "fail"]
    assert overload and overload[0]["total_kw"] == 80 and overload[0]["signed_excess_kw"] == 20
    assert stages[1]["origin"] == "greedy_a_fallback" and stages[1]["production_check"] == "fail"
    assert runs["B-fault"].observed["executed_starts_by_slot"] == {}
    assert runs["B-fault"].observed["completed"] == []


def test_scenario_b_progress_is_separate_and_feasible(all_runs):
    _, runs = all_runs
    sr = runs["B-progress"]
    assert starts_of(sr) == {"J1": 0, "J2": 1}
    assert sr.observed["completed"] == ["J1", "J2"]
    assert c.CASE_B.jobs != c.CASE_B_PROGRESS.jobs  # never combined with the impossible case


def test_no_model_calls_and_synthetic_labels(all_runs):
    _, runs = all_runs
    for sr in runs.values():
        assert sr.observed["model_call_count"] == 0
        assert "not g/kWh" in sr.observed["accounting"]["label"]


def test_trace_records_keep_proposal_check_fallback_and_execution_separate(all_runs):
    _, runs = all_runs
    rec = runs["B"].run.outcomes[0].record
    assert [st.origin for st in rec.proposal_stages] == ["rules-v1", "greedy_a_fallback"]
    assert all(st.check_result is not None for st in rec.proposal_stages)
    assert rec.selected_stage_id is None and rec.execution.status == "blocked"
    assert rec.bindings.code_commit == TEST_ONLY_COMMIT


# ------------------------------------------------------------------ replay
def test_every_saved_run_replays_from_disk_without_a_simulator_step(all_runs):
    _, runs = all_runs
    for sr in runs.values():
        assert sr.replay["status"] == "pass", sr.replay["problems"]
        assert sr.replay["decisions_replayed"] == 30
        assert sr.replay["simulator_steps_during_replay"] == 0
        assert sr.replay["all_replayed_from_saved_evidence"] is True
        assert sr.replay["result_rebuilt_equals_saved"] is True


def test_replay_command_accepts_the_output_directory_and_a_case_folder(all_runs, capsys):
    out, runs = all_runs
    code, io = run_main(["--replay", str(out)], capsys)
    reports = json.loads(io.out)
    assert code == 0 and len(reports) == 4 and all(x["status"] == "pass" for x in reports)
    code, io = run_main(["--replay", str(runs["A"].run.root)], capsys)
    assert code == 0 and json.loads(io.out)[0]["case_id"] == "A"


def test_replay_detects_a_changed_decision_record(tmp_path):
    sr = d.run_scenario("A", "rules-v1", tmp_path / "o", code_commit=TEST_ONLY_COMMIT)
    target = sr.run.root / "decisions" / "decision-00.json"
    target.write_text(
        target.read_text(encoding="utf-8").replace("EP-RULEA", "EP-RULEZ"), encoding="utf-8"
    )
    report = d.replay_saved(sr.run.root)
    assert report["status"] == "fail" and report["problems"]


def test_replay_detects_changed_state_evidence(tmp_path):
    sr = d.run_scenario("B", "rules-v1", tmp_path / "o", code_commit=TEST_ONLY_COMMIT)
    victim = next((sr.run.root / "states").glob("*.json"))
    victim.write_text(victim.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert d.replay_saved(sr.run.root)["status"] == "fail"


def test_replay_detects_a_changed_result_file(tmp_path):
    sr = d.run_scenario("A", "rules-v1", tmp_path / "o", code_commit=TEST_ONLY_COMMIT)
    path = sr.run.root / "result.json"
    path.write_text(
        path.read_text(encoding="utf-8").replace('"complete"', '"partial"'), encoding="utf-8"
    )
    assert d.replay_saved(sr.run.root)["status"] == "fail"


def test_replay_of_a_non_run_folder_fails_cleanly(tmp_path, capsys):
    assert d.replay_saved(tmp_path)["status"] == "fail"
    code, io = run_main(["--replay", str(tmp_path)], capsys)
    assert code == 2 and "no saved rule-study run" in io.err


# ------------------------------------------------------------------ files, overwrite safety, CLI
def test_summary_is_hashed_and_matches_the_saved_files(all_runs):
    out, runs = all_runs
    summary = d.summary_record(list(runs.values()), d.load_expectations(), "test")
    assert summary["record_kind"] == d.SUMMARY_KIND and summary[
        "independent_verification"
    ].startswith("NOT_RUN")
    for entry in summary["runs"]:
        text = (d.Path(entry["trace_root"]) / "result.json").read_text(encoding="utf-8")
        assert r.study_sha256(text) == entry["result_sha256"]
        assert len(entry["decision_sha256s"]) == 30


def test_a_new_run_never_overwrites_an_old_one(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(d, "DEFAULT_OUT_ROOT", tmp_path / "root")
    assert run_main(["--scenario", "A", "--json"], capsys)[0] == 0
    assert run_main(["--scenario", "A", "--json"], capsys)[0] == 0
    folders = sorted((tmp_path / "root").iterdir())
    assert len(folders) == 2 and folders[0] != folders[1]
    assert all((f / d.SUMMARY_NAME).is_file() for f in folders)


def test_a_non_empty_out_dir_is_refused_and_left_untouched(tmp_path, capsys):
    (tmp_path / "keep.txt").write_text("x")
    code, io = run_main(["--scenario", "A", "--out-dir", str(tmp_path)], capsys)
    assert code == 2 and "refusing" in io.err
    assert [p.name for p in tmp_path.iterdir()] == ["keep.txt"]


def test_summary_file_is_create_only(tmp_path):
    (tmp_path / d.SUMMARY_NAME).write_text("old")
    with pytest.raises(FileExistsError):
        d._write_summary(tmp_path, {"x": 1})
    assert (tmp_path / d.SUMMARY_NAME).read_text() == "old"


def test_scenario_flag_is_case_insensitive_and_prints_expected_before_observed(tmp_path, capsys):
    code, io = run_main(["--scenario", "b-fault", "--out-dir", str(tmp_path / "o")], capsys)
    assert code == 0
    text = io.out
    assert (
        text.index("EXPECTED (specification")
        < text.index("OBSERVED: decision 0")
        < text.index("EXPECTED vs OBSERVED")
    )
    assert "fault_injection" in text and "production check=fail" in text


def test_json_output_is_parseable(tmp_path, capsys):
    code, io = run_main(
        ["--scenario", "B-progress", "--json", "--out-dir", str(tmp_path / "o")], capsys
    )
    payload = json.loads(io.out)
    assert code == 0 and payload["runs"][0]["observed"]["completed"] == ["J1", "J2"]
    assert payload["runs"][0]["replay"]["status"] == "pass"


def test_list_unknown_scenario_and_no_terminal(monkeypatch, capsys):
    assert run_main(["--list"], capsys)[0] == 0
    assert run_main(["--scenario", "Z"], capsys)[0] == 2
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert run_main([], capsys)[0] == 2


def test_fault_scenario_rejects_other_policies(tmp_path, capsys):
    code, io = run_main(
        ["--scenario", "B-fault", "--policy", "greedy_a", "--out-dir", str(tmp_path / "o")], capsys
    )
    assert code == 2 and "rules-v1 demonstration only" in io.err


def test_interactive_menu(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "1")
    code, io = run_main(["--out-dir", str(tmp_path / "o")], capsys)
    assert code == 0 and "Scenario A / policy rules-v1" in io.out


def test_an_unbindable_checkout_is_reported_not_invented(tmp_path, monkeypatch, capsys):
    def refuse(case, root, code_commit=None):
        raise d.BindingError("a clean committed checkout is required")

    monkeypatch.setattr(d, "make_bindings", refuse)
    code, io = run_main(["--scenario", "A", "--out-dir", str(tmp_path / "o")], capsys)
    assert code == 2 and "cannot bind" in io.err


def test_module_runs_as_a_command_without_touching_the_general_cli():
    done = subprocess.run(
        [sys.executable, "-m", "dc_sustainability.rule_demo", "--list"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert done.returncode == 0 and "B-progress" in done.stdout


# ------------------------------------------------------------------ audit additions
def report_text(sr, scenario):
    return d.render(
        sr, d.load_expectations()[scenario], d.compare_with_expectation(scenario, sr.observed)
    )


def test_blocked_is_a_distinct_outcome_not_a_success(all_runs):
    _, runs = all_runs
    assert runs["B"].observed["scenario_outcome"] == "BLOCKED"
    assert runs["B-fault"].observed["scenario_outcome"] == "BLOCKED"
    assert runs["A"].observed["scenario_outcome"] == "COMPLETED"
    assert runs["B-progress"].observed["scenario_outcome"] == "COMPLETED"
    text = report_text(runs["B"], "B")
    assert "SCENARIO OUTCOME: BLOCKED" in text and "not a scheduling success" in text
    assert "[MATCH] expected: at most one" not in text  # the literal bound is not shown as a match
    assert "[BOUND-MET-LITERAL]" in text and "zero completions is not progress" in text
    assert "not a scheduling outcome" in text  # trace status 'complete' is explained


def test_scenario_outcome_classification():
    assert (
        d.scenario_outcome(completed=["J1"], missed=[], unfinished=[], executed_any=True)
        == "COMPLETED"
    )
    assert (
        d.scenario_outcome(completed=[], missed=["J1"], unfinished=["J1"], executed_any=False)
        == "BLOCKED"
    )
    assert (
        d.scenario_outcome(completed=["J1"], missed=["J2"], unfinished=["J2"], executed_any=True)
        == "PARTIAL"
    )


def test_b_separates_proposed_load_hypothetical_joint_load_and_checker_reason(all_runs):
    _, runs = all_runs
    stage = runs["B"].observed["decision_0"]["stages"][0]
    (proposed,) = stage["capacity_arithmetic"]
    (hypothetical,) = stage["hypothetical_joint_arithmetic"]
    assert (proposed["total_kw"], proposed["limit_kw"], proposed["outcome"]) == (50, 60, "pass")
    assert (
        hypothetical["total_kw"],
        hypothetical["signed_excess_kw"],
        hypothetical["outcome"],
    ) == (80, 20, "fail")
    assert {t["job_id"] for t in hypothetical["terms"]} == {None, "J1", "J2"}
    assert any(
        "abstention lacks individual physical justification" in v for v in stage["check_violations"]
    )
    text = report_text(runs["B"], "B")
    assert "PROPOSED load, slot 0 (R04): background 20 + J1 30 = 50 kW" in text
    assert "HYPOTHETICAL, not proposed (R05 rejected candidate)" in text
    assert "background 20 + J1 30 + J2 30 = 80 kW" in text
    assert "not because it overloads the site" in text


def test_b_fault_proposed_overload_is_labeled_as_the_injected_proposal(all_runs):
    _, runs = all_runs
    text = report_text(runs["B-fault"], "B-fault")
    assert "PROPOSED load, slot 0 (R04): background 20 + J1 30 + J2 30 = 80 kW" in text
    assert "injected (not natural) slot-0 proposal" in text


def test_inputs_and_synthetic_identities_are_shown(all_runs):
    _, runs = all_runs
    inputs = runs["B"].inputs
    assert inputs["episode_id"] == "EP-RULEB" and inputs["scenario_id"] == "SCN-B"
    assert "no private or source data" in inputs["origin"]
    assert [j["job_id"] for j in inputs["jobs"]] == ["J1", "J2"]
    text = report_text(runs["B"], "B")
    assert "EP-RULEB" in text and "J2: 30 kW x 1 slot(s)" in text
    assert "not measured carbon intensity" in text
    summary = d.summary_record([runs["B"]], d.load_expectations(), "t")
    assert summary["runs"][0]["inputs"]["case_sha256"] == runs["B"].bindings.case_sha256


def test_no_rejected_plan_is_ever_executed(all_runs):
    _, runs = all_runs
    assert all(sr.observed["no_rejected_plan_executed"] for sr in runs.values())


def _swap(root):
    a, b = root / "decisions" / "decision-01.json", root / "decisions" / "decision-02.json"
    ta, tb = a.read_text(encoding="utf-8"), b.read_text(encoding="utf-8")
    a.write_text(tb, encoding="utf-8")
    b.write_text(ta, encoding="utf-8")


def _extra_decision(root):
    (root / "decisions" / "decision-30.json").write_text(
        (root / "decisions" / "decision-29.json").read_text(encoding="utf-8"), encoding="utf-8"
    )


CORRUPTIONS = {
    "missing-state": lambda r: next((r / "states").glob("*.json")).unlink(),
    "missing-snapshot": lambda r: next((r / "snapshots").glob("*.json")).unlink(),
    "missing-middle-decision": lambda r: (r / "decisions" / "decision-05.json").unlink(),
    "missing-last-decision": lambda r: (r / "decisions" / "decision-29.json").unlink(),
    "missing-completion-commitment": lambda r: (r / ".completed" / "decision-03.json").unlink(),
    "missing-reservation": lambda r: (r / ".intents" / "decision-00.json").unlink(),
    "corrupt-transition": lambda r: (r / "transitions" / "transition-01.json").write_text("{}"),
    "missing-transition": lambda r: (r / "transitions" / "transition-01.json").unlink(),
    "missing-case-json": lambda r: (r / "case.json").unlink(),
    "altered-case-json": lambda r: (r / "case.json").write_text(
        (r / "case.json").read_text(encoding="utf-8").replace('"J1"', '"JX"', 1), encoding="utf-8"
    ),
    "missing-result": lambda r: (r / "result.json").unlink(),
    "extra-decision": _extra_decision,
    "swapped-decisions": _swap,
}


@pytest.mark.parametrize("name", sorted(CORRUPTIONS))
def test_replay_detects_each_kind_of_damaged_evidence(name, all_runs, tmp_path):
    import shutil

    _, runs = all_runs
    copy = tmp_path / "rules-v1" / "A-rules-v1"
    shutil.copytree(runs["A"].run.root, copy)
    assert d.replay_saved(copy)["status"] == "pass"  # the pristine copy replays
    CORRUPTIONS[name](copy)
    report = d.replay_saved(copy)
    assert report["status"] == "fail" and report["problems"], name


def test_missing_case_json_is_reported_by_name(all_runs, tmp_path):
    import shutil

    _, runs = all_runs
    copy = tmp_path / "rules-v1" / "B-rules-v1"
    shutil.copytree(runs["B"].run.root, copy)
    (copy / "case.json").unlink()
    assert any("case.json is missing" in p for p in d.replay_saved(copy)["problems"])


def test_verification_statuses_are_explicit_and_never_pass(all_runs):
    _, runs = all_runs
    summary = d.summary_record(list(runs.values()), d.load_expectations(), "t")
    assert summary["verification_statuses"]["independent_verification"] == "NOT_RUN"
    assert summary["verification_statuses"]["vocabulary"] == [
        "PASS",
        "FAIL",
        "INCOMPLETE",
        "NOT_RUN",
    ]
    assert "INCOMPLETE" in summary["trace_reader_compatibility_smoke"]
    assert "exit code 2" in summary["trace_reader_compatibility_smoke"]
    text = report_text(runs["A"], "A")
    assert "independent verification (Nisha, #241): NOT_RUN" in text
    assert "not independent verification" in text


@pytest.mark.parametrize("policy", ["greedy_a", "greedy_b"])
def test_baselines_replay_with_the_same_score_convention(tmp_path, policy):
    sr = d.run_scenario("A", policy, tmp_path, code_commit=TEST_ONLY_COMMIT)
    assert sr.replay["status"] == "pass"
    assert sr.replay["simulator_steps_during_replay"] == 0


def test_replay_never_invokes_decide_even_if_evidence_disappears(all_runs, monkeypatch):
    _, runs = all_runs
    monkeypatch.setattr(
        d.RuleStudyRunner, "decide", lambda *a: pytest.fail("readonly replay must not execute")
    )
    assert d.replay_saved(runs["A"].run.root)["status"] == "pass"


@pytest.mark.parametrize("damage", ["reservation", "decision_and_reservation", "directory"])
def test_incomplete_replay_does_not_repair_or_write_evidence(all_runs, tmp_path, damage):
    import shutil

    _, runs = all_runs
    root = tmp_path / "rules-v1/A-rules-v1"
    shutil.copytree(runs["A"].run.root, root)
    if damage == "directory":
        shutil.rmtree(root / ".completed")
    else:
        (root / ".intents/decision-00.json").unlink()
        if damage == "decision_and_reservation":
            (root / "decisions/decision-00.json").unlink()
            (root / ".completed/decision-00.json").unlink()
    before = {
        p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }
    assert d.replay_saved(root)["status"] == "fail"
    after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert before == after


def test_line_ending_change_is_not_normalized_away(all_runs, tmp_path):
    import shutil

    _, runs = all_runs
    root = tmp_path / "rules-v1/A-rules-v1"
    shutil.copytree(runs["A"].run.root, root)
    p = root / "decisions/decision-00.json"
    p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
    assert d.replay_saved(root)["status"] == "fail"


def test_all_does_not_silently_ignore_selected_baseline(tmp_path, capsys):
    out = tmp_path / "never"
    code, captured = run_main(["--all", "--policy", "greedy_a", "--out-dir", str(out)], capsys)
    assert code == 2 and "rules-v1" in captured.err
    assert not out.exists()


def test_readonly_runner_never_executes_a_missing_reservation(all_runs, tmp_path):
    import shutil

    _, runs = all_runs
    root = tmp_path / "rules-v1/A-rules-v1"
    shutil.copytree(runs["A"].run.root, root)
    for folder in ("decisions", ".intents", ".completed"):
        (root / folder / "decision-00.json").unlink()
    sim = d.SchedulingSimulator(allow_completion_starts=False)
    case = c.CASE_A
    sim.reset(case.episode(), forecasts_by_slot=case.forecasts_by_slot())
    runner = d.RuleStudyRunner(
        sim,
        case.snapshot,
        tmp_path,
        policy_id="rules-v1",
        case_id="A",
        decision_time_utc=case.decision_time_utc,
        bindings=runs["A"].bindings,
        score_convention=d.ScoreKwhConvention(),
        read_only=True,
    )
    with pytest.raises(ValueError, match="cannot execute"):
        runner.decide(0)
    assert len(sim.history) == 0
    assert not (root / "decisions/decision-00.json").exists()


def test_readonly_constructor_does_not_create_directories(all_runs, tmp_path):
    _, runs = all_runs
    with pytest.raises(ValueError, match="existing unlinked"):
        d.RuleStudyRunner(
            None,
            c.CASE_A.snapshot,
            tmp_path,
            policy_id="rules-v1",
            case_id="A",
            decision_time_utc=c.CASE_A.decision_time_utc,
            bindings=runs["A"].bindings,
            score_convention=d.ScoreKwhConvention(),
            read_only=True,
        )
    assert not list(tmp_path.iterdir())
