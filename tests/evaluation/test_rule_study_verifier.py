"""RULE-03 verifier tests: oracle facts, property predicates and counterexample detection.

The systems below are test fixtures, not rules-v1, Greedy A or Greedy B. Each one is
deliberately correct or deliberately broken so the verifier's verdicts can be checked.
"""

import json
from pathlib import Path

import pytest

from dc_sustainability.evaluation import rule_study_verifier as v

SPEC = json.loads(
    (Path(__file__).parents[2] / "docs/rule_study/specification.json").read_text("utf-8")
)


def _fits(view, chosen):
    for slot in range(view.slot, v.HORIZON):
        load = view.background_kw + sum(p for _, p, s, e in view.running if s <= slot < e)
        load += sum(j.power_kw for j in chosen if view.slot <= slot < view.slot + j.duration_slots)
        if load > view.capacity_kw:
            return False
    return True


def _legal_now(view, job):
    if view.slot > v.LAST_START_SLOT:
        return False
    if not job.flexible and view.slot != job.arrival_slot:
        return False
    return view.slot + job.duration_slots <= min(job.deadline_slot, v.HORIZON)


def _greedy(order):
    def system(view):
        chosen = []
        for job in sorted(view.waiting, key=order):
            if _legal_now(view, job) and _fits(view, chosen + [job]):
                chosen.append(job)
        return v.SystemDecision(tuple(j.job_id for j in chosen))

    return system


deadline_first = _greedy(lambda j: (j.latest_start, j.job_id))
id_order = _greedy(lambda j: j.job_id)


def all_now(view):
    return v.SystemDecision(tuple(j.job_id for j in view.waiting))


def never(view):
    return v.SystemDecision(())


def _status(report):
    return {p: report["properties"][p]["status"] for p in v.PROPERTY_IDS}


# --- Oracle --------------------------------------------------------------------------------


def test_primary_domain_has_64_distinct_inputs():
    cases = v.primary_domain()
    assert len(cases) == 64
    assert len({(c.jobs, c.scores) for c in cases}) == 64


def test_extended_domain_has_1024_distinct_inputs():
    cases = v.extended_domain()
    assert len(cases) == 1024
    assert len({(c.jobs, c.scores) for c in cases}) == 1024


def test_primary_feasibility_matches_hand_count():
    # Only 20 kW is free. Both jobs deadline 1 must share slot 0, so only 10+10 fits:
    # 3 of 16 job-type pairs are infeasible, times 4 score profiles.
    report = v.verify_system(v.primary_domain(), None, system_id="oracle-only")
    assert report["counts"]["complete_feasible"] == 52
    assert report["counts"]["not_complete_feasible"] == 12
    assert report["oracle_crosscheck"]["mismatches"] == 0
    assert report["budget"]["ceiling_hit"] is None
    assert all(p["status"] == "NOT_RUN" for p in report["properties"].values())


def test_oracle_crosscheck_agrees_on_extended_domain():
    report = v.verify_system(v.extended_domain(), None, system_id="oracle-only")
    assert report["oracle_crosscheck"]["mismatches"] == 0
    assert report["counts"]["inputs_explored"] == 1024


def test_authored_case_labels():
    cases = {c.case_id: c for c in v.authored_cases(SPEC)}
    assert set(cases) == {"A", "B", "B-fault", "B-progress"}
    assert v.completion_witness(cases["A"], v.initial_state())[0] is not None
    assert v.completion_witness(cases["B"], v.initial_state())[0] is None
    assert v.completion_witness(cases["B-progress"], v.initial_state())[0] == {
        "J1": 0,
        "J2": 1,
    }
    assert cases["B-fault"].fault_starts == ("J1", "J2")


def test_fault_proposal_arithmetic_case_b():
    case = next(c for c in v.authored_cases(SPEC) if c.case_id == "B-fault")
    violations = v.check_starts(case, v.initial_state(), case.fault_starts)
    assert [x.property_id for x in violations] == ["S3"]
    arithmetic = violations[0].arithmetic
    assert [t["value"] for t in arithmetic["terms"]] == [20, 30, 30]
    assert (arithmetic["total"], arithmetic["limit"], arithmetic["signed_excess"]) == (80, 60, 20)


# --- Predicates and state ------------------------------------------------------------------


def _one(job, **kw):
    return v.Case("t", kw.get("cap", 30), kw.get("bg", 10), (job,), v._profile((100, 300)))


def test_predicate_codes():
    late = v.Job("J1", 10, 1, 1, 3, True)
    case = _one(late)
    assert [x.code for x in v.check_starts(case, v.initial_state(), ("J1",))] == ["not_arrived"]
    assert [x.code for x in v.check_starts(case, v.initial_state(), ("J9",))] == ["unknown_job"]
    rigid = v.Job("J1", 10, 1, 0, 3, False)
    state1 = v.State(slot=1)
    assert "nonflexible_timing" in [x.code for x in v.check_starts(_one(rigid), state1, ("J1",))]
    tight = v.Job("J1", 10, 2, 0, 1, True)
    assert "deadline" in [x.code for x in v.check_starts(_one(tight), v.initial_state(), ("J1",))]
    dup = v.Job("J1", 10, 1, 0, 3, True)
    codes = [x.code for x in v.check_starts(_one(dup), v.initial_state(), ("J1", "J1"))]
    assert "duplicate_start" in codes
    assert "drain_slot_start" in [
        x.code for x in v.check_starts(_one(v.Job("J1", 10, 1, 0, 30, True)), v.State(24), ("J1",))
    ]


def test_impossible_arrival_is_missed_after_its_arrival_decision():
    job = v.Job("J1", 10, 1, 1, 1, True)  # arrives at 1, deadline 1: no legal start
    case = _one(job)
    state = v.advance(case, v.initial_state(), ())
    assert state.slot == 1 and state.missed == ()
    assert v.legal_actions(case, state) == [()]
    state = v.advance(case, state, ())
    assert state.missed == ("J1",)


def test_running_job_completes_at_its_end_boundary():
    case = _one(v.Job("J1", 10, 2, 0, 3, True))
    s1 = v.advance(case, v.initial_state(), ("J1",))
    assert s1.running == (("J1", 0, 2),)
    s2 = v.advance(case, s1, ())
    assert s2.completed == (("J1", 0, 2),) and s2.running == ()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"power_kw": True},
        {"power_kw": 0},
        {"arrival_slot": 24},
        {"deadline_slot": 31},
        {"flexible": 1},
    ],
)
def test_job_fails_closed(kwargs):
    base = dict(
        job_id="J1", power_kw=10, duration_slots=1, arrival_slot=0, deadline_slot=2, flexible=True
    )
    with pytest.raises(ValueError):
        v.Job(**{**base, **kwargs})


def test_case_rejects_duplicate_ids():
    job = v.Job("J1", 10, 1, 0, 2, True)
    with pytest.raises(ValueError):
        v.Case("t", 30, 10, (job, job), None)


def test_view_hides_future_arrivals():
    case = v.Case(
        "t", 30, 10, (v.Job("J1", 10, 1, 0, 2, True), v.Job("J2", 10, 1, 1, 3, True)), None
    )
    view = v.view_for(case, v.initial_state())
    assert [j.job_id for j in view.waiting] == ["J1"]
    assert view.scores is None


# --- System verdicts -----------------------------------------------------------------------


def test_correct_fixture_passes_primary_domain():
    report = v.verify_system(v.primary_domain(), deadline_first, system_id="fixture-edf")
    assert _status(report) == {
        "S1": "PASS",
        "S2": "PASS",
        "S3": "PASS",
        "S4": "NOT_RUN",  # no invalid proposal occurs in this domain
        "S5": "PASS",
        "P1": "PASS",
        "P2": "NOT_RUN",
    }
    assert report["properties"]["S4"]["reason"] == "no invalid proposal occurred in this domain"
    assert report["counts"]["p1_eligible_inputs"] == 52
    assert "Not a rules-v1 result" in report["status_note"]


def test_id_order_fixture_is_safe_but_refutes_p1():
    report = v.verify_system(v.primary_domain(), id_order, system_id="fixture-id-order")
    status = _status(report)
    assert {status[p] for p in ("S1", "S2", "S3", "S5")} == {"PASS"}
    assert status["P1"] == "FAIL"
    example = next(x for x in report["counterexamples"] if x["property"] == "P1")
    assert example["code"] == "feasible_work_not_completed"


def test_unsafe_fixture_fails_capacity_with_arithmetic():
    report = v.verify_system(v.primary_domain(), all_now, system_id="fixture-all-now")
    assert report["properties"]["S3"]["status"] == "FAIL"
    example = next(x for x in report["counterexamples"] if x["property"] == "S3")
    assert example["arithmetic"]["signed_excess"] > 0


def test_idle_fixture_is_safe_and_fails_progress():
    report = v.verify_system(v.primary_domain(), never, system_id="fixture-never")
    assert report["properties"]["S3"]["status"] == "PASS"
    assert report["properties"]["P1"]["status"] == "FAIL"
    assert report["properties"]["P1"]["violations"] == 52


def test_executing_injected_fault_fails_s4():
    def obey_fault(view):
        if view.injected_proposal:
            return v.SystemDecision(view.injected_proposal)
        return deadline_first(view)

    cases = [c for c in v.authored_cases(SPEC) if c.case_id == "B-fault"]
    report = v.verify_system(cases, obey_fault, system_id="fixture-obey-fault")
    assert report["properties"]["S4"]["status"] == "FAIL"
    assert report["properties"]["S3"]["status"] == "FAIL"


def test_blocking_injected_fault_passes_s4_without_p1_claim():
    def block_fault(view):
        if view.injected_proposal:
            stage = v.ProposalStage("fault_injection", view.injected_proposal)
            return v.SystemDecision((), (stage,))
        return deadline_first(view)

    cases = [c for c in v.authored_cases(SPEC) if c.case_id == "B-fault"]
    report = v.verify_system(cases, block_fault, system_id="fixture-block-fault")
    assert report["properties"]["S4"]["status"] == "PASS"
    assert report["properties"]["P1"]["status"] == "NOT_RUN"  # infeasible and faulted


def test_drain_slot_start_fails_s5():
    # J1 runs 23-25 so slot 24 is still a decision point; J2 expired at 24.
    def start_late(view):
        if view.slot == 23 and "J1" in [j.job_id for j in view.waiting]:
            return v.SystemDecision(("J1",))
        if view.slot == 24:
            return v.SystemDecision(view.missed_ids)
        return v.SystemDecision(())

    case = v.Case(
        "t",
        30,
        10,
        (v.Job("J1", 10, 2, 0, 30, True), v.Job("J2", 10, 1, 0, 30, True)),
        v._profile((100, 300)),
    )
    report = v.verify_system([case], start_late, system_id="fixture-late")
    assert report["properties"]["S5"]["status"] == "FAIL"
    codes = {x["code"] for x in report["counterexamples"]}
    assert {"drain_slot_start", "not_waiting"} <= codes


def test_expired_jobs_are_never_offered_as_waiting():
    # Timing rules R02/R03 are enforced by expiry: a nonflexible job not started at arrival,
    # or any job past its latest start, is missed at the next boundary. So a timing
    # violation can only come from starting a job that is not waiting.
    for case in v.extended_domain():
        states, _, complete = v.explore_legal_graph(case, v.Budget())
        assert complete
        for state in states:
            for job in state.waiting(case):
                assert state.slot in job.legal_starts(state.slot) or (
                    not job.legal_starts(state.slot) and state.slot == job.arrival_slot
                )


def test_restarting_missed_job_fails_s1_and_s2():
    # J1 (2 slots) takes the only free capacity at 0; nonflexible J2 expires at 1 while J1
    # still runs, so the policy is asked again and restarts the missed job.
    def restart_missed(view):
        return v.SystemDecision(view.missed_ids or deadline_first(view).executed_starts)

    case = v.Case(
        "t",
        30,
        10,
        (v.Job("J1", 20, 2, 0, 3, False), v.Job("J2", 20, 1, 0, 1, False)),
        v._profile((100, 300)),
    )
    report = v.verify_system([case], restart_missed, system_id="fixture-restart")
    assert report["properties"]["S1"]["status"] == "FAIL"
    assert report["properties"]["S2"]["status"] == "FAIL"
    codes = {x["code"] for x in report["counterexamples"] if x["property"] == "S2"}
    assert codes == {"nonflexible_timing", "deadline"}


def test_combined_budget_and_overlap_across_domains():
    report = v.verify_domains(
        [("primary", v.primary_domain()), ("extended", v.extended_domain())],
        deadline_first,
        system_id="fixture-edf",
    )
    primary, extended = report["results"]
    assert primary["counts"]["overlap_with_earlier_domains"] == 0
    assert extended["counts"]["overlap_with_earlier_domains"] == 64  # primary is a subset
    scopes = report["budget"]["by_scope"]
    assert set(scopes) == {
        "primary/legal_action_graph_for_joint_feasibility",
        "primary/policy_induced_graph_for_properties",
        "extended/legal_action_graph_for_joint_feasibility",
        "extended/policy_induced_graph_for_properties",
    }
    assert report["budget"]["states_used"] == sum(s["states"] for s in scopes.values())
    assert report["budget"]["states_used"] <= 10_000
    assert extended["counts"]["p1_outside_scope"]["not_closed_at_slot0"] > 0


def test_supplement_hitting_ceiling_keeps_primary_result():
    budget = v.Budget(max_states=2_000)
    report = v.verify_domains(
        [("primary", v.primary_domain()), ("extended", v.extended_domain())],
        deadline_first,
        system_id="fixture-edf",
        budget=budget,
    )
    primary, extended = report["results"]
    assert primary["properties"]["S3"]["status"] == "PASS"
    assert extended["properties"]["S3"]["status"] == "INCOMPLETE"


def test_system_error_is_recorded_not_passed():
    def broken(view):
        raise RuntimeError("boom")

    report = v.verify_system(v.primary_domain()[:1], broken, system_id="fixture-error")
    assert report["properties"]["S5"]["status"] == "FAIL"
    assert report["counterexamples"][0]["code"] == "system_error"


def test_ceiling_hit_is_incomplete_not_pass():
    budget = v.Budget(max_states=10)
    report = v.verify_system(v.primary_domain(), deadline_first, system_id="fixture", budget=budget)
    assert report["budget"]["ceiling_hit"] == "states"
    assert report["properties"]["S3"]["status"] == "INCOMPLETE"
    assert report["counts"]["inputs_explored"] < 64


# --- Report identity -----------------------------------------------------------------------


def test_report_identity_fields_and_hashes():
    report = v.verify_system(v.authored_cases(SPEC), None, system_id="oracle-only")
    assert report["record_kind"] == "rule_study_verification_v1"
    assert len(report["verifier_source_sha256"]) == 64
    assert report["methods"] == [
        "legal_action_graph_for_joint_feasibility",
        "brute_force_joint_assignment_crosscheck",
    ]
    assert v.canonical_sha256({"b": 1, "a": [1, 2]}) == v.canonical_sha256({"a": [1, 2], "b": 1})
    with pytest.raises(ValueError):
        v.canonical_sha256({"x": float("nan")})


def test_cli_writes_new_canonical_report(tmp_path, capsys):
    import importlib.util

    path = Path(__file__).parents[2] / "scripts/verify_rule_study.py"
    spec = importlib.util.spec_from_file_location("verify_rule_study", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    out = tmp_path / "report.json"
    assert cli.main(["--domain", "authored", "--out", str(out)]) == 0
    report = json.loads(out.read_text("utf-8"))
    assert report["results"][0]["counts"]["complete_feasible"] == 2
    assert report["spec_sha256"] == v.canonical_sha256(SPEC)
    with pytest.raises(SystemExit):
        cli.main(["--domain", "authored", "--out", str(out)])  # refuses to overwrite
