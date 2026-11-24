"""RULE-04 metric records: hand-built run records, no policy or simulator runs."""

import hashlib
import json
import tarfile
from pathlib import Path

import pytest

from scripts import rule_study_metrics_core as m

SCORES = [300, 100] + [200] * 28


def case(case_id="A", scores=SCORES):
    return {
        "case_id": case_id,
        "capacity_kw": 60,
        "background_kw": 20,
        "jobs": [
            {
                "job_id": "J1",
                "power_kw": 20,
                "duration_slots": 1,
                "arrival_slot": 0,
                "deadline_slot": 3,
                "flexible": True,
            },
            {
                "job_id": "J2",
                "power_kw": 20,
                "duration_slots": 1,
                "arrival_slot": 0,
                "deadline_slot": 1,
                "flexible": False,
            },
        ],
        "scores": scores,
    }


def result(policy, starts, *, case_id="A", case_sha="c" * 64, missed=()):
    missed = missed or tuple(sorted({"J1", "J2"} - starts.keys()))
    per_job = [
        {
            "job_id": j,
            "power_kw": 20,
            "start_slot": s,
            "end_slot": s + 1,
            "synthetic_impact": 20 * SCORES[s],
        }
        for j, s in starts.items()
    ]
    return {
        "record_kind": "rule_study_result_v1",
        "case_id": case_id,
        "policy_id": policy,
        "status": "complete",
        "bindings": {"case_sha256": case_sha, "code_commit": "abc"},
        "completed_job_ids": sorted(starts),
        "missed_job_ids": list(missed),
        "unfinished_job_ids": list(missed),
        "accounting": {
            "per_job": per_job,
            "pue": 1.0,
            "slot_hours": 1.0,
            "synthetic_impact_total": sum(j["synthetic_impact"] for j in per_job),
        },
    }


def decision(index, starts, *, status="pass", origin="rules-v1", selected=True, blocked=False):
    stage = {"stage_id": "STG-0", "origin": origin, "check_result": {"status": status}}
    return {
        "decision_index": index,
        "selected_stage_id": "STG-0" if selected else None,
        "proposal_stages": [stage],
        "errors": [{"code": "NO_APPROVED_CANDIDATE"}] if blocked else [],
        "execution": {"current_starts": starts, "status": "blocked" if blocked else "executed"},
    }


def test_completed_turnaround_delay_and_impact():
    rec = m.run_metrics(
        case(), result("rules-v1", {"J1": 1, "J2": 0}), [decision(0, ["J2"]), decision(1, ["J1"])]
    )
    assert (rec["completed"], rec["missed"], rec["unfinished"]) == (2, 0, 0)
    assert rec["turnaround_slots"] == {"values": [1, 2], "count": 2}
    assert rec["start_delay_slots"] == {"values": [0, 1], "count": 2}
    assert rec["synthetic_impact"]["producer_total"] == 20 * 300 + 20 * 100
    assert rec["synthetic_impact"]["matches_producer"] is True
    assert rec["execution_violations"] == 0 and rec["executed_starts"] == 2


def test_executed_start_without_a_passing_selected_stage_is_a_violation():
    rec = m.run_metrics(case(), result("rules-v1", {"J2": 0}), [decision(0, ["J2"], status="fail")])
    assert rec["execution_violations"] == 1
    rec = m.run_metrics(
        case(), result("rules-v1", {"J2": 0}), [decision(0, ["J2"], selected=False)]
    )
    assert rec["execution_violations"] == 1


def test_producer_impact_mismatch_is_reported_not_hidden():
    bad = result("rules-v1", {"J2": 0})
    bad["accounting"]["synthetic_impact_total"] += 1
    rec = m.run_metrics(case(), bad, [decision(0, ["J2"])])
    assert rec["synthetic_impact"]["matches_producer"] is False


def test_hidden_weights_are_not_recomputed():
    rec = m.run_metrics(case(scores=None), result("greedy_a", {"J2": 0}), [decision(0, ["J2"])])
    assert rec["synthetic_impact"]["recomputed_total"] is None
    assert rec["synthetic_impact"]["matches_producer"] is None


def test_fallback_and_blocked_decisions_are_counted():
    d = decision(0, [], origin=m.FALLBACK_ORIGIN, selected=False, blocked=True)
    rec = m.run_metrics(case(), result("rules-v1", {}, missed=("J1", "J2")), [d])
    assert rec["fallback"]["attempted_stages"] == 1
    assert rec["fallback"]["selected"] == 0
    assert rec["fallback"]["blocked_decisions"] == 1
    assert rec["fallback"]["error_codes"] == {"NO_APPROVED_CANDIDATE": 1}


def _rec(policy, starts, **kw):
    return m.run_metrics(case(), result(policy, starts, **kw), [decision(0, [])])


def test_equal_work_reduction_only_on_matching_work():
    rows = m.equal_work(
        [_rec("greedy_a", {"J1": 0, "J2": 0}), _rec("rules-v1", {"J1": 1, "J2": 0})]
    )
    assert rows == [
        {
            "case_id": "A",
            "policy_id": "rules-v1",
            "available": True,
            "greedy_a_total": 12000,
            "policy_total": 8000,
            "reduction": pytest.approx(1 / 3),
        }
    ]


@pytest.mark.parametrize(
    ("other", "reason"),
    [
        ({"policy": "rules-v1", "starts": {"J2": 0}, "missed": ("J1",)}, "job_outcome_sets_differ"),
        (
            {"policy": "rules-v1", "starts": {"J1": 0, "J2": 0}, "case_sha": "d" * 64},
            "case_hash_differs",
        ),
    ],
)
def test_equal_work_unavailable_is_never_zero(other, reason):
    base = _rec("greedy_a", {"J1": 0, "J2": 0})
    rec = _rec(
        other["policy"],
        other["starts"],
        missed=other.get("missed", ()),
        case_sha=other.get("case_sha", "c" * 64),
    )
    (row,) = m.equal_work([base, rec])
    assert row == {"case_id": "A", "policy_id": "rules-v1", "available": False, "reason": reason}


def test_equal_work_needs_a_positive_baseline_and_a_baseline_run():
    empty = _rec("greedy_a", {}, missed=("J1", "J2"))
    (row,) = m.equal_work([empty, _rec("rules-v1", {}, missed=("J1", "J2"))])
    assert row["reason"] == "greedy_a_impact_not_positive"
    (row,) = m.equal_work([_rec("rules-v1", {"J2": 0})])
    assert row["reason"] == "no_greedy_a_run_for_case"


def test_load_run_and_report_from_folders(tmp_path):
    folder = tmp_path / "A-rules-v1"
    (folder / "decisions").mkdir(parents=True)
    (folder / "case.json").write_text(json.dumps(case()), "utf-8")
    (folder / "result.json").write_text(json.dumps(result("rules-v1", {"J2": 0})), "utf-8")
    (folder / "decisions" / "decision-00.json").write_text(json.dumps(decision(0, ["J2"])), "utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        m.metrics_report([folder], label="fixture")
    (folder / "decisions" / "decision-02.json").write_text(json.dumps(decision(2, [])), "utf-8")
    with pytest.raises(ValueError, match="contiguous"):
        m.load_run(folder)


def test_equal_work_refuses_impact_mismatch():
    a = _rec("greedy_a", {"J1": 0, "J2": 0})
    other = _rec("rules-v1", {"J1": 1, "J2": 0})
    other["synthetic_impact"]["matches_producer"] = False
    assert m.equal_work([a, other])[0]["available"] is False


def test_equal_work_refuses_unchecked_impact_and_violations():
    a = _rec("greedy_a", {"J1": 0, "J2": 0})
    other = _rec("rules-v1", {"J1": 1, "J2": 0})
    a["synthetic_impact"]["matches_producer"] = None
    assert m.equal_work([a, other])[0]["available"] is False
    a["synthetic_impact"]["matches_producer"] = True
    other["execution_violations"] = 1
    assert m.equal_work([a, other])[0]["available"] is False


def test_duplicate_policy_cannot_silently_replace_baseline():
    a = _rec("greedy_a", {"J1": 0, "J2": 0})
    with pytest.raises(ValueError, match="duplicate"):
        m.equal_work([a, a, _rec("rules-v1", {"J1": 1, "J2": 0})])


def test_different_producer_and_incomplete_run_are_not_comparable():
    a = _rec("greedy_a", {"J1": 0, "J2": 0})
    other = _rec("rules-v1", {"J1": 1, "J2": 0})
    other["code_commit"] = "another producer"
    assert m.equal_work([a, other])[0]["available"] is False
    other["code_commit"] = a["code_commit"]
    other["status"] = "partial"
    assert m.equal_work([a, other])[0]["available"] is False


def test_selected_current_starts_must_match_execution():
    d = decision(0, ["J1"])
    d["proposal_stages"][0]["plan"] = {"starts": [{"job_id": "J2", "start_slot": 0}]}
    rec = m.run_metrics(case(), result("rules-v1", {"J1": 0}), [d])
    assert rec["execution_violations"] == 1


def test_accounting_cannot_drop_or_change_completed_work():
    r = result("rules-v1", {"J1": 0, "J2": 0})
    r["accounting"]["per_job"].pop()
    with pytest.raises(ValueError, match="coverage"):
        m.run_metrics(case(), r, [])
    r = result("rules-v1", {"J1": 0})
    r["accounting"]["per_job"][0]["power_kw"] = 1
    with pytest.raises(ValueError, match="power"):
        m.run_metrics(case(), r, [])


@pytest.mark.parametrize("text", ['{"x":1,"x":2}', '{"x":NaN}', "[]"])
def test_metric_json_is_strict(tmp_path, text):
    path = tmp_path / "input.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        m._load(path)


def test_saved_authored_metrics_and_corruption_refusal(tmp_path):
    evidence = Path(__file__).resolve().parents[2] / "docs/evidence/rule03-nov23-native"
    raw = (evidence / "authored-artifacts.tar.gz").read_bytes()
    receipt = json.loads((evidence / "attempt-receipt.json").read_bytes())
    assert hashlib.sha256(raw).hexdigest() == receipt["authored_archive_sha256"]
    with tarfile.open(evidence / "authored-artifacts.tar.gz", "r:gz") as archive:
        for member in archive:
            parts = Path(member.name).parts
            if len(parts) >= 3 and parts[2] in ("A-greedy_a", "A-rules-v1"):
                assert member.isfile() and not member.name.startswith("/") and ".." not in parts
                target = tmp_path.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
    a = tmp_path / "authored/greedy_a/A-greedy_a"
    r = tmp_path / "authored/rules-v1/A-rules-v1"
    report = m.metrics_report([a, r], label="retained-file read only")
    assert len(report["runs"]) == 2
    assert all(row["execution_violations"] == 0 for row in report["runs"])
    assert report["equal_work_vs_greedy_a"][0]["reduction"] == pytest.approx(1 / 3)
    result_path = r / "result.json"
    data = json.loads(result_path.read_bytes())
    data["decision_sha256s"][0] = "0" * 64
    result_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        m.metrics_report([a, r], label="corrupt retained fixture")
