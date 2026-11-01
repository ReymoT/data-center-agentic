"""L01 plain-LLM comparison: one shared-adapter call per decision, never corrected.

For a nonempty waiting queue the plain system sees the same flat F02 context as the
agent and makes one request through Matty's OllamaProvider, which fixes model and
generation settings for both systems. An empty queue returns a no-call proposal.
The original model response is kept for scoring. There are no tools, checker
feedback, repair, retry or greedy-A fallback here; the runtime gate decides what may
execute, and blocked or failed decisions still advance the simulator.

The flat presentation is the F02 ``ContextContent`` JSON from K02 ``retrieve``
(representation "flat"). The prompt files are frozen by ``prompt_template_sha256``;
A01's bounded validation on October 30, 2026 sent one real request through
``propose`` with prompt hash ``ff550134...`` (``docs/handoffs/A01_BOUNDED_PAIRED_
VALIDATION_2026-10-30.md``). That validates the shared provider path only: no Plain
development episode or study run has been made.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from string import Template

from dc_sustainability import schemas as s
from dc_sustainability.llm.provider import Attempt, CallBlocked, OllamaProvider

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"
PROMPT_FILES = (
    "shared/task_rules.md",
    "shared/explanation_rules.md",
    "plain_llm/system.md",
    "plain_llm/user.md",
)


def _read_prompt(name: str) -> str:
    # Normalize line endings so Git checkout settings cannot change prompt hashes.
    return (PROMPT_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n").strip()


def prompt_template_sha256() -> str:
    """Hash of every prompt file the plain system uses, for the freeze manifest."""
    digest = hashlib.sha256()
    for name in PROMPT_FILES:
        digest.update(name.encode("utf-8") + b"\0" + _read_prompt(name).encode("utf-8") + b"\0")
    return digest.hexdigest()


def _check_context(state: s.VisibleState, context: s.Context) -> None:
    """Refuse a context that is not the flat view of exactly this visible state."""
    if context.representation != "flat":
        raise ValueError("the plain LLM receives the flat context representation")
    c = context.content
    expected = (
        state.episode_id,
        state.current_slot,
        state.state_version,
        state.constraint_snapshot_id,
        state.site,
        set(state.waiting_jobs),
        set(state.running_jobs),
        set(state.completed_jobs),
        set(state.missed_job_ids),
        set(state.carbon_facts),
        set(state.missing_carbon_slots),
        set(state.constraint_ids),
    )
    actual = (
        c.episode_id,
        c.current_slot,
        c.state_version,
        c.snapshot_id,
        c.site,
        set(c.waiting_jobs),
        set(c.running_jobs),
        set(c.completed_jobs),
        set(c.missed_job_ids),
        set(c.carbon_facts),
        set(c.missing_carbon_slots),
        {constraint.constraint_id for constraint in c.constraints},
    )
    if expected != actual:
        raise ValueError("context does not match the requesting visible state")


def render_messages(context: s.Context) -> list[dict[str, str]]:
    """Render the system and user messages for one plain decision."""
    system = Template(_read_prompt("plain_llm/system.md")).substitute(
        task_rules=_read_prompt("shared/task_rules.md"),
        explanation_rules=_read_prompt("shared/explanation_rules.md"),
    )
    user = Template(_read_prompt("plain_llm/user.md")).substitute(
        schema_version=s.SCHEMA_VERSION,
        episode_id=context.content.episode_id,
        slot=context.content.current_slot,
        state_version=context.content.state_version,
        context_json=context.content.to_json(),
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def messages_sha256(messages: Sequence[dict[str, str]]) -> str:
    return s.sha256_hex([dict(m) for m in messages])


def _response_text(attempt: Attempt) -> str | None:
    """The model's message content when present, else the raw body; never rewritten."""
    if not attempt.raw_response:
        return None
    try:
        content = json.loads(attempt.raw_response)["message"]["content"]
    except (ValueError, TypeError, KeyError):
        content = None
    if isinstance(content, str):
        return content or None
    return attempt.raw_response.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class PlainDecision:
    """One plain decision: scored output plus the evidence needed to trace it.

    ``attempt`` is None when the adapter blocked before dispatch, with the reason in
    ``blocked_reason``, or when the waiting queue was empty and no request was made
    (``empty_queue_noop``). A schema-valid ``output`` is still only a proposal.
    """

    output: s.PolicyOutput
    attempt: Attempt | None
    blocked_reason: str | None
    messages_sha256: str
    prompt_template_sha256: str
    context_hash: str
    empty_queue_noop: bool = False


class PlainLLMPolicy:
    """Plain-LLM comparator. Use one instance per run, with that run's shared provider."""

    system = "plain_llm"

    def __init__(self, provider: OllamaProvider):
        self._provider = provider
        self._requested: set[tuple[str, int]] = set()

    def propose(
        self,
        state: s.VisibleState,
        context: s.Context,
        *,
        seed: int,
        decision_deadline: float,
    ) -> PlainDecision:
        """Make the single allowed request for this decision and keep what came back.

        Calling twice for the same episode/slot raises, even if the first call was
        blocked before dispatch: the plain system never gets a second chance. With no
        waiting jobs, no request is made and a deterministic no-op is recorded (Q03.4).
        """
        if state.current_slot >= s.PROPOSED_DECISION_SLOTS:
            raise CallBlocked("no model calls in completion slots")
        key = (state.episode_id, state.current_slot)
        if key in self._requested:
            raise CallBlocked("the plain LLM already used its one request for this decision")
        # F02 model_copy/model_construct can bypass validation, including the content
        # hash and unique-job checks. Revalidate before rendering or spending an attempt.
        state = s.VisibleState.model_validate(
            state.model_dump(mode="python", warnings="none"), strict=True
        )
        context = s.Context.model_validate(
            context.model_dump(mode="python", warnings="none"), strict=True
        )
        _check_context(state, context)
        messages = render_messages(context)
        self._requested.add(key)
        evidence = dict(
            messages_sha256=messages_sha256(messages),
            prompt_template_sha256=prompt_template_sha256(),
            context_hash=context.content_hash,
        )
        if not state.waiting_jobs:
            # Q03.4: an empty queue has one valid output, so neither LLM system calls the
            # model. The no-op has no explanation; its claim review is not applicable (Q10).
            noop = s.Plan(
                episode_id=state.episode_id,
                slot=state.current_slot,
                state_version=state.state_version,
                status="proposed",
            )
            output = s.PolicyOutput(system="plain_llm", output_status="ok", plan=noop)
            return PlainDecision(output, None, None, **evidence, empty_queue_noop=True)
        try:
            attempt = self._provider.generate(
                system="plain_llm",
                state=state,
                seed=seed,
                messages=messages,
                response_model=s.PolicyOutput,
                decision_deadline=decision_deadline,
            )
        except CallBlocked as exc:
            output = s.PolicyOutput(system="plain_llm", output_status="error")
            return PlainDecision(output, None, str(exc), **evidence)

        text = _response_text(attempt)
        if attempt.output is not None and attempt.error is None:
            # Keep the model's own fields; only attach the original text it was parsed from.
            output = attempt.output.model_copy(update={"raw_response": text})
        elif attempt.uncertain_outcome:
            output = s.PolicyOutput(system="plain_llm", output_status="error", raw_response=text)
        elif text is None:
            output = s.PolicyOutput(system="plain_llm", output_status="no_output")
        else:
            output = s.PolicyOutput(
                system="plain_llm", output_status="malformed", raw_response=text
            )
        return PlainDecision(output, attempt, None, **evidence)
