"""Regression tests for O03 offline hindsight reference generation/export."""

import json
import os
from datetime import timedelta
from pathlib import Path

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.reference.hindsight import (
    HindsightError,
    export_hindsight_reference,
    generate_hindsight_reference,
    load_hindsight_reference,
    reject_hindsight_in_context,
    solve_hindsight,
)
from tests.contracts import fixtures as f


def _extend_carbon(episode: s.PrivateEpisode) -> s.PrivateEpisode:
    """Pad the hand fixture's 7-slot realized carbon to the full 30-slot horizon."""
    base = list(episode.realized_carbon)
    last = base[-1]
    horizon = episode.n_decision_slots + episode.n_completion_slots
    for i in range(len(base), horizon):
        base.append(
            last.model_copy(
                update={
                    "fact_id": f"FACT-OBS-CI-s{i:02d}",
                    "valid_slot": i,
                    "observed_at_utc": last.observed_at_utc + timedelta(hours=i - last.valid_slot),
                }
            )
        )
    return episode.model_copy(update={"realized_carbon": tuple(base)})


def _full_episode() -> s.PrivateEpisode:
    return _extend_carbon(f.private_episode())


def test_hindsight_solver_is_certified_optimal():
    episode = _full_episode()
    result = solve_hindsight(episode, time_limit_s=5.0)
    assert result.status == "certified_optimal"
    assert result.kind == "hindsight"
    assert result.uses_future_arrivals is True
    assert result.offline_only is True
    assert result.schedule is not None
    scheduled = {(ps.job_id, ps.start_slot) for ps in result.schedule}
    assert scheduled == {("J1", 2), ("J2", 4)}
    assert result.objective_kg == pytest.approx(48.4, abs=1e-6)
    assert result.matching_work_job_ids == ("J1", "J2")
    assert result.backend == "scipy.optimize.milp"


def test_capacity_blocked_job_cannot_silently_disappear():
    ep = _full_episode()
    jobs = tuple(
        pj.model_copy(update={"job": pj.job.model_copy(update={"power_kw": 80.0})})
        if pj.job.job_id == "J1"
        else pj
        for pj in ep.jobs
    )
    result = solve_hindsight(ep.model_copy(update={"jobs": jobs}), time_limit_s=5.0)
    assert result.status == "certified_infeasible"
    assert result.schedule is None


@pytest.mark.parametrize("limit", [0, -1, float("nan"), float("inf")])
def test_hindsight_rejects_invalid_time_budget(limit):
    with pytest.raises(HindsightError, match="positive and finite"):
        solve_hindsight(_full_episode(), time_limit_s=limit)


def test_hindsight_artifact_has_correct_markers():
    episode = _full_episode()
    artifact = generate_hindsight_reference(episode, time_limit_s=5.0)
    assert artifact.record_type == "HindsightReferenceArtifact"
    assert artifact.offline_only is True
    assert artifact.complete is True
    assert artifact.solver_result.kind == "hindsight"
    assert artifact.solver_result.uses_future_arrivals is True
    assert artifact.solver_version == "o03-v1"
    assert artifact.source_snapshot_hash == episode.snapshot.canonical_hash()
    assert artifact.realized_carbon_hash
    assert artifact.solver_config_hash
    assert artifact.generated_at_utc.tzinfo is not None


def test_hindsight_is_deterministic():
    episode = _full_episode()
    first = generate_hindsight_reference(episode, time_limit_s=5.0)
    second = generate_hindsight_reference(episode, time_limit_s=5.0)
    assert first.solver_result.schedule == second.solver_result.schedule
    assert first.solver_result.objective_kg == second.solver_result.objective_kg
    assert first.solver_result.input_hash == second.solver_result.input_hash
    assert first.realized_carbon_hash == second.realized_carbon_hash


def test_realized_carbon_alignment():
    """The hindsight objective must equal the hand-calculated realized emissions."""
    episode = _full_episode()
    result = solve_hindsight(episode, time_limit_s=5.0)
    assert result.schedule is not None
    carbon = {obs.valid_slot: obs.value for obs in episode.realized_carbon}
    site = episode.snapshot.site
    total_g = 0.0
    for ps in result.schedule:
        job = next(pj.job for pj in episode.jobs if pj.job.job_id == ps.job_id)
        for slot in range(ps.start_slot, ps.start_slot + job.duration_slots):
            total_g += job.power_kw * site.slot_hours * site.pue * carbon[slot]
    assert result.objective_kg == pytest.approx(total_g / 1000.0, abs=1e-6)


def test_rejects_non_private_episode():
    with pytest.raises(HindsightError):
        solve_hindsight("not an episode")  # type: ignore[arg-type]


def test_rejects_missing_realized_carbon():
    episode = _full_episode().model_copy(update={"realized_carbon": ()})
    with pytest.raises(HindsightError, match="realized carbon"):
        solve_hindsight(episode)


def test_rejects_misaligned_realized_carbon():
    episode = _full_episode()
    truncated = episode.realized_carbon[:5]
    episode = episode.model_copy(update={"realized_carbon": truncated})
    with pytest.raises(HindsightError, match="slot"):
        solve_hindsight(episode)


def test_infeasible_episode_is_certified_infeasible():
    """Make capacity so low that even background load leaves no room for jobs."""
    episode = _full_episode()
    snap = episode.snapshot.model_copy(
        update={
            "constraints": tuple(
                c.model_copy(update={"limit_value": 10.0}) if c.constraint_type == "capacity" else c
                for c in episode.snapshot.constraints
            )
        }
    )
    episode = episode.model_copy(update={"snapshot": snap})
    result = solve_hindsight(episode, time_limit_s=5.0)
    assert result.status == "certified_infeasible"
    assert result.schedule is None
    assert result.objective_kg is None


def test_export_and_load_roundtrip(tmp_path: Path):
    episode = _full_episode()
    artifact = generate_hindsight_reference(episode, time_limit_s=5.0)
    artifact_path, manifest_path = export_hindsight_reference(artifact, tmp_path)
    assert artifact_path.exists()
    assert manifest_path.exists()
    if os.name != "nt":
        assert artifact_path.stat().st_mode & 0o777 == 0o600
        assert manifest_path.stat().st_mode & 0o777 == 0o600

    loaded = load_hindsight_reference(artifact_path)
    assert loaded.artifact_id == artifact.artifact_id
    assert loaded.solver_result.schedule == artifact.solver_result.schedule
    assert loaded.offline_only is True

    manifest = json.loads(manifest_path.read_text())
    assert manifest["artifact_id"] == artifact.artifact_id
    assert manifest["offline_only"] is True
    assert manifest["uses_future_arrivals"] is True


def test_export_rejects_git_directory(tmp_path: Path):
    git_dir = tmp_path / "repo"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()
    artifact = generate_hindsight_reference(_full_episode(), time_limit_s=5.0)
    with pytest.raises(HindsightError, match="Git"):
        export_hindsight_reference(artifact, git_dir)


def test_export_rejects_overwrite(tmp_path: Path):
    artifact = generate_hindsight_reference(_full_episode(), time_limit_s=5.0)
    export_hindsight_reference(artifact, tmp_path)
    with pytest.raises(HindsightError, match="already exist"):
        export_hindsight_reference(artifact, tmp_path)


def test_reject_hindsight_in_context():
    episode = _full_episode()
    generate_hindsight_reference(episode, time_limit_s=5.0)
    state = f.visible_state(episode.snapshot)
    context = s.Context.build(state, episode.snapshot, representation="flat")
    # Simulate a poisoned context JSON payload that somehow contains hindsight-only evidence.
    jsonable = context.to_jsonable()
    jsonable["content"]["solver_result_kind"] = "hindsight"
    # Bypass pydantic extra-field rejection so the defensive check can fire.
    with pytest.raises(HindsightError, match="not policy-visible"):
        reject_hindsight_in_context(jsonable)


def test_hindsight_result_does_not_mix_with_visible_labels():
    """Hindsight schedule must not be mistaken for a visible-state label."""
    episode = _full_episode()
    result = solve_hindsight(episode, time_limit_s=5.0)
    assert result.kind == "hindsight"
    assert result.uses_future_arrivals is True
    # A visible-state result would have kind="visible" and uses_future_arrivals=False.
    assert result.kind != "visible"
    assert result.uses_future_arrivals is not False
