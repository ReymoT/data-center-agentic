# E01 independent validator: first deliverable

Task ID / Issue: E01. No E01 Issue exists yet. The rules come from [issue #7](https://github.com/ReymoT/data-center-agentic/issues/7) (Q01-Q04).
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk); technical contact Ved (vedp3705); Matty for checker-disagreement cases.
Active assistant session / instruction version: one Claude Code session for Nisha; instruction deployment 1.13.
Objective: Judge each decision's validity, and the numbers in explanations, independently of the production checker.
Base commit / branch / PR: base `91eead1` on main; branch `nisha/e01-independent-validator`; PR not yet opened.

Changed paths:
- `dc_sustainability/evaluation/validator.py` (new): `facts_from_state`, `validate_plan`, `validate_output`, `compare_with_check`, and the explicit `Protocol` / `Q03_DRAFT` rule set.
- `dc_sustainability/evaluation/claims.py` (new): job energy and emissions from raw facts, `score_numeric_claim`, `compare_emissions`.
- `dc_sustainability/evaluation/__init__.py`: docstring only.
- `tests/evaluation/test_validator.py`, `tests/evaluation/test_claims.py` (new, 55 tests).

Independence: neither module imports `verification`, `simulator`, `metrics`, `policies` or `runtime`, and a test enforces this. Shared F02 schemas and fixtures are used as input records only. Capacity is read from the constraint records directly. A CheckResult is only compared with the validator's result, never used as truth.

Rules applied (`Q03_DRAFT`, status recorded on every result):
- Q01: no new start after slot 23. Agreed by Matty (proposer), Reimo and Ved; Edison pending.
- Q03.1 coverage: every waiting job exactly once; no running, completed, missed or unknown starts; a whole-decision abstention covers all; empty queue means a no-op.
- Timing: no start before the current slot or arrival; deadline is a completion boundary; nonflexible jobs start at arrival.
- Capacity: background + running + all planned starts in every occupied slot, including future intentions. A start without a capacity constraint is unverifiable, so the decision is invalid.
- Q03.2 deferral: valid only if a later legal start exists (≤ slot 23, meets the deadline; capacity ignored). Nonflexible jobs cannot be deferred.
- Q03.3 abstention: justified when capacity evidence is missing, or when no legal start fits even with no other new work. Missing carbon is never a justification.
- Failed outputs (`malformed`, `no_output`, `error`, missing) are invalid.
- Claims: 0.05 tolerance for kWh and kg. Savings only when both schedules completed exactly the same jobs over the same horizon and inputs.

Pending cases (status `pending`, neither pass nor fail):
- Abstaining from a job that fits alone but may not fit alongside other waiting jobs (`joint_infeasibility_not_assessed`). Q02/Q08 must define joint infeasibility.
- Claims in kW, g/kWh, slot or h (`unscored_unit`): no tolerance is agreed. The 0.05 percentage-point rule can't be applied yet because F02 `Unit` has no percentage unit.
- Matching a claim to the quantity it describes: F02 `Claim` has no quantity kind, so a reviewer chooses the reference (E04). A `claim_kind` field would need Ved's agreement.

Design choices to confirm with the team:
- Future intentions count toward capacity, so a plan whose later starts overlap past capacity is invalid.
- A citation to an unknown evidence ID is recorded as a note for E04 and does not change validity.

Input and output contract/config versions: F02 1.0.0. No schema, setting, prompt or other owner's module changed.
Artifact locations and checksums: none.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/evaluation -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m pip check
```

Tests actually run and observed results: Windows, Python 3.12.10, hashed lock. 871 tests and 19 subtests passed (816 before, 55 new). Ruff check/format, compileall, setup validation and pip check passed. Mutation check: six deliberate bugs were injected (capacity tolerance, deadline, last-start window, omission check, infeasibility verdict, running load). Each made the tests fail, and the code was restored afterward. Expected values are hand-derived: 54.5 kg and 48.4 kg for the proposal's hand schedules, 110 kW overloads, and the D03 generator's `intentionally_infeasible` labels matched by independent arithmetic over 4 scenarios × 10 seeds.

Limitations and open decisions:
- Not E01 acceptance. Matty and Edison still have to agree Q03, the decision must be recorded, and the pending cases must be resolved.
- Validates one decision from a supplied state. Rebuilding the state independently from a private episode plus executed starts (to catch simulator disagreements) is the next step.
- No run over real policy outputs yet, because no policy produces traces yet.

Receiving owner and consumer check: Ved, to review the independence boundary and the `claim_kind` question; Matty, to compare `compare_with_check` results against A03 on shared cases; Edison, to cross-check the emissions arithmetic against P01 once it exists.
Next checkpoint: open the PR and an E01 Issue, then add episode replay and the remaining Q03 boundary cases after the decision is recorded.
