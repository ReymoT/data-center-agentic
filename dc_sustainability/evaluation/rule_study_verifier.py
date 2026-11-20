"""RULE-03 independent bounded safety and progress verifier (Nisha, #241).

Checks a scheduling system against the RULE-01 safety properties S1-S5 and progress
properties P1-P2 on small finite synthetic domains. It is deliberately standard-library
only: it does not import the production checker, the simulator, shared schemas or any
rules-v1 code, so a defect there shows up as a disagreement instead of being copied.

Timing follows the shared rules: occupancy is [start, start + duration), new starts only
in slots 0-23, all work ends by boundary 30, and a start must finish by
min(deadline, 30). A nonflexible job may start only at its arrival slot. A waiting job is
missed at the first boundary after both its arrival and its latest legal start.

Two methods are kept separate and named in every report:

- ``legal_action_graph_for_joint_feasibility``: from each input, enumerate every
  reachable state under every legal current-start subset (including starting nothing).
  This is only the independent oracle for which inputs can complete all their work; its
  answer is cross-checked against a brute-force joint assignment search. Arbitrary legal
  actions are not the policy's behavior.
- ``policy_induced_graph_for_properties``: follow the system under test's own decisions
  from slot 0 and check S1-S5 at every state it reaches, then P1 at the end.

One combined ceiling covers every domain and both methods (RULE-01 review-2), with
counters per domain/method. Ceilings are stop limits, not claimed counts: hitting one
makes every unfinished property INCOMPLETE, never PASS. Nothing here proves behavior
outside the enumerated domain.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Literal, Mapping, Sequence

RECORD_KIND = "rule_study_verification_v1"
VERIFIER_VERSION = "rule03-review-3"
HORIZON = 30
LAST_START_SLOT = 23
DEFAULT_SCORE = 200
COUNTEREXAMPLES_PER_PROPERTY = 10  # all violations are counted; this caps examples only

PropertyId = Literal["S1", "S2", "S3", "S4", "S5", "P1", "P2"]
Status = Literal["PASS", "FAIL", "INCOMPLETE", "NOT_RUN"]
PROPERTY_IDS: tuple[PropertyId, ...] = ("S1", "S2", "S3", "S4", "S5", "P1", "P2")
PROPERTY_MEANING: dict[str, str] = {
    "S1": "starts only arrived waiting jobs, each job at most once",
    "S2": "nonflexible jobs start at arrival; every start finishes by its deadline",
    "S3": "background + running + new job power <= IT capacity in every occupied slot",
    "S4": "no invalid proposal (including injected faults) is executed",
    "S5": "valid clock transition: one slot per step, no new starts in drain slots 24-29",
    "P1": "closed, fault-free, forecast-present, jointly feasible inputs complete all jobs",
    "P2": "every arrived job ends completed or explicitly missed, matching the reported result",
}


@dataclass(frozen=True)
class Job:
    job_id: str
    power_kw: int
    duration_slots: int
    arrival_slot: int
    deadline_slot: int
    flexible: bool

    def __post_init__(self):
        for name in ("power_kw", "duration_slots", "arrival_slot", "deadline_slot"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"{self.job_id}: {name} must be an integer")
        if not isinstance(self.job_id, str) or not self.job_id:
            raise ValueError("job_id must be a nonempty string")
        if not isinstance(self.flexible, bool):
            raise ValueError(f"{self.job_id}: flexible must be a boolean")
        if self.power_kw <= 0 or self.duration_slots <= 0:
            raise ValueError(f"{self.job_id}: power and duration must be positive")
        if not 0 <= self.arrival_slot <= LAST_START_SLOT:
            raise ValueError(f"{self.job_id}: arrival must be in slots 0-23")
        if not 1 <= self.deadline_slot <= HORIZON:
            raise ValueError(f"{self.job_id}: deadline must be in 1-30")
        # A deadline at or before arrival is allowed: an impossible arrival is a valid input
        # that must end missed, never started.

    @property
    def latest_start(self) -> int:
        latest = min(min(self.deadline_slot, HORIZON) - self.duration_slots, LAST_START_SLOT)
        return min(latest, self.arrival_slot) if not self.flexible else latest

    def legal_starts(self, now: int) -> range:
        first = max(now, self.arrival_slot)
        if not self.flexible:
            return (
                range(first, first + 1)
                if first == self.arrival_slot <= self.latest_start
                else range(0)
            )
        return range(first, self.latest_start + 1)


@dataclass(frozen=True)
class Case:
    """One synthetic input. ``scores`` is None when no forecast is visible."""

    case_id: str
    capacity_kw: int
    background_kw: int
    jobs: tuple[Job, ...]
    scores: tuple[int, ...] | None
    fault_starts: tuple[str, ...] = ()  # injected slot-0 proposal; empty means no fault

    def __post_init__(self):
        if not isinstance(self.case_id, str) or not self.case_id:
            raise ValueError("case_id must be a nonempty string")
        if not isinstance(self.jobs, tuple) or not all(isinstance(j, Job) for j in self.jobs):
            raise ValueError("jobs must be an immutable tuple of Job records")
        for value in (self.capacity_kw, self.background_kw):
            if type(value) is not int:
                raise ValueError("capacity/background must be integers, not bool or float")
        if self.scores is not None and (
            not isinstance(self.scores, tuple)
            or any(type(x) is not int or x < 0 for x in self.scores)
        ):
            raise ValueError("scores must be an immutable tuple of nonnegative integers")
        if not isinstance(self.fault_starts, tuple) or any(
            not isinstance(x, str) or not x for x in self.fault_starts
        ):
            raise ValueError("fault_starts must be a tuple of nonempty IDs")
        if len(self.jobs) > 4:
            raise ValueError("case exceeds the four-job study bound")
        ids = [j.job_id for j in self.jobs]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{self.case_id}: duplicate job IDs")
        if self.capacity_kw <= 0 or not 0 <= self.background_kw <= self.capacity_kw:
            raise ValueError(f"{self.case_id}: invalid capacity/background")
        if self.scores is not None and len(self.scores) != HORIZON:
            raise ValueError(f"{self.case_id}: scores must cover all 30 slots")

    def job(self, job_id: str) -> Job | None:
        return next((j for j in self.jobs if j.job_id == job_id), None)

    @property
    def fault_injected(self) -> bool:
        return bool(self.fault_starts)

    @property
    def closed_at_slot0(self) -> bool:
        return all(j.arrival_slot == 0 for j in self.jobs)


@dataclass(frozen=True)
class State:
    """Reconstructed state at a slot boundary; tuples are sorted for hashing."""

    slot: int
    running: tuple[tuple[str, int, int], ...] = ()  # (job_id, start, end)
    completed: tuple[tuple[str, int, int], ...] = ()
    missed: tuple[str, ...] = ()

    def resolved_ids(self) -> set[str]:
        return {r[0] for r in self.running} | {c[0] for c in self.completed} | set(self.missed)

    def waiting(self, case: Case) -> tuple[Job, ...]:
        done = self.resolved_ids()
        return tuple(j for j in case.jobs if j.arrival_slot <= self.slot and j.job_id not in done)

    def pending(self, case: Case) -> tuple[Job, ...]:
        """Waiting plus not-yet-arrived jobs."""
        done = self.resolved_ids()
        return tuple(j for j in case.jobs if j.job_id not in done)


@dataclass(frozen=True)
class Violation:
    property_id: PropertyId
    code: str
    detail: str
    arithmetic: Mapping | None = None


@dataclass(frozen=True)
class ProposalStage:
    origin: str  # e.g. rules-v1, greedy_a_fallback, fault_injection
    starts: tuple[str, ...]


@dataclass(frozen=True)
class SystemView:
    """Exactly what a policy may see at a decision: no future arrivals or hidden facts."""

    case_id: str
    slot: int
    state_version: int
    capacity_kw: int
    background_kw: int
    waiting: tuple[Job, ...]
    running: tuple[tuple[str, int, int, int], ...]  # (job_id, power_kw, start, end)
    completed_ids: tuple[str, ...]
    missed_ids: tuple[str, ...]
    scores: tuple[int, ...] | None  # visible score profile for slots slot..29, or None
    injected_proposal: tuple[str, ...] | None = None  # fault to route through the gate


@dataclass(frozen=True)
class SystemDecision:
    executed_starts: tuple[str, ...]
    proposals: tuple[ProposalStage, ...] = ()


SystemFn = Callable[[SystemView], SystemDecision]


def initial_state() -> State:
    return State(slot=0)


def load_terms(case: Case, state: State, starts: Sequence[str], slot: int) -> list[dict]:
    terms = [{"label": "background", "job_id": None, "value": case.background_kw, "unit": "kW"}]
    for job_id, start, end in state.running:
        if start <= slot < end:
            job = case.job(job_id)
            terms.append(
                {"label": "running", "job_id": job_id, "value": job.power_kw, "unit": "kW"}
            )
    for job_id in starts:
        job = case.job(job_id)
        if job is not None and state.slot <= slot < state.slot + job.duration_slots:
            terms.append({"label": "new", "job_id": job_id, "value": job.power_kw, "unit": "kW"})
    return terms


def capacity_arithmetic(
    case: Case, state: State, starts: Sequence[str], slot: int
) -> dict[str, object]:
    terms = load_terms(case, state, starts, slot)
    total = sum(t["value"] for t in terms)
    return {
        "slot": slot,
        "terms": terms,
        "total": total,
        "limit": case.capacity_kw,
        "signed_excess": total - case.capacity_kw,
        "holds": total <= case.capacity_kw,
    }


def check_starts(case: Case, state: State, starts: Sequence[str]) -> list[Violation]:
    """Independent S1/S2/S3/S5 predicate for one batch of current starts."""
    out: list[Violation] = []
    if starts and state.slot > LAST_START_SLOT:
        out.append(Violation("S5", "drain_slot_start", f"starts at slot {state.slot}"))
    seen: set[str] = set()
    waiting = {j.job_id for j in state.waiting(case)}
    resolved = state.resolved_ids()
    known = []
    for job_id in starts:
        job = case.job(job_id)
        if job_id in seen:
            out.append(Violation("S1", "duplicate_start", job_id))
            continue
        seen.add(job_id)
        if job is None:
            out.append(Violation("S1", "unknown_job", job_id))
            continue
        known.append(job_id)
        if job.arrival_slot > state.slot:
            out.append(Violation("S1", "not_arrived", f"{job_id} arrives {job.arrival_slot}"))
        elif job_id in resolved or job_id not in waiting:
            out.append(Violation("S1", "not_waiting", job_id))
        if not job.flexible and state.slot != job.arrival_slot:
            out.append(
                Violation("S2", "nonflexible_timing", f"{job_id} arrival {job.arrival_slot}")
            )
        if state.slot + job.duration_slots > min(job.deadline_slot, HORIZON):
            out.append(
                Violation(
                    "S2",
                    "deadline",
                    f"{job_id} ends {state.slot + job.duration_slots} > {job.deadline_slot}",
                )
            )
    for slot in range(state.slot, HORIZON):
        arithmetic = capacity_arithmetic(case, state, known, slot)
        if not arithmetic["holds"]:
            out.append(Violation("S3", "capacity", f"slot {slot}", arithmetic))
            break
    return out


def _mark_missed(case: Case, state: State) -> State:
    missed = set(state.missed)
    for job in state.waiting(case):
        if state.slot > job.latest_start and state.slot > job.arrival_slot:
            missed.add(job.job_id)
    return State(state.slot, state.running, state.completed, tuple(sorted(missed)))


def advance(case: Case, state: State, starts: Sequence[str]) -> State:
    """Apply already-checked starts and move one slot. Never call with invalid starts."""
    running = list(state.running)
    for job_id in starts:
        job = case.job(job_id)
        running.append((job_id, state.slot, state.slot + job.duration_slots))
    finished = [r for r in running if r[2] == state.slot + 1]
    still = [r for r in running if r[2] != state.slot + 1]
    nxt = State(
        slot=state.slot + 1,
        running=tuple(sorted(still)),
        completed=tuple(sorted(state.completed + tuple(finished))),
        missed=state.missed,
    )
    return _mark_missed(case, nxt)


def view_for(case: Case, state: State) -> SystemView:
    return SystemView(
        case_id=case.case_id,
        slot=state.slot,
        state_version=state.slot,
        capacity_kw=case.capacity_kw,
        background_kw=case.background_kw,
        waiting=state.waiting(case),
        running=tuple(
            (jid, case.job(jid).power_kw, start, end) for jid, start, end in state.running
        ),
        completed_ids=tuple(c[0] for c in state.completed),
        missed_ids=state.missed,
        scores=None if case.scores is None else case.scores[state.slot :],
        injected_proposal=case.fault_starts if case.fault_starts and state.slot == 0 else None,
    )


class BudgetStopped(RuntimeError):
    """Cooperative stop during independent enumeration, never infeasibility evidence."""


def completion_witness(
    case: Case, state: State, *, budget: Budget | None = None
) -> tuple[dict[str, int] | None, int]:
    """Brute-force search for one schedule completing every pending job.

    Returns (witness start map or None, number of assignments examined). Independent of
    any solver: plain enumeration of legal starts with the S3 capacity rule.
    """
    pending = state.pending(case)
    options = [list(j.legal_starts(state.slot)) for j in pending]
    examined = 0
    for combo in itertools.product(*options):
        if budget is not None and not budget.check_time():
            raise BudgetStopped("time ceiling during joint-assignment cross-check")
        examined += 1
        if _assignment_fits(case, state, dict(zip((j.job_id for j in pending), combo))):
            return dict(zip((j.job_id for j in pending), combo)), examined
    return None, examined


def _assignment_fits(case: Case, state: State, starts: Mapping[str, int]) -> bool:
    for slot in range(state.slot, HORIZON):
        load = case.background_kw
        for job_id, start, end in state.running:
            if start <= slot < end:
                load += case.job(job_id).power_kw
        for job_id, start in starts.items():
            job = case.job(job_id)
            if start <= slot < start + job.duration_slots:
                load += job.power_kw
        if load > case.capacity_kw:
            return False
    return True


def legal_actions(case: Case, state: State) -> list[tuple[str, ...]]:
    """Every current-start subset that passes the independent predicate, including ()."""
    if state.slot > LAST_START_SLOT:
        return [()]
    candidates = [j.job_id for j in state.waiting(case) if state.slot in j.legal_starts(state.slot)]
    actions = []
    for size in range(len(candidates) + 1):
        for subset in itertools.combinations(candidates, size):
            if not check_starts(case, state, subset):
                actions.append(subset)
    return actions


def _idle(case: Case, state: State) -> bool:
    return not state.running and not state.pending(case)


ORACLE = "legal_action_graph_for_joint_feasibility"
POLICY = "policy_induced_graph_for_properties"


@dataclass
class Budget:
    """One combined ceiling across every domain and method (RULE-01 review-2 decision 2).

    Counters are also kept per scope ("domain/method") so each result names its own work.
    """

    max_states: int = 10_000
    max_transitions: int = 50_000
    max_seconds: float = 600.0
    states: int = 0
    transitions: int = 0
    started: float = field(default_factory=time.monotonic)
    exhausted: str | None = None
    by_scope: dict[str, dict[str, int]] = field(default_factory=dict)

    def __post_init__(self):
        for name in ("max_states", "max_transitions", "states", "transitions"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if (
            type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or self.max_seconds < 0
        ):
            raise ValueError("max_seconds must be finite and nonnegative")

    def check_time(self) -> bool:
        if self.exhausted:
            return False
        if time.monotonic() - self.started > self.max_seconds:
            self.exhausted = "seconds"
            return False
        return True

    def take_state(self, scope: str = "unscoped") -> bool:
        return self._take("states", self.max_states, scope)

    def take_transition(self, scope: str = "unscoped") -> bool:
        return self._take("transitions", self.max_transitions, scope)

    def _take(self, name: str, limit: int, scope: str) -> bool:
        if self.exhausted:
            return False
        if time.monotonic() - self.started > self.max_seconds:
            self.exhausted = "seconds"
            return False
        if getattr(self, name) >= limit:
            self.exhausted = name
            return False
        setattr(self, name, getattr(self, name) + 1)
        counters = self.by_scope.setdefault(scope, {"states": 0, "transitions": 0})
        counters[name] += 1
        return True

    def summary(self) -> dict:
        return {
            "max_states": self.max_states,
            "max_transitions": self.max_transitions,
            "max_seconds": self.max_seconds,
            "states_used": self.states,
            "transitions_used": self.transitions,
            "ceiling_hit": self.exhausted,
            "by_scope": {k: dict(v) for k, v in sorted(self.by_scope.items())},
        }


def explore_legal_graph(
    case: Case, budget: Budget, scope: str = ORACLE
) -> tuple[list[State], bool, bool]:
    """Return (reachable nonterminal states, any terminal completes all, complete flag).

    Once nothing is running or pending, the remaining idle slots to 30 are collapsed into
    one drain transition: no start is possible there and nothing changes but the clock.
    """
    start = initial_state()
    if not budget.take_state(scope):
        return [], False, False
    seen = {start}
    frontier = [start]
    nonterminal: list[State] = []
    all_done = False
    while frontier:
        state = frontier.pop()
        if state.slot >= HORIZON or _idle(case, state):
            if not state.missed and len(state.completed) == len(case.jobs):
                all_done = True
            continue
        nonterminal.append(state)
        for action in legal_actions(case, state):
            if not budget.take_transition(scope):
                return nonterminal, all_done, False
            nxt = advance(case, state, action)
            if nxt not in seen:
                if not budget.take_state(scope):
                    return nonterminal, all_done, False
                seen.add(nxt)
                frontier.append(nxt)
    nonterminal.sort(key=lambda s: (s.slot, s.running, s.completed, s.missed))
    return nonterminal, all_done, True


@dataclass
class _Tally:
    checked: dict[str, int] = field(default_factory=lambda: {p: 0 for p in PROPERTY_IDS})
    violations: dict[str, int] = field(default_factory=lambda: {p: 0 for p in PROPERTY_IDS})
    counterexamples: list[dict] = field(default_factory=list)
    counterexample_total: int = 0
    drain_slot_decisions: int = 0

    def record(self, case: Case, state: State, violation: Violation, extra: Mapping | None = None):
        self.violations[violation.property_id] += 1
        self.counterexample_total += 1
        kept = sum(1 for c in self.counterexamples if c["property"] == violation.property_id)
        if kept < COUNTEREXAMPLES_PER_PROPERTY:
            item = {
                "property": violation.property_id,
                "code": violation.code,
                "detail": violation.detail,
                "case_id": case.case_id,
                "slot": state.slot,
                "state": _state_json(state),
            }
            if violation.arithmetic is not None:
                item["arithmetic"] = violation.arithmetic
            if extra:
                item.update(extra)
            self.counterexamples.append(item)


def _state_json(state: State) -> dict:
    return {
        "slot": state.slot,
        "running": [list(r) for r in state.running],
        "completed": [list(c) for c in state.completed],
        "missed": list(state.missed),
    }


def _decide(system: SystemFn, case: Case, state: State, tally: _Tally) -> SystemDecision | None:
    try:
        decision = system(view_for(case, state))
        if not isinstance(decision, SystemDecision):
            raise TypeError("system must return SystemDecision")
        if not isinstance(decision.executed_starts, tuple) or not all(
            isinstance(j, str) and j for j in decision.executed_starts
        ):
            raise TypeError("executed_starts must be a tuple of nonempty job IDs")
        if not isinstance(decision.proposals, tuple) or not all(
            isinstance(stage, ProposalStage)
            and isinstance(stage.origin, str)
            and isinstance(stage.starts, tuple)
            and all(isinstance(j, str) and j for j in stage.starts)
            for stage in decision.proposals
        ):
            raise TypeError("proposals must contain valid ProposalStage records")
        return decision
    except Exception as exc:  # the system under test is untrusted
        tally.checked["S5"] += 1
        tally.record(case, state, Violation("S5", "system_error", f"{type(exc).__name__}: {exc}"))
        return None


def _check_decision(case: Case, state: State, decision: SystemDecision, tally: _Tally) -> bool:
    """Check one decision; return True when the executed starts are valid.

    S1-S3 and S5 are checked on every decision. S4 is counted as checked only where an
    invalid proposal actually existed, so a domain without one reports S4 NOT_RUN instead
    of a vacuous PASS.
    """
    for prop in ("S1", "S2", "S3", "S5"):
        tally.checked[prop] += 1
    if state.slot > LAST_START_SLOT:
        tally.drain_slot_decisions += 1
    executed = tuple(decision.executed_starts)
    violations = check_starts(case, state, executed)
    for v in violations:
        tally.record(case, state, v, {"executed_starts": list(executed)})
    stages = list(decision.proposals)
    if case.fault_starts and state.slot == 0:
        stages.append(ProposalStage("fault_injection", case.fault_starts))
    for stage in stages:
        if not check_starts(case, state, stage.starts):
            continue
        tally.checked["S4"] += 1
        if tuple(stage.starts) == executed:
            tally.record(
                case,
                state,
                Violation("S4", "invalid_proposal_executed", f"origin {stage.origin}"),
                {"executed_starts": list(executed)},
            )
    return not violations


def explore_policy_graph(
    system: SystemFn, case: Case, budget: Budget, tally: _Tally, scope: str = POLICY
) -> tuple[State | None, bool, int]:
    """Follow the system's own decisions from slot 0, checking S1-S5 at every state.

    Returns (final state or None if stopped, complete flag, system calls). An invalid
    execution stops the path there (fail closed); it is already recorded as a violation.
    """
    state = initial_state()
    if not budget.take_state(scope):
        return None, False, 0
    calls = 0
    seen = {state}
    while state.slot < HORIZON:
        # Unlike the oracle, the untrusted policy must be called at every clock slot.
        # Otherwise a restart/invalid start after the queue empties is never observed.
        decision = _decide(system, case, state, tally)
        calls += 1
        if decision is None or not _check_decision(case, state, decision, tally):
            return None, True, calls
        if not budget.take_transition(scope):
            return None, False, calls
        state = advance(case, state, decision.executed_starts)
        if state not in seen:
            if not budget.take_state(scope):
                return None, False, calls
            seen.add(state)
    return state, True, calls


def _p1_scope(case: Case, witness) -> str | None:
    """None when P1 applies; otherwise the scope reason it does not."""
    if case.fault_injected:
        return "fault_injected"
    if case.scores is None:
        return "missing_forecast"
    if not case.closed_at_slot0:
        return "not_closed_at_slot0"
    if witness is None:
        return "not_jointly_feasible"
    return None


def _verify_one_domain(name, cases, system, budget) -> dict:
    tally = _Tally()
    feasibility = {"complete_feasible": 0, "not_complete_feasible": 0}
    crosscheck = {"agreements": 0, "mismatches": 0, "mismatch_case_ids": []}
    p1_outside: dict[str, int] = {}
    p1_eligible = 0
    system_calls = 0
    explored = 0
    oracle_scope, policy_scope = f"{name}/{ORACLE}", f"{name}/{POLICY}"
    for case in cases:
        _, graph_done, complete = explore_legal_graph(case, budget, oracle_scope)
        if not complete:
            break
        try:
            witness, _ = completion_witness(case, initial_state(), budget=budget)
        except BudgetStopped:
            break
        if (witness is not None) == graph_done:
            crosscheck["agreements"] += 1
        else:
            crosscheck["mismatches"] += 1
            crosscheck["mismatch_case_ids"].append(case.case_id)
        feasibility["complete_feasible" if witness is not None else "not_complete_feasible"] += 1
        outside = _p1_scope(case, witness)
        if outside:
            p1_outside[outside] = p1_outside.get(outside, 0) + 1
        else:
            p1_eligible += 1
        if system is not None:
            final, complete, calls = explore_policy_graph(system, case, budget, tally, policy_scope)
            system_calls += calls
            if not complete:
                break
            if outside is None:
                tally.checked["P1"] += 1
                done = [] if final is None else [c[0] for c in final.completed]
                if len(done) != len(case.jobs):
                    tally.record(
                        case,
                        final or initial_state(),
                        Violation(
                            "P1",
                            "feasible_work_not_completed",
                            f"witness {witness}; completed {done}",
                        ),
                    )
        explored += 1

    properties = {
        prop: _status(prop, system, tally, budget, explored, len(cases)) for prop in PROPERTY_IDS
    }
    if crosscheck["mismatches"]:
        for prop, entry in properties.items():
            if entry["status"] == "PASS":
                properties[prop] = {
                    **entry,
                    "status": "INCOMPLETE",
                    "reason": "independent feasibility cross-check disagreed",
                }
    if system is not None and properties["P1"]["status"] == "PASS" and p1_eligible == 0:
        properties["P1"] = {**properties["P1"], "status": "NOT_RUN", "reason": "no P1 inputs"}
    if (
        system is not None
        and properties["S4"]["status"] not in ("FAIL", "INCOMPLETE")
        and not tally.checked["S4"]
    ):
        properties["S4"] = {
            **properties["S4"],
            "status": "NOT_RUN",
            "reason": "no invalid proposal occurred in this domain",
        }
    return {
        "domain": name,
        "counts": {
            "inputs": len(cases),
            "inputs_explored": explored,
            "system_calls": system_calls,
            "drain_slot_decisions": tally.drain_slot_decisions,
            "p1_eligible_inputs": p1_eligible,
            "p1_outside_scope": dict(sorted(p1_outside.items())),
            **feasibility,
        },
        "oracle_crosscheck": crosscheck,
        "properties": properties,
        "counterexample_total": tally.counterexample_total,
        "counterexamples": tally.counterexamples,
    }


def _case_key(case: Case) -> tuple:
    return (case.capacity_kw, case.background_kw, case.jobs, case.scores, case.fault_starts)


def verify_domains(
    domains: Sequence[tuple[str, Sequence[Case]]],
    system: SystemFn | None,
    *,
    system_id: str,
    is_rules_v1: bool = False,
    budget: Budget | None = None,
    spec_sha256: str | None = None,
) -> dict:
    """Verify domains in order under one combined budget (primary first, then supplements).

    Overlap with earlier domains is reported, never pooled as independent evidence.
    """
    budget = budget or Budget()
    results = []
    earlier: set[tuple] = set()
    for name, cases in domains:
        cases = list(cases)
        result = _verify_one_domain(name, cases, system, budget)
        keys = {_case_key(c) for c in cases}
        result["counts"]["overlap_with_earlier_domains"] = len(keys & earlier)
        earlier |= keys
        results.append(result)
    report = {
        "record_kind": RECORD_KIND,
        "study_acceptance": "not_established_by_harness_or_caller_identity_flag",
        "verifier_version": VERIFIER_VERSION,
        "verifier_source_sha256": source_sha256(),
        "spec_sha256": spec_sha256,
        "system": {"system_id": system_id, "is_rules_v1": is_rules_v1},
        "methods": [ORACLE, "brute_force_joint_assignment_crosscheck"]
        + ([POLICY] if system is not None else []),
        "budget": budget.summary(),
        "results": results,
        "exclusions": EXCLUSIONS,
    }
    if not is_rules_v1:
        report["status_note"] = (
            "Not a rules-v1 result: this report verifies the harness itself or a non-rules-v1 "
            "fixture."
        )
    return report


def verify_system(cases: Iterable[Case], system: SystemFn | None, **kwargs) -> dict:
    """Single-domain convenience wrapper: returns that domain's result plus report fields."""
    name = kwargs.pop("domain_name", "domain")
    report = verify_domains([(name, list(cases))], system, **kwargs)
    result = report.pop("results")[0]
    return {**report, **result}


def _status(prop, system, tally, budget, explored, total) -> dict:
    entry = {"meaning": PROPERTY_MEANING[prop], "checked": tally.checked[prop]}
    entry["violations"] = tally.violations[prop]
    if prop == "P2":
        return {
            **entry,
            "status": "NOT_RUN",
            "reason": "P2 compares reported results; it runs in trace mode on adapter records",
        }
    if system is None:
        return {**entry, "status": "NOT_RUN", "reason": "no system under test"}
    if tally.violations[prop]:
        return {**entry, "status": "FAIL"}
    if budget.exhausted or explored < total:
        return {**entry, "status": "INCOMPLETE", "reason": f"ceiling hit: {budget.exhausted}"}
    if not tally.checked[prop]:
        return {**entry, "status": "NOT_RUN", "reason": "property was not exercised"}
    return {**entry, "status": "PASS"}


EXCLUSIONS = [
    "Callback exploration checks declared actions on the verifier's own clock; actual runner "
    "state transitions require confirmed adapter trace semantics and evidence.",
    "Elapsed ceilings are cooperative between operations. An untrusted in-process callback "
    "cannot be preempted here; an approved process supervisor is required for a real run.",
    "Bounded: results hold only for the enumerated inputs and stated bounds; no unbounded proof.",
    "P1 covers only closed workloads revealed at slot 0, jointly feasible by the oracle, with a "
    "visible forecast and no injected fault; other inputs are reported, not claimed complete.",
    "Systems are treated as stateless functions of the visible state; a system with hidden "
    "memory needs trace-mode verification instead.",
    "Policy properties are judged on the system's own reachable states; the legal-action "
    "graph only decides P1 eligibility.",
    "Scores are artificial weights; no emissions, savings or real-site claim is made.",
    "Explanation text and arithmetic records are not checked here.",
]


# --- Domains -------------------------------------------------------------------------------


def _profile(first: Sequence[int]) -> tuple[int, ...]:
    return tuple(first) + (DEFAULT_SCORE,) * (HORIZON - len(first))


def primary_domain() -> list[Case]:
    """RULE-01's 64 inputs: two flexible arrival-0, duration-1 jobs on 30 kW / 10 kW."""
    cases = []
    types = list(itertools.product((10, 20), (1, 2)))
    for n, ((p1, d1), (p2, d2), s0, s1) in enumerate(
        itertools.product(types, types, (100, 300), (100, 300)), start=1
    ):
        jobs = (Job("J1", p1, 1, 0, d1, True), Job("J2", p2, 1, 0, d2, True))
        cases.append(Case(f"D64-{n:04d}", 30, 10, jobs, _profile((s0, s1))))
    return cases


def extended_domain() -> list[Case]:
    """Optional review-2 supplement: also vary arrival {0,1} and flexibility.

    The 64 primary inputs are a subset; reports count that overlap instead of pooling.
    """
    cases = []
    types = list(itertools.product((10, 20), (1, 2), (0, 1), (False, True)))
    for n, (t1, t2, s0, s1) in enumerate(
        itertools.product(types, types, (100, 300), (100, 300)), start=1
    ):
        jobs = [
            Job(job_id, power, 1, arrival, deadline, flexible)
            for job_id, (power, deadline, arrival, flexible) in (("J1", t1), ("J2", t2))
        ]
        cases.append(Case(f"X1024-{n:04d}", 30, 10, tuple(jobs), _profile((s0, s1))))
    return cases


def authored_cases(spec: Mapping) -> list[Case]:
    """Cases A, B, B-progress and B with fault injection, read from specification.json."""
    out = []
    for scenario in spec["scenarios"]:
        jobs = tuple(
            Job(
                j["job_id"],
                j["power_kw"],
                j["duration_slots"],
                j["arrival_slot"],
                j["deadline_slot"],
                j["flexible"],
            )
            for j in scenario["jobs"]
        )
        profile = tuple(scenario["first_scores"]) + (scenario["remaining_score"],) * (
            HORIZON - len(scenario["first_scores"])
        )
        cap, bg = scenario["capacity_kw"], scenario["background_kw"]
        out.append(Case(scenario["id"], cap, bg, jobs, profile))
        fault = scenario.get("fault_injection_not_natural_output")
        if fault:
            starts = []
            for item in fault["starts"]:
                job_id, slot = item.split("@")
                if int(slot) != 0:
                    raise ValueError("only slot-0 fault injection is supported")
                starts.append(job_id)
            out.append(Case(f"{scenario['id']}-fault", cap, bg, jobs, profile, tuple(starts)))
        sub = scenario.get("feasible_progress_subcase")
        if sub:
            changed = tuple(
                Job(
                    j.job_id,
                    j.power_kw,
                    j.duration_slots,
                    j.arrival_slot,
                    sub["deadline_slot"],
                    sub["flexible"],
                )
                if j.job_id == sub["change_job"]
                else j
                for j in jobs
            )
            out.append(Case(f"{scenario['id']}-progress", cap, bg, changed, profile))
    return out


# --- Hashing -------------------------------------------------------------------------------


def canonical_sha256(value) -> str:
    """Adapter proposal-1 convention: sorted keys, compact separators, one final LF."""
    text = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return hashlib.sha256((text + "\n").encode("utf-8")).hexdigest()


def source_sha256() -> str:
    data = Path(__file__).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()
