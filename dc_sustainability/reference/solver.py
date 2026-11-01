"""Deterministic visible-state reference solver (O01 backend) for O02 labels.

This module is intentionally separate from the simulator, feature builder, and fold
splitter. It consumes a policy-visible ``VisibleState`` and ``Context`` and emits a
``SolverResult`` whose status is one of:

* ``certified_optimal`` – MILP found a proven-optimal schedule.
* ``certified_infeasible`` – MILP proved no schedule satisfies all physical constraints.
* ``unresolved`` – the solver timed out or failed.
* ``insufficient_evidence`` – required evidence (capacity, carbon forecasts) is missing
  or stale; this is distinct from physical infeasibility.

Only ``certified_optimal`` results carry a schedule and objective. The solver never
uses future arrivals; it is a *visible-state* solver, so ``uses_future_arrivals`` is
always ``False`` and ``kind`` is always ``visible``.

Design choices (Q08 stand-in until the team records them):

* Backend: ``scipy.optimize.milp``.
* Objective: minimize total emissions (kg CO2) = sum_kWh * carbon_g_per_kWh / 1000.
* Energy per slot: job power (kW) * site slot_hours * site PUE.
* Decision variables: one binary per feasible ``(job_id, start_slot)`` candidate.
* Constraints:
  1. Each arrived waiting job must start exactly once.
  2. Each job starts within its visible window (encoded by variable existence).
  3. Capacity per slot: background + running + newly started jobs <= capacity limit.
  4. Non-flexible jobs must start exactly at their arrival slot.
* Tie-breaking: deterministic lexicographic ordering of candidates (job_id, start_slot)
  implemented as a tiny secondary objective term so the MILP itself breaks ties.
* Tolerance: ``1e-6`` for integrality/objective reporting.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from scipy import __version__ as _scipy_version
from scipy.optimize import Bounds, LinearConstraint, milp

from dc_sustainability import schemas as s
from dc_sustainability.training.features import (
    _capacity_kw,
    _max_age_seconds,
    _running_load,
    _window,
)


class _MissingFreshnessError(Exception):
    """Raised when the solver cannot locate an authoritative freshness constraint."""


_BACKENDS = ("scipy.optimize.milp",)
_BACKEND_VERSION = f"scipy-{_scipy_version}"
_TIME_LIMIT_S = 30.0
_TOLERANCE = 1e-6
_LEXICOGRAPHIC_BASE = 2  # base for secondary tie-break objective (overridden dynamically)


@dataclass(frozen=True)
class CandidateVar:
    """One MILP binary variable: ``x[idx] == 1`` means ``job_id`` starts at ``start_slot``."""

    idx: int
    job_id: str
    start_slot: int
    job: s.Job
    energy_kwh: float
    carbon_g_per_kwh: float

    @property
    def emissions_kg(self) -> float:
        return self.energy_kwh * self.carbon_g_per_kwh / 1000.0


class _MILPModel:
    """Build and solve a deterministic MILP for one visible decision."""

    def __init__(
        self,
        state: s.VisibleState,
        context: s.Context,
        *,
        decision_time_utc: datetime,
        time_limit_s: float = _TIME_LIMIT_S,
        tolerance: float = _TOLERANCE,
    ) -> None:
        self.state = state
        self.context = context
        self.decision_time_utc = decision_time_utc
        self.time_limit_s = time_limit_s
        self.tolerance = tolerance
        self.capacity: Optional[float] = _capacity_kw(context)
        self.horizon = s.PROPOSED_DECISION_SLOTS + s.PROPOSED_COMPLETION_SLOTS
        self.facts: dict[int, s.CarbonForecast] = {
            fact.valid_slot: fact for fact in state.carbon_facts
        }
        self.occupancy = _running_load(state)
        self.vars: list[CandidateVar] = []
        # Per-job bookkeeping used to distinguish physical infeasibility from missing evidence.
        self._job_has_physical_candidate: dict[str, bool] = {}
        self._job_has_fresh_candidate: dict[str, bool] = {}
        # Set by _build_vars when the freshness constraint is missing.
        self._missing_freshness_reason: Optional[str] = None
        self._build_vars()

    def _build_vars(self) -> None:
        current = self.state.current_slot
        visible_end = min(current + s.PROPOSED_DECISION_SLOTS, self.horizon)
        try:
            max_age = self._max_age_seconds()
        except _MissingFreshnessError as exc:
            # Defer the insufficient_evidence decision until solve() so we can report
            # it with a proper SolverResult and input hash. Do not use float("inf")
            # as a working freshness bound; that would disable all stale-forecast checks.
            self._missing_freshness_reason = str(exc)
            max_age = None
        for job in sorted(self.state.waiting_jobs, key=lambda j: j.job_id):
            if job.arrival_slot > current:
                continue
            has_physical = False
            has_fresh = False
            for start in _window(job, current):
                if start + job.duration_slots > visible_end:
                    continue
                if not self._fits(start, job):
                    continue
                has_physical = True
                if max_age is None:
                    # Freshness evidence is missing; do not create candidates.
                    continue
                carbon = self._fresh_carbon(start, job.duration_slots, max_age)
                if carbon is None:
                    continue
                has_fresh = True
                energy = self._energy_kwh(job, start)
                mean_carbon = sum(carbon) / len(carbon)
                var = CandidateVar(
                    idx=len(self.vars),
                    job_id=job.job_id,
                    start_slot=start,
                    job=job,
                    energy_kwh=energy,
                    carbon_g_per_kwh=mean_carbon,
                )
                self.vars.append(var)
            self._job_has_physical_candidate[job.job_id] = has_physical
            self._job_has_fresh_candidate[job.job_id] = has_fresh

    def _max_age_seconds(self) -> float:
        try:
            return _max_age_seconds(self.state, self.context)
        except s.MissingEvidenceError as exc:
            # Missing freshness evidence is not the same as "any age is acceptable".
            # Surface it as a sentinel so the solver reports insufficient_evidence.
            raise _MissingFreshnessError(str(exc)) from exc

    def _fits(self, start: int, job: s.Job) -> bool:
        if self.capacity is None:
            return False
        return all(
            self.occupancy.get(slot, 0.0) + job.power_kw <= self.capacity
            for slot in range(start, start + job.duration_slots)
        )

    def _fresh_carbon(
        self, start: int, duration: int, max_age: float
    ) -> Optional[tuple[float, ...]]:
        current = self.state.current_slot
        visible_end = min(current + s.PROPOSED_DECISION_SLOTS, self.horizon)
        values: list[float] = []
        for slot in range(start, start + duration):
            fact = self.facts.get(slot)
            if fact is None or not current <= slot < visible_end:
                return None
            age = (self.decision_time_utc - fact.issued_at_utc).total_seconds()
            if age < 0 or age > max_age:
                return None
            values.append(fact.value)
        return tuple(values)

    def _energy_kwh(self, job: s.Job, start: int) -> float:
        site = self.state.site
        # Energy is the same for every feasible start of a job; carbon varies.
        return job.power_kw * job.duration_slots * site.slot_hours * site.pue

    def solve(self) -> s.SolverResult:
        start_time = time.perf_counter()
        if self.capacity is None:
            elapsed = time.perf_counter() - start_time
            return self._insufficient_evidence("capacity constraint missing from context", elapsed)

        # Missing freshness evidence disables all stale-forecast checking. Treat this as
        # insufficient evidence for the whole decision, not as physical infeasibility.
        if self._missing_freshness_reason is not None:
            elapsed = time.perf_counter() - start_time
            return self._insufficient_evidence(self._missing_freshness_reason, elapsed)

        # Every arrived waiting job must be explicitly constrained. If a job has no
        # candidate at all, classify the root cause before declaring infeasibility.
        arrived_jobs = [
            j for j in self.state.waiting_jobs if j.arrival_slot <= self.state.current_slot
        ]
        for job in arrived_jobs:
            physical = self._job_has_physical_candidate.get(job.job_id, False)
            fresh = self._job_has_fresh_candidate.get(job.job_id, False)
            if not physical:
                # No start satisfies capacity/deadline/nonflexible constraints.
                return self._certified_infeasible(
                    f"job {job.job_id} has no feasible start within capacity/deadline/nonflexible constraints",
                    time.perf_counter() - start_time,
                )
            if not fresh:
                # Feasible starts exist but required carbon forecasts are missing or stale.
                return self._insufficient_evidence(
                    f"job {job.job_id} has feasible starts but missing or stale carbon forecasts",
                    time.perf_counter() - start_time,
                )

        if not self.vars:
            # No waiting jobs and no candidates: trivially optimal empty schedule.
            elapsed = time.perf_counter() - start_time
            return self._certified_optimal([], 0.0, "empty visible horizon", elapsed)

        n = len(self.vars)

        # Build shared constraint matrices once.
        job_ids = sorted({var.job_id for var in self.vars})
        job_index = {job_id: i for i, job_id in enumerate(job_ids)}
        a_job = np.zeros((len(job_ids), n))
        for var in self.vars:
            a_job[job_index[var.job_id], var.idx] = 1.0
        job_con = LinearConstraint(a_job, lb=1.0, ub=1.0)

        # Non-flexible jobs must start exactly at their arrival slot.
        nonflex_jobs = {
            var.job_id: var.idx
            for var in self.vars
            if not var.job.flexible and var.start_slot == var.job.arrival_slot
        }
        nonflex_rows = []
        for job_id in job_ids:
            job = next(var.job for var in self.vars if var.job_id == job_id)
            if not job.flexible:
                if job_id not in nonflex_jobs:
                    elapsed = time.perf_counter() - start_time
                    return self._certified_infeasible(
                        f"non-flexible job {job_id} has no feasible start at arrival",
                        elapsed,
                    )
                row = np.zeros(n)
                row[nonflex_jobs[job_id]] = 1.0
                nonflex_rows.append(row)
        if nonflex_rows:
            a_nonflex = np.vstack(nonflex_rows)
            nonflex_con = LinearConstraint(a_nonflex, lb=1.0, ub=1.0)
        else:
            nonflex_con = None

        # Capacity per slot: background + running + new starts <= capacity.
        a_cap = np.zeros((self.horizon, n))
        for var in self.vars:
            for slot in range(var.start_slot, var.start_slot + var.job.duration_slots):
                a_cap[slot, var.idx] = var.job.power_kw
        cap_ub = np.array(
            [
                (self.capacity or 0.0) - self.occupancy.get(slot, 0.0)
                for slot in range(self.horizon)
            ],
            dtype=float,
        )
        cap_con = LinearConstraint(a_cap, lb=-np.inf, ub=cap_ub)

        constraints = [job_con, cap_con]
        if nonflex_con is not None:
            constraints.append(nonflex_con)

        bounds = Bounds(lb=np.zeros(n), ub=np.ones(n))
        integrality = np.ones(n, dtype=int)

        # Stage 1: solve the original, unmodified primary carbon-minimization problem.
        primary_c = np.array([var.emissions_kg for var in self.vars], dtype=float)
        try:
            primary_res = milp(
                c=primary_c,
                constraints=constraints,
                bounds=bounds,
                integrality=integrality,
                options={"time_limit": self.time_limit_s},
            )
        except Exception as exc:  # pragma: no cover - solver failure
            elapsed = time.perf_counter() - start_time
            return self._unresolved(f"scipy milp raised {type(exc).__name__}: {exc}", elapsed)

        elapsed = time.perf_counter() - start_time

        # HiGHS status codes through scipy:
        # 0 -> success, 1 -> timeout, 2 -> infeasible, 3 -> unbounded.
        if primary_res.status == 2:
            return self._certified_infeasible(primary_res.message, elapsed)
        if not (primary_res.success and primary_res.status == 0):
            return self._unresolved(primary_res.message, elapsed)

        primary_objective = float(primary_res.fun)
        primary_gap = getattr(primary_res, "mip_gap", None)
        primary_bound = getattr(primary_res, "mip_dual_bound", None)

        # Stage 2: among primary-optimal schedules, choose the deterministic canonical
        # lexicographic schedule. We fix the primary objective within a small tolerance
        # and then iterate candidates in lexicographic (job_id, start_slot) order. For
        # each candidate we attempt to fix it to 1 while preserving primary optimality.
        # If feasible, we lock it in and forbid all other starts for the same job. This
        # is a true lexicographic optimization: earlier candidates in the ordering are
        # preferred regardless of later candidates, which a single weighted-sum objective
        # cannot guarantee with finite coefficients.
        sorted_vars = sorted(self.vars, key=lambda v: (v.job_id, v.start_slot))

        # Preserve the certified primary optimum: c^T x <= primary_objective + eps.
        # Use a modest multiple of the integrality tolerance to avoid numerical noise.
        objective_slack = _TOLERANCE * max(1.0, abs(primary_objective))
        a_obj = primary_c.reshape(1, -1)
        obj_con = LinearConstraint(a_obj, lb=-np.inf, ub=primary_objective + objective_slack)

        stage2_constraints = list(constraints)
        stage2_constraints.append(obj_con)
        fixed: set[int] = set()
        for var in sorted_vars:
            if var.idx in fixed:
                continue
            # Try fixing this candidate to 1.
            fix_row = np.zeros(n)
            fix_row[var.idx] = 1.0
            fix_con = LinearConstraint(fix_row, lb=1.0, ub=1.0)
            try:
                test_res = milp(
                    c=primary_c,
                    constraints=stage2_constraints + [fix_con],
                    bounds=bounds,
                    integrality=integrality,
                    options={"time_limit": self.time_limit_s},
                )
            except Exception as exc:  # pragma: no cover - solver failure
                elapsed = time.perf_counter() - start_time
                return self._unresolved(
                    f"lexicographic tie-break milp raised {type(exc).__name__}: {exc}",
                    elapsed,
                    unresolved_reason="lexicographic tie-break unresolved",
                )
            if not (test_res.success and test_res.status == 0):
                # This candidate cannot be part of any primary-optimal schedule.
                continue
            # Commit to this candidate: forbid all other starts for this job and fix it.
            fixed.add(var.idx)
            same_job = [v for v in self.vars if v.job_id == var.job_id and v.idx != var.idx]
            if same_job:
                zero_row = np.zeros(n)
                for v in same_job:
                    zero_row[v.idx] = 1.0
                stage2_constraints.append(LinearConstraint(zero_row, lb=0.0, ub=0.0))
            stage2_constraints.append(fix_con)

        elapsed = time.perf_counter() - start_time

        selected = [var for var in self.vars if var.idx in fixed]
        if not selected:
            # Should not happen because the primary optimum is feasible, but keep safe.
            return self._unresolved(
                "primary certified optimal but lexicographic tie-break produced no selection",
                elapsed,
                unresolved_reason="lexicographic tie-break unresolved",
            )

        return self._certified_optimal(
            selected,
            primary_objective,
            "primary carbon optimum with deterministic lexicographic tie-break",
            elapsed,
            gap=primary_gap,
            bound_kg=primary_bound,
        )

    def _input_hash(self) -> str:
        return self.context.content_hash

    def _schedule_from(self, selected: list[CandidateVar]) -> tuple[s.PlannedStart, ...]:
        starts = sorted(
            (s.PlannedStart(job_id=var.job_id, start_slot=var.start_slot) for var in selected),
            key=lambda ps: (ps.job_id, ps.start_slot),
        )
        return tuple(starts)

    def _certified_optimal(
        self,
        selected: list[CandidateVar],
        objective_kg: float,
        termination: str,
        elapsed_s: float,
        *,
        gap: Optional[float] = None,
        bound_kg: Optional[float] = None,
    ) -> s.SolverResult:
        # Report the primary MILP objective, not a recomputed sum, so tiny
        # floating-point differences between the solver's reported optimum and
        # a manual recomputation do not break oracle comparisons. The selected
        # schedule is certified primary-optimal, so the solver's objective is
        # authoritative.
        return s.SolverResult(
            solver_result_id=_new_solver_id(),
            kind="visible",
            uses_future_arrivals=False,
            input_hash=self._input_hash(),
            status="certified_optimal",
            backend=_BACKENDS[0],
            backend_version=_BACKEND_VERSION,
            time_limit_s=self.time_limit_s,
            elapsed_s=round(elapsed_s, 6),
            termination=termination,
            tolerance=self.tolerance,
            objective_kg=round(objective_kg, 9),
            bound_kg=round(bound_kg, 9) if bound_kg is not None else None,
            gap=round(gap, 9) if gap is not None else None,
            tie_break="lexicographic (job_id, start_slot) via sequential fixing",
            certification_basis=(
                "scipy.optimize.milp mixed-integer linear program; "
                "minimize emissions; capacity + one-start + nonflexible constraints; "
                "deterministic lexicographic tie-break"
            ),
            schedule=self._schedule_from(selected),
            matching_work_job_ids=tuple(sorted({var.job_id for var in selected})),
        )

    def _certified_infeasible(self, reason: str, elapsed_s: float) -> s.SolverResult:
        return s.SolverResult(
            solver_result_id=_new_solver_id(),
            kind="visible",
            uses_future_arrivals=False,
            input_hash=self._input_hash(),
            status="certified_infeasible",
            backend=_BACKENDS[0],
            backend_version=_BACKEND_VERSION,
            time_limit_s=self.time_limit_s,
            elapsed_s=round(elapsed_s, 6),
            termination=reason,
            tolerance=self.tolerance,
            certification_basis="scipy.optimize.milp proved infeasibility",
        )

    def _unresolved(
        self,
        reason: str,
        elapsed_s: float,
        *,
        unresolved_reason: Optional[str] = None,
    ) -> s.SolverResult:
        return s.SolverResult(
            solver_result_id=_new_solver_id(),
            kind="visible",
            uses_future_arrivals=False,
            input_hash=self._input_hash(),
            status="unresolved",
            backend=_BACKENDS[0],
            backend_version=_BACKEND_VERSION,
            time_limit_s=self.time_limit_s,
            elapsed_s=round(elapsed_s, 6),
            termination=reason,
            tolerance=self.tolerance,
            unresolved_reason=unresolved_reason or reason,
        )

    def _insufficient_evidence(self, reason: str, elapsed_s: float) -> s.SolverResult:
        return s.SolverResult(
            solver_result_id=_new_solver_id(),
            kind="visible",
            uses_future_arrivals=False,
            input_hash=self._input_hash(),
            status="insufficient_evidence",
            backend=_BACKENDS[0],
            backend_version=_BACKEND_VERSION,
            time_limit_s=self.time_limit_s,
            elapsed_s=round(elapsed_s, 6),
            termination=reason,
            tolerance=self.tolerance,
            unresolved_reason=reason,
        )


def _new_solver_id() -> str:
    return f"SOLVE-{uuid.uuid4().hex[:16].upper()}"


def solve_visible(
    state: s.VisibleState,
    context: s.Context,
    *,
    decision_time_utc: datetime,
    time_limit_s: float = _TIME_LIMIT_S,
    tolerance: float = _TOLERANCE,
) -> s.SolverResult:
    """Solve one visible decision and return a typed ``SolverResult``.

    Args:
        state: policy-visible state at the decision slot.
        context: hashed policy context built from the same state.
        decision_time_utc: explicit trusted UTC time used to evaluate forecast freshness.
        time_limit_s: MILP solver time limit in seconds.
        tolerance: integrality/objective reporting tolerance.
    """
    if state.constraint_snapshot_id != context.content.snapshot_id:
        raise s.ContractError("state and context snapshot ids differ")
    if not isinstance(decision_time_utc, datetime) or decision_time_utc.utcoffset() != timedelta(0):
        raise ValueError("an explicit trusted UTC decision time is required")
    model = _MILPModel(
        state,
        context,
        decision_time_utc=decision_time_utc,
        time_limit_s=time_limit_s,
        tolerance=tolerance,
    )
    return model.solve()
