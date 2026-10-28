"""Receive deterministic policy output through the production execution gate.

This is a single-decision boundary for the future E02 runner.  It does not
choose an episode, policy, clock, retry, or experiment configuration.
"""

from dc_sustainability import schemas as s
from dc_sustainability.verification.checker import check_schedule

from .controller import ExecutionController, ExecutionOutcome


def execute_policy_output(
    controller: ExecutionController,
    output: s.PolicyOutput,
    view: s.VisibleState,
    snapshot: s.ConstraintSnapshot,
    *,
    requested_system: s.SystemId,
    decision_id: str,
    run_id: str,
    trial: int | None = None,
) -> ExecutionOutcome:
    """Check and execute one already-produced deterministic policy output.

    ``requested_system`` remains the comparison-system identity.  The only
    different effective output currently allowed is Greedy A as Greedy B's
    explicit checked fallback.  Unsuccessful policy output is still recorded
    and advances the simulator once through the controller's refusal path.
    """
    if not isinstance(controller, ExecutionController):
        raise TypeError("the production execution controller is required")
    output = s.PolicyOutput.model_validate(output.model_dump(mode="python"), strict=True)
    view = s.VisibleState.model_validate(view.model_dump(mode="python"), strict=True)
    snapshot = s.ConstraintSnapshot.model_validate(snapshot.model_dump(mode="python"), strict=True)
    if requested_system in {"agent", "plain_llm"}:
        raise ValueError("model systems require their own bounded policy adapters")
    if output.system != requested_system and not (
        requested_system == "greedy_b" and output.system == "greedy_a"
    ):
        raise ValueError("effective policy output does not match the requested system")

    stage = None
    initial = None
    fallback = None
    errors: tuple[str, ...] = ()
    if output.output_status == "ok":
        check = check_schedule(output.plan, view, snapshot)
        selected = s.StageRecord(plan=output.plan, check=check)
        if requested_system == "greedy_b" and output.system == "greedy_a":
            stage, fallback = "fallback", selected
        else:
            stage, initial = "initial", selected
    else:
        errors = (f"policy output status: {output.output_status}",)

    record = s.DecisionRecord(
        decision_id=decision_id,
        run_id=run_id,
        trial=trial,
        system=requested_system,
        episode_id=view.episode_id,
        slot=view.current_slot,
        raw_response=output.raw_response,
        initial=initial,
        fallback=fallback,
        not_applicable_stages=("initial", "repaired")
        if stage == "fallback"
        else ("repaired", "fallback"),
        final_status="blocked",
        explanation=output.explanation,
        errors=errors,
    )
    return controller.execute_step(record, stage=stage, expected_state_version=view.state_version)
