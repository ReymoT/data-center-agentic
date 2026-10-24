"""Real S01/A03 execution on synthetic hand inputs, without model or policy stubs."""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.data.scenarios import hand_jobs
from dc_sustainability.runtime import ExecutionController, IndeterminateExecution, TraceStore
from dc_sustainability.simulator import SchedulingSimulator
from dc_sustainability.verification.checker import check_schedule, recheck_schedule
from tests.simulator.test_core import episode


def setup(tmp_path):
    ep = episode(hand_jobs()[:2])
    sim = SchedulingSimulator(allow_completion_starts=False)
    sim.reset(ep)
    store = TraceStore(tmp_path / "traces")
    controller = ExecutionController(sim, lambda: ep.snapshot, store)
    return ep, sim, store, controller


def intention(sim, snapshot, *, decision_id="DEC-GATE", starts=(("J1", 0), ("J2", 2)), **fields):
    state = sim.state()
    plan = s.Plan(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        status="proposed",
        starts=tuple(s.PlannedStart(job_id=j, start_slot=t) for j, t in starts),
    )
    return s.DecisionRecord(
        decision_id=decision_id,
        run_id="RUN-GATE",
        system="greedy_a",
        episode_id=state.episode_id,
        slot=state.current_slot,
        initial=s.StageRecord(plan=plan, check=check_schedule(plan, state, snapshot)),
        not_applicable_stages=("repaired", "fallback"),
        final_status="blocked",
        **fields,
    )


def execute(controller, draft, version=0, stage="initial"):
    return controller.execute_step(draft, stage=stage, expected_state_version=version)


def test_actual_checked_current_start_executes_but_future_intention_does_not(tmp_path):
    ep, sim, store, controller = setup(tmp_path)
    draft = intention(sim, ep.snapshot)
    outcome = execute(controller, draft)
    assert outcome.record.final_status == "executed"
    assert outcome.record.executed_starts == (s.ApprovedStart(job_id="J1", start_slot=0),)
    assert outcome.transition.slot.started_job_ids == ("J1",)
    assert sim.state().current_slot == 1 and len(sim.history) == 1
    assert store.read(draft.decision_id) == outcome.record
    assert outcome.record.initial == draft.initial


def test_capacity_change_between_proposal_and_execution_is_actually_rechecked(tmp_path):
    ep, sim, store, _ = setup(tmp_path)
    draft = intention(sim, ep.snapshot)
    changed = ep.snapshot.model_copy(
        update={
            "constraints": tuple(
                c.model_copy(update={"limit_value": 70.0}) if c.constraint_type == "capacity" else c
                for c in ep.snapshot.constraints
            )
        }
    )
    controller = ExecutionController(sim, lambda: changed, store)
    result = execute(controller, draft)
    assert draft.initial.check.status == "pass"
    assert result.record.execution_check.status == "fail"
    assert result.record.final_status == "blocked" and not result.record.executed_starts
    assert result.transition.slot.job_load_kw == 0 and sim.state().current_slot == 1


def test_stale_version_refuses_and_advances_once_then_replays_without_advancement(tmp_path):
    ep, sim, _, controller = setup(tmp_path)
    draft = intention(sim, ep.snapshot)
    first = execute(controller, draft, version=1)
    assert first.record.final_status == "blocked" and first.record.execution_check is None
    assert any("expected version" in e for e in first.record.errors)
    second = execute(controller, draft, version=1)
    assert second.replayed and second.record == first.record and second.transition is None
    assert sim.state().current_slot == len(sim.history) == 1


def test_restart_replays_the_saved_actual_trace_without_a_second_step(tmp_path):
    ep, sim, store, controller = setup(tmp_path)
    draft = intention(sim, ep.snapshot)
    first = execute(controller, draft)
    restarted = ExecutionController(sim, lambda: ep.snapshot, TraceStore(store.directory))
    second = execute(restarted, draft)
    assert second.replayed and second.record == first.record
    assert sim.state().current_slot == 1


def test_different_request_cannot_claim_the_same_run_slot(tmp_path):
    ep, sim, _, controller = setup(tmp_path)
    draft = intention(sim, ep.snapshot)
    execute(controller, draft)
    changed = draft.model_copy(update={"decision_id": "DEC-OTHER"})
    with pytest.raises(ValueError, match="already reserved"):
        execute(controller, changed)
    assert len(sim.history) == 1


def test_stale_slot_is_rejected_without_poisoning_another_slot(tmp_path):
    ep, sim, store, controller = setup(tmp_path)
    state = sim.state()
    empty = s.DecisionRecord(
        decision_id="DEC-WRONG",
        run_id="RUN-GATE",
        system="greedy_a",
        episode_id=state.episode_id,
        slot=1,
        final_status="blocked",
    )
    with pytest.raises(ValueError, match="stale/different"):
        execute(controller, empty, stage=None)
    assert not list(store._intents.iterdir()) and sim.state() == state
    assert execute(controller, intention(sim, ep.snapshot)).record.final_status == "executed"


def test_pending_effect_without_trace_requires_reconciliation_not_retry(tmp_path):
    ep, sim, store, controller = setup(tmp_path)
    draft = intention(sim, ep.snapshot)
    # Fault fixture: process stopped after intent publication, before effect completion.
    store.reserve(draft, "initial", 0)
    with pytest.raises(IndeterminateExecution, match="reconcile"):
        execute(controller, draft)
    assert sim.state().current_slot == 0


def test_trace_failure_after_real_execution_cannot_repeat_effect(tmp_path, monkeypatch):
    ep, sim, store, controller = setup(tmp_path)
    draft = intention(sim, ep.snapshot)
    with monkeypatch.context() as patch:

        def broken_write(record):
            raise OSError("test-only storage failure")

        patch.setattr(store, "write", broken_write)
        with pytest.raises(IndeterminateExecution):
            execute(controller, draft)
    assert sim.state().current_slot == 1
    with pytest.raises(IndeterminateExecution):
        execute(controller, draft)
    assert len(sim.history) == 1


def test_trace_write_is_immutable_and_rejects_corruption(tmp_path):
    ep, sim, store, controller = setup(tmp_path)
    final = execute(controller, intention(sim, ep.snapshot)).record
    original = store._path(final.decision_id).read_bytes()
    assert store.write(final).read_bytes() == original
    with pytest.raises(ValueError, match="different immutable"):
        store.write(final.model_copy(update={"errors": ("different record",)}))
    assert store._path(final.decision_id).read_bytes() == original
    store._path(final.decision_id).write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError):
        store.read(final.decision_id)


def test_direct_capability_cannot_bypass_controller(tmp_path):
    ep, sim, _, controller = setup(tmp_path)
    draft = intention(sim, ep.snapshot)
    capability = s.ApprovedActions.from_checked_plan(draft.initial.plan, draft.initial.check, 0)
    with pytest.raises(TypeError, match="DecisionRecord"):
        execute(controller, capability)
    assert not sim.history


def test_actual_failed_check_blocks_starts_and_advances_the_clock(tmp_path):
    ep, sim, _, controller = setup(tmp_path)
    draft = intention(sim, ep.snapshot, starts=(("J1", 0),))  # J2 omitted.
    assert draft.initial.check.status == "fail"
    result = execute(controller, draft)
    assert result.record.final_status == "blocked" and result.record.execution_check is None
    assert not result.transition.slot.started_job_ids and len(sim.history) == 1


def test_constraints_changing_during_recheck_refuse_instead_of_using_stale_approval(tmp_path):
    ep, sim, store, _ = setup(tmp_path)
    draft = intention(sim, ep.snapshot)
    snapshots = iter((ep.snapshot, ep.snapshot.model_copy(update={"snapshot_id": "SNAP-CHANGED"})))
    controller = ExecutionController(sim, lambda: next(snapshots), store)
    result = execute(controller, draft)
    assert result.record.final_status == "blocked"
    assert any("changed during recheck" in e for e in result.record.errors)
    assert not result.transition.slot.started_job_ids and sim.state().current_slot == 1


def test_plain_system_cannot_execute_a_fallback_stage(tmp_path):
    ep, sim, _, controller = setup(tmp_path)
    draft = intention(sim, ep.snapshot)
    staged = draft.model_copy(
        update={
            "system": "plain_llm",
            "fallback": draft.initial,
            "not_applicable_stages": ("repaired",),
        }
    )
    result = execute(controller, staged, stage="fallback")
    assert result.record.final_status == "blocked"
    assert any("plain LLM" in e for e in result.record.errors)
    assert not result.transition.slot.started_job_ids


def test_existing_decision_id_cannot_be_reused_for_another_slot(tmp_path):
    ep, sim, _, controller = setup(tmp_path)
    execute(controller, intention(sim, ep.snapshot))
    changed = intention(sim, ep.snapshot, starts=(("J2", 2),))
    with pytest.raises(ValueError, match="already has a trace"):
        execute(controller, changed, version=1)
    assert len(sim.history) == 1


def test_historical_error_does_not_block_a_later_actually_checked_stage(tmp_path):
    ep, sim, _, controller = setup(tmp_path)
    invalid = intention(sim, ep.snapshot, starts=(("J1", 0),))
    valid = intention(sim, ep.snapshot)
    # Test-only staged inputs; this is not an implemented P02 fallback or model result.
    draft = invalid.model_copy(
        update={
            "system": "agent",
            "fallback": valid.initial,
            "not_applicable_stages": ("repaired",),
            "errors": ("initial proposal omitted J2",),
        }
    )
    result = execute(controller, draft, stage="fallback")
    assert result.record.final_status == "executed"
    assert result.record.initial == invalid.initial and result.record.fallback == valid.initial
    assert "initial proposal omitted J2" in result.record.errors


@pytest.mark.parametrize("field,value", [("model_call_count", 4), ("repair_count", 2)])
def test_caps_refuse_execution_without_manufacturing_usage(tmp_path, field, value):
    ep, sim, _, controller = setup(tmp_path)
    draft = intention(sim, ep.snapshot).model_copy(update={"system": "agent", field: value})
    result = execute(controller, draft)
    assert result.record.final_status == "blocked" and not result.record.executed_starts
    assert getattr(result.record, field) == value


def test_same_slot_new_version_rechecks_content_and_retains_original_plan_hash(tmp_path):
    ep, sim, _, _ = setup(tmp_path)
    draft = intention(sim, ep.snapshot)
    latest = sim.state().model_copy(update={"state_version": 5})
    result = recheck_schedule(draft.initial.plan, latest, ep.snapshot)
    assert result.status == "pass" and result.state_version == 5
    assert result.plan_hash == draft.initial.plan.plan_hash
    assert s.ApprovedActions.from_checked_plan(draft.initial.plan, result, 5).state_version == 5


def test_thirty_actual_slots_drain_running_work_and_keep_each_trace(tmp_path):
    ep, sim, store, controller = setup(tmp_path)
    for slot in range(30):
        starts = tuple(
            (job.job_id, 0 if job.job_id == "J1" else 2) for job in sim.state().waiting_jobs
        )
        draft = intention(sim, ep.snapshot, decision_id=f"DEC-S{slot}", starts=starts)
        result = execute(controller, draft, version=slot)
        assert result.record.final_status == "executed"
        assert result.record.model_call_count == result.record.repair_count == 0
        assert store.read(draft.decision_id) == result.record
    assert len(sim.history) == 30
    assert sim.result(run_id="RUN-GATE", system="greedy_a").completed_job_ids == ("J1", "J2")
