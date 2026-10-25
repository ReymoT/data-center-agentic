"""P03 constructor receiving on real F02/checker inputs; no trained-model claim."""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.knowledge import retrieve
from dc_sustainability.runtime import ExecutionController, TraceStore
from dc_sustainability.simulator import SchedulingSimulator
from dc_sustainability.training import schedule_from_probabilities
from dc_sustainability.verification.checker import check_schedule
from tests.contracts import fixtures as f
from tests.simulator.test_core import episode


class Classifier:
    """Explicit test-only injected scoring input, not a trained policy artifact."""

    def __init__(self, score=0.5):
        self.score = score

    def selection_probability(self, job, start_slot):
        return self.score


def inputs(jobs, *, current=0, include_capacity=True, running=(), pue=1.0):
    snapshot = f.snapshot(include_capacity=include_capacity, pue=pue)
    state = s.VisibleState.from_snapshot(
        snapshot,
        episode_id=f.EPISODE_ID,
        current_slot=current,
        state_version=current,
        waiting_jobs=tuple(jobs),
        running_jobs=tuple(running),
    )
    return state, s.Context.build(state, snapshot, "flat"), snapshot


def job(job_id, **updates):
    return s.Job(**(f.jobs()["J2"].model_dump(mode="python") | {"job_id": job_id} | updates))


def test_individually_infeasible_jobs_are_explicit_and_real_checker_accepts_valid_remainder():
    state, context, snapshot = inputs(
        (
            job("JFIT", duration_slots=1),
            job("JHEAVY", power_kw=150),
            job("JLATE", deadline_slot=1, duration_slots=3),
        )
    )
    output = schedule_from_probabilities(state, context, Classifier(), system="decision_tree_c")
    assert [(a.job_id, a.reason) for a in output.plan.abstentions] == [
        ("JHEAVY", "constraint_violation"),
        ("JLATE", "infeasible_deadline"),
    ]
    assert check_schedule(output.plan, state, snapshot).status == "pass"


def test_missing_capacity_is_explicit_missing_evidence_not_silent_job_omission():
    state, context, _ = inputs((job("JWAIT"),), include_capacity=False)
    output = schedule_from_probabilities(state, context, Classifier(), system="random_forest_d")
    assert not output.plan.starts
    assert [(a.job_id, a.reason) for a in output.plan.abstentions] == [
        ("JWAIT", "missing_evidence")
    ]


def test_equal_scores_and_nonnumeric_ids_are_deterministic_under_queue_shuffle():
    jobs = (job("JB"), job("JA"))
    outputs = []
    for waiting in (jobs, tuple(reversed(jobs))):
        state, context, _ = inputs(waiting)
        outputs.append(
            schedule_from_probabilities(state, context, Classifier(), system="decision_tree_c")
        )
    assert outputs[0].plan == outputs[1].plan
    assert [start.job_id for start in outputs[0].plan.starts] == ["JA", "JB"]


@pytest.mark.parametrize("score", [-0.1, 1.1, float("nan"), float("inf"), "0.9", None, True])
def test_invalid_classifier_probability_fails_explicitly(score):
    state, context, _ = inputs((job("JWAIT"),))
    with pytest.raises(ValueError, match="probability"):
        schedule_from_probabilities(state, context, Classifier(score), system="decision_tree_c")


@pytest.mark.parametrize("duration,expected_starts", [(7, (23,)), (8, ())])
def test_q01_finish_at_30_is_allowed_but_finish_after_30_is_not(duration, expected_starts):
    state, context, snapshot = inputs(
        (job("JEND", duration_slots=duration, deadline_slot=40),), current=23
    )
    output = schedule_from_probabilities(state, context, Classifier(), system="decision_tree_c")
    assert tuple(start.start_slot for start in output.plan.starts) == expected_starts
    assert check_schedule(output.plan, state, snapshot).status == "pass"


@pytest.mark.parametrize("pue", [1.0, 2.0])
def test_background_running_and_reserved_jobs_use_it_capacity_not_pue(pue):
    running = s.RunningJobView(job=job("JRUN", power_kw=30), start_slot=0)
    state, context, snapshot = inputs(
        (job("JA", power_kw=30), job("JB", power_kw=30)), running=(running,), pue=pue
    )
    output = schedule_from_probabilities(state, context, Classifier(), system="random_forest_d")
    assert [(x.job_id, x.start_slot) for x in output.plan.starts] == [("JA", 0), ("JB", 2)]
    assert check_schedule(output.plan, state, snapshot).status == "pass"


@pytest.mark.parametrize("system", ["decision_tree_c", "random_forest_d"])
def test_injected_fold_constructor_replans_through_real_controller_for_thirty_slots(
    tmp_path, system
):
    ep = episode((f.jobs()["J1"], f.jobs()["J2"]))
    sim = SchedulingSimulator(allow_completion_starts=False)
    sim.reset(ep)
    store = TraceStore(tmp_path / "traces")
    controller = ExecutionController(sim, lambda: ep.snapshot, store)
    starts = []
    for slot in range(30):
        state = sim.state()
        output = schedule_from_probabilities(
            state, retrieve(state, ep.snapshot).context, Classifier(), system=system
        )
        check = check_schedule(output.plan, state, ep.snapshot)
        assert check.status == "pass", (slot, check)
        draft = s.DecisionRecord(
            decision_id=f"DEC-P03-{slot}",
            run_id="RUN-P03",
            system=system,
            episode_id=state.episode_id,
            slot=slot,
            initial=s.StageRecord(plan=output.plan, check=check),
            not_applicable_stages=("repaired", "fallback"),
            final_status="blocked",
        )
        result = controller.execute_step(
            draft, stage="initial", expected_state_version=state.state_version
        )
        assert result.record.final_status == "executed"
        assert result.record.execution_check.status == "pass"
        assert result.record.model_call_count == result.record.repair_count == 0
        assert store.read(draft.decision_id) == result.record
        starts.extend((slot, x.job_id) for x in result.record.executed_starts)
    assert starts == [(0, "J1"), (2, "J2")]
    assert sim.result(run_id="RUN-P03", system=system).completed_job_ids == ("J1", "J2")
    assert sim.state().current_slot == len(sim.history) == 30
