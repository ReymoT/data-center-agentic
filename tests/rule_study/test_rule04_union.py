"""Artificial retained-file fixtures only; no scientific execution or invented findings."""

import copy
import json
from types import SimpleNamespace

import pytest

from scripts import build_rule04_union as u


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return u.core._sha(path)


@pytest.fixture
def union(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(u.w, "ROOT", root)
    write(
        root / "docs/rule_study/RULE03_VERIFICATION_BASELINE_NOV23.json",
        {"baseline_code_sha256": {"science": "fixed"}},
    )
    parsed = {"A": SimpleNamespace(scores={})}
    monkeypatch.setattr(u.w, "pair", lambda: ({}, {}, parsed))
    selected = [("A", "greedy_b")]
    monkeypatch.setattr(u.suffix, "selection", lambda *a, **k: selected)
    runs, requests = [], []
    for index, policies in enumerate((u.w.POLICIES[:2], u.w.POLICIES[2:])):
        folder = tmp_path / f"attempt-{index}"
        folder.mkdir()
        request = {
            "kind": u.w.KIND if index == 0 else u.w.SUFFIX_KIND,
            "plan": {
                "code_commit": f"source-{index}",
                "code_sha256": {"science": "fixed"},
                "inputs": {k: {"sha256": v[1]} for k, v in u.w.INPUTS.items()},
                "output_directory": str(folder),
                "proposed_authorization_id": f"fixture-{index}",
            },
            "limits": {"states": 180, "transitions": 180},
            "freeze_reference": "fixture",
        }
        metrics = []
        for policy in policies:
            m = {
                "case_id": "A",
                "policy_id": policy,
                "case_sha256": "same-case",
                "code_commit": f"source-{index}",
                "bindings": {"code_commit": f"source-{index}"},
                "status": "complete",
                "execution_violations": 0,
                "executed_starts": 1,
                "checked_decisions": 30,
                "jobs": 1,
                "completed": 1,
                "missed": 0,
                "unfinished": 0,
                "completed_job_ids": ["J"],
                "missed_job_ids": [],
                "unfinished_job_ids": [],
                "turnaround_slots": {"values": [1]},
                "start_delay_slots": {"values": [0]},
                "fallback": {"selected": 0, "blocked_decisions": 0},
                "synthetic_impact": {"recomputed_total": 100, "matches_producer": True},
            }
            metrics.append(m)
            write(
                folder / f"A-{policy}" / "pair-result.json",
                {
                    "metric": m,
                    "budget": {"states_used": 60, "transitions_used": 60},
                    "execution_signature": "a" * 64,
                },
            )
        status = {
            "status": "FAIL_OR_INCOMPLETE" if index == 0 else "PASS",
            "charged_steps_completed_pairs_only" if index == 0 else "charged_steps": {
                "states": 60 * len(policies),
                "transitions": 60 * len(policies),
            },
        }
        write(folder / ("rollout-failure.json" if index == 0 else "rollout-report.json"), status)
        runs.append(
            {
                "metrics": metrics,
                "strata": {"A": "normal_feasible"},
                "failed": [],
                "complete": False,
                "run_status": status["status"],
                "recovered_unacknowledged_pairs": 0,
            }
        )
        requests.append(request)
    old_path = tmp_path / "parent-request.json"
    old_sha = write(old_path, requests[0])
    parent_path = tmp_path / "parent-receipt.json"
    parent_sha = write(
        parent_path,
        {
            "output": requests[0]["plan"]["output_directory"],
            "request": {"path": str(old_path), "sha256": old_sha},
        },
    )
    requests[1]["parent"] = {"path": str(parent_path), "sha256": parent_sha}
    path = tmp_path / "suffix.json"
    receipt_path = tmp_path / "union.json"
    outcome = {"status": "succeeded", "cleanup_verified": True, "retry_allowed": False}

    def refresh():
        sha = write(path, requests[1])
        for i, digest in enumerate((old_sha, sha)):
            runs[i]["authenticated_request_sha256"] = digest
            folder = tmp_path / f"attempt-{i}"
            for pair in folder.glob("*/pair-result.json"):
                record = u.w.read_json(pair)
                record["authenticated_request_sha256"] = digest
                write(pair, record)
        plan = requests[1]["plan"]
        entry = (
            root.parent
            / "RuleStudy_Run_Ledger"
            / (u.w.pf.sha(plan["proposed_authorization_id"].encode()) + ".json")
        )
        write(
            entry,
            {
                "receipt": {
                    "request_sha256": sha,
                    "code_commit": plan["code_commit"],
                    "authorization_id": plan["proposed_authorization_id"],
                    "limits": requests[1]["limits"],
                    "output_directory": plan["output_directory"],
                    "freeze_reference": "fixture",
                    "actor": "MattyAnd",
                    "decision": "approved",
                    "protocol_freeze_authenticated": True,
                    "operation": "retained_development_unexecuted_suffix_execution_and_replay",
                }
            },
        )
        outcome["authenticated_request_sha256"] = sha
        write(entry.with_suffix(".result.json"), outcome)
        digest = write(
            receipt_path,
            {
                "kind": "rule04_union_v1",
                "request": {"path": str(path), "sha256": sha},
                "artifacts": u.inventory(tmp_path / "attempt-1"),
            },
        )
        return digest, entry

    monkeypatch.setattr(u.core, "load_run", lambda p: copy.deepcopy(runs[int(p.name[-1])]))
    return SimpleNamespace(
        path=receipt_path,
        refresh=refresh,
        runs=runs,
        requests=requests,
        root=tmp_path,
        selected=selected,
        outcome=outcome,
        parsed=parsed,
    )


def test_complete_union_keeps_failure_authorities_and_split_source_unavailable(union):
    digest, _ = union.refresh()
    before = {p: p.read_bytes() for p in union.root.rglob("*") if p.is_file()}
    result = u.build(union.path, digest)
    assert result["coverage_status"] == "COMPLETE"
    assert result["run_status"] == "COMBINED_COVERAGE_ONLY"
    assert result["attempts"][0]["status"]["status"] == "FAIL_OR_INCOMPLETE"
    assert result["cumulative_completed_pair_counters"] == {"states": 180, "transitions": 180}
    assert result["comparison_rows"][1]["unavailable_reasons"] == {"source_bindings_differ": 1}
    assert "PENDING" in result["scientific_acceptance"]
    assert before == {p: p.read_bytes() for p in union.root.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    "mode",
    [
        "request",
        "inventory",
        "cleanup",
        "authority",
        "science",
        "inputs",
        "counter",
        "limit",
        "source",
        "overlap",
        "gap",
        "recovered",
        "outcome",
        "control",
    ],
)
def test_tampering_and_unsafe_union_refused(union, mode):
    if mode == "science":
        union.requests[1]["plan"]["code_sha256"]["science"] = "changed"
    if mode == "inputs":
        union.requests[1]["plan"]["inputs"]["development_cases"]["sha256"] = "changed"
    if mode == "limit":
        union.requests[1]["limits"]["states"] = 0
    if mode == "source":
        union.runs[1]["metrics"][0]["code_commit"] = "wrong"
    if mode == "overlap":
        union.runs[1]["metrics"][0]["policy_id"] = "rules-v1"
        union.selected[:] = [("A", "rules-v1")]
    if mode == "gap":
        union.selected.insert(0, ("A", "greedy_a"))
    if mode == "recovered":
        union.runs[1]["recovered_unacknowledged_pairs"] = 1
    if mode == "outcome":
        union.outcome["status"] = "failed_cleanup"
    if mode == "control":
        union.parsed["A"].scores = None
        p = union.root / "attempt-1/A-greedy_b/pair-result.json"
        value = u.w.read_json(p)
        value["execution_signature"] = "b" * 64
        write(p, value)
    if mode == "counter":
        p = union.root / "attempt-1/rollout-report.json"
        write(p, {"status": "PASS", "charged_steps": {"states": 61, "transitions": 60}})
    digest, entry = union.refresh()
    if mode == "request":
        (union.root / "suffix.json").write_text("{}")
    if mode == "inventory":
        (union.root / "attempt-1/new-file").write_text("unexpected")
    if mode in ("cleanup", "authority"):
        p = entry.with_suffix(".result.json") if mode == "cleanup" else entry
        value = u.w.read_json(p)
        if mode == "cleanup":
            value["cleanup_verified"] = False
        else:
            value["receipt"]["decision"] = "not-approved"
        write(p, value)
    with pytest.raises((ValueError, FileNotFoundError)):
        u.build(union.path, digest)


def test_partial_suffix_keeps_partial_coverage_and_unknown_work(union):
    union.runs[1]["metrics"] = []
    union.runs[1]["run_status"] = "FAIL_OR_INCOMPLETE"
    union.outcome["status"] = "failed"
    folder = union.root / "attempt-1"
    # An artificial empty stopped child; original fixture pair removed before receipt.
    (folder / "A-greedy_b/pair-result.json").unlink()
    (folder / "A-greedy_b").rmdir()
    (folder / "rollout-report.json").unlink()
    write(
        folder / "rollout-failure.json",
        {
            "status": "FAIL_OR_INCOMPLETE",
            "charged_steps_completed_pairs_only": {"states": 0, "transitions": 0},
        },
    )
    digest, _ = union.refresh()
    result = u.build(union.path, digest)
    assert result["coverage_status"] == "PARTIAL"
    assert "not established" in result["cumulative_total_work"]


def test_cli_refuses_bad_hash_without_creating_output(union):
    union.refresh()
    out = union.root / "report"
    assert u.main(["--receipt", str(union.path), "--sha256", "bad", "--out", str(out)]) == 1
    assert not out.exists()


def test_cli_writes_summary_and_refuses_overwrite(union):
    digest, _ = union.refresh()
    out = union.root / "report"
    args = ["--receipt", str(union.path), "--sha256", digest, "--out", str(out)]
    assert u.main(args) == 0
    assert {p.name for p in out.iterdir()} == {
        "summary.json",
        "RULE04_TABLES.md",
        "turnaround_vs_impact.svg",
    }
    assert u.w.read_json(out / "summary.json")["attempts"][0]["completed_pairs"] == 2
    assert u.main(args) == 1


def test_failed_foreign_pair_refused(union):
    union.runs[1]["failed"] = [{"case_id": "foreign", "policy_id": "greedy_b"}]
    digest, _ = union.refresh()
    with pytest.raises(ValueError, match="next selected pair"):
        u.build(union.path, digest)


def test_inventory_drift_after_arithmetic_refused(union, monkeypatch):
    digest, _ = union.refresh()
    original = u.core.summarize

    def changed(data):
        result = original(data)
        (union.root / "attempt-1/drift").write_text("changed after validation")
        return result

    monkeypatch.setattr(u.core, "summarize", changed)
    with pytest.raises(ValueError, match="changed during union"):
        u.build(union.path, digest)
