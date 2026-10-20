# E01 preparation: Matty's merge review

Owner: Nisha (nkolekar-nk); technical contact Ved (vedp3705), Matty for A03 compatibility. [PR #23](https://github.com/ReymoT/data-center-agentic/pull/23), [acceptance issue #24](https://github.com/ReymoT/data-center-agentic/issues/24). Reviewed original head f5a2542c1816ed0f34d8f784053453ae9b26c1f6 against current main 7d988f082c02d4ca3b35e28feeeecc49c166f974, instruction deployment 1.14, F02 1.0.0.

Authority: Matty explicitly requested reviewing nisha/e01-independent-validator, merging it and deleting its branch. [The review scope/owner notification](https://github.com/ReymoT/data-center-agentic/issues/24#issuecomment-6299147677) records the bounded cross-owner corrections before editing. Original Nisha commits are preserved; current main is deliberately merged into the review branch. No shared schema, setting, dependency lock or instruction policy changes. This merges implemented preparation, not full E01 or scientific protocol acceptance.

## Findings and fixes

- Removed the unagreed 1e-9 kW margin in both plan capacity and abstention feasibility. Background 40 + J1 40 + EPS 20.0000000001 exceeds 100 and must be invalid. Exact 100 remains allowed. This preserves the authoritative physical limit, without choosing a new numerical tolerance.
- Revalidate state/snapshot/plan/output/check/claim F02 structure at public record boundaries. Modified model_copy/model_construct records cannot silently collapse duplicate jobs or introduce NaN capacity, booleans or fractional starts. Malformed typed records raise ValueError; score missing/malformed/error PolicyOutput envelopes through validate_output, where they remain invalid.
- Independently derive visible constraint IDs and check arrival/deadline/nonflexible constraints against raw jobs. Contradictory evidence is refused; production Context/checker helpers do not establish E01 truth.
- Bind checker comparisons to episode/slot/state version/plan hash using internal optional ValidationResult.decision_key metadata. Different or unbound records return not_comparable. Failed outputs without a plan have no bound comparison. This is not a canonical shared F02 format change.
- Remove the extra claim-tolerance epsilon. Decimal representations of recorded values implement the stated inclusive 0.05 kWh/kg boundary: 0.55 versus 0.5 is correct, 0.5500000001 is incorrect. No scientific tolerance is changed. Non-finite references remain unavailable; invalid carbon/emissions cannot become comparable savings.
- Enforce the proposal's fixed end at boundary 30 for starts, deferrals and feasibility search, independently of a job's later structural deadline. J@23 lasting eight slots is invalid even with deadline 40; J@22 lasting eight ends exactly at 30 and is allowed.
- Correct stale Issue/PR/Q03-status references. Preserve Nisha's historical test report and explicit pending joint-infeasibility/unit/reference limits. Updated README/architecture/coordination describes available per-decision preparation, not an integrated evaluator.

## Evidence

Added 35 hand-derived regression/intake cases: 28 review cases, two episode-boundary cases and five actual A03/E01 consumer cases. The defects were reproduced before the relevant fixes; initial test fixture enum/ID mistakes were corrected rather than attributed to production. All 90 focused E01 tests pass locally on Windows CPython 3.12.14 with the existing hashed environment.

Full local run: 905 passed, 19 subtests passed, one existing deep-JSON synthetic HTTP object test timed out. This same intermittent test behavior was already reproduced on unchanged main/E01 and recorded in the October 20 handoff. No HTTP test assertion/deadline or production transport is changed. Hosted exact-head CI must pass before merge, and exact main CI must pass before branch deletion. Final CI counts/commit and cleanup evidence are recorded in issue #24, not fabricated here.

Ruff check/format (58 Python files), compileall, pip consistency, setup/link/policy validation and diff/whitespace checks pass. Canonical F02 Git blobs remain 41ab733816ac171fa283f75c5252c658025c124d (interface) and f139266bc9638208617e23c686ac97c442757fbf (schemas).

```powershell
.venv\Scripts\python.exe -m pytest tests/evaluation -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
.venv\Scripts\python.exe -m pip check
```

Tests/evaluation/test_a03_intake.py exercises actual A03 against independent hand expectations; production imports exist only in that consumer test, not evaluation implementations. E01 does not call checker/simulator/metrics/policies/runtime as truth. Otherwise feasible A03 unresolved errors remain not_comparable, never manufactured approval. The original pinned review script/evidence in main remains historical for f5a2542 and is not silently rewritten to claim fixed code had its old results.

## Remaining work

Issue #24 stays open for affected-owner Q01-Q04 agreement, joint-infeasibility/Q08 details, independent episode/state replay, unsupported claim units/reference selection (with Ved), Q10 review scope and actual saved policy-output evaluation. Nisha retains ownership. Full scientific correctness is not established by merged preparation or green CI. No model call, fake response, runtime execution, held-out result or source-license acceptance is claimed. Delete only a verified merged branch after main CI; preserve unrelated local worktrees/unpublished work. Matty records the final outcome and notifies Nisha/Ved in issue #24.
