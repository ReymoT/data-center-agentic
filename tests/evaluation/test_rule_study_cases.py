"""RULE-03 case-set checker: labels, stratum predicates, diversity and overlap.

All cases are hand-built test inputs in the assumed RULE-04 shape, not generator output.
"""

import copy
import json
from pathlib import Path

import pytest

from dc_sustainability.evaluation import rule_study_cases as rc

SPEC = json.loads(
    (Path(__file__).parents[2] / "docs/rule_study/specification.json").read_text("utf-8")
)


def job(job_id, power, duration, arrival, deadline, flexible):
    return {
        "job_id": job_id,
        "power_kw": power,
        "duration_slots": duration,
        "arrival_slot": arrival,
        "deadline_slot": deadline,
        "flexible": flexible,
    }


def case(case_id, stratum, jobs, first=(100, 300, 200, 200, 100, 300), label="jointly_feasible"):
    scores = None if stratum == "missing_forecast" else list(first) + [200] * 24
    return {
        "case_id": case_id,
        "stratum": stratum,
        "feasibility_label": label,
        "capacity_kw": 60,
        "background_kw": 20,
        "scores": scores,
        "jobs": jobs,
    }


NORMAL = case(
    "N1", "normal_feasible", [job("J1", 20, 1, 0, 3, True), job("J2", 20, 2, 1, 3, False)]
)
OVERLOAD = case(
    "O1",
    "overloaded_impossible",
    [job("J1", 30, 1, 0, 1, False), job("J2", 30, 1, 0, 1, False), job("J3", 10, 1, 2, 4, True)],
    label="jointly_infeasible",
)
MISSING = case(
    "M1", "missing_forecast", [job("J1", 10, 2, 0, 3, True), job("J2", 30, 1, 1, 2, False)]
)


def one_set(set_id="final", cases=(NORMAL, OVERLOAD, MISSING)):
    return {"set_id": set_id, "cases": [copy.deepcopy(c) for c in cases]}


def run(*sets, expected=1):
    return rc.check_case_sets(
        list(sets), spec=SPEC, expected_per_stratum={s["set_id"]: expected for s in sets}
    )


def checks(report, index=0):
    return {k: c["status"] for k, c in report["sets"][index]["checks"].items()}


def test_conforming_set_passes():
    report = run(one_set())
    assert report["overall"] == "PASS"
    assert set(checks(report).values()) == {"PASS"}
    strata = report["sets"][0]["strata"]
    assert {s: row["cases"] for s, row in strata.items()} == {
        "normal_feasible": 1,
        "overloaded_impossible": 1,
        "missing_forecast": 1,
    }
    assert report["checks"]["no_full_case_overlap"]["status"] == "PASS"


def test_wrong_generator_label_is_caught():
    bad = copy.deepcopy(NORMAL)
    bad["feasibility_label"] = "jointly_infeasible"
    report = run(one_set(cases=(bad, OVERLOAD, MISSING)))
    assert checks(report)["feasibility_labels"] == "FAIL"
    assert report["sets"][0]["label_mismatches"] == [
        {"case_id": "N1", "generator": "jointly_infeasible", "oracle": "jointly_feasible"}
    ]
    assert report["overall"] == "FAIL"


def test_infeasible_case_in_feasible_stratum_fails_predicate():
    bad = case(
        "N2",
        "normal_feasible",
        [job("J1", 30, 1, 0, 1, False), job("J2", 30, 1, 0, 1, True)],
        label="jointly_infeasible",
    )
    report = run(one_set(cases=(bad, OVERLOAD, MISSING)))
    failure = report["sets"][0]["predicate_failures"][0]
    assert "stratum_requires_feasible" in failure["findings"]


@pytest.mark.parametrize(
    "mutate, finding",
    [
        (lambda c: c.update(capacity_kw=70), "site_parameters"),
        (
            lambda c: c["jobs"].pop(),  # one job; more than four is refused as malformed
            "job_count",
        ),
        (lambda c: c["jobs"][0].update(power_kw=25), "job_values:J1"),
        (lambda c: c["jobs"][0].update(arrival_slot=3, deadline_slot=6), "arrival:J1"),
        (lambda c: c["jobs"][0].update(deadline_slot=5), "deadline:J1"),
        (lambda c: c["jobs"][0].update(job_id="X1"), "job_ids"),
        (lambda c: c["jobs"][0].update(flexible=False), "no_flexible_job"),
        (lambda c: c.update(scores=[100] * 6 + [200] * 24), "constant_profile"),
        (lambda c: c.update(scores=[100, 300, 200, 200, 100, 250] + [200] * 24), "score_values"),
        (lambda c: c.update(scores=None), "forecast_missing"),
    ],
)
def test_normal_stratum_predicates(mutate, finding):
    bad = copy.deepcopy(NORMAL)
    mutate(bad)
    report = run(one_set(cases=(bad, OVERLOAD, MISSING)))
    found = [f for row in report["sets"][0]["predicate_failures"] for f in row["findings"]]
    assert finding in found


def test_overload_needs_conflict_pair_and_three_jobs():
    no_pair = copy.deepcopy(OVERLOAD)
    no_pair["jobs"][1]["flexible"] = True
    two_jobs = copy.deepcopy(OVERLOAD)
    two_jobs["case_id"] = "O2"
    two_jobs["jobs"] = two_jobs["jobs"][:2]
    report = run(one_set(cases=(NORMAL, no_pair, two_jobs, MISSING)), expected=None)
    by_id = {r["case_id"]: r["findings"] for r in report["sets"][0]["predicate_failures"]}
    assert "missing_conflict_pair" in by_id["O1"]
    assert by_id["O2"] == ["job_count"]


def test_missing_forecast_stratum_must_hide_scores():
    bad = copy.deepcopy(MISSING)
    bad["scores"] = [100, 300, 200, 200, 100, 300] + [200] * 24
    report = run(one_set(cases=(NORMAL, OVERLOAD, bad)))
    found = [f for row in report["sets"][0]["predicate_failures"] for f in row["findings"]]
    assert "forecast_visible" in found


def test_counts_must_match_expected():
    report = run(one_set(), expected=40)
    assert checks(report)["stratum_counts"] == "FAIL"


def test_duplicates_and_workload_diversity_are_counted():
    twin = copy.deepcopy(NORMAL)
    twin["case_id"] = "N2"
    profile_variant = copy.deepcopy(NORMAL)
    profile_variant["case_id"] = "N3"
    profile_variant["scores"] = [300, 100, 200, 200, 100, 300] + [200] * 24
    report = run(one_set(cases=(NORMAL, twin, profile_variant, OVERLOAD, MISSING)), expected=None)
    section = report["sets"][0]
    assert checks(report)["no_duplicate_cases"] == "FAIL"
    assert section["strata"]["normal_feasible"] == {
        "cases": 3,
        "distinct_full_cases": 2,
        "distinct_workloads": 1,
        "expected": None,
    }


def test_duplicate_case_ids_fail():
    other = copy.deepcopy(OVERLOAD)
    other["case_id"] = "N1"
    report = run(one_set(cases=(NORMAL, other, MISSING)))
    assert report["sets"][0]["duplicate_case_ids"] == ["N1"]
    assert checks(report)["no_duplicate_cases"] == "FAIL"


def test_overlap_between_sets_fails_and_workload_overlap_is_reported():
    final = one_set("final")
    dev_variant = copy.deepcopy(NORMAL)
    dev_variant["case_id"] = "D9"
    dev_variant["scores"] = [300, 100, 200, 200, 100, 300] + [200] * 24
    development = one_set("development", cases=(dev_variant,))
    report = run(final, development, expected=None)
    pair = next(o for o in report["overlap"] if o["pair"] == ["final", "development"])
    assert pair == {"pair": ["final", "development"], "full_case_overlap": 0, "workload_overlap": 1}
    assert report["checks"]["no_full_case_overlap"]["status"] == "PASS"

    leaked = one_set("development", cases=(NORMAL,))
    report = run(final, leaked, expected=None)
    assert report["checks"]["no_full_case_overlap"]["status"] == "FAIL"
    assert report["overall"] == "FAIL"


def test_overlap_with_authored_example_fails():
    scenario = next(s for s in SPEC["scenarios"] if s["id"] == "A")
    copied = {
        "case_id": "F1",
        "stratum": "normal_feasible",
        "feasibility_label": "jointly_feasible",
        "capacity_kw": scenario["capacity_kw"],
        "background_kw": scenario["background_kw"],
        "first_scores": scenario["first_scores"],
        "remaining_score": scenario["remaining_score"],
        "jobs": scenario["jobs"],
    }
    report = run(one_set(cases=(copied, OVERLOAD, MISSING)))
    authored = next(o for o in report["overlap"] if o["pair"] == ["final", "authored"])
    assert authored["full_case_overlap"] == 1
    assert report["checks"]["no_full_case_overlap"]["status"] == "FAIL"


def test_malformed_cases_are_listed_not_scored():
    broken = copy.deepcopy(NORMAL)
    del broken["capacity_kw"]
    too_many = copy.deepcopy(MISSING)
    too_many["jobs"] += [job(f"J{i}", 10, 1, 0, 3, True) for i in (3, 4, 5)]
    unknown = copy.deepcopy(OVERLOAD)
    unknown["stratum"] = "easy"
    report = run(one_set(cases=(broken, unknown, too_many)), expected=None)
    section = report["sets"][0]
    assert [m["case_id"] for m in section["malformed"]] == ["N1", "O1", "M1"]
    assert checks(report)["well_formed"] == "FAIL"


def test_oracle_crosscheck_agrees():
    report = run(one_set())
    assert report["sets"][0]["oracle_crosscheck_counts"] == {"agreements": 3}


def test_invalid_input_shapes_are_rejected():
    with pytest.raises(ValueError):
        rc.check_case_sets([{"cases": []}], spec=SPEC)
    with pytest.raises(ValueError):
        rc.check_case_sets([one_set("x"), one_set("x")], spec=SPEC)


def test_identity_ignores_metadata_and_case_id():
    a = copy.deepcopy(NORMAL)
    b = copy.deepcopy(NORMAL)
    b["case_id"] = "other"
    b["generator_attempt"] = 17
    from dc_sustainability.evaluation import rule_study_trace as tr

    ida = rc.case_identity(tr.case_from_dict(a))
    idb = rc.case_identity(tr.case_from_dict(b))
    assert ida == idb


def test_cli_exit_codes_and_exclusive_output(tmp_path):
    import importlib.util

    path = Path(__file__).parents[2] / "scripts/check_rule_study_cases.py"
    spec = importlib.util.spec_from_file_location("check_rule_study_cases", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    good = tmp_path / "final.json"
    good.write_text(json.dumps(one_set()), "utf-8")
    out = tmp_path / "report.json"
    assert cli.main(["--set", str(good), "--expected", "final=1", "--out", str(out)]) == 0
    assert json.loads(out.read_text("utf-8"))["overall"] == "PASS"
    with pytest.raises(SystemExit):
        cli.main(["--set", str(good), "--out", str(out)])  # never overwrites
    assert cli.main(["--set", str(good)]) == 1  # default expects 40 per stratum
    with pytest.raises(SystemExit):
        cli.main(["--set", str(good), "--expected", "final=forty"])


# Manager review regressions: supplied fixtures only, no generated evaluation set.
def test_empty_collection_cannot_pass():
    with pytest.raises(ValueError):
        rc.check_case_sets([], spec=SPEC)


def test_skipped_counts_are_incomplete_not_overall_pass():
    report = run(one_set(), expected=None)
    assert report["overall"] == "INCOMPLETE"


@pytest.mark.parametrize("expected", [True, 0, -1, 1.5])
def test_invalid_expected_counts_refused(expected):
    with pytest.raises(ValueError):
        run(one_set(), expected=expected)


def test_changed_specification_cannot_be_silently_certified():
    changed = copy.deepcopy(SPEC)
    changed["evaluation"]["job_count_options"]["overloaded_impossible"] = [2]
    with pytest.raises(ValueError, match="specification"):
        rc.check_case_sets([one_set()], spec=changed)


@pytest.mark.parametrize("field,value", [("horizon", 12), ("pue", 9), ("fault_injected", True)])
def test_unknown_semantic_case_fields_cannot_hide_as_metadata(field, value):
    bad = copy.deepcopy(NORMAL)
    bad[field] = value
    assert run(one_set(cases=(bad, OVERLOAD, MISSING)))["overall"] == "FAIL"


def test_unknown_job_fields_cannot_change_downstream_workload():
    bad = copy.deepcopy(NORMAL)
    bad["jobs"][0]["priority"] = 99
    assert run(one_set(cases=(bad, OVERLOAD, MISSING)))["overall"] == "FAIL"


def test_conflicting_score_encodings_are_refused():
    bad = copy.deepcopy(NORMAL)
    bad.update(first_scores=[300] * 6, remaining_score=200)
    assert run(one_set(cases=(bad, OVERLOAD, MISSING)))["overall"] == "FAIL"


def test_one_shared_budget_and_reported_counters():
    from dc_sustainability.evaluation import rule_study_verifier as v

    budget = v.Budget(max_states=1, max_transitions=1)
    report = rc.check_case_sets(
        [one_set()], spec=SPEC, graph_budget=budget, expected_per_stratum={"final": 1}
    )
    assert report["overall"] == "INCOMPLETE"
    assert report["budget"]["states_used"] <= 1
    assert report["budget"]["transitions_used"] <= 1


def test_zero_time_budget_does_not_run_unbounded_assignment_search(monkeypatch):
    from dc_sustainability.evaluation import rule_study_verifier as v

    monkeypatch.setattr(v, "completion_witness", lambda *a, **k: pytest.fail("oracle ran"))
    report = rc.check_case_sets(
        [one_set()],
        spec=SPEC,
        graph_budget=v.Budget(max_seconds=0),
        expected_per_stratum={"final": 1},
    )
    assert report["overall"] == "INCOMPLETE"


def test_unknown_expected_set_is_not_silently_ignored():
    with pytest.raises(ValueError):
        rc.check_case_sets([one_set()], spec=SPEC, expected_per_stratum={"typo": 40})


@pytest.mark.parametrize(
    "payload", ['{"set_id":"a","set_id":"b","cases":[]}', '{"set_id":"a","cases":[],"x":NaN}']
)
def test_ambiguous_json_is_refused(tmp_path, payload):
    p = tmp_path / "bad.json"
    p.write_text(payload)
    with pytest.raises(ValueError):
        rc.load_case_set(p)


def test_invalid_domain_is_not_enumerated(monkeypatch):
    from dc_sustainability.evaluation import rule_study_verifier as v

    bad = copy.deepcopy(NORMAL)
    bad["jobs"][0]["deadline_slot"] = 24

    def witness(case, *a, **k):
        assert case.case_id != "N1", "unbounded out-of-domain oracle"
        return original(case, *a, **k)

    original = v.completion_witness
    monkeypatch.setattr(v, "completion_witness", witness)
    assert run(one_set(cases=(bad, OVERLOAD, MISSING)))["overall"] == "FAIL"


def test_single_set_does_not_establish_unseen_isolation_or_acceptance():
    report = run(one_set())
    assert report["study_acceptance"] == "NOT_ESTABLISHED"
    assert "INCOMPLETE" in report["unseen_isolation"]
    assert "not checked" in report["missing_forecast_accounting"]


def test_graph_disagreement_retains_case_id_and_blocks_pass(monkeypatch):
    from dc_sustainability.evaluation import rule_study_verifier as v

    monkeypatch.setattr(v, "explore_legal_graph", lambda *a, **k: ([], False, True))
    report = run(one_set())
    assert report["overall"] == "FAIL"
    assert report["sets"][0]["oracle_crosscheck_mismatched_case_ids"] == ["N1", "M1"]


@pytest.mark.parametrize(
    "kwargs", [{"max_states": 10001}, {"max_transitions": 50001}, {"max_seconds": 601}]
)
def test_increased_budgets_cannot_bypass_shared_ceiling(kwargs):
    from dc_sustainability.evaluation import rule_study_verifier as v

    with pytest.raises(ValueError, match="ceilings"):
        rc.check_case_sets([one_set()], spec=SPEC, graph_budget=v.Budget(**kwargs))


def test_oversized_input_is_refused_before_json_parse(tmp_path, monkeypatch):
    p = tmp_path / "large.json"
    p.write_text(" " * 50)
    monkeypatch.setattr(rc, "MAX_INPUT_BYTES", 20)
    with pytest.raises(ValueError, match="byte limit"):
        rc.load_case_set(p)


def test_cli_preserves_failure_and_incomplete_reports(tmp_path):
    from scripts import check_rule_study_cases as cli

    source = tmp_path / "cases.json"
    source.write_text('{"set_id":"x","set_id":"y","cases":[]}')
    failed = tmp_path / "failed.json"
    assert cli.main(["--set", str(source), "--out", str(failed)]) == 1
    assert json.loads(failed.read_text())["input_error"] == "ValueError"
    source.write_text(json.dumps(one_set()))
    partial = tmp_path / "partial.json"
    assert (
        cli.main(
            [
                "--set",
                str(source),
                "--expected",
                "final=1",
                "--max-states",
                "0",
                "--out",
                str(partial),
            ]
        )
        == 2
    )
    assert json.loads(partial.read_text())["overall"] == "INCOMPLETE"


def test_cli_duplicate_or_unknown_expected_counts_are_refused(tmp_path):
    from scripts import check_rule_study_cases as cli

    source = tmp_path / "cases.json"
    source.write_text(json.dumps(one_set()))
    with pytest.raises(SystemExit):
        cli.main(["--set", str(source), "--expected", "final=1", "--expected", "final=2"])
    assert cli.main(["--set", str(source), "--expected", "typo=1"]) == 1
