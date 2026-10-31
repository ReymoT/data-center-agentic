"""E02-b: the Plain and Agent systems inside the runner, from explicit model inputs.

Nothing here builds a provider, deployment or prompt renderer; the caller supplies
them after A01 acceptance and a run authorization. Each unit (system × episode ×
trial) gets a fresh provider ledger and, for the agent, a fresh harness: both bound
their per-decision caps by episode and slot, not by trial, so one ledger per unit is
what keeps trial 1 from being blocked by trial 0.

Every attempt is persisted before the decision executes. A sent request whose outcome
is uncertain is ``unknown``, and a sent request whose artifact could not be saved is
``unsaved``. Either stops the unit for reconciliation (``unknown.json``), and no
further model unit starts until it is reconciled. Nothing is retried. A run-wide
attempt budget counts every spent attempt in the run directory, saved artifacts and
the unsaved ones listed in ``unknown.json``, so neither a restart nor a lost artifact
gives back budget.
"""

import dataclasses
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dc_sustainability import schemas as s
from dc_sustainability.agent import AgentHarness
from dc_sustainability.experiments.config import ModelSettings
from dc_sustainability.llm.plain import PlainLLMPolicy, prompt_template_sha256
from dc_sustainability.llm.provider import Attempt, OllamaProvider
from dc_sustainability.policies import propose
from dc_sustainability.runtime import ExecutionController, ExecutionOutcome
from dc_sustainability.verification.checker import check_schedule

CALL_CAP = {"plain_llm": 1, "agent": 3}  # per decision, as enforced by A01 and A04


class UncertainRequest(Exception):
    """A sent model request is unknown or unsaved; the unit needs reconciliation."""

    def __init__(self, message: str, attempts=(), unsaved=()):
        super().__init__(message)
        self.attempts = tuple(attempts)  # this decision's spent attempts
        self.unsaved = frozenset(unsaved)  # trace IDs with no saved artifact


@dataclass(frozen=True)
class AgentRenderers:
    """Reviewed agent prompt renderers (A02 callables); a missing stage stays missing."""

    proposal: Callable
    repair: Callable | None = None
    explanation: Callable | None = None


@dataclass(frozen=True)
class ModelInputs:
    """Live objects for the model systems. ``provider_factory`` returns a new ledger."""

    provider_factory: Callable[[], OllamaProvider]
    agent_renderers: AgentRenderers | None = None


def deployment_pins(deployment) -> dict:
    """The A01 deployment fields that belong in the run identity (not the address)."""
    pins = dataclasses.asdict(deployment)
    pins.pop("base_url")
    return pins


def check_inputs(settings: ModelSettings, models: ModelInputs, systems) -> None:
    """Refuse model inputs that do not match the frozen settings, before any unit runs."""
    if "plain_llm" in systems and settings.plain_prompt_sha256 != prompt_template_sha256():
        raise ValueError("plain prompt files differ from the hash frozen in the run config")
    if "agent" in systems and models.agent_renderers is None:
        raise ValueError("an agent run needs its reviewed renderers")
    new_provider(settings, models)  # constructing a ledger sends nothing


def new_provider(settings: ModelSettings, models: ModelInputs) -> OllamaProvider:
    provider = models.provider_factory()
    if not isinstance(provider, OllamaProvider):
        raise TypeError("the shared A01 OllamaProvider is required")
    if provider.attempts:
        raise ValueError("each unit needs a fresh provider ledger")
    if deployment_pins(provider.deployment) != settings.deployment:
        raise ValueError("provider deployment differs from the pins frozen in the run config")
    return provider


def spent_attempts(root: Path) -> int:
    """Attempts spent anywhere in this run: saved artifacts plus unsaved ones on record."""
    saved = sum(1 for _ in Path(root).glob("units/*/traces/provider-attempts/*.json"))
    unsaved = 0
    for path in Path(root).glob("units/*/unknown.json"):
        attempts = json.loads(path.read_text(encoding="utf-8"))["attempts"]
        unsaved += sum(1 for a in attempts if not a["saved"])
    return saved + unsaved


def worst_case_attempts(system: str, settings: ModelSettings) -> int:
    """The most attempts one unit can spend: its call caps, or its ledger cap if lower.

    ``check_inputs`` makes every provider's pins equal ``settings.deployment``, so the
    unit's fresh ledger refuses dispatch past ``max_run_attempts``.
    """
    per_slot = s.PROPOSED_DECISION_SLOTS * CALL_CAP[system]
    return min(per_slot, settings.deployment["max_run_attempts"])


def outcome(attempt: Attempt) -> str:
    if attempt.uncertain_outcome:
        return "unknown"
    return "failed" if attempt.error is not None else "ok"


def attempt_summary(attempts, unsaved=frozenset()) -> list[dict]:
    return [
        {
            "slot": a.slot,
            "client_trace_id": a.client_trace_id,
            "outcome": outcome(a),
            "saved": a.client_trace_id not in unsaved,
            "error": a.error,
        }
        for a in attempts
    ]


def raise_if_unreconciled(slot: int, attempts, attempt_dir: Path) -> None:
    """Stop the unit if a spent attempt is unknown or has no saved artifact."""
    unknown = [a.client_trace_id for a in attempts if a.uncertain_outcome]
    unsaved = [
        a.client_trace_id
        for a in attempts
        if not (Path(attempt_dir) / f"{a.client_trace_id}.json").exists()
    ]
    problems = []
    if unknown:
        problems.append(f"sent request(s) {', '.join(unknown)} have an unknown outcome")
    if unsaved:
        problems.append(f"sent request(s) {', '.join(unsaved)} could not be saved")
    if problems:
        raise UncertainRequest(
            f"slot {slot}: {'; '.join(problems)}; reconcile before continuing, never retry",
            attempts,
            unsaved,
        )


def plain_step(
    controller: ExecutionController,
    policy: PlainLLMPolicy,
    provider: OllamaProvider,
    view: s.VisibleState,
    snapshot: s.ConstraintSnapshot,
    context: s.Context,
    *,
    decision_id: str,
    run_id: str,
    trial: int,
    seed: int,
    decision_deadline: float,
) -> tuple[ExecutionOutcome, tuple[Attempt, ...]]:
    """One plain decision: its single request, saved, checked once, then the gate.

    The plain system has no repair or fallback. Its output is checked as the initial
    stage and the controller decides; anything else is a recorded blocked decision.
    """
    before = len(provider.attempts)
    errors: list[str] = []
    decision = None
    try:
        decision = policy.propose(view, context, seed=seed, decision_deadline=decision_deadline)
    except Exception as exc:
        errors.append(f"plain policy error: {type(exc).__name__}: {exc}")
    attempts = provider.attempts[before:]
    for i, attempt in enumerate(attempts):  # persisted before anything executes
        try:
            controller.record_attempt(
                attempt, decision_id=decision_id, run_id=run_id, stage="propose"
            )
        except Exception as exc:  # nothing executes; the unit stops for reconciliation
            raise UncertainRequest(
                f"slot {view.current_slot}: sent request {attempt.client_trace_id} could not "
                f"be saved ({type(exc).__name__}: {exc}); reconcile before continuing, "
                "never retry",
                attempts,
                {a.client_trace_id for a in attempts[i:]},
            ) from exc

    output = decision.output if decision is not None else None
    if decision is not None and decision.blocked_reason:
        errors.append(f"propose pre-dispatch blocked: {decision.blocked_reason}")
    for attempt in attempts:
        if attempt.error is not None:
            errors.append(f"propose response failed: {attempt.error}")
    if output is not None and output.output_status != "ok":
        errors.append(f"policy output status: {output.output_status}")

    initial = None
    if output is not None and output.output_status == "ok" and output.plan is not None:
        try:
            initial = s.StageRecord(
                plan=output.plan, check=check_schedule(output.plan, view, snapshot)
            )
        except Exception as exc:
            errors.append(f"initial checker error: {exc}")

    def total(name):
        values = [getattr(a, name) for a in attempts]
        return sum(values) if values and all(v is not None for v in values) else None

    record = s.DecisionRecord(
        decision_id=decision_id,
        run_id=run_id,
        trial=trial,
        system="plain_llm",
        episode_id=view.episode_id,
        slot=view.current_slot,
        input_hash=decision.context_hash if decision is not None else None,
        raw_response=output.raw_response if output is not None else None,
        initial=initial,
        not_applicable_stages=("repaired", "fallback"),
        final_status="blocked",
        explanation=output.explanation if output is not None else None,
        model_call_count=len(attempts),
        latency_ms=total("latency_ms"),
        prompt_tokens=total("prompt_tokens"),
        completion_tokens=total("completion_tokens"),
        errors=tuple(errors),
    )
    execution = controller.execute_step(
        record,
        stage="initial" if initial is not None else None,
        expected_state_version=view.state_version,
    )
    return execution, attempts


def new_harness(
    provider: OllamaProvider, controller: ExecutionController, renderers: AgentRenderers
) -> AgentHarness:
    """A02 harness with the real Greedy A as its checked fallback."""

    def fallback(view, context):
        return propose(view, context, system="greedy_a")

    return AgentHarness(
        provider,
        controller,
        proposal_messages=renderers.proposal,
        repair_messages=renderers.repair,
        explanation_messages=renderers.explanation,
        fallback=fallback,
    )


def agent_step(
    harness: AgentHarness,
    view: s.VisibleState,
    snapshot: s.ConstraintSnapshot,
    *,
    decision_id: str,
    run_id: str,
    trial: int,
    seed: int,
    decision_deadline: float,
) -> tuple[ExecutionOutcome, tuple[Attempt, ...]]:
    """One agent decision; the harness saves its attempts and calls the controller."""
    result = harness.run_decision(
        view,
        snapshot,
        decision_id=decision_id,
        run_id=run_id,
        trial=trial,
        seed=seed,
        decision_deadline=decision_deadline,
    )
    return result.execution, result.attempts


def deadline(settings: ModelSettings) -> float:
    return time.monotonic() + settings.decision_seconds
