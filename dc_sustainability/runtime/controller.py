"""Controller-only S01 execution with real A03 rechecks and durable F02 evidence.

One controller is the sole simulator mutator. Its lock serializes its own calls;
it does not claim protection against unrelated code directly mutating S01.
"""

import threading
from dataclasses import dataclass

from dc_sustainability import schemas as s
from dc_sustainability.runtime.traces import IndeterminateExecution, TraceStore
from dc_sustainability.verification.checker import recheck_schedule


@dataclass(frozen=True)
class ExecutionOutcome:
    record: s.DecisionRecord
    transition: object | None
    replayed: bool = False


class ExecutionController:
    def __init__(self, simulator, snapshot_reader, trace_store: TraceStore):
        self._simulator = simulator
        self._snapshot_reader = snapshot_reader
        self._traces = trace_store
        self._lock = threading.Lock()

    def execute_step(self, record, *, stage, expected_state_version):
        """Consume a nonexecuted F02 decision intention, not an execution capability.

        Stage is initial/repaired/fallback or None when no candidate is available.
        Persisted replay returns its actual trace without another simulator step.
        A reserved but unfinished effect requires reconciliation, not retry.
        """
        if not isinstance(record, s.DecisionRecord):
            raise TypeError("controller requires DecisionRecord, never direct ApprovedActions")
        record = s.DecisionRecord.model_validate(record.model_dump(mode="python"), strict=True)
        if stage not in {None, "initial", "repaired", "fallback"}:
            raise ValueError("unknown selected stage")
        if type(expected_state_version) is not int or expected_state_version < 0:
            raise ValueError("expected state version must be a nonnegative strict integer")
        if record.final_status == "executed" or record.executed_starts or record.execution_check:
            raise ValueError("supply an unexecuted intention, not a completed trace")
        with self._lock:
            # Reservation/replay happens before reading a now-advanced live slot.
            replay = self._traces.replay(record, stage, expected_state_version)
            if replay is not None:
                return ExecutionOutcome(replay, None, True)
            state = self._simulator.state()
            if (state.episode_id, state.current_slot) != (record.episode_id, record.slot):
                raise ValueError("stale/different episode or slot; no additional advancement")
            if state.current_slot >= 30:
                raise ValueError("episode is complete")
            replay = self._traces.reserve(record, stage, expected_state_version)
            if replay is not None:
                return ExecutionOutcome(replay, None, True)
            errors = list(record.errors)
            gate_errors = []
            check, approved = None, None
            selected = getattr(record, stage) if stage else None
            cap = 3 if record.system == "agent" else 1 if record.system == "plain_llm" else 0
            if record.model_call_count > cap or record.repair_count > (
                1 if record.system == "agent" else 0
            ):
                gate_errors.append("decision call/repair cap exceeded")
            if state.current_slot >= 24 and (record.model_call_count or record.repair_count):
                gate_errors.append("completion slots cannot spend model calls or repairs")
            if state.state_version != expected_state_version:
                gate_errors.append("latest state version differs from the expected version")
            if record.system == "plain_llm" and (
                record.repaired is not None or record.fallback is not None
            ):
                gate_errors.append("plain LLM cannot use repair or fallback stages")
            if selected is None or selected.check is None or selected.check.status != "pass":
                gate_errors.append("no selected actually passing proposal check")
            if not gate_errors:
                try:
                    snapshot = self._snapshot_reader()
                    check = recheck_schedule(selected.plan, state, snapshot)
                    latest = self._simulator.state()
                    if latest != state or self._snapshot_reader() != snapshot:
                        gate_errors.append("state or constraints changed during recheck")
                    elif check.status == "pass":
                        approved = s.ApprovedActions.from_checked_plan(
                            selected.plan, check, latest.state_version
                        )
                    else:
                        gate_errors.append("latest physical recheck refused execution")
                except Exception as exc:
                    gate_errors.append(f"execution recheck error: {exc}")
            errors.extend(gate_errors)
            try:
                # None invokes S01's actual refusal-and-drain path: no forged noop approval.
                transition = self._simulator.step(approved)
                if transition.rejection:
                    errors.append(f"simulator refusal: {transition.rejection}")
                executed = tuple(
                    s.ApprovedStart(job_id=j, start_slot=state.current_slot)
                    for j in transition.slot.started_job_ids
                )
                if approved is None and executed:
                    raise RuntimeError("simulator executed starts without controller approval")
                if (
                    approved is not None
                    and not transition.rejection
                    and set(executed) != set(approved.starts)
                ):
                    raise RuntimeError("executed starts differ from approved current starts")
                status = (
                    "executed" if approved is not None and not transition.rejection else "blocked"
                )
                if (
                    status == "executed"
                    and selected.plan.abstentions
                    and not selected.plan.starts
                    and not selected.plan.deferrals
                ):
                    status = "abstained"
                final = s.DecisionRecord.model_validate(
                    {
                        **record.model_dump(mode="python"),
                        "execution_check": check,
                        "final_status": status,
                        "executed_starts": executed,
                        "errors": tuple(errors),
                    },
                    strict=True,
                )
                self._traces.write(final)
            except Exception as exc:
                raise IndeterminateExecution(
                    "effect or trace completion failed; do not retry automatically"
                ) from exc
            return ExecutionOutcome(final, transition)
