"""Common checked runner: real simulator, real production checker, unchanged Greedy A/B."""

import hashlib
import json
from dataclasses import replace

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.rule_study import cases as c
from dc_sustainability.rule_study import runner as rn
from dc_sustainability.rule_study.runner import IndeterminateExecution, replay_case
from tests.rule_study.helpers import REPO_ROOT, bindings_for, case_with, fresh_runner, job, run


def _evidence(case_run, index):
    ref = case_run.outcomes[index].record.execution.transition_ref
    return json.loads((case_run.root / ref).read_text(encoding="utf-8"))


def _reasons(case_run, index):
    return _evidence(case_run, index)["fallback_reasons"]


def starts_by_slot(case_run):
    return {
        o.record.decision_index: sorted(o.record.execution.current_starts)
        for o in case_run.outcomes
        if o.record.execution.current_starts
    }


# --------------------------------------------------------------------------- scenario A
def test_scenario_a_executes_only_current_starts_and_completes_both(tmp_path):
    case_run, sim, _ = run(tmp_path, c.CASE_A)
    result = case_run.result
    # Slot 0 starts J2 only; J1@1 is an advisory future start that is re-evaluated at slot 1.
    assert starts_by_slot(case_run) == {0: ["J2"], 1: ["J1"]}
    assert result.status == "complete"
    assert result.completed_job_ids == ("J1", "J2")
    assert result.missed_job_ids == () and result.unfinished_job_ids == ()
    assert len(sim.history) == 30 and len(case_run.outcomes) == 30
    first = case_run.outcomes[0].record
    assert first.execution.status == "executed"
    assert first.execution.current_starts == ("J2",)
    assert first.proposal_stages[0].origin == "rules-v1"
    assert first.model_call_count == 0


def test_future_start_is_never_executed_early(tmp_path):
    case_run, _, _ = run(tmp_path, c.CASE_A)
    plan = case_run.outcomes[0].record.proposal_stages[0].plan
    assert {(p.job_id, p.start_slot) for p in plan.starts} == {("J2", 0), ("J1", 1)}
    assert case_run.outcomes[0].record.execution.current_starts == ("J2",)
    assert case_run.outcomes[1].record.execution.current_starts == (
        "J1",
    )  # only once slot 1 is current


def test_latest_state_recheck_is_performed_and_recorded(tmp_path, monkeypatch):
    seen = []
    real = rn.recheck_schedule

    def spy(plan, state, snapshot):
        seen.append((state.current_slot, state.state_version))
        return real(plan, state, snapshot)

    monkeypatch.setattr(rn, "recheck_schedule", spy)
    runner, _ = fresh_runner(tmp_path, c.CASE_A)
    outcome = runner.decide(0)
    assert seen == [(0, 0)]
    evidence = json.loads(
        (runner.root / outcome.record.execution.transition_ref).read_text(encoding="utf-8")
    )
    assert evidence["latest_state_recheck"]["status"] == "pass"


def test_accounting_uses_actual_transitions_and_labels_the_convention(tmp_path):
    case_run, _, _ = run(tmp_path, c.CASE_A)
    accounting = case_run.result.accounting
    assert accounting.synthetic_impact_total == 8000  # J2@0: 20*300, J1@1: 20*100
    assert accounting.slots_recorded == 30
    assert accounting.score_convention_status != "agreed"
    assert accounting.pue == 1.0
    assert accounting.job_it_energy_kwh == 40.0
    assert accounting.site_facility_energy_kwh == 40.0 + 20.0 * 30


# --------------------------------------------------------------------------- scenario B
def test_scenario_b_is_blocked_honestly_with_a_failed_fallback(tmp_path):
    case_run, _, _ = run(tmp_path, c.CASE_B)
    first = case_run.outcomes[0].record
    origins = [(st.origin, st.check_result.status) for st in first.proposal_stages]
    assert origins[0][0] == "rules-v1" and origins[0][1] != "pass"
    assert origins[-1][0] == "greedy_a_fallback" and origins[-1][1] != "pass"
    assert first.selected_stage_id is None
    assert first.execution.current_starts == ()
    assert first.execution.status == "blocked"
    result = case_run.result
    assert result.completed_job_ids == ()
    assert result.missed_job_ids == ("J1", "J2")
    assert any(e.code == "NO_APPROVED_CANDIDATE" for e in first.errors)


def test_scenario_b_progress_runs_j1_then_j2(tmp_path):
    case_run, _, _ = run(tmp_path, c.CASE_B_PROGRESS)
    assert starts_by_slot(case_run) == {0: ["J1"], 1: ["J2"]}
    assert case_run.result.completed_job_ids == ("J1", "J2")
    assert case_run.result.status == "complete"


def test_refusal_advances_exactly_one_slot_and_running_work_progresses(tmp_path):
    runner, sim = fresh_runner(tmp_path, c.CASE_B)
    outcome = runner.decide(0)
    assert outcome.record.execution.status == "blocked"
    assert sim.state().current_slot == 1
    assert len(sim.history) == 1
    assert outcome.record.execution.simulator_rejection  # the simulator's own refusal-and-drain


# --------------------------------------------------------------------------- fallback
def _incomplete_plan(state):
    """A proposal the production checker rejects: it silently drops a nonflexible job."""
    if state.current_slot != 0:
        return None
    return s.Plan(
        episode_id=state.episode_id,
        slot=0,
        state_version=state.state_version,
        starts=(s.PlannedStart(job_id="J1", start_slot=0),),
        evidence_ids=("CON-CAP-01", "FACT-JOB-J1"),
        status="proposed",
    )


def test_invalid_proposal_routes_to_the_actual_greedy_a_fallback(tmp_path):
    case_run, _, _ = run(tmp_path, c.CASE_A, fault_injection=_incomplete_plan)
    first = case_run.outcomes[0].record
    origins = [st.origin for st in first.proposal_stages]
    assert origins == ["fault_injection", "greedy_a_fallback"]
    injected, fallback = first.proposal_stages
    assert injected.check_result.status != "pass"
    assert fallback.check_result.status == "pass"
    assert _reasons(case_run, 0)[fallback.stage_id] == "invalid_proposal"
    assert any(e.rule_id == "R08" for e in fallback.arithmetic)
    assert first.selected_stage_id == fallback.stage_id
    assert sorted(first.execution.current_starts) == ["J1", "J2"]
    assert _evidence(case_run, 0)["latest_state_recheck"]["status"] == "pass"


def test_fallback_is_independently_checked_and_never_trusted(tmp_path, monkeypatch):
    seen = []
    real = rn.check_schedule

    def spy(plan, state, snapshot):
        result = real(plan, state, snapshot)
        seen.append(result.status)
        return result

    monkeypatch.setattr(rn, "check_schedule", spy)
    runner, _ = fresh_runner(tmp_path, c.CASE_A, fault_injection=_incomplete_plan)
    runner.decide(0)
    assert len(seen) == 2 and seen[0] != "pass" and seen[1] == "pass"


def test_failed_fallback_executes_no_starts(tmp_path):
    runner, sim = fresh_runner(tmp_path, c.CASE_B, fault_injection=_incomplete_plan)
    outcome = runner.decide(0)
    assert outcome.record.execution.current_starts == ()
    assert outcome.record.execution.status == "blocked"
    assert all(not t.slot.started_job_ids for t in sim.history)


# --------------------------------------------------------------------------- forecast fallback
def _tampered(case, mutate):
    table = case.forecasts_by_slot()
    return {slot: tuple(mutate(slot, f) for f in facts) for slot, facts in table.items()}


def _run_with_forecasts(tmp_path, case, table):
    from dc_sustainability.simulator import SchedulingSimulator

    sim = SchedulingSimulator(allow_completion_starts=False)
    sim.reset(case.episode(), forecasts_by_slot=table)
    runner, _ = fresh_runner(tmp_path, case, simulator=sim)
    outcome = runner.decide(0)
    evidence = json.loads(
        (runner.root / outcome.record.execution.transition_ref).read_text(encoding="utf-8")
    )
    return outcome, evidence["fallback_reasons"]


def test_missing_forecast_routes_to_checked_greedy_a(tmp_path):
    case = replace(c.CASE_A, forecast_present=False, case_id="NOFC")
    case_run, _, _ = run(tmp_path, case)
    first = case_run.outcomes[0].record
    fallback = first.proposal_stages[-1]
    assert fallback.origin == "greedy_a_fallback"
    assert _reasons(case_run, 0)[fallback.stage_id] == "missing"
    assert fallback.check_result.status == "pass"
    assert first.execution.status == "executed"


def test_partial_forecast_routes_to_checked_greedy_a(tmp_path):
    table = {
        slot: tuple(f for f in facts if f.valid_slot != slot + 1)
        for slot, facts in c.CASE_A.forecasts_by_slot().items()
    }
    outcome, reasons = _run_with_forecasts(tmp_path, replace(c.CASE_A, case_id="PART"), table)
    fallback = outcome.record.proposal_stages[-1]
    assert (fallback.origin, reasons[fallback.stage_id]) == ("greedy_a_fallback", "partial")
    assert fallback.check_result.status == "pass"


def test_stale_forecast_routes_to_checked_greedy_a(tmp_path):
    from datetime import timedelta

    table = _tampered(
        c.CASE_A,
        lambda slot, f: f.model_copy(
            update={"issued_at_utc": f.issued_at_utc - timedelta(hours=10)}
        ),
    )
    outcome, reasons = _run_with_forecasts(tmp_path, replace(c.CASE_A, case_id="STALE"), table)
    fallback = outcome.record.proposal_stages[-1]
    assert (fallback.origin, reasons[fallback.stage_id]) == ("greedy_a_fallback", "stale")


def test_future_issued_forecast_routes_to_checked_greedy_a(tmp_path):
    from datetime import timedelta

    table = _tampered(
        c.CASE_A,
        lambda slot, f: f.model_copy(
            update={"issued_at_utc": f.issued_at_utc + timedelta(hours=10)}
        ),
    )
    outcome, reasons = _run_with_forecasts(tmp_path, replace(c.CASE_A, case_id="FUT"), table)
    fallback = outcome.record.proposal_stages[-1]
    assert (fallback.origin, reasons[fallback.stage_id]) == ("greedy_a_fallback", "future")


# --------------------------------------------------------------------------- races
class RacingSimulator:
    """Delegates to the real simulator but advances it externally on the Nth ``state()`` call."""

    def __init__(self, real, on_call):
        self._real, self._on_call, self.state_calls = real, on_call, 0

    def state(self):
        self.state_calls += 1
        if self.state_calls == self._on_call:
            self._real.step(None)  # someone else moved the live simulator
        return self._real.state()

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_state_change_during_check_refuses_without_stepping(tmp_path):
    from dc_sustainability.simulator import SchedulingSimulator

    real = SchedulingSimulator(allow_completion_starts=False)
    real.reset(c.CASE_A.episode(), forecasts_by_slot=c.CASE_A.forecasts_by_slot())
    racing = RacingSimulator(real, on_call=3)
    runner, _ = fresh_runner(tmp_path, c.CASE_A, simulator=racing)
    outcome = runner.decide(0)
    assert outcome.stopped
    assert [e.code for e in outcome.record.errors] == ["STOP_STATE_CHANGED"]
    # No step happened, so there is no state_after: the merged reader requires one for every
    # status except "indeterminate", which is how a stop needing reconciliation is recorded.
    assert outcome.record.execution.status == "indeterminate"
    assert outcome.record.execution.state_after is None
    assert outcome.record.execution.current_starts == ()
    assert len(real.history) == 1  # only the external step; the runner never stepped


def test_constraint_change_during_check_triggers_one_refusal_and_drain(tmp_path):
    original = c.CASE_A.snapshot()
    changed = replace(c.CASE_A, capacity_kw=40).snapshot()
    calls = {"n": 0}

    def reader():
        calls["n"] += 1
        return changed if calls["n"] >= 3 else original

    runner, sim = fresh_runner(tmp_path, c.CASE_A, reader=reader)
    outcome = runner.decide(0)
    codes = [e.code for e in outcome.record.errors]
    assert "CONSTRAINTS_CHANGED" in codes
    assert outcome.record.execution.current_starts == ()
    assert len(sim.history) == 1 and not sim.history[0].slot.started_job_ids


# --------------------------------------------------------------------------- horizon & stop rules
def test_no_starts_are_executed_in_completion_slots(tmp_path):
    case = case_with([job("J1", 20, 30, True, duration=1)], scores=(100,) * 30, remaining=100)
    case_run, _, _ = run(tmp_path, case)
    assert all(slot <= 5 for slot in starts_by_slot(case_run))
    assert all(
        not o.record.execution.current_starts
        for o in case_run.outcomes
        if o.record.decision_index >= 24
    )


def test_five_waiting_jobs_stop_without_stepping(tmp_path):
    jobs = [job(f"J{i}", 10, 6, True) for i in range(1, 6)]
    case = case_with(jobs, capacity=200)
    case_run, sim, _ = run(tmp_path, case)
    first = case_run.outcomes[0]
    assert first.stopped
    assert len(case_run.outcomes) == 1 and len(sim.history) == 0
    assert case_run.result.status == "partial"
    assert any(e.code.startswith("STOP_") for e in first.record.errors)


# --------------------------------------------------------------------------- replay & idempotency
def test_replay_returns_identical_saved_evidence_without_stepping(tmp_path):
    case_run, sim, runner = run(tmp_path, c.CASE_A)
    before = len(sim.history)
    replayed = replay_case(runner)
    assert len(sim.history) == before
    assert all(o.replayed for o in replayed)
    for original, again in zip(case_run.outcomes, replayed):
        assert original.record == again.record
        assert original.decision_sha256 == again.decision_sha256


@pytest.mark.parametrize(
    "case_id", ["../escape", "..\\escape", "/absolute", "C:drive", "a/b", "a\\b"]
)
def test_case_identity_cannot_escape_trace_directory(tmp_path, case_id):
    with pytest.raises(ValueError, match="single path component"):
        rn.RuleStudyRunner(
            None,
            c.CASE_A.snapshot,
            tmp_path,
            policy_id="rules-v1",
            case_id=case_id,
            decision_time_utc=c.CASE_A.decision_time_utc,
            bindings=bindings_for(c.CASE_A),
            score_convention=rn.sch.ScoreKwhConvention(),
        )
    assert list(tmp_path.iterdir()) == []


def test_case_body_must_match_binding_before_writing(tmp_path):
    case = c.CASE_A
    with pytest.raises(ValueError, match="different immutable file"):
        rn.RuleStudyRunner(
            None,
            case.snapshot,
            tmp_path,
            policy_id="rules-v1",
            case_id=case.case_id,
            decision_time_utc=case.decision_time_utc,
            bindings=bindings_for(replace(case, background_kw=10)),
            score_convention=rn.sch.ScoreKwhConvention(),
            case_json=case.case_json(),
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("target", ["decision", "transition", "state", "snapshot", "case"])
def test_replay_refuses_modified_saved_evidence_without_stepping(tmp_path, target):
    runner, sim = fresh_runner(tmp_path, c.CASE_A)
    outcome = runner.decide(0)
    record = outcome.record
    paths = {
        "decision": runner.root / outcome.decision_ref,
        "transition": runner.root / record.execution.transition_ref,
        "state": runner.root / "states" / f"{record.state_before.visible_state_sha256}.json",
        "snapshot": runner.root
        / "snapshots"
        / f"{record.state_before.constraint_snapshot_sha256}.json",
        "case": runner.root / "case.json",
    }
    # Still parseable JSON: even whitespace changes exact persisted bytes.
    with paths[target].open("a", encoding="utf-8") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="commitment|hash mismatch"):
        runner.decide(0)
    assert len(sim.history) == 1


def test_missing_completion_commitment_never_reexecutes(tmp_path):
    runner, sim = fresh_runner(tmp_path, c.CASE_A)
    runner.decide(0)
    (runner.root / ".completed" / "decision-00.json").unlink()
    with pytest.raises(IndeterminateExecution, match="completion commitment"):
        runner.decide(0)
    assert len(sim.history) == 1


def test_result_refuses_modified_transition(tmp_path):
    case_run, _, _ = run(tmp_path, c.CASE_A)
    path = case_run.root / case_run.outcomes[0].record.execution.transition_ref
    with path.open("a", encoding="utf-8") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="transition hash mismatch"):
        rn.build_result(
            case_run.root, c.CASE_A, "rules-v1", bindings_for(c.CASE_A), rn.sch.ScoreKwhConvention()
        )


def test_nonunit_pue_is_not_silently_bound_to_same_case(tmp_path):
    with pytest.raises(ValueError, match="PUE to 1"):
        run(tmp_path, replace(c.CASE_A, pue=1.7))
    assert list(tmp_path.iterdir()) == []


def test_replay_from_a_restarted_runner_uses_only_saved_evidence(tmp_path):
    case_run, _, _ = run(tmp_path, c.CASE_A)
    runner2, sim2 = fresh_runner(tmp_path, c.CASE_A)
    outcome = runner2.decide(0)
    assert outcome.replayed
    assert outcome.decision_sha256 == case_run.outcomes[0].decision_sha256
    assert len(sim2.history) == 0  # no transition was repeated


def test_different_request_on_a_reserved_slot_is_refused(tmp_path):
    runner, _ = fresh_runner(tmp_path, c.CASE_A)
    runner.decide(0)
    # Same policy/case identity and trace directory, but a different case body (different
    # case hash): the reserved intent belongs to another request and must not be reused.
    other = replace(c.CASE_A, background_kw=10)
    with pytest.raises(ValueError, match="different immutable file"):
        fresh_runner(tmp_path, other)  # the saved case.json is immutable and differs
    # With the same case body but different bindings the reserved intent itself refuses.
    runner3, _ = fresh_runner(tmp_path, c.CASE_A)
    runner3._bindings = bindings_for(other)
    with pytest.raises(ValueError, match="already reserved"):
        runner3.decide(0)


def test_indeterminate_failure_is_recorded_and_never_retried(tmp_path, monkeypatch):
    runner, sim = fresh_runner(tmp_path, c.CASE_A)

    def boom(*args, **kwargs):
        raise OSError("disk went away")

    monkeypatch.setattr(runner, "_publish_record", boom)
    with pytest.raises(IndeterminateExecution):
        runner.decide(0)
    monkeypatch.undo()
    steps = len(sim.history)
    with pytest.raises(IndeterminateExecution):
        runner.decide(0)  # reserved intent without a final record: reconcile, do not retry
    assert len(sim.history) == steps == 1


def test_run_case_reports_a_failed_result_after_an_indeterminate_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        rn.RuleStudyRunner, "_publish_record", lambda *a, **k: (_ for _ in ()).throw(OSError("x"))
    )
    case_run, _, _ = run(tmp_path, c.CASE_A)
    assert case_run.result.status == "failed"
    assert case_run.result.accounting is None
    assert any(e.code == "INDETERMINATE_EXECUTION" for e in case_run.result.errors)


def test_decision_index_must_match_the_live_slot(tmp_path):
    runner, sim = fresh_runner(tmp_path, c.CASE_A)
    with pytest.raises(ValueError, match="stale/different slot"):
        runner.decide(3)
    assert len(sim.history) == 0
    for bad in (-1, 30, True, 1.0):
        with pytest.raises(ValueError):
            runner.decide(bad)


# --------------------------------------------------------------------------- policy parity
@pytest.mark.parametrize("policy", ["rules-v1", "greedy_a", "greedy_b"])
def test_all_policies_use_the_same_gate_and_record_the_outer_policy(tmp_path, policy):
    case_run, _, _ = run(tmp_path, c.CASE_A, policy)
    assert case_run.result.policy_id == policy
    assert all(o.record.policy_id == policy for o in case_run.outcomes)
    assert all(o.record.model_call_count == 0 for o in case_run.outcomes)
    for outcome in case_run.outcomes:
        for stage in outcome.record.proposal_stages:
            assert stage.check_result is not None  # every stage is checked by production code


def test_greedy_b_fallback_is_labelled_as_greedy_a_origin(tmp_path):
    case = replace(c.CASE_A, forecast_present=False, case_id="NOFC")
    case_run, _, _ = run(tmp_path, case, "greedy_b")
    stage = case_run.outcomes[0].record.proposal_stages[0]
    assert stage.origin == "greedy_a_fallback"
    assert case_run.outcomes[0].record.policy_id == "greedy_b"


def test_fault_injection_is_rules_v1_only(tmp_path):
    with pytest.raises(ValueError, match="rules-v1 demonstration"):
        fresh_runner(tmp_path, c.CASE_A, "greedy_a", fault_injection=_incomplete_plan)


# --------------------------------------------------------------------------- persisted evidence
def test_persisted_files_hash_to_their_recorded_digests(tmp_path):
    case_run, _, _ = run(tmp_path, c.CASE_A)
    root = case_run.root
    for outcome in case_run.outcomes:
        record = outcome.record
        state = root / "states" / f"{record.state_before.visible_state_sha256}.json"
        snap = root / "snapshots" / f"{record.state_before.constraint_snapshot_sha256}.json"
        for path, digest in (
            (state, record.state_before.visible_state_sha256),
            (snap, record.state_before.constraint_snapshot_sha256),
        ):
            data = path.read_bytes()
            assert hashlib.sha256(data).hexdigest() == digest
            assert data.endswith(b"\n") and not data.endswith(b"\n\n")
        transition = record.execution
        data = (root / transition.transition_ref).read_bytes()
        assert hashlib.sha256(data).hexdigest() == transition.transition_sha256
        # decision file bytes hash to the digest bound by the result
        assert hashlib.sha256((root / outcome.decision_ref).read_bytes()).hexdigest() == (
            outcome.decision_sha256
        )
    result_bytes = (root / case_run.result_ref).read_bytes()
    assert hashlib.sha256(result_bytes).hexdigest() == case_run.result_sha256
    assert list(case_run.result.decision_sha256s) == [o.decision_sha256 for o in case_run.outcomes]
    assert "model_call_count" not in json.loads(result_bytes)


def test_state_after_hash_is_the_next_states_visible_hash(tmp_path):
    case_run, _, _ = run(tmp_path, c.CASE_A)
    records = [o.record for o in case_run.outcomes]
    for before, after in zip(records, records[1:]):
        assert before.execution.state_after.state_sha256 == after.state_before.visible_state_sha256
        assert before.execution.state_after.slot == after.state_before.slot


def test_trace_folder_has_the_reader_layout_and_a_hash_bound_case_file(tmp_path):
    case_run, _, _ = run(tmp_path, c.CASE_A)
    root = case_run.root
    assert root.name == "A-rules-v1" and root.parent.name == "rules-v1"
    assert (root / "case.json").is_file() and (root / "result.json").is_file()
    assert len(list((root / "decisions").glob("decision-*.json"))) == 30
    raw = (root / "case.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == case_run.result.bindings.case_sha256
    assert json.loads(raw) == c.CASE_A.case_json()


# --------------------------------------------------------------------------- bindings
def test_bindings_bind_actual_artifacts_exactly_as_the_reader_expects():
    from dc_sustainability.evaluation import rule_study_generator as gen
    from dc_sustainability.evaluation import rule_study_verifier as v

    root = REPO_ROOT
    bindings = bindings_for(c.CASE_A)
    spec = json.loads((root / "docs/rule_study/specification.json").read_text(encoding="utf-8"))
    assert bindings.spec_sha256 == v.canonical_sha256(spec)
    assert bindings.spec_sha256 == (
        "9597931fcee09bc895605b65401483c9c3658da9e0bdf7c954f8669dfa8542bd"
    )
    assert bindings.generator_source_sha256 == gen.source_sha256()
    lock = (root / "requirements/requirements-windows-py312.lock.txt").read_bytes()
    assert (
        bindings.environment_lock_sha256 == hashlib.sha256(lock.replace(b"\r\n", b"\n")).hexdigest()
    )
    assert bindings.case_sha256 == v.canonical_sha256(c.CASE_A.case_json())
    package = {
        p.name: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for p in sorted((root / "dc_sustainability/rule_study").glob("*.py"))
    }
    assert bindings.adapter_source_sha256 == v.canonical_sha256(package)
    assert all(value is not None for value in bindings.model_dump().values())


def test_make_bindings_refuses_a_dirty_or_unbindable_tree(tmp_path):
    with pytest.raises(rn.BindingError):
        rn.make_bindings(c.CASE_A, tmp_path)  # none of the required artifacts exist there


def test_make_bindings_refuses_a_dirty_checkout_instead_of_binding_a_base_commit(tmp_path):
    import shutil
    import subprocess

    for rel in (
        "docs/rule_study/specification.json",
        "dc_sustainability/evaluation/rule_study_generator.py",
        "requirements/requirements-windows-py312.lock.txt",
    ):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / rel, tmp_path / rel)
    (tmp_path / "dc_sustainability/rule_study").mkdir(parents=True, exist_ok=True)
    shutil.copy(
        REPO_ROOT / "dc_sustainability/rule_study/records.py",
        tmp_path / "dc_sustainability/rule_study/records.py",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    with pytest.raises(rn.BindingError, match="clean committed checkout"):
        rn.make_bindings(c.CASE_A, tmp_path)  # untracked files: dirty
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
        cwd=tmp_path,
        check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert rn.make_bindings(c.CASE_A, tmp_path).code_commit == head
