"""RULE-03 receiving of the current RULE-02 implementation: pin, mapping, artifacts, replay.

Runs use the real runner/simulator/production checker on authored and a few primary-domain
cases with a unit-test-only commit, so binding status stays INCOMPLETE by design. These tests
are not a frozen-system verification result.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dc_sustainability.evaluation import rule_study_receiving as rv
from dc_sustainability.evaluation import rule_study_verifier as v
from dc_sustainability.rule_study import cases as rcases
from dc_sustainability.rule_study import runner as rr

ROOT = Path(__file__).parents[2]
SPEC = json.loads((ROOT / "docs/rule_study/specification.json").read_text("utf-8"))
TEST_COMMIT = "0123456789abcdef0123456789abcdef01234567"
AUTHORED = v.authored_cases(SPEC)
PRIMARY = v.primary_domain()[:3]


@pytest.fixture(scope="module")
def received(tmp_path_factory):
    out = tmp_path_factory.mktemp("rcv") / "runs"
    report = rv.run_receiving(
        ["authored", "primary"],
        ["rules-v1", "greedy_a"],
        out,
        ROOT,
        SPEC,
        code_commit=TEST_COMMIT,
        cases_by_domain={"authored": AUTHORED, "primary": PRIMARY},
    )
    return out, report


def _folders(out, domain, policy):
    return sorted(p for p in (out / domain / policy).iterdir() if p.is_dir())


def _pin():
    return rv.reconstruct_pin(ROOT, code_commit=TEST_COMMIT)


def _git_like_pin():
    return {**_pin(), "commit_source": "git", "clean_tree": True, "merged_main": True}


# --------------------------------------------------------------------------- pin


def test_independent_pin_matches_the_runner_bindings():
    case = rv.case_spec_for(AUTHORED[0])
    bindings = rr.make_bindings(case, ROOT, code_commit=TEST_COMMIT).model_dump()
    pin = _pin()
    for key in rv.BINDING_FIELDS:
        if key != "case_sha256":
            assert pin[key] == bindings[key], key
    assert pin["commit_source"] == "test_only_override" and pin["clean_tree"] is None


def test_pin_lists_every_adapter_source():
    pin = _pin()
    names = sorted(p.name for p in (ROOT / "dc_sustainability/rule_study").glob("*.py"))
    assert sorted(pin["adapter_files"]) == names
    assert pin["adapter_source_sha256"] == v.canonical_sha256(pin["adapter_files"])


def test_git_pin_reports_commit_and_tree_state():
    pin = rv.reconstruct_pin(ROOT)
    assert len(pin["code_commit"]) == 40 and pin["commit_source"] == "git"
    assert isinstance(pin["clean_tree"], bool)


# --------------------------------------------------------------------------- mapping


@pytest.mark.parametrize("case", AUTHORED, ids=lambda c: c.case_id)
def test_authored_mapping_matches_the_runner_authored_cases(case):
    mine = rv.case_spec_for(case)
    theirs = rcases.AUTHORED_CASES[case.case_id]
    assert mine.case_json() == theirs.case_json()
    assert mine.case_sha256() == theirs.case_sha256()


def test_primary_mapping_preserves_the_case_exactly():
    for case in v.primary_domain():
        spec = rv.case_spec_for(case)
        data = spec.case_json()
        assert data["case_id"] == case.case_id
        assert (data["capacity_kw"], data["background_kw"]) == (30, 10)
        assert tuple(data["scores"]) == case.scores and spec.pue == 1.0
        assert [j["job_id"] for j in data["jobs"]] == [j.job_id for j in case.jobs]


def test_missing_forecast_maps_to_withheld_scores():
    case = v.Case("M-1", 60, 20, AUTHORED[0].jobs, None)
    spec = rv.case_spec_for(case)
    assert spec.forecast_present is False and spec.case_json()["scores"] is None
    assert spec.episode_id == "EP-RCVM1"


def test_domains_and_runs():
    assert len(rv.domain_cases("primary", SPEC)) == 64
    assert len(rv.domain_cases("extended", SPEC)) == 1024
    assert len(rv._runs(AUTHORED, ["rules-v1"])) == 4
    # Baselines skip the injected fault case.
    assert len(rv._runs(AUTHORED, ["greedy_a", "greedy_b"])) == 6
    with pytest.raises(ValueError):
        rv.domain_cases("final", SPEC)
    with pytest.raises(ValueError):
        rv._check_policies(["rules-v1", "rules-v1"])


def test_plan_runs_nothing():
    plan = rv.plan_receiving(["primary", "authored"], ["rules-v1"], ROOT, SPEC)
    assert plan["status"] == "NOT_RUN"
    assert (plan["domains"]["primary"]["cases"], plan["domains"]["primary"]["runs"]) == (64, 64)
    assert plan["domains"]["authored"]["runs"] == 4


# --------------------------------------------------------------------------- real runs


def test_real_runs_replay_with_all_properties_passing(received):
    _, report = received
    for name, section in report["domains"].items():
        assert section["run_errors"] == [] and section["replay"]["refused_traces"] == []
        assert section["binding_check"]["findings"] == {}
        for policy, props in section["property_statuses"].items():
            core = {props[p] for p in ("S1", "S2", "S3", "S5", "P1", "P2")}
            assert core == {"PASS"}, (name, policy)
        assert section["arithmetic"]["rules-v1"] == "PASS"
    assert report["domains"]["authored"]["property_statuses"]["rules-v1"]["S4"] == "PASS"
    assert report["domains"]["authored"]["runs_completed"] == 7
    assert report["domains"]["primary"]["runs_completed"] == 6


def test_test_only_commit_keeps_binding_incomplete(received):
    _, report = received
    assert {s["binding_check"]["status"] for s in report["domains"].values()} == {"INCOMPLETE"}
    assert report["overall"] == "INCOMPLETE"


def test_clean_git_pin_would_pass(received):
    out, _ = received
    folders = [("x", "rules-v1", f) for f in _folders(out, "authored", "rules-v1")]
    section = rv._receive_folders("authored", 4, folders, [], _git_like_pin(), SPEC)
    assert section["binding_check"]["status"] == "PASS"
    assert section["overall"] == "PASS"


def test_dirty_tree_is_incomplete(received):
    out, _ = received
    folders = [("x", "rules-v1", f) for f in _folders(out, "authored", "rules-v1")]
    pin = {**_git_like_pin(), "clean_tree": False}
    assert rv._receive_folders("authored", 4, folders, [], pin, SPEC)["overall"] == "INCOMPLETE"


def test_run_receiving_refuses_existing_directory(tmp_path):
    with pytest.raises(FileExistsError):
        rv.run_receiving(["authored"], ["rules-v1"], tmp_path, ROOT, SPEC, code_commit=TEST_COMMIT)


# --------------------------------------------------------------------------- tampering


@pytest.fixture
def copy_a(received, tmp_path):
    out, _ = received
    src = next(f for f in _folders(out, "authored", "rules-v1") if f.name == "A-rules-v1")
    dst = tmp_path / "A-rules-v1"
    shutil.copytree(src, dst)
    return dst


def _findings(folder, pin=None):
    return rv.check_trace_artifacts(folder, pin or _pin())


def test_clean_copy_has_no_findings(copy_a):
    assert _findings(copy_a) == []


def test_other_commit_is_a_binding_finding(copy_a):
    pin = {**_pin(), "code_commit": "f" * 39 + "e"}
    assert any("code_commit differs" in f for f in _findings(copy_a, pin))


def test_changed_adapter_hash_is_a_binding_finding(copy_a):
    pin = {**_pin(), "adapter_source_sha256": "1" * 64}
    assert any("adapter_source_sha256" in f for f in _findings(copy_a, pin))


def test_edited_raw_state_is_detected(copy_a):
    state = sorted((copy_a / "states").glob("*.json"))[0]
    state.write_bytes(state.read_bytes() + b" ")
    assert any("does not match its name" in f for f in _findings(copy_a))


def test_missing_snapshot_is_detected(copy_a):
    for p in (copy_a / "snapshots").glob("*.json"):
        p.unlink()
    assert any("snapshots/" in f and "missing" in f for f in _findings(copy_a))


def test_edited_transition_is_detected(copy_a):
    t = copy_a / "transitions" / "transition-00.json"
    t.write_bytes(t.read_bytes() + b" ")
    assert any("transition content" in f for f in _findings(copy_a))


def test_missing_completion_commitment_is_detected(copy_a):
    (copy_a / ".completed" / "decision-00.json").unlink()
    assert any("completion commitment" in f for f in _findings(copy_a))


def test_edited_case_json_breaks_case_binding(copy_a):
    case = copy_a / "case.json"
    case.write_bytes(case.read_bytes().replace(b'"J1"', b'"J9"', 1))
    assert any("case_sha256 differs" in f for f in _findings(copy_a))


def test_tampered_folder_fails_the_section(copy_a):
    (copy_a / ".completed" / "decision-00.json").unlink()
    section = rv._receive_folders("t", 1, [("A", "rules-v1", copy_a)], [], _git_like_pin(), SPEC)
    assert section["binding_check"]["status"] == "FAIL" and section["overall"] == "FAIL"


def test_receive_existing_reads_supplied_folders(copy_a):
    report = rv.receive_existing([copy_a], ROOT, SPEC, code_commit=TEST_COMMIT)
    section = report["domains"]["supplied"]
    assert section["runs_completed"] == 1 and section["binding_check"]["findings"] == {}
    assert report["policies"] == ["rules-v1"]


def test_run_error_is_recorded_not_hidden(tmp_path):
    bad = v.Case("!!!", 60, 20, AUTHORED[0].jobs, AUTHORED[0].scores)
    report = rv.run_receiving(
        ["authored"],
        ["rules-v1"],
        tmp_path / "runs",
        ROOT,
        SPEC,
        code_commit=TEST_COMMIT,
        cases_by_domain={"authored": [bad]},
    )
    section = report["domains"]["authored"]
    assert section["run_errors"] and section["overall"] == "FAIL"


# --------------------------------------------------------------------------- CLI


def _cli(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/receive_rule_study_system.py"), *args],
        capture_output=True,
        text=True,
    )


def test_cli_plan_only_by_default(tmp_path):
    result = _cli("--domain", "authored", "--out", str(tmp_path / "never"))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "NOT_RUN"
    assert not (tmp_path / "never").exists()


def test_cli_execute_refuses_missing_or_existing_out(tmp_path):
    assert _cli("--domain", "authored", "--execute").returncode != 0
    result = _cli("--domain", "authored", "--execute", "--out", str(tmp_path))
    assert result.returncode != 0 and "refusing to reuse" in result.stderr


def test_cli_cannot_turn_execute_flag_into_uncontained_approval(tmp_path):
    out = tmp_path / "never"
    result = _cli("--domain", "authored", "--execute", "--out", str(out))
    assert result.returncode != 0 and "Uncontained" in result.stderr
    assert not out.exists()


@pytest.mark.parametrize(
    "domains", [[], ["primary", "primary"], ["extended"], ["extended", "primary"]]
)
def test_invalid_or_duplicate_domains_never_plan_a_run(domains):
    with pytest.raises(ValueError):
        rv.plan_receiving(domains, ["rules-v1"], ROOT, SPEC)


def test_one_budget_stops_actual_runner_and_is_shared_with_later_domains(tmp_path):
    budget = v.Budget(max_states=1, max_transitions=1, max_seconds=30)
    report = rv.run_receiving(
        ["authored", "primary"],
        ["rules-v1"],
        tmp_path / "runs",
        ROOT,
        SPEC,
        code_commit=TEST_COMMIT,
        cases_by_domain={"authored": AUTHORED[:1], "primary": PRIMARY},
        budget=budget,
    )
    assert report["overall"] == "INCOMPLETE"
    assert report["combined_budget"]["states_used"] == 1
    assert report["combined_budget"]["transitions_used"] == 1
    assert report["domains"]["primary"]["runs_completed"] == 0
    assert (
        len(
            [
                p
                for p in (tmp_path / "runs").rglob("decision-*.json")
                if p.parent.name == "decisions"
            ]
        )
        == 1
    )


def test_oversized_combined_budget_is_rejected_before_output(tmp_path):
    with pytest.raises(ValueError, match="combined accepted"):
        rv.run_receiving(
            ["authored"],
            ["rules-v1"],
            tmp_path / "never",
            ROOT,
            SPEC,
            budget=v.Budget(max_states=10_001),
        )
    assert not (tmp_path / "never").exists()


def test_malformed_artifact_becomes_finding_and_is_not_replayed(copy_a, monkeypatch):
    (copy_a / "result.json").write_text("not JSON", encoding="utf-8")
    monkeypatch.setattr(
        rv.tr, "load_trace_dir", lambda path: pytest.fail("bad artifacts must not be reread")
    )
    section = rv._receive_folders("bad", 1, [("A", "rules-v1", copy_a)], [], _git_like_pin(), SPEC)
    assert section["overall"] == "FAIL"
    assert section["binding_check"]["findings"]


def test_missing_decision_cannot_pass_artifact_receiving(copy_a):
    (copy_a / "decisions/decision-05.json").unlink()
    assert any("decision" in x for x in _findings(copy_a))


def test_clean_unmerged_pin_cannot_pass_receiving(copy_a):
    pin = {**_git_like_pin(), "merged_main": False}
    section = rv._receive_folders("supplied", 1, [("A", "rules-v1", copy_a)], [], pin, SPEC)
    assert section["binding_check"]["status"] == "INCOMPLETE"
    assert section["overall"] == "INCOMPLETE"


def test_unaccepted_spec_cannot_plan_or_execute(tmp_path):
    changed = dict(SPEC, unaccepted=True)
    with pytest.raises(ValueError, match="unsupported"):
        rv.plan_receiving(["authored"], ["rules-v1"], ROOT, changed)
    with pytest.raises(ValueError, match="unsupported"):
        rv.run_receiving(["authored"], ["rules-v1"], tmp_path / "never", ROOT, changed)
    assert not (tmp_path / "never").exists()
