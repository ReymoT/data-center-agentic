"""Offline authored fixtures only. No final RNG, generator batch or real release."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import prepare_rule_study_final as f
from scripts import prepare_rule_study_rollout as w
from scripts import rule04_final_generation as gen


def binding(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def test_no_authority_touches_no_request_or_output(tmp_path):
    with pytest.raises(PermissionError):
        f.dispatch_once(tmp_path / "missing.json", ledger=tmp_path / "ledger")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("phase", ["generate", "evaluate"])
def test_draft_does_not_draw_or_release(monkeypatch, phase):
    def forbidden(*a, **kw):
        pytest.fail("draft must not construct RNG, generate or execute")

    monkeypatch.setattr("random.Random", forbidden)
    monkeypatch.setattr(f.w, "draft", lambda: {"plan": {"fixture": True}})
    monkeypatch.setattr(f.w.supervisor, "supervise", forbidden)
    result = f.draft(phase)
    assert result["final_inputs"] is None and result["freeze_reference"] is None
    assert all(v is None for v in result["limits"].values())


@pytest.mark.parametrize("phase", ["bad", None, 3])
def test_unknown_phase_refused(phase):
    with pytest.raises(ValueError):
        f.draft(phase)


def test_bound_single_read_rejects_drift_and_duplicate_keys(tmp_path):
    item = binding(tmp_path / "x.json", {"fixture": 1})
    assert f.bound(item) == {"fixture": 1}
    Path(item["path"]).write_text('{"fixture":2}')
    with pytest.raises(ValueError, match="changed"):
        f.bound(item)
    raw = b'{"x":1,"x":2}'
    Path(item["path"]).write_bytes(raw)
    item["sha256"] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match="duplicate"):
        f.bound(item)


@pytest.mark.parametrize(
    "value",
    [None, {}, {"path": "relative", "sha256": "a" * 64}, {"path": "/fixture", "sha256": "bad"}],
)
def test_bad_input_bindings_refused(value):
    with pytest.raises(ValueError):
        f.bound(value)


def generation_limits():
    return dict(wall_seconds=1, output_bytes=1024, proposals=1, feasibility_assignments=81)


@pytest.mark.parametrize(
    "key,value",
    [
        ("wall_seconds", True),
        ("wall_seconds", 901),
        ("proposals", 30001),
        ("feasibility_assignments", 2430001),
        ("output_bytes", 0),
    ],
)
def test_generation_limits_are_strict(key, value):
    limits = generation_limits()
    limits[key] = value
    with pytest.raises(ValueError):
        f.generation_limits(limits)


def test_generation_budget_stop_uses_only_authored_fixture_no_final_seed():
    from dc_sustainability.evaluation import rule_study_generator as g

    proposal = g.Proposal(
        (g.Job("J1", 10, 1, 0, 2, True),), (100, 200, 300, 100, 200, 300) + (200,) * 24
    )
    limits = generation_limits()
    with pytest.raises(ValueError, match="proposal/time ceiling"):
        gen.build(object(), {"cases": []}, limits, draw=lambda rng, stratum: proposal)


def test_generation_reserves_feasibility_before_search(monkeypatch):
    from dc_sustainability.evaluation import rule_study_generator as g

    proposal = g.Proposal((g.Job("J1", 10, 1, 0, 3, True),), (100,) * 30)
    limits = generation_limits()
    limits["feasibility_assignments"] = 1
    monkeypatch.setattr(g, "rejection_reason", lambda *a: pytest.fail("over-budget search called"))
    with pytest.raises(ValueError, match="feasibility ceiling"):
        gen.build(object(), {"cases": []}, limits, draw=lambda rng, stratum: proposal)


def fixture_loaded():
    parsed = {f"fixture-{i:03d}": SimpleNamespace() for i in range(120)}
    return ({}, {}, parsed)


def test_fixed_two_stages_have_no_overlap_and_same_total():
    loaded = fixture_loaded()
    request = {"stage": 0, "parent": None}
    first = f.selection(request, loaded)
    assert len(first) == 180 and len(set(first)) == 180
    assert first[0] == ("fixture-000", "rules-v1")
    assert first[-1] == ("fixture-059", "greedy_b")


@pytest.mark.parametrize("stage", [True, -1, 2, "0", None])
def test_bad_stage_refused(stage):
    with pytest.raises(ValueError):
        f.selection({"stage": stage}, fixture_loaded())


def test_second_stage_requires_exact_same_parent_and_cleanup(tmp_path):
    loaded = fixture_loaded()
    first = f.selection({"stage": 0, "parent": None}, loaded)
    request = dict(
        stage=1, plan=dict(code_commit="fixture", code_sha256={}), final_inputs={}, receiving={}
    )
    parent = dict(
        status="PASS",
        runs=180,
        selected_pairs=[list(p) for p in first],
        charged_steps=dict(states=10800, transitions=10800),
        code_commit="fixture",
        code_sha256={},
        final_inputs={},
        receiving={},
        supervision=dict(status="succeeded", cleanup_verified=True),
    )
    request["parent"] = binding(tmp_path / "parent.json", parent)
    second = f.selection(request, loaded)
    assert len(second) == 180 and not set(first) & set(second)
    for key, value in [
        ("status", "FAIL_OR_INCOMPLETE"),
        ("charged_steps", {}),
        ("code_commit", "drift"),
        ("selected_pairs", []),
        ("supervision", {"status": "succeeded", "cleanup_verified": False}),
    ]:
        changed = dict(parent, **{key: value})
        request["parent"] = binding(tmp_path / "parent.json", changed)
        with pytest.raises(ValueError, match="first stage"):
            f.selection(request, loaded)


def test_command_uses_same_containment_gate_but_fixed_final_worker():
    value = f.command(Path("fixture.json"), "a" * 64, deadline=123, original_hash="b" * 64)
    assert value[:5] == [f.sys.executable, "-B", "-X", "utf8", "-c"]
    assert 'sys.stdin.buffer.read(1) != b"G"' in value[5]
    assert "from scripts.prepare_rule_study_final import execute_prepared" in value[5]
    assert "from scripts.prepare_rule_study_rollout import execute_prepared" not in value[5]
    assert "RULE04_WORKER_DEADLINE" in value[5]


def test_phase_fields_cannot_smuggle_evaluation_into_generation():
    request = dict.fromkeys(f.FIELDS)
    request.update(kind=f.KIND, phase="generate", stage=0)
    with pytest.raises(ValueError, match="generation cannot"):
        f.validate_shape(request)


def test_legacy_generator_final_entry_stays_disabled(monkeypatch):
    from dc_sustainability.evaluation import rule_study_generator as g

    monkeypatch.setattr(g.random, "Random", lambda *a: pytest.fail("final RNG constructed"))
    with pytest.raises(PermissionError):
        g.generate("final", authorization="fixture URL cannot approve")


def test_cli_offers_no_execute_action():
    with pytest.raises(SystemExit):
        f.main(["execute"])


def test_authored_serialization_fixture_passes_accounting_without_any_rng(monkeypatch):
    import itertools

    from dc_sustainability.evaluation import rule_study_accounting as ac
    from dc_sustainability.evaluation import rule_study_generator as g

    # Forty manually enumerated fixture profiles, not either study's seed stream.
    profiles = iter(p for p in itertools.product((100, 200, 300), repeat=6) if len(set(p)) > 1)
    jobs = (g.Job("J1", 10, 1, 0, 3, True), g.Job("J2", 10, 1, 0, 3, True))
    monkeypatch.setattr(g, "STRATA", ("normal_feasible",))
    monkeypatch.setattr(g.random, "Random", lambda *a: pytest.fail("RNG forbidden in fixture"))

    def draw(rng, stratum):
        return g.Proposal(jobs, tuple(next(profiles)) + (200,) * 24)

    cases, weights, counters = gen.build(
        object(),
        {"cases": []},
        dict(wall_seconds=10, proposals=40, feasibility_assignments=360),
        draw=draw,
    )
    assert len(cases["cases"]) == 40
    assert counters == dict(proposals=40, feasibility_assignments_reserved=360)
    assert ac.check_accounting(cases, weights)["overall"] == "PASS"


def host_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(f, "ROOT", tmp_path / "repo")
    f.ROOT.mkdir()
    monkeypatch.setattr(f, "assess", lambda *a, **kw: {"problems": []})
    monkeypatch.setattr(f, "drift", lambda *a: False)
    monkeypatch.setattr(w.worker, "environment_evidence", lambda: {"fixture": True})
    request = dict(
        phase="generate",
        stage=None,
        freeze_reference="fixture only",
        limits=generation_limits(),
        plan=dict(
            code_commit="fixture",
            proposed_authorization_id="offline-fixture-only",
            output_directory=str(tmp_path / "out"),
        ),
    )
    path = tmp_path / "request.json"
    w._write(path, request)
    return path, tmp_path / "RuleStudy_Run_Ledger", request


def fixture_authority(subject):
    return dict(
        subject,
        actor="MattyAnd",
        decision="approved",
        protocol_freeze_authenticated=True,
        generation_and_isolation_receiving_authenticated=False,
        parent_stage_authenticated=False,
    )


def test_wrong_host_authority_never_reserves(tmp_path, monkeypatch):
    path, ledger, _ = host_fixture(tmp_path, monkeypatch)
    with pytest.raises(PermissionError):
        f.dispatch_once(path, ledger=ledger, trusted_authorize=lambda s: {})
    assert not ledger.exists()


def test_drift_after_reservation_consumes_id_and_preserves_failure(tmp_path, monkeypatch):
    path, ledger, _ = host_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        w.supervisor, "supervise", lambda *a, **kw: pytest.fail("drift released worker")
    )

    def authority(subject):
        path.write_text("{}")
        return fixture_authority(subject)

    with pytest.raises(ValueError, match="drift"):
        f.dispatch_once(path, ledger=ledger, trusted_authorize=authority)
    records = [json.loads(p.read_bytes()) for p in ledger.glob("*.json")]
    assert len(records) == 2
    assert any(
        r.get("status") == "failed_after_reservation" and r["retry_allowed"] is False
        for r in records
    )


@pytest.mark.parametrize(
    "status,cleanup", [("timed_out", True), ("succeeded", False), ("output_limit", True)]
)
def test_timeout_output_cleanup_cannot_pass(tmp_path, monkeypatch, status, cleanup):
    path, ledger, _ = host_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        w.supervisor, "supervise", lambda *a, **kw: dict(status=status, cleanup_verified=cleanup)
    )
    result = f.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)
    assert result["status"] == "FAIL_OR_INCOMPLETE" and result["retry_allowed"] is False
    with pytest.raises(FileExistsError):
        f.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)


def test_json_cannot_supply_isolation_authentication(tmp_path, monkeypatch):
    path, ledger, request = host_fixture(tmp_path, monkeypatch)
    request.update(phase="evaluate", stage=0)
    path.write_text(json.dumps(request))
    with pytest.raises(PermissionError, match="receiving"):
        f.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)
    assert not ledger.exists()


def test_relabelling_retained_development_as_final_is_rejected(tmp_path, monkeypatch):
    # Deliberately fraudulent offline fixture; no final RNG or new study cases.
    from dc_sustainability.evaluation import rule_study_generator as g

    dev, accounting, _ = w.pair()
    cases = json.loads(json.dumps(dev))
    cases["set_id"] = f"{g.STUDY_ID}-final"
    cases["metadata"].update(seed_domain="final", seed=g.SEED_DOMAINS["final"])
    for c in cases["cases"]:
        c["case_id"] = c["case_id"].replace("development-", "final-", 1)
    values = {"cases": cases, "accounting": accounting, "generation_receipt": {}}
    request = {"final_inputs": {k: binding(tmp_path / f"{k}.json", v) for k, v in values.items()}}
    with pytest.raises(ValueError, match="overlap"):
        f.pair(request)


@pytest.mark.parametrize("missing", [None, {}, {"cases": {"path": "fixture"}}])
def test_missing_final_pair_or_receiving_cannot_reach_worker(missing):
    with pytest.raises(ValueError, match="bindings"):
        f.pair({"final_inputs": missing})


def test_supervisor_success_with_missing_generation_output_is_failure(tmp_path, monkeypatch):
    path, ledger, _ = host_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        w.supervisor, "supervise", lambda *a, **kw: dict(status="succeeded", cleanup_verified=True)
    )
    with pytest.raises(FileNotFoundError):
        f.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)
    records = [json.loads(p.read_bytes()) for p in ledger.glob("*.result.json")]
    assert len(records) == 1 and records[0]["status"] == "failed_after_reservation"


def test_batch_uses_fixed_backend_without_development_selection(tmp_path, monkeypatch):
    from scripts import rule_study_metrics_core as mc

    out = tmp_path / "output"
    loaded = (
        {"cases": [{"case_id": "A", "stratum": "fixture"}]},
        {},
        {"A": SimpleNamespace(scores=(100,))},
    )
    calls = []
    backend = SimpleNamespace(
        pair=lambda request: loaded,
        selection=lambda request, actual: [("A", "rules-v1")],
        command=lambda *a, **kw: ["fixture-python", "-B", "-X", "utf8", "-c", "fixture", "root"],
        drift=lambda request: False,
    )
    monkeypatch.setattr(w, "pair", lambda: pytest.fail("legacy inputs used"))
    monkeypatch.setattr(w, "selection", lambda *a, **kw: pytest.fail("legacy selection used"))
    monkeypatch.setattr(mc, "equal_work", lambda metrics: [])

    def done(command, *a, **kw):
        calls.append(command)
        directory = out / "A-rules-v1"
        directory.mkdir()
        w._write(
            directory / "pair-result.json",
            dict(
                budget=dict(states_used=60, transitions_used=60),
                metric=dict(case_id="A", policy_id="rules-v1"),
            ),
        )
        return dict(status="succeeded", cleanup_verified=True)

    monkeypatch.setattr(w.supervisor, "supervise", done)
    request = dict(
        kind=f.KIND,
        limits=dict(
            wall_seconds=100, case_policy_seconds=1, states=60, transitions=60, output_bytes=1024
        ),
    )
    assert w._batch(request, out, backend=backend) == 0
    report = w.read_json(out / "rollout-report.json")
    assert report["runs"] == 1 and report["scope_complete_only"] is True
    assert report["selected_pairs"] == [["A", "rules-v1"]]
    assert len(calls) == 1 and "RULE04_WORKER_PAIR" in calls[0][5]


def test_saved_stage_join_refuses_missing_pairs_and_source_changes(tmp_path, monkeypatch):
    from scripts import rule_study_metrics_core as mc

    loaded = fixture_loaded()
    loaded[0]["cases"] = [{"case_id": c, "stratum": "fixture"} for c in loaded[2]]
    monkeypatch.setattr(f, "pair", lambda request: loaded)
    monkeypatch.setattr(mc, "equal_work", lambda metrics: [])
    request = dict(final_inputs={}, receiving={}, plan=dict(code_commit="fixture", code_sha256={}))
    pairs = [(c, p) for c in loaded[2] for p in w.POLICIES]
    reports = []
    for stage in (0, 1):
        selected = pairs[stage * 180 : (stage + 1) * 180]
        reports.append(
            dict(
                status="PASS",
                runs=180,
                selected_pairs=[list(p) for p in selected],
                charged_steps=dict(states=10800, transitions=10800),
                final_inputs={},
                receiving={},
                code_commit="fixture",
                code_sha256={},
                supervision=dict(status="succeeded", cleanup_verified=True),
                strata={"fixture": [dict(case_id=c, policy_id=p) for c, p in selected]},
            )
        )
    first = binding(tmp_path / "first.json", reports[0])
    reports[1]["parent"] = first
    second = binding(tmp_path / "second.json", reports[1])
    result = f.join_stages(request, first, second)
    assert result["pairs"] == 360 and len(result["metrics"]) == 360
    assert result["charged_steps"] == dict(states=21600, transitions=21600)
    assert "PENDING_INDEPENDENT_RECEIVING" in result["status"]
    reports[1]["strata"]["fixture"].pop()
    second = binding(tmp_path / "second.json", reports[1])
    with pytest.raises(ValueError, match="coverage"):
        f.join_stages(request, first, second)
    reports[1]["code_commit"] = "changed"
    second = binding(tmp_path / "second.json", reports[1])
    with pytest.raises(ValueError, match="same-freeze"):
        f.join_stages(request, first, second)
