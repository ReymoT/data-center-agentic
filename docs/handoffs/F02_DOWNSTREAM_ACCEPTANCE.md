# F02 Downstream Interface Acceptance Handoff

**Status:** Bounded downstream acceptance (with solver/label receiving tests added)
**Branch:** `ved/f02-downstream-acceptance`
**Date:** 2026-10-30
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

### 3.1 Reference solver receiving tests (`tests/reference/test_solver.py`)

Added 10 new receiving tests and extended 4 existing ones to exercise the F02 `SolverResult` contract surface:

- `test_solver_requires_decision_time_utc` — proves the solver rejects calls without an explicit trusted UTC time.
- `test_solver_rejects_naive_decision_time` — proves timezone-aware UTC enforcement.
- `test_stale_forecast_is_insufficient_evidence` — a physically feasible start with stale carbon forecast returns `insufficient_evidence`, not `certified_infeasible`.
- `test_missing_forecast_is_insufficient_evidence` — a job whose only feasible starts need missing forecasts returns `insufficient_evidence`.
- `test_physical_capacity_infeasibility_is_certified` — capacity infeasibility is `certified_infeasible`.
- `test_empty_waiting_jobs_is_optimal` — empty visible horizon is `certified_optimal` with zero objective.
- `test_nonflexible_job_requires_arrival_start` — non-flexible job missing its arrival start is `certified_infeasible`.
- `test_solver_populates_gap_and_bound` — `gap` and `bound_kg` are populated on optimal solves.
- `test_solver_timeout_is_unresolved` — tiny time limit produces `unresolved`.
- `test_tie_break_is_deterministic` — the pinned backend and stable candidate order
  repeat the same equal-cost schedule. This does not freeze the final Q08 scientific
  tie-break rule.
- `test_solver_input_hash_matches_context` — `input_hash` equals `context.content_hash`.

Existing tests were updated to pass `decision_time_utc` and assert `backend_version`, `time_limit_s`, `elapsed_s`, `gap`, and `bound_kg`.

### 3.2 Reference label tests (`tests/reference/test_labels.py`)

Updated 5 call sites to pass `decision_time_utc=_decision_time(state.current_slot)` so label generation continues to receive an explicit trusted decision time.

### 3.3 Production code touched

- `dc_sustainability/reference/solver.py` — requires explicit `decision_time_utc`,
  distinguishes missing/stale evidence from physical infeasibility and reports
  elapsed/gap/bound values. Missing freshness evidence fails closed. Stable candidate
  order and the pinned backend are repeatable, but the final Q08 scientific tie-break
  rule remains open.
- `dc_sustainability/reference/labels.py` — forwards the collected decision time and
  requires replay/audit callers to provide an explicit trusted UTC decision time. It
  has no production dependency on test fixtures.

No schema changes were made.

## 4. Validation Results

| Suite | Result |
|-------|--------|
| `tests/contracts/test_schemas.py` | **168 passed** |
| `tests/reference/test_solver.py` | **16 passed** |
| `tests/reference/test_labels.py` | **7 passed** |
| Focused downstream set (`tests/reference/`, `tests/training/test_schedule_receiving.py`, `tests/runtime/test_policy_receiving.py`, `tests/e2e/test_p02a_receiving.py`, `tests/e2e/test_p02b_receiving.py`, `tests/e2e/test_s02_receiving.py`) | **62 passed** |
| Full suite (`pytest`) | **1615 passed, 10155 warnings, 19 subtests passed** |
| `ruff check .` | **passed** |
| `ruff format --check .` | **passed** (Python files only; 2 pre-existing Markdown files flagged) |

## 5. Blockers / Follow-up

- **No blocker for bounded development receiving.** The final Q08 scientific tie-break
  and source/scientific acceptance remain freeze items and are not settled here.
- **Note:** `docs/handoffs/D04_DEVELOPMENT_FOLD_MAP_102.md` and `data/D02_CALIBRATION.md` are flagged by `ruff format` as unformatted Markdown, but they are pre-existing and unrelated to F02.
- **Future work:** If additional consumers (e.g., a new policy or renderer) begin calling `solve_visible` directly, they must pass an explicit `decision_time_utc`; the contract test `test_solver_requires_decision_time_utc` now enforces this.

## 6. Commit Plan

Commit the four modified files to `ved/f02-downstream-acceptance`:

```text
dc_sustainability/reference/labels.py
dc_sustainability/reference/solver.py
tests/reference/test_labels.py
tests/reference/test_solver.py
```

Suggested message:

```text
F02: downstream acceptance for solver/label surface

- Add receiving tests for explicit decision_time_utc, freshness,
  infeasibility, gap/bound, deterministic tie-break, and input hash.
- Update label tests to pass explicit decision_time_utc.
- No schema changes; all F02 consumers pass.
```
