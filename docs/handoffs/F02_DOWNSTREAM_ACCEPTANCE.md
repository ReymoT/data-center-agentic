# F02 Downstream Interface Acceptance Handoff

**Status:** Accepted (O01 tie-break fix validated and integrated)  
**Branch:** `ved/f02-downstream-acceptance`  
**Date:** 2026-10-31  
**Owner:** Ved  
**Interface:** F02 — Policy-visible state, context, plan, and solver/label outputs  
**Contract version:** v1.0.0 (see `docs/INTERFACES.md`)

## 1. Goal

Complete downstream acceptance of the F02 schema contract by:

1. Confirming every production consumer of F02 types still compiles and behaves correctly.
2. Adding real consumer-level receiving tests where the solver/label surface had gaps.
3. Recording evidence, blockers, and follow-up work.

No schema changes were required; the existing `SolverResult` / `CandidateLabel` / `VisibleState` / `Context` contract already supports the new fields.

## 2. Consumer Inventory

| Area | Module(s) | F02 types used | Status |
|------|-----------|----------------|--------|
| Simulator | `dc_sustainability/simulator/core.py` | `VisibleState`, `Context`, `ApprovedActions`, `EpisodeResult` | Accepted — covered by `tests/simulator/test_core.py`, `tests/e2e/test_s02_receiving.py` |
| Knowledge | `dc_sustainability/knowledge/retrieval.py` | `Context` | Accepted — covered by `tests/knowledge/test_retrieval.py` |
| Verification | `dc_sustainability/verification/checker.py` | `Plan`, `VisibleState`, `ConstraintSnapshot`, `Context` | Accepted — covered by `tests/verification/test_checker.py`, `tests/training/test_schedule_receiving.py` |
| Runtime | `dc_sustainability/runtime/controller.py` | `DecisionRecord`, `ApprovedActions` | Accepted — covered by `tests/runtime/test_controller.py`, `tests/runtime/test_policy_receiving.py` |
| Policies | `dc_sustainability/policies/greedy.py` | `VisibleState`, `Context`, `Plan`, `PolicyOutput` | Accepted — covered by `tests/policies/test_greedy_*.py`, `tests/e2e/test_p02*.py` |
| Reference solver | `dc_sustainability/reference/solver.py` | `VisibleState`, `Context`, `SolverResult` | **Accepted with new receiving tests** — see §3 |
| Reference labels | `dc_sustainability/reference/labels.py` | `VisibleState`, `Context`, `SolverResult`, `CandidateLabel` | **Accepted with test updates** — see §3 |
| Training collection | `dc_sustainability/training/collect.py` | `PrivateEpisode`, `Context`, `ApprovedActions` | Accepted — covered by `tests/training/test_collect.py` |
| Training features | `dc_sustainability/training/features.py` | `VisibleState`, `Context` | Accepted — covered by `tests/training/test_features.py` |
| Data scenarios | `dc_sustainability/data/scenarios.py` | `PrivateEpisode`, `Job`, `ConstraintSnapshot`, `CarbonObservation` | Accepted — covered by `tests/data/test_scenarios.py` |
| Data splits | `dc_sustainability/data/splits.py` | `SCHEMA_VERSION` | Accepted — covered by `tests/data/test_splits.py` |
| Data frontier | `dc_sustainability/data/frontier.py` | `SourceRef` | Accepted — covered by `tests/data/test_frontier.py` |
| Evaluation | `dc_sustainability/evaluation/validator.py`, `replay.py` | `SolverResult`, `VisibleState`, `Plan` | Accepted — covered by `tests/evaluation/test_validator.py`, `tests/evaluation/test_replay.py` |
| Runtime traces | `dc_sustainability/runtime/traces.py` | `TraceStore` | Accepted — covered by `tests/runtime/test_controller.py` |
| LLM policy | `dc_sustainability/llm/plain.py` | `VisibleState`, `Context`, `PolicyOutput` | Accepted — covered by `tests/llm/test_plain*.py` |

## 3. Changes Made

### 3.1 Reference solver (`dc_sustainability/reference/solver.py`)

Replaced the weighted-sum secondary tie-break with a **sequential variable-fixing lexicographic optimizer**:

1. After the primary carbon-minimization MILP proves optimality, constrain the primary objective to stay within `primary_objective + tolerance`.
2. Iterate candidates in lexicographic `(job_id, start_slot)` order.
3. For each candidate, solve a feasibility MILP with that candidate fixed to `1`.
4. If feasible, lock the candidate to `1` and forbid all other starts for the same job; otherwise skip it.
5. The final locked selection is the deterministic canonical schedule.

This guarantees true lexicographic ordering. The previous weighted-sum approach with base `n+1` failed on uniform-carbon fixtures (selected `(J1@4, J2@2)` instead of `(J1@0, J2@2)`), as demonstrated by the new brute-force oracle tests.

Also increased objective/bound/gap reporting precision from 6 to 9 decimal places so near-tie schedules (differences < 1e-6 kg) compare correctly against the oracle.

**Audit fix:** when the freshness constraint is missing, `_max_age_seconds()` now raises `_MissingFreshnessError`, `_build_vars()` keeps `max_age = None`, and `solve()` reports `insufficient_evidence`. The code no longer falls back to `float("inf")`, which would have disabled stale-forecast checking.

### 3.2 Reference solver receiving tests (`tests/reference/test_solver.py`)

Added an independent brute-force oracle and oracle-based tests:

- `_emissions_kg`, `_feasible_schedules`, `_oracle_result` — independent enumeration helpers that do not use the MILP model.
- `test_hand_example_matches_brute_force_oracle` — MILP matches oracle on the hand fixture.
- `test_capacity_infeasibility_matches_oracle` — both solver and oracle report `certified_infeasible`.
- `test_nonflexible_job_matches_oracle` — both report infeasibility for a missed non-flexible arrival.
- `test_empty_waiting_jobs_matches_oracle` — empty schedule agreement.
- `test_tie_break_prefers_lower_job_id_start_slot` — uniform carbon resolves to lexicographically earliest schedule.
- `test_near_tie_prefers_lower_carbon` — schedules differing by < 1e-7 kg resolve to the lower-carbon schedule.
- `test_missing_freshness_constraint_is_insufficient_evidence` — missing freshness evidence returns `insufficient_evidence`.
- `test_stale_forecast_is_insufficient_evidence_oracle` — stale forecasts return `insufficient_evidence`.
- `test_missing_forecast_is_insufficient_evidence_oracle` — missing forecasts return `insufficient_evidence`.

Existing tests were updated to pass `decision_time_utc` and assert `backend_version`, `time_limit_s`, `elapsed_s`, `gap`, and `bound_kg`.

**Audit fix:** `_feasible_schedules` now computes running/background load inline from `state.site.background_kw`, `state.completed_jobs`, and any `start_slot` on waiting jobs, rather than importing `_running_load`/`_window` from `training.features`. This keeps the oracle independent of solver-internal helpers.

### 3.3 Reference label tests (`tests/reference/test_labels.py`)

Updated 5 call sites to pass `decision_time_utc=_decision_time(state.current_slot)` so label generation continues to receive an explicit trusted decision time.

**Audit additions:**
- `test_labels_from_solver_result_rejects_missing_decision_time` — proves `labels_from_solver_result` raises `ValueError` when `decision_time_utc` is missing or naive.
- `test_label_decision_requires_collected_decision_time` — proves `label_decision` propagates the explicit UTC timestamp from `CollectedDecision` through to the solver.

### 3.4 Production code touched

- `dc_sustainability/reference/solver.py` — sequential lexicographic tie-break, 9-decimal objective reporting, tightened missing-freshness handling.
- `dc_sustainability/reference/labels.py` — already forwarded `decision_time_utc` to `solve_visible`; no further changes.

No schema changes were made.

## 4. Validation Results

| Suite | Result |
|-------|--------|
| `tests/reference/test_solver.py` + `tests/reference/test_labels.py` | **34 passed** |
| `tests/reference/` + `tests/contracts/` | **202 passed** |
| `ruff check dc_sustainability/reference tests/reference` | **passed** |
| `ruff format --check dc_sustainability/reference tests/reference` | **passed** |

> Note: the full-suite run from the original F02 acceptance pass is still valid for the rest of the codebase; only the solver/label surface changed in this follow-up.

## 5. Blockers / Follow-up

- **None blocking.** The F02 downstream interface is accepted on this branch and the O01 reference-solver tie-break correctness gap is closed.
- **Final audit commit:** `f64d91d` on `ved/f02-downstream-acceptance`.
- **Note:** `docs/handoffs/D04_DEVELOPMENT_FOLD_MAP_102.md` and `data/D02_CALIBRATION.md` are flagged by `ruff format` as unformatted Markdown, but they are pre-existing and unrelated to F02.
- **Future work:** If additional consumers (e.g., a new policy or renderer) begin calling `solve_visible` directly, they must pass an explicit `decision_time_utc`; the contract test `test_solver_requires_decision_time_utc` now enforces this.
