"""Pending-plan controls with explicit synthetic bindings; no human approval fabricated."""

import copy
import json
import os

import pytest

from scripts import prepare_rule_study_dispatch as d


@pytest.fixture
def plan(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "snapshot", lambda: ("a" * 40, {"fixture.py": "b" * 64}))
    value = d.draft()
    for role in d.ROLES:
        path = tmp_path / f"{role}.json"
        path.write_text('{"synthetic_unit_fixture": true}')
        value["inputs"][role] = {"path": str(path), "sha256": d.sha(path.read_bytes())}
    value["output_directory"] = str(tmp_path / "future-study-not-created")
    value["proposed_authorization_id"] = "proposed-fixture-only"
    value["proposed_limit_seconds"] = 5
    value["receiving_references"] = {r: "fixture-only-not-a-human-approval" for r in d.RECEIPTS}
    return value


def test_pending_hash_readiness_never_means_authorization(plan):
    report = d.assess(plan)
    assert report["status"] == "HASH_PREFLIGHT_READY_NOT_AUTHORIZATION"
    assert report["research_execution_authorized"] is False
    assert not __import__("pathlib").Path(plan["output_directory"]).exists()


@pytest.mark.parametrize("field,value", [("status", "approved"), ("kind", "actual-run")])
def test_json_approval_cannot_enable_any_dispatch(plan, field, value):
    plan[field] = value
    with pytest.raises(ValueError):
        d.assess(plan)


def test_draft_names_exact_missing_bindings(monkeypatch):
    monkeypatch.setattr(d, "snapshot", lambda: ("a" * 40, {}))
    report = d.assess(d.draft())
    assert report["status"] == "BLOCKED" and len(report["problems"]) == 8


@pytest.mark.parametrize("field", ["code_commit", "specification_sha256", "code_sha256"])
def test_changed_source_or_specification_blocks_release(plan, field):
    plan[field] = "changed"
    assert d.assess(plan)["status"] == "BLOCKED"


def test_changed_input_and_reused_output_block(plan):
    from pathlib import Path

    Path(plan["inputs"]["development_cases"]["path"]).write_text("changed")
    Path(plan["output_directory"]).mkdir()
    report = d.assess(plan)
    assert any("hash mismatch" in x for x in report["problems"])
    assert any("output must" in x for x in report["problems"])


@pytest.mark.parametrize("seconds", [True, 0, -1, float("inf"), 901])
def test_invalid_worker_bounds_block(plan, seconds):
    plan["proposed_limit_seconds"] = seconds
    assert d.assess(plan)["status"] == "BLOCKED"


def test_preflight_is_repeatable_and_does_not_consume_any_id(plan):
    before = copy.deepcopy(plan)
    assert d.assess(plan) == d.assess(plan)
    assert plan == before


def test_id_is_consumed_before_dummy_failure_and_never_reused(plan, tmp_path, monkeypatch):
    calls = []

    def dummy(mode, out, seconds):
        calls.append(mode)
        raise RuntimeError("dummy failure")

    monkeypatch.setattr(d, "rehearse", dummy)
    args = dict(rehearsal_id="dummy-once", ledger=tmp_path / "ledger", out=tmp_path / "dummy-out")
    with pytest.raises(RuntimeError):
        d.rehearsal(plan, **args)
    with pytest.raises(FileExistsError):
        d.rehearsal(plan, **args)
    assert calls == ["success"]
    entry = json.loads(next((tmp_path / "ledger").glob("*.json")).read_text())
    assert entry["scope"] == "dummy_rehearsal_only"


def test_hash_change_after_id_reservation_never_releases_worker(plan, tmp_path, monkeypatch):
    original = d.assess
    calls = []

    def changing(p):
        calls.append(1)
        return original(p) if len(calls) == 1 else {"status": "BLOCKED"}

    monkeypatch.setattr(d, "assess", changing)
    monkeypatch.setattr(d, "rehearse", lambda *a: pytest.fail("worker released"))
    with pytest.raises(ValueError, match="changed"):
        d.rehearsal(
            plan, rehearsal_id="dummy-change", ledger=tmp_path / "ledger", out=tmp_path / "out"
        )
    assert len(list((tmp_path / "ledger").glob("*.json"))) == 1


def test_real_authorization_id_cannot_be_consumed_by_rehearsal(plan, tmp_path):
    with pytest.raises(ValueError, match="dummy-prefixed"):
        d.rehearsal(
            plan,
            rehearsal_id=plan["proposed_authorization_id"],
            ledger=tmp_path / "ledger",
            out=tmp_path / "out",
        )
    assert not (tmp_path / "ledger").exists()


@pytest.mark.skipif(os.name != "nt", reason="real Windows containment")
def test_preflight_to_real_dummy_worker_preserves_study_output_absence(plan, tmp_path):
    result = d.rehearsal(
        plan, rehearsal_id="dummy-real", ledger=tmp_path / "ledger", out=tmp_path / "dummy"
    )
    assert result["rehearsal"]["rehearsal_passed"]
    assert not result["real_authorization_consumed"]
    assert not (tmp_path / "future-study-not-created").exists()


def test_cli_report_never_overwrites_existing_file(plan, tmp_path):
    source, out = tmp_path / "plan.json", tmp_path / "report.json"
    source.write_text(json.dumps(plan))
    out.write_text("keep")
    with pytest.raises(SystemExit):
        d.main(["--assess", str(source), "--out", str(out)])
    assert out.read_text() == "keep"


def test_dummy_ledger_cannot_create_the_actual_study_output(plan, tmp_path):
    from pathlib import Path

    study = Path(plan["output_directory"])
    with pytest.raises(ValueError, match="separate"):
        d.rehearsal(plan, rehearsal_id="dummy-separate", ledger=study, out=tmp_path / "out")
    assert not study.exists()


def test_input_byte_ceiling_refuses_before_worker_release(plan, tmp_path, monkeypatch):
    monkeypatch.setattr(
        d, "bounded_bytes", lambda path: (_ for _ in ()).throw(ValueError("byte limit"))
    )
    monkeypatch.setattr(d, "rehearse", lambda *a: pytest.fail("worker released"))
    with pytest.raises(ValueError, match="byte limit"):
        d.rehearsal(
            plan, rehearsal_id="dummy-large", ledger=tmp_path / "ledger", out=tmp_path / "out"
        )
    assert not (tmp_path / "ledger").exists()
