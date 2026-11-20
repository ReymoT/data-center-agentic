"""RULE-03 trace mode: strict reading and independent replay of adapter records.

Traces here are constructed test records in the agreed proposal-1 shape, produced from
fixture policies, not rules-v1, Greedy or runner output.
"""

import copy
import json
from pathlib import Path

import pytest

from dc_sustainability.evaluation import rule_study_trace as tr
from dc_sustainability.evaluation import rule_study_verifier as v

SPEC = json.loads(
    (Path(__file__).parents[2] / "docs/rule_study/specification.json").read_text("utf-8")
)
SCENARIOS = {s["id"]: s for s in SPEC["scenarios"]}
H = "ab" * 32
COMMIT = "c" * 40


def case_dict(scenario_id, **changes):
    s = copy.deepcopy(SCENARIOS[scenario_id])
    data = {
        "case_id": s["id"],
        "capacity_kw": s["capacity_kw"],
        "background_kw": s["background_kw"],
        "first_scores": s["first_scores"],
        "remaining_score": s["remaining_score"],
        "jobs": s["jobs"],
    }
    data.update(changes)
    return data


def edf(view):
    chosen = []
    for job in sorted(view.waiting, key=lambda j: (j.latest_start, j.job_id)):
        trial = chosen + [job]
        legal = view.slot <= v.LAST_START_SLOT and view.slot in job.legal_starts(view.slot)
        fits = all(
            view.background_kw
            + sum(p for _, p, s, e in view.running if s <= slot < e)
            + sum(j.power_kw for j in trial if view.slot <= slot < view.slot + j.duration_slots)
            <= view.capacity_kw
            for slot in range(view.slot, v.HORIZON)
        )
        if legal and fits:
            chosen.append(job)
    return tuple(j.job_id for j in chosen)


def _state_sha(state):
    return v.canonical_sha256(v._state_json(state))


def build_trace(data, policy=edf, policy_id="rules-v1", fault=None, fault_executed=False):
    """Simulate with the verifier's own state machine and emit proposal-1 records."""
    case = tr.case_from_dict(data)
    bindings = {
        "spec_sha256": H,
        "adapter_source_sha256": H,
        "generator_source_sha256": H,
        "case_sha256": v.canonical_sha256(data),
        "environment_lock_sha256": H,
        "code_commit": COMMIT,
    }
    state = v.initial_state()
    decisions = []
    for slot in range(v.HORIZON):
        stages = []
        if fault and slot == 0:
            stages.append(
                {
                    "stage_id": "fault",
                    "origin": "fault_injection",
                    "plan": {"starts": [{"job_id": j, "start_slot": 0} for j in fault]},
                }
            )
        current = (
            tuple(fault)
            if (fault and slot == 0 and fault_executed)
            else policy(v.view_for(case, state))
        )
        if fault and slot == 0 and not fault_executed:
            current = ()
        stage_plan = [{"job_id": j, "start_slot": slot} for j in current]
        arithmetic = []
        if current:
            a = v.capacity_arithmetic(case, state, current, slot)
            arithmetic.append(
                {
                    "rule_id": "R04",
                    "slot": slot,
                    "terms": a["terms"],
                    "total": a["total"],
                    "limit": a["limit"],
                    "signed_excess": a["signed_excess"],
                }
            )
        selected = None
        if current and not (fault and slot == 0 and fault_executed):
            stages.append(
                {
                    "stage_id": "main",
                    "origin": policy_id,
                    "plan": {"starts": stage_plan},
                    "rule_ids": ["R04"],
                    "arithmetic": arithmetic,
                }
            )
            selected = "main"
        if fault and slot == 0 and fault_executed:
            selected = "fault"
        nxt = v.advance(case, state, current)
        decisions.append(
            {
                "record_kind": "rule_study_decision_v1",
                "adapter_version": "proposal-1",
                "study_id": "rule-study-20261119-v1",
                "policy_id": policy_id,
                "case_id": case.case_id,
                "decision_index": slot,
                "bindings": dict(bindings),
                "state_before": {
                    "slot": slot,
                    "state_version": slot,
                    "visible_state_sha256": _state_sha(state),
                    "constraint_snapshot_sha256": H,
                },
                "proposal_stages": stages,
                "selected_stage_id": selected,
                "execution": {
                    "status": "executed" if current else ("blocked" if fault else "abstained"),
                    "current_starts": list(current),
                    "state_after": {
                        "slot": slot + 1,
                        "state_version": slot + 1,
                        "state_sha256": _state_sha(nxt),
                    },
                },
                "errors": [],
                "model_call_count": 0,
            }
        )
        state = nxt
    completed = sorted(c[0] for c in state.completed)
    result = {
        "record_kind": "rule_study_result_v1",
        "adapter_version": "proposal-1",
        "study_id": "rule-study-20261119-v1",
        "policy_id": policy_id,
        "case_id": case.case_id,
        "bindings": dict(bindings),
        "decision_sha256s": [v.canonical_sha256(d) for d in decisions],
        "completed_job_ids": completed,
        "missed_job_ids": sorted(state.missed),
        "unfinished_job_ids": sorted({j.job_id for j in case.jobs} - set(completed)),
        "accounting": {},
        "status": "complete",
    }
    return data, decisions, result


def rebind(trace):
    """Recompute decision hashes after a deliberate mutation of decision content."""
    data, decisions, result = trace
    result["decision_sha256s"] = [v.canonical_sha256(d) for d in decisions]
    return data, decisions, result


def status(report, policy="rules-v1"):
    return {p: x["status"] for p, x in report["results"][policy]["properties"].items()}


# --- Valid traces --------------------------------------------------------------------------


def test_valid_case_a_trace_passes():
    report = tr.verify_traces([build_trace(case_dict("A"))])
    assert report["refused_traces"] == []
    result = report["results"]["rules-v1"]
    assert status(report) == {
        "S1": "PASS",
        "S2": "PASS",
        "S3": "PASS",
        "S4": "NOT_RUN",
        "S5": "PASS",
        "P1": "PASS",
        "P2": "PASS",
    }
    assert result["arithmetic_consistency"]["checked"] > 0
    assert result["arithmetic_consistency"]["mismatches"] == 0
    assert result["state_hash_continuity"]["mismatches"] == 0
    assert "Not a rules-v1 result" in report["status_note"]


def test_blocked_fault_in_case_b_passes_s4_and_accounts_missed_jobs():
    trace = build_trace(case_dict("B"), fault=("J1", "J2"), policy=lambda view: ())
    report = tr.verify_traces([trace])
    st = status(report)
    assert st["S4"] == "PASS" and st["S3"] == "PASS"
    assert st["P1"] == "NOT_RUN"  # infeasible input: outside P1, never counted as a pass
    assert st["P2"] == "PASS"
    counts = report["results"]["rules-v1"]["counts"]
    assert counts["p1_outside_scope"] == {"not_jointly_feasible": 1}


def test_progress_subcase_completes_sequentially():
    data = case_dict("B")
    data["jobs"][1].update(flexible=True, deadline_slot=2)
    report = tr.verify_traces([build_trace(data)])
    assert status(report)["P1"] == "PASS"


# --- Property failures ---------------------------------------------------------------------


def test_executed_fault_fails_s3_and_s4():
    trace = build_trace(case_dict("B"), fault=("J1", "J2"), fault_executed=True)
    report = tr.verify_traces([trace])
    st = status(report)
    assert st["S4"] == "FAIL" and st["S3"] == "FAIL"


def test_execution_differing_from_selected_stage_fails_s4():
    data, decisions, result = build_trace(case_dict("A"))
    decisions[0]["proposal_stages"][0]["plan"]["starts"] = [{"job_id": "J2", "start_slot": 0}]
    decisions[0]["execution"]["current_starts"] = ["J1", "J2"]
    report = tr.verify_traces([rebind((data, decisions, result))])
    codes = {x["code"] for x in report["results"]["rules-v1"]["counterexamples"]}
    assert "execution_differs_from_selected_stage" in codes
    assert status(report)["S4"] == "FAIL"


def test_wrong_state_version_fails_s5():
    data, decisions, result = build_trace(case_dict("A"))
    decisions[1]["state_before"]["state_version"] = 7
    report = tr.verify_traces([rebind((data, decisions, result))])
    assert status(report)["S5"] == "FAIL"


def test_result_job_sets_must_match_reconstruction():
    data, decisions, result = build_trace(case_dict("B"), policy=lambda view: ())
    result["completed_job_ids"] = ["J1"]
    report = tr.verify_traces([(data, decisions, result)])
    assert status(report)["P2"] == "FAIL"


def test_never_starting_on_feasible_input_fails_p1():
    report = tr.verify_traces([build_trace(case_dict("A"), policy=lambda view: ())])
    assert status(report)["P1"] == "FAIL"
    assert status(report)["P2"] == "PASS"  # honest accounting of a bad schedule


def test_arithmetic_mismatch_is_reported_not_a_safety_verdict():
    data, decisions, result = build_trace(case_dict("A"))
    decisions[0]["proposal_stages"][0]["arithmetic"][0]["total"] = 999
    report = tr.verify_traces([rebind((data, decisions, result))])
    assert report["results"]["rules-v1"]["arithmetic_consistency"]["mismatches"] == 1
    assert status(report)["S3"] == "PASS"


def test_indeterminate_execution_makes_trace_partial():
    data, decisions, result = build_trace(case_dict("A"))
    decisions[1]["execution"] = {
        "status": "indeterminate",
        "current_starts": [],
        "state_after": None,
    }
    result["status"] = "partial"
    report = tr.verify_traces([rebind((data, decisions, result))])
    assert report["results"]["rules-v1"]["counts"]["partial_traces"] == 1
    assert status(report)["P1"] == "INCOMPLETE"


# --- Fail-closed reading -------------------------------------------------------------------


def _refused(mutate):
    data, decisions, result = build_trace(case_dict("A"))
    mutate(data, decisions, result)
    report = tr.verify_traces([(data, decisions, result)])
    assert len(report["refused_traces"]) == 1, report["refused_traces"]
    assert report["results"] == {}
    return report["refused_traces"][0]["reason"]


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda d, ds, r: ds[0].update(extra=1), "unknown fields"),
        (lambda d, ds, r: ds[0].update(record_kind="x"), "record_kind"),
        (lambda d, ds, r: ds[0].update(adapter_version="proposal-2"), "adapter_version"),
        (lambda d, ds, r: ds[0].update(model_call_count=1), "model_call_count"),
        (lambda d, ds, r: ds[0].update(policy_id="agent"), "identity"),
        (lambda d, ds, r: ds[0]["bindings"].update(code_commit="abc"), "code_commit"),
        (lambda d, ds, r: ds[0]["bindings"].update(spec_sha256=None), "sha256"),
        (lambda d, ds, r: ds[0].update(selected_stage_id="nope"), "names no stage"),
        (lambda d, ds, r: d["jobs"][0].update(power_kw=21), "case_sha256"),
        (lambda d, ds, r: ds.pop(3), "decision_index"),
        (lambda d, ds, r: ds[2]["errors"].append("x"), "decision_sha256s"),
        (lambda d, ds, r: r.update(status="done"), "status"),
    ],
)
def test_contract_breaches_refuse_the_trace(mutate, fragment):
    assert fragment in _refused(mutate)


def test_illustrative_example_is_refused():
    example = json.loads(
        (Path(__file__).parents[2] / "docs/rule_study/adapter_record.example.json").read_text(
            "utf-8"
        )
    )
    data, _, result = build_trace(case_dict("A"))
    result["decision_sha256s"] = [v.canonical_sha256(example)]
    report = tr.verify_traces([(data, [example], result)])
    assert "unknown fields" in report["refused_traces"][0]["reason"]


def test_refused_trace_makes_other_results_incomplete():
    good = build_trace(case_dict("A"))
    bad = build_trace(case_dict("A"))
    bad[1][0]["model_call_count"] = 2
    report = tr.verify_traces([good, bad])
    assert status(report)["S3"] == "INCOMPLETE"


def test_expected_spec_hash_is_enforced():
    report = tr.verify_traces([build_trace(case_dict("A"))], expected_spec_sha256="0" * 64)
    assert "spec_sha256" in report["refused_traces"][0]["reason"]


def test_policies_are_reported_separately():
    report = tr.verify_traces(
        [build_trace(case_dict("A")), build_trace(case_dict("A"), policy_id="greedy_a")]
    )
    assert set(report["results"]) == {"greedy_a", "rules-v1"}


def test_load_trace_dir_round_trip(tmp_path):
    data, decisions, result = build_trace(case_dict("A"))
    (tmp_path / "decisions").mkdir()
    (tmp_path / "case.json").write_text(json.dumps(data), "utf-8")
    (tmp_path / "result.json").write_text(json.dumps(result), "utf-8")
    for d in reversed(decisions):
        name = f"{d['decision_index']:02d}.json"
        (tmp_path / "decisions" / name).write_text(json.dumps(d), "utf-8")
    report = tr.verify_traces([tr.load_trace_dir(tmp_path)])
    assert status(report)["P2"] == "PASS"


def test_cli_trace_mode(tmp_path, capsys):
    import importlib.util

    path = Path(__file__).parents[2] / "scripts/verify_rule_study.py"
    spec = importlib.util.spec_from_file_location("verify_rule_study_trace", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    data, decisions, result = build_trace(case_dict("A"))
    folder = tmp_path / "runs" / "A-rules"
    (folder / "decisions").mkdir(parents=True)
    (folder / "case.json").write_text(json.dumps(data), "utf-8")
    (folder / "result.json").write_text(json.dumps(result), "utf-8")
    for d in decisions:
        (folder / "decisions" / f"{d['decision_index']:02d}.json").write_text(
            json.dumps(d), "utf-8"
        )
    out = tmp_path / "report.json"
    assert cli.main(["--traces", str(tmp_path / "runs"), "--out", str(out)]) == 1
    report = json.loads(out.read_text("utf-8"))
    # Test bindings carry a placeholder spec hash, so the real-spec check refuses them.
    assert "spec_sha256" in report["refused_traces"][0]["reason"]
    with pytest.raises(SystemExit):
        cli.main(["--traces", str(tmp_path / "runs"), "--domain", "primary"])


# Manager review regressions use constructed traces, never real adapter results.
def test_review_executed_empty_plan_is_a_valid_checked_noop():
    data, decisions, result = build_trace(case_dict("A"))
    d = decisions[24]
    d["proposal_stages"] = [{"stage_id": "noop", "origin": "rules-v1", "plan": {"starts": []}}]
    d["selected_stage_id"] = "noop"
    d["execution"]["status"] = "executed"
    report = tr.verify_traces([rebind((data, decisions, result))])
    assert status(report)["S5"] == "PASS"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(model_call_count=0.0),
        lambda d: d["execution"]["state_after"].update(state_version=99),
        lambda d: d["proposal_stages"][0]["arithmetic"][0]["terms"][0].update(value="bad"),
        lambda d: d["proposal_stages"][0]["plan"]["starts"][0].update(extra="unrecognized"),
    ],
)
def test_review_malformed_evidence_is_refused(mutate):
    data, decisions, result = build_trace(case_dict("A"))
    mutate(decisions[0])
    report = tr.verify_traces([rebind((data, decisions, result))])
    assert report["refused_traces"]


def test_review_invalid_future_plan_cannot_supply_current_execution():
    data, decisions, result = build_trace(case_dict("A"))
    # Actual starts are physically valid, but the selected plan also repeats J1 later.
    decisions[0]["proposal_stages"][0]["plan"]["starts"].append({"job_id": "J1", "start_slot": 1})
    report = tr.verify_traces([rebind((data, decisions, result))])
    assert status(report)["S4"] == "FAIL"


def test_review_arithmetic_terms_are_bound_to_input_jobs_and_units():
    data, decisions, result = build_trace(case_dict("A"))
    decisions[0]["proposal_stages"][0]["arithmetic"][0]["terms"][1]["unit"] = "MW"
    report = tr.verify_traces([rebind((data, decisions, result))])
    assert report["results"]["rules-v1"]["arithmetic_consistency"]["status"] == "FAIL"


def test_review_unprovided_artifact_bindings_are_not_claimed_authenticated():
    report = tr.verify_traces([build_trace(case_dict("A"))])
    assert report["binding_validation"]["status"] == "INCOMPLETE"
    assert "external adapter" in report["binding_validation"]["not_authenticated"]


def test_review_unknown_plan_fields_are_refused():
    stale_data, stale_decisions, stale_result = build_trace(case_dict("A"))
    stale_decisions[0]["proposal_stages"][0]["plan"]["state_version"] = 99
    stale = tr.verify_traces([rebind((stale_data, stale_decisions, stale_result))])
    assert "state_version" in stale["refused_traces"][0]["reason"]
    data, decisions, result = build_trace(case_dict("A"))
    decisions[0]["proposal_stages"][0]["plan"]["unknown"] = True
    report = tr.verify_traces([rebind((data, decisions, result))])
    assert "unknown fields" in report["refused_traces"][0]["reason"]


def test_review_trace_mode_obeys_shared_budget():
    report = tr.verify_traces([build_trace(case_dict("A"))], budget=v.Budget(max_states=1))
    assert status(report)["S3"] == "INCOMPLETE"
    assert report["budget"]["ceiling_hit"] == "states"
    assert report["budget"]["states_used"] == 1
