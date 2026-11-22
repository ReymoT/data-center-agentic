"""The merged RULE-03 strict reader and CLI must accept what the runner writes, and fail closed.

Nothing here modifies the reader. Traces come from the real runner/simulator/checker with a
unit-test-only commit value (the tree is uncommitted while tests run). These tests do not
establish frozen-commit verification; that requires a separately accepted artifact handoff.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dc_sustainability.evaluation import rule_study_trace as tr
from dc_sustainability.evaluation import rule_study_verifier as v
from dc_sustainability.rule_study import demo
from tests.rule_study.helpers import REPO_ROOT, TEST_ONLY_COMMIT

SPEC = json.loads((REPO_ROOT / "docs/rule_study/specification.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def traces(tmp_path_factory):
    out = tmp_path_factory.mktemp("compat") / "out"
    demo.run_demo(out, code_commit=TEST_ONLY_COMMIT)
    return out


def _load(folder: Path):
    return tr.load_trace_dir(folder)


def _verify(triples, **kwargs):
    return tr.verify_traces(
        triples, expected_spec_sha256=v.canonical_sha256(SPEC), is_rules_v1_run=True, **kwargs
    )


def _all(traces_dir: Path, policy: str):
    return [_load(p) for p in sorted((traces_dir / policy).iterdir()) if p.is_dir()]


@pytest.mark.parametrize("policy", ["rules-v1", "greedy_a", "greedy_b"])
def test_strict_reader_accepts_every_trace_and_verifies_safety_and_progress(traces, policy):
    report = _verify(_all(traces, policy))
    assert report["refused_traces"] == []
    result = report["results"][policy]
    counts = result["counts"]
    assert counts["traces"] == counts["complete_traces"] == (4 if policy == "rules-v1" else 3)
    assert counts["partial_traces"] == 0 and counts["p2_checked_traces"] == counts["traces"]
    statuses = {p: x["status"] for p, x in result["properties"].items()}
    assert {statuses[p] for p in ("S1", "S2", "S3", "S5", "P1", "P2")} == {"PASS"}
    assert statuses["S4"] == ("PASS" if policy == "rules-v1" else "NOT_RUN")
    assert result["arithmetic_consistency"]["mismatches"] == 0
    assert result["state_hash_continuity"]["checked"] > 0
    assert result["state_hash_continuity"]["mismatches"] == 0
    assert result["counterexample_total"] == 0


def test_rules_v1_arithmetic_is_actually_compared_by_the_reader(traces):
    result = _verify(_all(traces, "rules-v1"))["results"]["rules-v1"]
    assert result["arithmetic_consistency"]["status"] == "PASS"
    assert result["arithmetic_consistency"]["checked"] >= 8


def test_reader_scopes_p1_exactly_as_the_specification_says(traces):
    counts = _verify(_all(traces, "rules-v1"))["results"]["rules-v1"]["counts"]
    # A and B-progress are closed, fault-free and jointly feasible. B is infeasible; B-fault is faulted.
    assert counts["p1_eligible_traces"] == 2
    assert counts["p1_outside_scope"] == {"fault_injected": 1, "not_jointly_feasible": 1}


def test_binding_validation_stays_incomplete_for_unauthenticated_external_artifacts(traces):
    report = _verify(_all(traces, "rules-v1"))
    assert report["binding_validation"]["status"] == "INCOMPLETE"


# --------------------------------------------------------------------------- fail closed
def _copy(traces: Path, tmp_path: Path) -> Path:
    target = tmp_path / "A-rules-v1"
    shutil.copytree(traces / "rules-v1" / "A-rules-v1", target)
    return target


def _refused(folder: Path) -> list:
    return _verify([_load(folder)])["refused_traces"]


def test_untouched_copy_is_accepted(traces, tmp_path):
    assert _refused(_copy(traces, tmp_path)) == []


def test_an_edited_decision_breaks_the_hash_binding(traces, tmp_path):
    folder = _copy(traces, tmp_path)
    path = folder / "decisions" / "decision-05.json"
    record = json.loads(path.read_text())
    record["errors"] = [{"stage": None, "code": "X", "message": "edited"}]
    path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    assert "does not bind the supplied decisions" in _refused(folder)[0]["reason"]


def test_an_unknown_decision_field_is_refused(traces, tmp_path):
    folder = _copy(traces, tmp_path)
    path = folder / "decisions" / "decision-00.json"
    record = json.loads(path.read_text())
    record["state_before"]["visible_state_ref"] = (
        "states/x.json"  # the prior implementation's field
    )
    path.write_text(json.dumps(record))
    assert "unknown fields" in _refused(folder)[0]["reason"]


def test_a_missing_decision_is_refused_or_partial(traces, tmp_path):
    folder = _copy(traces, tmp_path)
    (folder / "decisions" / "decision-29.json").unlink()
    report = _verify([_load(folder)])
    assert (
        report["refused_traces"] or report["results"]["rules-v1"]["counts"]["partial_traces"] == 1
    )


def test_a_changed_case_input_breaks_the_case_hash(traces, tmp_path):
    folder = _copy(traces, tmp_path)
    case = json.loads((folder / "case.json").read_text())
    case["background_kw"] = 10
    (folder / "case.json").write_text(json.dumps(case))
    assert "case_sha256" in _refused(folder)[0]["reason"]


@pytest.mark.parametrize(
    "mutate,expected",
    [
        (lambda r: r.update(model_call_count=0), "unknown fields"),
        (lambda r: r.update(decisions=[]), "unknown fields"),
        (lambda r: r["bindings"].update(code_commit=None), "code_commit"),
        (lambda r: r["bindings"].update(environment_lock_sha256=None), "environment_lock_sha256"),
        (lambda r: r.update(adapter_version="proposal-2"), "not accepted"),
    ],
)
def test_malformed_results_are_refused(traces, tmp_path, mutate, expected):
    folder = _copy(traces, tmp_path)
    result = json.loads((folder / "result.json").read_text())
    mutate(result)
    (folder / "result.json").write_text(json.dumps(result))
    assert expected in _refused(folder)[0]["reason"]


def test_a_wrong_specification_hash_is_refused(traces, tmp_path):
    folder = _copy(traces, tmp_path)
    triple = _load(folder)
    bad = tr.verify_traces([triple], expected_spec_sha256="1" * 63 + "2", is_rules_v1_run=True)
    assert "spec_sha256" in bad["refused_traces"][0]["reason"]


def test_the_illustrative_example_is_refused_by_the_reader():
    example = json.loads((REPO_ROOT / "docs/rule_study/adapter_record.example.json").read_text())
    case = {"case_id": "A", "capacity_kw": 60, "background_kw": 20, "jobs": [], "scores": None}
    report = _verify([(case, [example], example)])
    assert report["refused_traces"]


# --------------------------------------------------------------------------- the CLI
def test_cli_verifies_the_traces_writes_an_exclusive_report_and_exits_incomplete(traces, tmp_path):
    out = tmp_path / "report.json"
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/verify_rule_study.py"),
        "--traces",
        str(traces / "rules-v1"),
        "--rules-v1",
        "--out",
        str(out),
    ]
    done = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    # Exit 2 = binding validation INCOMPLETE (external artifacts are never authenticated by the
    # reader); it must not be 1 (FAIL/refused).
    assert done.returncode == 2, done.stdout + done.stderr
    report = json.loads(out.read_text())
    assert report["refused_traces"] == []
    again = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    assert again.returncode != 0 and "refusing to overwrite" in (again.stdout + again.stderr)
