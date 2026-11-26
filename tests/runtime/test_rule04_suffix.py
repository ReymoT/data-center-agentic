"""Static retained-prefix and dummy-worker tests, never the research cases."""

import copy
import json
from pathlib import Path

import pytest

from scripts import prepare_rule_study_rollout as w


@pytest.fixture
def prefix(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(w, "ROOT", root)
    monkeypatch.setattr(w, "pair", lambda: ({}, {}, {"A": object(), "B": object()}))
    baseline = root / "docs/rule_study/RULE03_VERIFICATION_BASELINE_NOV23.json"
    baseline.parent.mkdir(parents=True)
    w._write(baseline, {"baseline_code_sha256": {"science": "unchanged"}})
    output = tmp_path / "old"
    output.mkdir()
    old = {
        "kind": w.KIND,
        "plan": {
            "code_commit": "old-source",
            "code_sha256": {"science": "unchanged"},
            "inputs": {k: {"sha256": v[1]} for k, v in w.INPUTS.items()},
            "output_directory": str(output),
            "proposed_authorization_id": "dummy-parent",
        },
        "limits": {"states": 21600},
        "freeze_reference": "fixture",
    }
    request_path = tmp_path / "parent.json"
    w._write(request_path, old)
    old_sha = w.pf.sha(request_path.read_bytes())
    ledger = tmp_path / "RuleStudy_Run_Ledger"
    ledger.mkdir()
    entry = ledger / (w.pf.sha(b"dummy-parent") + ".json")
    w._write(
        entry,
        {
            "receipt": {
                "request_sha256": old_sha,
                "code_commit": "old-source",
                "authorization_id": "dummy-parent",
                "actor": "MattyAnd",
                "decision": "approved",
                "limits": old["limits"],
                "output_directory": str(output),
            }
        },
    )
    w._write(
        entry.with_suffix(".result.json"),
        {"authenticated_request_sha256": old_sha, "cleanup_verified": True, "retry_allowed": False},
    )
    rows = []
    for policy in w.POLICIES:
        pair = output / f"A-{policy}"
        pair.mkdir()
        path = pair / "pair-result.json"
        w._write(
            path,
            {
                "status": "PASS",
                "case_id": "A",
                "policy_id": policy,
                "replay": {"overall": "PASS"},
                "authenticated_request_sha256": old_sha,
                "metric": {"code_commit": "old-source", "execution_violations": 0},
                "budget": {"states_used": 60, "transitions_used": 60},
            },
        )
        rows.append({"case_id": "A", "policy_id": policy, "sha256": w.pf.sha(path.read_bytes())})
    failure = output / "rollout-failure.json"
    w._write(
        failure,
        {
            "status": "FAIL_OR_INCOMPLETE",
            "message": "combined resource budget exhausted",
            "authenticated_request_sha256": old_sha,
            "completed_runs": 3,
            "charged_steps_completed_pairs_only": {"states": 180, "transitions": 180},
        },
    )
    receipt = {
        "kind": "rule04_retained_prefix_v1",
        "output": str(output),
        "request": {"path": str(request_path), "sha256": old_sha},
        "status_sha256": w.pf.sha(failure.read_bytes()),
        "pairs": rows,
        "artifacts": {
            p.relative_to(output).as_posix(): w.pf.sha(p.read_bytes())
            for p in output.rglob("*")
            if p.is_file()
        },
    }
    receipt_path = tmp_path / "receipt.json"
    w._write(receipt_path, receipt)
    new = {
        "kind": w.SUFFIX_KIND,
        "plan": {
            "output_directory": str(tmp_path / "new"),
            "proposed_authorization_id": "dummy-new",
        },
        "limits": {},
        "freeze_reference": "fixture",
        "parent": {"path": str(receipt_path), "sha256": w.pf.sha(receipt_path.read_bytes())},
    }
    return new, receipt, receipt_path, output, entry


def rebind(req, receipt, path):
    path.write_text(json.dumps(receipt))
    req["parent"]["sha256"] = w.pf.sha(path.read_bytes())


def test_exact_suffix_and_full_parent_bytes(prefix):
    req, _, _, output, _ = prefix
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert w.selection(req, full=True) == [("B", p) for p in w.POLICIES]
    assert {
        p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()
    } == before


@pytest.mark.parametrize("mode", ["reorder", "duplicate", "foreign", "count", "artifact", "path"])
def test_rebound_but_invalid_parent_refused(prefix, mode):
    req, r, path, _, _ = prefix
    if mode == "reorder":
        r["pairs"].reverse()
    if mode == "duplicate":
        r["pairs"][1] = copy.deepcopy(r["pairs"][0])
    if mode == "foreign":
        r["pairs"][0]["case_id"] = "foreign"
    if mode == "count":
        r["pairs"].pop()
    if mode == "artifact":
        r["artifacts"][next(iter(r["artifacts"]))] = "0" * 64
    if mode == "path":
        r["output"] = str(path.parent / "missing")
    rebind(req, r, path)
    with pytest.raises((ValueError, OSError)):
        w.selection(req, full=True)


@pytest.mark.parametrize(
    "mode",
    ["receipt", "status", "pair", "extra_pair", "artifact", "cleanup", "consent", "id", "output"],
)
def test_tampering_or_retry_refused(prefix, mode):
    req, _, path, out, entry = prefix
    if mode == "receipt":
        path.write_text("{}")
    if mode == "status":
        (out / "rollout-failure.json").write_text("{}")
    if mode == "pair":
        (out / "A-rules-v1/pair-result.json").write_text("{}")
    if mode == "extra_pair":
        (out / "B-rules-v1").mkdir()
    if mode == "artifact":
        (out / "A-rules-v1/extra.json").write_text("{}")
    if mode == "cleanup":
        p = entry.with_suffix(".result.json")
        value = w.read_json(p)
        value["cleanup_verified"] = False
        p.write_text(json.dumps(value))
    if mode == "consent":
        value = w.read_json(entry)
        value["receipt"]["decision"] = "pending"
        entry.write_text(json.dumps(value))
    if mode == "id":
        req["plan"]["proposed_authorization_id"] = "dummy-parent"
    if mode == "output":
        req["plan"]["output_directory"] = str(out / "new")
    with pytest.raises((ValueError, OSError)):
        w.selection(req, full=True)


def test_smaller_limit_is_scoped_not_a_full_batch_waiver():
    limits = {
        "states": 10680,
        "transitions": 10680,
        "wall_seconds": 900,
        "case_policy_seconds": 60,
        "output_bytes": 268435456,
    }
    w.validate_limits(limits, 178)
    with pytest.raises(ValueError):
        w.validate_limits(limits)
    with pytest.raises(ValueError):
        w.validate_limits(dict(limits, states=10679), 178)
    with pytest.raises(ValueError):
        w.validate_limits(limits, True)


def test_absent_authority_cannot_consume_suffix_id(tmp_path):
    with pytest.raises(PermissionError):
        w.dispatch_once(tmp_path / "absent", ledger=tmp_path / "ledger")
    assert not list(tmp_path.iterdir())


def test_batch_skips_prefix_with_fixed_dummy_workers(tmp_path, monkeypatch):
    from types import SimpleNamespace

    cases = {"cases": [{"case_id": c, "stratum": "fixture"} for c in ("A", "B")]}
    monkeypatch.setattr(
        w, "pair", lambda: (cases, {}, dict.fromkeys(("A", "B"), SimpleNamespace(scores=[1])))
    )
    monkeypatch.setattr(w, "selection", lambda *a, **k: [("B", p) for p in w.POLICIES])
    monkeypatch.setattr(w, "assess_after_run", lambda req: False)
    monkeypatch.setattr(w, "monotonic", lambda: 0)
    monkeypatch.setattr(w, "suffix_controls", lambda *a: {})
    from scripts import rule_study_metrics_core as mc

    monkeypatch.setattr(mc, "equal_work", lambda metrics: [])
    calls = []
    out = tmp_path / "output"

    def dummy(command, seconds, *, output, **kwargs):
        calls.append(output.name)
        output.mkdir()
        policy = output.name.removeprefix("B-")
        w._write(
            output / "pair-result.json",
            {
                "budget": {"states_used": 60, "transitions_used": 60},
                "metric": {"case_id": "B", "policy_id": policy},
            },
        )
        return {"status": "succeeded", "cleanup_verified": True}

    monkeypatch.setattr(w.supervisor, "supervise", dummy)
    request = {
        "kind": w.SUFFIX_KIND,
        "parent": {"sha256": "fixture"},
        "limits": {
            "states": 180,
            "transitions": 180,
            "wall_seconds": 900,
            "case_policy_seconds": 60,
            "output_bytes": 1024,
        },
    }
    assert w._batch(request, out) == 0
    assert calls == [f"B-{p}" for p in w.POLICIES]
    report = w.read_json(out / "rollout-report.json")
    assert report["runs"] == 3 and report["scope_complete_only"] is True
    assert report["charged_steps"] == {"states": 180, "transitions": 180}
    assert report["parent"] == request["parent"]


def test_hidden_control_signature_is_carried_and_mismatch_refused(prefix, monkeypatch):
    from types import SimpleNamespace

    req, receipt, path, out, _ = prefix
    parsed = {"A": SimpleNamespace(scores=None), "B": SimpleNamespace(scores=[1])}
    monkeypatch.setattr(w, "pair", lambda: ({}, {}, parsed))
    for row in receipt["pairs"]:
        file = out / f"A-{row['policy_id']}" / "pair-result.json"
        value = w.read_json(file)
        value["execution_signature"] = "a" * 64
        file.write_text(json.dumps(value))
        row["sha256"] = w.pf.sha(file.read_bytes())
    receipt["artifacts"] = {
        p.relative_to(out).as_posix(): w.pf.sha(p.read_bytes())
        for p in out.rglob("*")
        if p.is_file()
    }
    rebind(req, receipt, path)
    w.selection(req, full=True)
    assert w.suffix_controls(req, ({}, {}, parsed)) == {"A": "a" * 64}
    file = out / "A-greedy_b/pair-result.json"
    value = w.read_json(file)
    value["execution_signature"] = "b" * 64
    file.write_text(json.dumps(value))
    receipt["pairs"][2]["sha256"] = w.pf.sha(file.read_bytes())
    rebind(req, receipt, path)
    with pytest.raises(ValueError, match="control differs"):
        w.selection(req)


@pytest.mark.parametrize("tamper", [False, True])
def test_suffix_dispatch_requires_new_operation_and_exact_scope(prefix, monkeypatch, tamper):
    req, _, path, out, _ = prefix
    req["plan"]["code_commit"] = "unit-fixture-only"
    req["limits"] = {"wall_seconds": 10, "output_bytes": 1024}
    request_path = path.parent / "new-request.json"
    w._write(request_path, req)
    selected = [("B", p) for p in w.POLICIES]
    monkeypatch.setattr(w, "selection", lambda *a, **k: selected)
    monkeypatch.setattr(w, "assess", lambda r: {"problems": []})
    monkeypatch.setattr(w, "assess_after_run", lambda r: False)
    monkeypatch.setattr(w.worker, "environment_evidence", lambda: {"fixture": True})

    def authority(subject):
        assert subject["operation"] == "retained_development_unexecuted_suffix_execution_and_replay"
        assert subject["request_sha256"] == w.pf.sha(request_path.read_bytes())
        return dict(
            subject, actor="MattyAnd", decision="approved", protocol_freeze_authenticated=True
        )

    def dummy(*args, **kwargs):
        folder = Path(req["plan"]["output_directory"])
        folder.mkdir()
        w._write(
            folder / "rollout-report.json",
            {
                "status": "PASS",
                "runs": 3,
                "scope_complete_only": True,
                "selected_pairs": [] if tamper else [list(k) for k in selected],
                "parent": req["parent"],
            },
        )
        return {"status": "succeeded", "cleanup_verified": True}

    monkeypatch.setattr(w.supervisor, "supervise", dummy)
    result = w.dispatch_once(
        request_path, ledger=path.parent / "RuleStudy_Run_Ledger", trusted_authorize=authority
    )
    assert result["status"] == ("failed_result_or_drift" if tamper else "succeeded")
    with pytest.raises(FileExistsError):
        w.dispatch_once(
            request_path, ledger=path.parent / "RuleStudy_Run_Ledger", trusted_authorize=authority
        )


def test_controls_rechecks_receipt_even_when_no_hidden_pairs(prefix):
    request, _, path, _, _ = prefix
    w.selection(request)
    path.write_text("{}")
    with pytest.raises(ValueError, match="parent receipt changed"):
        w.suffix_controls(request, ({}, {}, {"A": object()}))


def test_controls_reads_and_authenticates_hidden_pair_bytes(prefix):
    from types import SimpleNamespace

    request, receipt, path, output, _ = prefix
    parsed = {"A": SimpleNamespace(scores=None), "B": SimpleNamespace(scores=[1])}
    for row in receipt["pairs"]:
        p = output / f"A-{row['policy_id']}" / "pair-result.json"
        value = w.read_json(p)
        value["execution_signature"] = "a" * 64
        p.write_text(json.dumps(value))
        row["sha256"] = w.pf.sha(p.read_bytes())
    rebind(request, receipt, path)
    assert w.suffix_controls(request, ({}, {}, parsed)) == {"A": "a" * 64}
    (output / "A-greedy_a/pair-result.json").write_text("{}")
    with pytest.raises(ValueError, match="parent control pair changed"):
        w.suffix_controls(request, ({}, {}, parsed))


def test_bound_json_uses_single_verified_read(tmp_path, monkeypatch):
    from scripts import rule04_suffix as suffix

    path = tmp_path / "data.json"
    path.write_text('{"value":1}')
    raw = path.read_bytes()
    real_read = w.pf.bounded_bytes
    calls = []

    def replace_after_read(p):
        calls.append(p)
        value = real_read(p)
        path.write_text('{"value":2}')
        return value

    monkeypatch.setattr(w.pf, "bounded_bytes", replace_after_read)
    assert suffix.bound_json(path, w.pf.sha(raw), "fixture") == {"value": 1}
    assert len(calls) == 1
    with pytest.raises(ValueError, match="fixture changed"):
        suffix.bound_json(path, w.pf.sha(raw), "fixture")


def test_inspect_missing_parent_writes_blocked_without_dispatch(prefix, monkeypatch):
    request, _, receipt, _, _ = prefix
    req = receipt.parent / "inspect-request.json"
    w._write(req, request)
    receipt.unlink()
    output = receipt.parent / "inspection.json"
    monkeypatch.setattr(w.supervisor, "supervise", lambda *a, **k: pytest.fail("no dispatch"))
    assert w.main(["--inspect", str(req), "--out", str(output)]) == 2
    report = w.read_json(output)
    assert report["status"] == "BLOCKED" and report["execution_authorized"] is False
    assert "FileNotFoundError" in report["problems"][0]
    assert not Path(request["plan"]["output_directory"]).exists()


def test_inspect_git_preflight_failure_writes_blocked(tmp_path, monkeypatch):
    import subprocess

    request = tmp_path / "request.json"
    request.write_text("{}")

    def fail_assessment(_):
        raise subprocess.CalledProcessError(1, ["git", "merge-base"])

    monkeypatch.setattr(w, "assess", fail_assessment)
    report = tmp_path / "inspection.json"
    assert w.main(["--inspect", str(request), "--out", str(report)]) == 2
    assert w.read_json(report)["status"] == "BLOCKED"


@pytest.mark.parametrize("drift", ["commit", "pins", "input"])
def test_suffix_child_rejects_source_or_input_drift_before_policy(prefix, monkeypatch, drift):
    request, _, _, _, _ = prefix
    request["plan"].update(
        code_commit="fixture",
        code_sha256={"fixture": "unchanged"},
        inputs={
            r: {"path": str(Path(w.__file__).parents[1] / "docs/evidence/rule04-dev-nov23" / name)}
            for r, (name, _) in w.INPUTS.items()
        },
    )
    request["limits"] = {
        "states": 21600,
        "transitions": 21600,
        "wall_seconds": 900,
        "case_policy_seconds": 60,
        "output_bytes": 268435456,
    }
    monkeypatch.setattr(
        w.pf,
        "snapshot",
        lambda: (
            "changed" if drift == "commit" else "fixture",
            {"fixture": "changed" if drift == "pins" else "unchanged"},
        ),
    )
    if drift == "input":
        original = w.pf.bounded_bytes
        case_path = request["plan"]["inputs"]["development_cases"]["path"]
        monkeypatch.setattr(
            w.pf, "bounded_bytes", lambda p: b"changed" if str(p) == case_path else original(p)
        )
    monkeypatch.setenv("RULE04_WORKER_PAIR", json.dumps(["B", "rules-v1", 180, 180]))
    monkeypatch.setattr(w, "_one_pair", lambda *a, **k: pytest.fail("drift released policy"))
    new_output = Path(request["plan"]["output_directory"])
    new_output.mkdir()
    with pytest.raises(ValueError, match="source/input"):
        w.execute_prepared(request)
    failure = w.read_json(new_output / "B-rules-v1/pair-failure.json")
    assert failure["retry_allowed"] is False


@pytest.mark.parametrize("stop", ["failed", "timed_out", "cleanup"])
def test_suffix_failure_after_one_pair_preserves_counts_and_stops(tmp_path, monkeypatch, stop):
    from types import SimpleNamespace

    loaded = (
        {"cases": [{"case_id": "B", "stratum": "fixture"}]},
        {},
        {"B": SimpleNamespace(scores=[1])},
    )
    monkeypatch.setattr(w, "pair", lambda: loaded)
    monkeypatch.setattr(w, "selection", lambda *a, **k: [("B", p) for p in w.POLICIES])
    monkeypatch.setattr(w, "suffix_controls", lambda *a: {})
    monkeypatch.setattr(w, "monotonic", lambda: 0)
    calls = []

    def dummy(*args, output, **kwargs):
        calls.append(output.name)
        output.mkdir()
        if len(calls) == 1:
            w._write(
                output / "pair-result.json",
                {
                    "budget": {"states_used": 60, "transitions_used": 60},
                    "metric": {"case_id": "B", "policy_id": "rules-v1"},
                },
            )
            return {"status": "succeeded", "cleanup_verified": True}
        return {
            "status": "succeeded" if stop == "cleanup" else stop,
            "cleanup_verified": stop != "cleanup",
        }

    monkeypatch.setattr(w.supervisor, "supervise", dummy)
    request = {
        "kind": w.SUFFIX_KIND,
        "limits": {
            "states": 180,
            "transitions": 180,
            "wall_seconds": 900,
            "case_policy_seconds": 60,
            "output_bytes": 1024,
        },
    }
    out = tmp_path / "output"
    with pytest.raises(ValueError, match="no retry"):
        w._batch(request, out)
    report = w.read_json(out / "rollout-failure.json")
    assert report["completed_runs"] == 1
    assert report["charged_steps_completed_pairs_only"] == {"states": 60, "transitions": 60}
    assert report["retry_allowed"] is False and len(calls) == 2
    assert not (out / "B-greedy_b").exists()


def test_explicit_and_legacy_resource_stop_semantics():
    from scripts import rule04_suffix as suffix

    assert suffix.resource_stop({"message": "combined resource budget exhausted"})
    for reason in ("wall_time_reserve", "state_transition_budget"):
        error = w.ResourceStop(reason)
        assert suffix.resource_stop({"stop_reason": reason, "message": str(error)})
    assert not suffix.resource_stop(
        {"stop_reason": "other_failure", "message": "combined resource budget exhausted"}
    )
