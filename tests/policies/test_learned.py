"""Observable P05 reload, hash refusal, schedule, and checked A fallback."""

from hashlib import sha256
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.knowledge import retrieve
from dc_sustainability.policies import learned
from dc_sustainability.runtime import ExecutionController, TraceStore, execute_policy_output
from dc_sustainability.simulator import SchedulingSimulator
from dc_sustainability.training.dataset import LabeledRow, rows_for_episodes
from dc_sustainability.training.features import FEATURE_NAMES
from dc_sustainability.training.train import ModelSpec, fit_model, save_artifact
from tests.contracts import fixtures as f
from tests.simulator.test_core import episode


def _features(seed: float, label: bool) -> tuple[float, ...]:
    base = [seed + index for index in range(len(FEATURE_NAMES))]
    if label:
        base[0] += 10.0
    return tuple(float(value) for value in base)


def _rows() -> tuple[LabeledRow, ...]:
    rows = []
    for episode_index, episode_id in enumerate(("EP-A", "EP-B", "EP-C", "EP-D")):
        for index in range(4):
            label = index % 2 == 0
            rows.append(
                LabeledRow(
                    episode_id=episode_id,
                    slot=index,
                    job_id=f"J{index}",
                    start_slot=index,
                    features=_features(episode_index * 10 + index, label),
                    label=label,
                )
            )
    return tuple(rows)


def _fit_tree(tmp_path: Path):
    rows = rows_for_episodes(_rows(), ("EP-A", "EP-B", "EP-C", "EP-D"))
    fitted = fit_model(ModelSpec("decision_tree_c", 3), rows, seed=11)
    path = tmp_path / "decision_tree_c.joblib"
    digest = save_artifact(fitted, path, manifest={"seed": 11})
    return path, digest, fitted


def _flex_job():
    return f.jobs()["J2"].model_copy(
        update={"arrival_slot": 0, "deadline_slot": 4, "duration_slots": 2, "power_kw": 30}
    )


def _carbon_series(values, *, issued_at=f.SLOT0_UTC, id_prefix="LC"):
    return tuple(
        s.CarbonForecast(
            fact_id=f"FACT-{id_prefix}-s{i:02d}",
            value=v,
            unit="g/kWh",
            source_id=f.SOURCE_ID,
            valid_slot=i,
            issued_at_utc=issued_at,
            forecast_kind="perfect_foresight",
            semantics=f.semantics(),
            quality_status="unvalidated",
        )
        for i, v in enumerate(values)
    )


def _state(waiting, carbon_facts=()):
    return s.VisibleState.from_snapshot(
        f.snapshot(),
        episode_id=f.EPISODE_ID,
        current_slot=0,
        state_version=0,
        waiting_jobs=tuple(waiting),
        carbon_facts=tuple(carbon_facts),
    )


def test_published_digests_match_p04_handoff_text():
    handoff = Path("docs/handoffs/P04_REAL_DEVELOPMENT_ARTIFACTS.md").read_text(encoding="utf-8")
    for system, digest in learned.PUBLISHED_DEVELOPMENT_SHA256.items():
        assert digest in handoff, system


def test_load_verified_rejects_digest_mismatch(tmp_path):
    path, digest, _ = _fit_tree(tmp_path)
    with pytest.raises(ValueError, match="artifact digest mismatch"):
        learned.load_verified(path, expected_sha256="0" * 64)
    artifact = learned.load_verified(path, expected_sha256=digest)
    assert artifact.artifact_sha256 == digest == sha256(path.read_bytes()).hexdigest()
    assert artifact.system == "decision_tree_c"


def test_load_published_development_requires_matching_system_digest(tmp_path):
    path, digest, _ = _fit_tree(tmp_path)
    with pytest.raises(ValueError, match="artifact digest mismatch"):
        learned.load_published_development(path, system="decision_tree_c")
    # When the temporary artifact happens to collide (vanishingly unlikely), skip.
    if digest == learned.PUBLISHED_DEVELOPMENT_SHA256["decision_tree_c"]:
        pytest.skip("synthetic digest collided with published C hash")


def test_propose_schedules_without_solver_when_forecasts_cover(tmp_path):
    path, digest, _ = _fit_tree(tmp_path)
    artifact = learned.load_verified(path, expected_sha256=digest)
    job = _flex_job()
    facts = _carbon_series((400, 400, 400, 400), id_prefix="OK")
    state = _state((job,), facts)
    context = s.Context.build(state, f.snapshot(), "flat")
    output = learned.propose(
        state,
        context,
        system="decision_tree_c",
        artifact=artifact,
        decision_time_utc=f.SLOT0_UTC,
        decision_origin_utc=f.SLOT0_UTC,
    )
    assert output.system == "decision_tree_c"
    assert output.output_status == "ok"
    assert output.explanation is None
    assert output.plan.starts or output.plan.abstentions


def test_missing_forecasts_use_checked_a_fallback(tmp_path):
    path, digest, _ = _fit_tree(tmp_path)
    artifact = learned.load_verified(path, expected_sha256=digest)
    job = _flex_job()
    state = _state((job,), ())
    context = s.Context.build(state, f.snapshot(), "flat")
    output = learned.propose(
        state,
        context,
        system="decision_tree_c",
        artifact=artifact,
        decision_time_utc=f.SLOT0_UTC,
    )
    assert output.system == "greedy_a"
    assert output.explanation is not None
    assert output.explanation.summary.startswith("learned_fallback:")


def test_learned_fallback_reaches_controller(tmp_path):
    path, digest, _ = _fit_tree(tmp_path)
    artifact = learned.load_verified(path, expected_sha256=digest)
    ep = episode((f.jobs()["J1"], f.jobs()["J2"]), withheld=True)
    sim = SchedulingSimulator(allow_completion_starts=False)
    sim.reset(ep, forecasts_by_slot={})
    store = TraceStore(tmp_path / "traces")
    controller = ExecutionController(sim, lambda: ep.snapshot, store)
    view = sim.state()
    context = retrieve(view, ep.snapshot).context
    output = learned.propose(
        view,
        context,
        system="decision_tree_c",
        artifact=artifact,
        decision_time_utc=f.SLOT0_UTC,
    )
    assert output.system == "greedy_a"
    result = execute_policy_output(
        controller,
        output,
        view,
        ep.snapshot,
        requested_system="decision_tree_c",
        decision_id="DEC-LEARNED-0",
        run_id="RUN-LEARNED",
        trial=0,
    )
    record = result.record
    assert record.system == "decision_tree_c"
    assert record.final_status == "executed"
    assert record.fallback is not None
    assert record.fallback.check.status == "pass"
    assert record.initial is None


def test_module_does_not_import_reference_solver():
    source = Path("dc_sustainability/policies/learned.py").read_text(encoding="utf-8")
    assert "reference.solver" not in source
    assert "from dc_sustainability.reference" not in source
