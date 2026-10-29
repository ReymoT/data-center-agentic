"""Bounded A02 orchestration on actual K02/A01/A03/A04 components.

Reviewed prompt renderers and real P02 are explicit inputs, never substitutes.
This implements one development decision, not experiment resume or live readiness.
"""

import math
import threading
import time
from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context

from dc_sustainability import schemas as s
from dc_sustainability.knowledge import retrieve
from dc_sustainability.llm.provider import Attempt, CallBlocked, OllamaProvider
from dc_sustainability.runtime import ExecutionController, ExecutionOutcome
from dc_sustainability.verification.checker import check_schedule


class _State(TypedDict):
    decision_id: str
    run_id: str
    view: s.VisibleState
    snapshot: s.ConstraintSnapshot
    context: s.Context | None
    seed: int
    deadline: float
    initial: s.StageRecord | None
    repaired: s.StageRecord | None
    fallback: s.StageRecord | None
    selected: str | None
    attempts: list[Attempt]
    errors: list[str]
    route: list[str]
    explanation: s.Explanation | None
    repair_count: int
    predispatch_blocked: bool
    fatal: bool


@dataclass(frozen=True)
class AgentDecision:
    execution: ExecutionOutcome
    attempts: tuple[Attempt, ...]
    context_hash: str | None
    route: tuple[str, ...]
    elapsed_ms: float


class AgentHarness:
    def __init__(
        self,
        provider: OllamaProvider,
        controller: ExecutionController,
        *,
        proposal_messages=None,
        repair_messages=None,
        explanation_messages=None,
        fallback=None,
    ):
        if not isinstance(provider, OllamaProvider) or not isinstance(
            controller, ExecutionController
        ):
            raise TypeError("actual shared provider and execution controller are required")
        if any(
            value is not None and not callable(value)
            for value in (proposal_messages, repair_messages, explanation_messages, fallback)
        ):
            raise TypeError("renderers and fallback must be explicit callables or unavailable")
        self._provider = provider
        self._controller = controller
        self._proposal_messages = proposal_messages
        self._repair_messages = repair_messages
        self._explanation_messages = explanation_messages
        self._fallback = fallback
        self._lock = threading.Lock()
        self._requested = set()
        self._run_identity = None
        graph = StateGraph(_State)
        for name, node in (
            ("retrieve", self._retrieve),
            ("propose", self._propose),
            ("verify_initial", lambda st: self._verify(st, "initial")),
            ("repair", self._repair),
            ("verify_repaired", lambda st: self._verify(st, "repaired")),
            ("fallback", self._fallback_node),
            ("verify_fallback", lambda st: self._verify(st, "fallback")),
            ("explain", self._explain),
        ):
            graph.add_node(name, node)
        graph.add_edge(START, "retrieve")
        graph.add_edge("retrieve", "propose")
        graph.add_edge("propose", "verify_initial")
        graph.add_conditional_edges(
            "verify_initial",
            self._after_initial,
            {"explain": "explain", "repair": "repair", "fallback": "fallback"},
        )
        graph.add_edge("repair", "verify_repaired")
        graph.add_conditional_edges(
            "verify_repaired",
            lambda st: "explain" if st["selected"] else "fallback",
            {"explain": "explain", "fallback": "fallback"},
        )
        graph.add_edge("fallback", "verify_fallback")
        graph.add_edge("verify_fallback", "explain")
        graph.add_edge("explain", END)
        self._graph = graph.compile()

    @staticmethod
    def _update(st, name, **fields):
        return {"route": [*st["route"], name], **fields}

    @staticmethod
    def _time_left(st):
        return time.monotonic() < st["deadline"]

    def _retrieve(self, st):
        try:
            context = retrieve(st["view"], st["snapshot"], representation="graph").context
            return self._update(st, "retrieve", context=context)
        except Exception as exc:
            return self._update(
                st, "retrieve", fatal=True, errors=[*st["errors"], f"retrieval failed: {exc}"]
            )

    def _call(self, st, stage, renderer, args, response_model):
        errors = list(st["errors"])
        if st["fatal"] or st["context"] is None or renderer is None or not self._time_left(st):
            errors.append(f"{stage} unavailable: context, renderer, persistence or deadline")
            return self._update(st, stage, errors=errors, predispatch_blocked=True)
        if len(st["attempts"]) >= 3:
            return self._update(st, stage, errors=[*errors, "three-call decision cap exhausted"])
        before = {a.client_trace_id for a in self._provider.attempts}
        result = None
        blocked = False
        try:
            messages = renderer(*args)
            result = self._provider.generate(
                system="agent",
                state=st["view"],
                seed=st["seed"],
                messages=messages,
                response_model=response_model,
                decision_deadline=st["deadline"],
            )
        except CallBlocked as exc:
            errors.append(f"{stage} pre-dispatch blocked: {exc}")
            blocked = True
        except Exception as exc:
            errors.append(f"{stage} error: {exc}")
            blocked = True
        new = [
            a
            for a in self._provider.attempts
            if a.client_trace_id not in before
            and (a.system, a.episode_id, a.slot)
            == ("agent", st["view"].episode_id, st["view"].current_slot)
        ]
        fatal = st["fatal"]
        for attempt in new:
            try:
                self._controller.record_attempt(
                    attempt, decision_id=st["decision_id"], run_id=st["run_id"], stage=stage
                )
            except Exception as exc:
                fatal = True
                errors.append(f"attempt persistence failed: {exc}")
        # A sent request may still be running: no further dispatch or model-derived plan.
        uncertain = [a.client_trace_id for a in new if a.uncertain_outcome]
        if uncertain:
            fatal = True
            errors.append(f"{stage} outcome unknown for {', '.join(uncertain)}; fail closed")
        fields = {
            "attempts": [*st["attempts"], *new],
            "errors": errors,
            "predispatch_blocked": blocked,
            "fatal": fatal,
        }
        if stage == "repair":
            fields["repair_count"] = int(bool(new))
        if result is not None and result.error is not None:
            errors.append(f"{stage} response failed: {result.error}")
        if (
            result is not None
            and result.error is None
            and not uncertain
            and isinstance(result.output, response_model)
        ):
            if response_model is s.Explanation:
                fields["explanation"] = result.output
            else:
                fields["repaired" if stage == "repair" else "initial"] = s.StageRecord(
                    plan=result.output
                )
        return self._update(st, stage, **fields)

    def _propose(self, st):
        if not st["view"].waiting_jobs or st["view"].current_slot >= 24:
            view = st["view"]
            plan = s.Plan(
                episode_id=view.episode_id,
                slot=view.current_slot,
                state_version=view.state_version,
                status="proposed",
            )
            return self._update(st, "no_call", initial=s.StageRecord(plan=plan))
        return self._call(st, "propose", self._proposal_messages, (st["context"],), s.Plan)

    def _verify(self, st, stage):
        candidate = st[stage]
        if candidate is None:
            return self._update(st, "verify_" + stage, selected=None)
        try:
            check = check_schedule(candidate.plan, st["view"], st["snapshot"])
            return self._update(
                st,
                "verify_" + stage,
                **{
                    stage: s.StageRecord(plan=candidate.plan, check=check),
                    "selected": stage if check.status == "pass" else None,
                },
            )
        except Exception as exc:
            return self._update(
                st,
                "verify_" + stage,
                selected=None,
                errors=[*st["errors"], f"{stage} checker error: {exc}"],
            )

    def _after_initial(self, st):
        if st["selected"]:
            return "explain"
        if (
            st["view"].current_slot < 24
            and st["view"].waiting_jobs
            and not st["fatal"]
            and not st["predispatch_blocked"]
            and self._repair_messages is not None
            and self._time_left(st)
        ):
            return "repair"
        return "fallback"

    def _repair(self, st):
        return self._call(
            st,
            "repair",
            self._repair_messages,
            (st["context"], st["initial"], tuple(st["errors"])),
            s.Plan,
        )

    def _fallback_node(self, st):
        errors = list(st["errors"])
        if (
            st["fatal"]
            or st["context"] is None
            or not self._time_left(st)
            or self._fallback is None
            or st["view"].current_slot >= 24
        ):
            return self._update(
                st,
                "fallback_unavailable",
                errors=[*errors, "real P02 fallback unavailable or decision deadline exhausted"],
                selected=None,
            )
        try:
            output = self._fallback(st["view"], st["context"])
            output = s.PolicyOutput.model_validate(output.model_dump(mode="python"), strict=True)
            if (
                output.system != "greedy_a"
                or output.output_status != "ok"
                or output.plan is None
                or output.plan.status != "proposed"
            ):
                raise ValueError("fallback must provide actual greedy_a PolicyOutput with a plan")
            return self._update(st, "fallback", fallback=s.StageRecord(plan=output.plan))
        except Exception as exc:
            return self._update(
                st, "fallback_failed", selected=None, errors=[*errors, f"fallback error: {exc}"]
            )

    def _explain(self, st):
        if st["selected"] is None or not st["view"].waiting_jobs or st["view"].current_slot >= 24:
            return self._update(st, "no_explanation")
        return self._call(
            st,
            "explain",
            self._explanation_messages,
            (st["context"], st[st["selected"]]),
            s.Explanation,
        )

    def run_decision(self, view, snapshot, *, decision_id, run_id, trial, seed, decision_deadline):
        """One actual graph decision and controlled slot advancement; no hidden model retry.

        Caller-supplied renderers see only visible context/stages. Explanation is
        provisional before execution; it cannot return or replace a Plan. The
        controller's final recheck decides execution and preserves refusal evidence.
        """
        view = s.VisibleState.model_validate(view.model_dump(mode="python"), strict=True)
        snapshot = s.ConstraintSnapshot.model_validate(
            snapshot.model_dump(mode="python"), strict=True
        )
        s.DecisionRecord(
            decision_id=decision_id,
            run_id=run_id,
            trial=trial,
            system="agent",
            episode_id=view.episode_id,
            slot=view.current_slot,
            final_status="blocked",
        )
        if (
            type(seed) is not int
            or seed < 0
            or type(decision_deadline) not in {float, int}
            or not math.isfinite(decision_deadline)
        ):
            raise ValueError("explicit strict seed and finite monotonic deadline are required")
        key = (view.episode_id, view.current_slot)
        if not self._lock.acquire(blocking=False):
            raise CallBlocked("agent decisions must be serial")
        try:
            identity = (run_id, trial, seed)
            if self._run_identity is not None and self._run_identity != identity:
                raise CallBlocked("one harness/provider per run with fixed trial and seed")
            self._run_identity = identity
            if key in self._requested:
                raise CallBlocked("agent already handled this decision; use saved evidence")
            if any(
                (a.system, a.episode_id, a.slot) == ("agent", *key) for a in self._provider.attempts
            ):
                raise CallBlocked(
                    "provider already has attempts for this decision; reconcile existing run"
                )
            self._requested.add(key)
            started = time.perf_counter()
            state = _State(
                decision_id=decision_id,
                run_id=run_id,
                view=view,
                snapshot=snapshot,
                context=None,
                seed=seed,
                deadline=float(decision_deadline),
                initial=None,
                repaired=None,
                fallback=None,
                selected=None,
                attempts=[],
                errors=[],
                route=[],
                explanation=None,
                repair_count=0,
                predispatch_blocked=False,
                fatal=False,
            )
            # Never enable an external tracing service from environment inheritance.
            with tracing_context(enabled=False):
                final = self._graph.invoke(state, {"recursion_limit": 16, "callbacks": []})
            selected = final["selected"]
            if final["fatal"] or not self._time_left(final):
                selected = None
                final["errors"].append(
                    "execution withheld: persistence, unknown outcome or decision deadline"
                )
            attempts = tuple(final["attempts"])

            def usage(name):
                values = [getattr(a, name) for a in attempts]
                return sum(values) if all(v is not None for v in values) else None

            record = s.DecisionRecord(
                decision_id=decision_id,
                run_id=run_id,
                trial=trial,
                system="agent",
                episode_id=view.episode_id,
                slot=view.current_slot,
                input_hash=final["context"].content_hash
                if final["context"]
                else view.canonical_hash(),
                raw_response=attempts[0].raw_response.decode("utf-8", errors="replace")
                if attempts
                else None,
                initial=final["initial"],
                repaired=final["repaired"],
                fallback=final["fallback"],
                final_status="blocked",
                explanation=final["explanation"],
                model_call_count=len(attempts),
                repair_count=final["repair_count"],
                prompt_tokens=usage("prompt_tokens"),
                completion_tokens=usage("completion_tokens"),
                errors=tuple(final["errors"]),
            )
            execution = self._controller.execute_step(
                record, stage=selected, expected_state_version=view.state_version
            )
            return AgentDecision(
                execution,
                attempts,
                final["context"].content_hash if final["context"] else None,
                tuple(final["route"]),
                (time.perf_counter() - started) * 1000,
            )
        finally:
            self._lock.release()
