"""File-backed artificial host/evidence fixtures; never final RNG or study runs."""

import copy
import json
import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import prepare_rule_study_final as f
from scripts import prepare_rule_study_rollout as w
from scripts import rule04_final_generation as gen
from scripts import rule04_final_receipts as rr
from tests.runtime.test_rule04_final_preparation import (
    binding,
    fixture_authority,
    fixture_loaded,
    generation_limits,
    host_fixture,
)


def completed(root, directory, report, phase, stage):
    """Create explicit test-double ledger evidence, never a real host approval."""
    report.update(phase=phase, stage=stage, authorization_id=f"offline-fixture-{phase}-{stage}")
    report.setdefault("canonical_request_sha256", "c" * 64)
    name = "generation-receipt.json" if phase == "generate" else "stage-receipt.json"
    item = binding(directory / name, report)
    ident = report["authorization_id"]
    ledger = root.parent / "RuleStudy_Run_Ledger"
    ledger.mkdir(exist_ok=True)
    entry = ledger / (w.pf.sha(ident.encode()) + ".json")
    authority = dict(
        actor="MattyAnd",
        decision="approved",
        protocol_freeze_authenticated=True,
        phase=phase,
        stage=stage,
        authorization_id=ident,
        generation_and_isolation_receiving_authenticated=phase == "evaluate",
        parent_stage_authenticated=stage == 1,
        request_sha256=report["authenticated_request_sha256"],
        code_commit=report["code_commit"],
        freeze_reference=report["freeze_reference"],
        limits=report["limits"],
        output_directory=str(directory),
    )
    binding(
        entry, dict(receipt=authority, canonical_request_sha256=report["canonical_request_sha256"])
    )
    result = dict(
        status="succeeded", cleanup_verified=True, published_receipt_sha256=item["sha256"]
    )
    binding(entry.with_suffix(".result.json"), result)
    slot = rr.slot_path(root, phase, stage)
    binding(
        slot, dict(authorization_id=ident, request_sha256=report["authenticated_request_sha256"])
    )
    binding(slot.with_suffix(".result.json"), result)
    return item


@pytest.fixture
def parent_fixture(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(f, "ROOT", root)
    loaded = fixture_loaded()
    selected = f.stage_pairs(loaded)[:180]
    request = dict(
        stage=1,
        parent=None,
        phase="evaluate",
        kind=f.KIND,
        plan=dict(
            code_commit="fixture", code_sha256={}, proposed_authorization_id="fixture-stage1"
        ),
        final_inputs={},
        receiving={},
        freeze_reference="fixture-freeze",
        limits=dict(
            states=10800,
            transitions=10800,
            wall_seconds=900,
            case_policy_seconds=60,
            output_bytes=1024 * 1024,
        ),
    )
    directory = tmp_path / "stage0"
    directory.mkdir()
    original = "a" * 64
    canonical = rr.digest(request)
    rows = {s: [] for s in ("normal_feasible", "overloaded_impossible", "missing_forecast")}
    supervision = []
    for cid, policy in selected:
        stratum = next(s for s in rows if cid.startswith(f"fixture-{s}-"))
        metric = dict(case_id=cid, policy_id=policy, status="complete")
        rows[stratum].append(dict(metric, stratum=stratum))
        task = binding(directory / f"request-{cid}-{policy}.json", request)
        d = directory / f"{cid}-{policy}"
        d.mkdir()
        binding(
            d / "pair-result.json",
            dict(
                status="PASS",
                case_id=cid,
                policy_id=policy,
                metric=metric,
                authenticated_request_sha256=original,
                pair_request_sha256=task["sha256"],
                budget=dict(states_used=60, transitions_used=60),
                replay=dict(overall="PASS"),
            ),
        )
        supervision.append(
            dict(
                case_id=cid,
                policy_id=policy,
                supervision=dict(status="succeeded", cleanup_verified=True),
            )
        )
    raw = dict(
        status="PASS",
        runs=180,
        selected_pairs=[list(p) for p in selected],
        scope_complete_only=True,
        authenticated_request_sha256=original,
        charged_steps=dict(states=10800, transitions=10800),
        parent=None,
        strata=rows,
        supervision=supervision,
    )
    raw_item = binding(directory / "rollout-report.json", raw)
    inv = binding(directory / "stage-manifest.json", rr.inventory(directory))
    report = dict(
        raw,
        kind="rule04_complete_stage_receipt_v2",
        stage=0,
        code_commit="fixture",
        code_sha256={},
        final_inputs={},
        receiving={},
        freeze_reference=request["freeze_reference"],
        limits=request["limits"],
        canonical_request_sha256=canonical,
        host_supervision=dict(status="succeeded", cleanup_verified=True),
        pair_supervision=supervision,
        rollout_report_sha256=raw_item["sha256"],
        output_inventory=dict(path="stage-manifest.json", sha256=inv["sha256"]),
    )
    item = completed(root, directory, report, "evaluate", 0)
    request["parent"] = item
    return root, request, loaded, report, item


def test_real_file_parent_requires_metric_tree_and_canonical_host_result(parent_fixture):
    root, request, loaded, report, item = parent_fixture
    assert len(f.selection(request, loaded)) == 180
    entry = (
        root.parent
        / "RuleStudy_Run_Ledger"
        / (w.pf.sha(report["authorization_id"].encode()) + ".result.json")
    )
    entry.unlink()
    with pytest.raises(OSError):
        f.selection(request, loaded)


@pytest.mark.parametrize(
    "key,value",
    [
        ("strata", {}),
        ("authenticated_request_sha256", None),
        ("scope_complete_only", False),
        ("parent", {"path": "handwritten", "sha256": "a" * 64}),
        ("freeze_reference", "changed"),
        ("limits", {}),
        ("kind", "handwritten"),
        ("pair_supervision", []),
    ],
)
def test_hollow_or_rebound_parent_is_rejected_before_stage1(parent_fixture, key, value):
    _, request, loaded, report, item = parent_fixture
    changed = copy.deepcopy(report)
    changed[key] = value
    request["parent"] = binding(Path(item["path"]), changed)
    with pytest.raises((ValueError, KeyError)):
        f.selection(request, loaded)


@pytest.mark.parametrize("mode", ["extra", "pair", "manifest", "raw_report", "missing"])
def test_mutated_stage_tree_cannot_be_reused(parent_fixture, mode):
    _, request, loaded, _, item = parent_fixture
    directory = Path(item["path"]).parent
    pair = next(directory.glob("*/pair-result.json"))
    if mode == "extra":
        (directory / "unlisted.txt").write_text("extra")
    elif mode == "missing":
        pair.unlink()
    elif mode == "manifest":
        (directory / "stage-manifest.json").write_text("{}")
    elif mode == "raw_report":
        (directory / "rollout-report.json").write_text("{}")
    else:
        pair.write_text("{}")
    with pytest.raises((ValueError, OSError)):
        f.selection(request, loaded)


@pytest.mark.parametrize("kind", ["no_environment", "forged_environment"])
def test_direct_worker_never_reaches_rng_or_output(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(random, "Random", lambda *a: pytest.fail("unauthorized RNG reached"))
    monkeypatch.setattr(f, "drift", lambda *a, **kw: False)
    monkeypatch.setattr(f, "ROOT", tmp_path / "repo")
    request = dict(
        phase="generate", stage=None, plan=dict(proposed_authorization_id="offline-fixture-only")
    )
    for key in ("RULE04_AUTHENTICATED_REQUEST_SHA256", "RULE04_WORKER_REQUEST_SHA256"):
        monkeypatch.delenv(key, raising=False)
        if kind == "forged_environment":
            monkeypatch.setenv(key, "a" * 64)
    with pytest.raises(PermissionError):
        f.execute_prepared(request)
    assert not (tmp_path / "RuleStudy_Run_Ledger").exists()


def test_new_id_cannot_retry_failed_phase(tmp_path, monkeypatch):
    path, ledger, request = host_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        w.supervisor, "supervise", lambda *a, **kw: dict(status="timed_out", cleanup_verified=True)
    )
    f.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)
    request["plan"]["proposed_authorization_id"] = "another-offline-fixture-id"
    path.write_text(json.dumps(request))
    with pytest.raises(FileExistsError):
        f.dispatch_once(path, ledger=ledger, trusted_authorize=fixture_authority)
    assert len(list(ledger.glob("*.json"))) == 4


def test_structured_inspection_blocks_malformed_requests_without_traceback():
    for request in (None, {}, dict(kind=f.KIND, phase="evaluate")):
        result = f.assess(request)
        assert result["status"] == "BLOCKED" and result["execution_authorized"] is False


def test_prepared_batch_context_does_not_repeat_input_or_selection(monkeypatch, tmp_path):
    loaded = ({"cases": []}, {}, {})
    backend = SimpleNamespace(
        pair=lambda *a: pytest.fail("duplicate load"),
        selection=lambda *a: pytest.fail("duplicate selection"),
        drift=lambda *a: False,
    )
    from scripts import rule_study_metrics_core as mc

    monkeypatch.setattr(mc, "equal_work", lambda *a: [])
    request = dict(
        kind=f.KIND,
        limits=dict(
            wall_seconds=1, case_policy_seconds=1, states=60, transitions=60, output_bytes=1024
        ),
    )
    assert w._batch(request, tmp_path / "out", backend=backend, prepared=(loaded, [])) == 0


@pytest.fixture
def final_fixture(tmp_path, monkeypatch):
    """Known development-seed exclusion fixture; never constructs final RNG."""
    dev, _, _ = w.pair()
    rng = random.Random(2026111901)
    monkeypatch.setattr(random, "Random", lambda *a: pytest.fail("no further RNG allowed"))
    cases, weights, counters = gen.build(
        rng,
        dev,
        dict(wall_seconds=10, proposals=30000, feasibility_assignments=2430000),
        authorization_id="offline-fixture-generate-None",
    )
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(f, "ROOT", root)
    directory = tmp_path / "generated-fixture"
    directory.mkdir()
    pins = {
        "scripts/rule04_final_generation.py": cases["metadata"]["orchestrator_source_sha256_lf"],
        "dc_sustainability/evaluation/rule_study_generator.py": cases["metadata"][
            "generator_source_sha256"
        ],
    }
    request = dict(
        phase="evaluate",
        stage=0,
        freeze_reference="fixture-freeze",
        plan=dict(code_commit="fixture", code_sha256=pins, inputs={}),
    )
    c = binding(directory / "cases.json", cases)
    a = binding(directory / "accounting.json", weights)
    receipt = dict(
        status="GENERATED_PENDING_INDEPENDENT_RECEIVING",
        counters=counters,
        metadata_sha256=rr.digest(cases["metadata"]),
        code_commit="fixture",
        code_sha256=pins,
        development_inputs={},
        artifacts=dict(cases=c["sha256"], accounting=a["sha256"]),
        authenticated_request_sha256="a" * 64,
        freeze_reference="fixture-freeze",
        limits=generation_limits(),
    )
    gen_item = completed(root, directory, receipt, "generate", None)
    request["final_inputs"] = dict(cases=c, accounting=a, generation_receipt=gen_item)
    request["receiving"] = binding(
        tmp_path / "receiving.json",
        dict(
            artifact_sha256={k: v["sha256"] for k, v in request["final_inputs"].items()},
            reviewer="nkolekar-nk",
            case_predicates="PASS",
            strata_counts="PASS",
            no_full_case_overlap="PASS",
            accounting_visibility="PASS",
        ),
    )
    return request, cases, weights, receipt


def test_successful_generated_pair_static_guards_use_development_seed_only(final_fixture):
    request, _, _, _ = final_fixture
    assert len(f.pair(request)[2]) == 120


@pytest.mark.parametrize(
    "mode",
    [
        "authorization",
        "orchestrator_source_sha256_lf",
        "generator_version",
        "report",
        "generator_attempt",
        "label",
    ],
)
def test_rehashed_metadata_tamper_is_rejected_before_evaluation(final_fixture, mode, tmp_path):
    from dc_sustainability.evaluation import rule_study_generator as g

    request, cases, weights, receipt = final_fixture
    if mode == "generator_attempt":
        cases["cases"][0]["generator_attempt"] = 0
    elif mode == "label":
        next(c for c in cases["cases"] if c["stratum"] == "overloaded_impossible")[
            "feasibility_label"
        ] = "jointly_feasible"
    else:
        cases["metadata"][mode] = {} if mode == "report" else "tampered"
    weights["case_set_sha256"] = g.canonical_sha256(cases)
    for role, value in (("cases", cases), ("accounting", weights)):
        request["final_inputs"][role] = binding(Path(request["final_inputs"][role]["path"]), value)
    receipt["artifacts"] = {
        k: request["final_inputs"][k]["sha256"] for k in ("cases", "accounting")
    }
    request["final_inputs"]["generation_receipt"] = binding(
        Path(request["final_inputs"]["generation_receipt"]["path"]), receipt
    )
    with pytest.raises(ValueError):
        f.pair(request)


def test_host_publishes_bound_two_stage_evidence_and_join(tmp_path, monkeypatch):
    """Mock only policy/supervisor output; exercise actual host publication/guards."""
    from scripts import rule_study_metrics_core as mc

    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(f, "ROOT", root)
    monkeypatch.setattr(f, "assess", lambda *a, **kw: {"problems": []})
    monkeypatch.setattr(f, "drift", lambda *a, **kw: False)
    monkeypatch.setattr(w.worker, "environment_evidence", lambda: {"fixture": True})
    monkeypatch.setattr(mc, "equal_work", lambda *a: [])
    loaded = fixture_loaded()
    monkeypatch.setattr(f, "pair", lambda *a: loaded)
    request = dict(
        kind=f.KIND,
        phase="evaluate",
        stage=0,
        parent=None,
        plan=dict(
            code_commit="fixture",
            code_sha256={},
            proposed_authorization_id="offline-fixture-stage0",
            output_directory=str(tmp_path / "s0"),
        ),
        final_inputs={},
        receiving={},
        freeze_reference="fixture-freeze",
        limits=dict(
            states=10800,
            transitions=10800,
            wall_seconds=900,
            case_policy_seconds=60,
            output_bytes=256 * 1024 * 1024,
        ),
    )

    def authority(subject):
        return dict(
            subject,
            actor="MattyAnd",
            decision="approved",
            protocol_freeze_authenticated=True,
            generation_and_isolation_receiving_authenticated=True,
            parent_stage_authenticated=subject["stage"] == 1,
        )

    def supervised(command, *args, **kwargs):
        # No command is executed. These are explicit artificial fixture records.
        raw = Path(command[-2]).read_bytes()
        actual = w.decode_json(raw)
        out = Path(actual["plan"]["output_directory"])
        out.mkdir()
        chosen = f.selection(actual, loaded)
        auth = w.pf.sha(raw)
        grouped = {s: [] for s in ("normal_feasible", "overloaded_impossible", "missing_forecast")}
        sup = []
        for cid, policy in chosen:
            s = next(s for s in grouped if cid.startswith(f"fixture-{s}-"))
            metric = dict(case_id=cid, policy_id=policy, status="complete")
            grouped[s].append(dict(metric, stratum=s))
            task = binding(out / f"request-{cid}-{policy}.json", actual)
            directory = out / f"{cid}-{policy}"
            directory.mkdir()
            binding(
                directory / "pair-result.json",
                dict(
                    status="PASS",
                    case_id=cid,
                    policy_id=policy,
                    metric=metric,
                    authenticated_request_sha256=auth,
                    pair_request_sha256=task["sha256"],
                    budget=dict(states_used=60, transitions_used=60),
                    replay=dict(overall="PASS"),
                ),
            )
            sup.append(
                dict(
                    case_id=cid,
                    policy_id=policy,
                    supervision=dict(status="succeeded", cleanup_verified=True),
                )
            )
        binding(
            out / "rollout-report.json",
            dict(
                status="PASS",
                runs=180,
                selected_pairs=[list(p) for p in chosen],
                scope_complete_only=True,
                authenticated_request_sha256=auth,
                parent=actual["parent"],
                charged_steps=dict(states=10800, transitions=10800),
                strata=grouped,
                supervision=sup,
            ),
        )
        return dict(status="succeeded", cleanup_verified=True)

    monkeypatch.setattr(w.supervisor, "supervise", supervised)
    ledger = tmp_path / "RuleStudy_Run_Ledger"
    first = None
    items = []
    for stage in (0, 1):
        request["stage"] = stage
        request["parent"] = first
        request["plan"]["proposed_authorization_id"] = f"offline-fixture-stage{stage}"
        request["plan"]["output_directory"] = str(tmp_path / f"s{stage}")
        path = tmp_path / f"request{stage}.json"
        binding(path, request)
        result = f.dispatch_once(path, ledger=ledger, trusted_authorize=authority)
        assert result["status"] == "succeeded" and rr.is_digest(result["published_receipt_sha256"])
        rp = Path(request["plan"]["output_directory"]) / "stage-receipt.json"
        item = dict(path=str(rp), sha256=w.pf.sha(rp.read_bytes()))
        report = w.read_json(rp)
        assert len(report["supervision"]) == len(report["pair_supervision"]) == 180
        assert report["host_supervision"]["cleanup_verified"] is True
        f.validate_stage_receipt(request, item, stage, loaded, first=first)
        items.append(item)
        first = item
    assert f.join_stages(request, *items)["pairs"] == 360


def test_inspect_cli_returns_blocked_for_bad_json(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text('{"broken":')
    assert f.main(["inspect", str(path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "BLOCKED" and result["execution_authorized"] is False


def test_tree_inventory_stops_on_expired_publication_deadline(tmp_path):
    (tmp_path / "fixture.txt").write_text("fixture")
    with pytest.raises(TimeoutError, match="deadline"):
        rr.inventory(tmp_path, deadline=0)
    result = f.assess({}, deadline=0)
    assert result["status"] == "BLOCKED" and "deadline" in result["problems"][0]
