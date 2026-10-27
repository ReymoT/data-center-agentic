# E01 agreed portion: completed work, units, energy basis

Task ID / Issue: E01, [issue #24](https://github.com/ReymoT/data-center-agentic/issues/24). Decisions: Ved's E01 quantity/unit/reference reply, Matty's and Edison's confirmations, and Nisha's strict energy-basis confirmation in #24; checkpoint October 27 recorded by Matty.
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk); technical contact Ved (vedp3705); Edison for the P01 facility-versus-IT distinction; Matty for coordination.
Objective: implement only the portion of E01 agreed in #24, with hand-truth tests.
Base commit / branch: base `96345d5` on main; branch `nisha/e01-agreed-portion`. Independent of the option B replay fix in PR #85.

Changed paths:
- `dc_sustainability/evaluation/claims.py`: per-unit tolerances, `stated_energy_basis`, `score_energy_claim`, `ScoreSummary` and `summarize`; the `unscored_unit` status is removed.
- `dc_sustainability/evaluation/replay.py`: `Replay.completed_job_count`, `WORK_UNIT`, `WORK_DEFINITION`, `WorkComparison`, `compare_completed_work`; `compare_result` reports a supplied `completed_work` instead of raising.
- `tests/evaluation/test_e01_agreed.py` (new, 31 tests); `tests/evaluation/test_claims.py` and `tests/evaluation/test_replay_review.py` updated for the agreed behavior.
- `docs/handoffs/E01_AGREED_PORTION.md` (this file).

What it does, item by item:
1. **Completed work.** `completed_job_count` (jobs whose occupancy ended by boundary 30) and `completed_it_energy_kwh` (power × duration × slot hours over completed jobs, before PUE) are separate quantities derived by job ID from the private episode and executed starts. Missed and unfinished jobs are listed separately with no credit. Nothing is imported from P01; facility energy stays separate.
2. **`completed_work`.** `compare_completed_work` returns `absent` when the field is None, the expected case for current runs. Any supplied value is `not_comparable`:
   - `mapping_differs` unless the unit is exactly `kWh` and the definition exactly `completed_it_energy_before_pue_v1` (this includes the F02 example definition);
   - `precision_not_agreed` for the agreed mapping, because the optional numeric precision is deferred (Ved, Matty). The recorded-minus-derived difference is kept separately and is never a pass; the 0.05 claim tolerance is not borrowed.
   `compare_result` adds a `completed_work` mismatch carrying the `WorkComparison`, so a supplied value never gets a clean result.
3. **Claim units.** kWh, kg, kW and g/kWh: absolute difference ≤ 0.05, inclusive, compared on decimal representations with no extra epsilon. slot and h: exact, so the claim must equal the whole-number reference (4.0 equals 4; 4.04 and 4.5 are incorrect); a fractional slot/h reference is a caller error. Percentages: F02 `Unit` has no percent, so a percentage is never a numeric claim here; it stays with the separately reported manual E04 review.
4. **Strict energy basis.** A kWh claim is scored only on the basis its text or cited evidence identifies: "IT", "before PUE", "excluding PUE" or "without PUE" for IT energy; "facility", "including PUE", "with PUE" or "after PUE", or citing `FACT-SITE-PUE`, for facility energy. "IT" is case-sensitive, so the pronoun "it" never names a basis. Neither or both → `basis_unstated` (unsupported), even if the value matches one basis. A stated basis is compared only with that basis's reference; matching the other basis never rescues it. `score_energy_claim(claim, it_kwh=..., facility_kwh=...)` picks the reference; `score_numeric_claim` refuses a kWh reference without its basis.
   - One reading to confirm: Nisha's #24 note said a claim citing the PUE fact identifies facility energy "and its value matches the facility basis". Ved's and Matty's later wording (stated basis checked only on that basis; a contradicted stated-basis claim is contradicted) is implemented: citing the PUE fact states the facility basis, and a non-matching value is then incorrect, not unstated.
5. **Counting.** `summarize` reports total, correct, incorrect and every other status by name (`not_numeric`, `reference_unavailable`, `unit_mismatch`, `basis_unstated`). `correct_of_all` counts unscored claims in the denominator, so they are never treated as correct; `correct_of_scored` is reported alongside it.

Not in this change: the closed reference-kind list and the energy-basis worked examples belong in `docs/e04/EXTRACTION_RULE.md` before freeze (E04); savings comparability is E03 (#61); arrival option B is PR #85; Q08 and real saved-output acceptance stay open. No F02 schema, setting, prompt or other owner's module changed.

Input and output contract/config versions: F02 1.0.0, unchanged.
Artifact locations and checksums: none.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/evaluation -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability tests
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m pip check
```

Tests actually run and observed results: Windows 11, Python 3.12.10, hashed lock. Full suite 1,349 tests and 19 subtests passed (1,325 on main before); all 182 evaluation tests pass. Ruff check/format, compileall, setup validation and pip check passed.
- Mutation check: six deliberate bugs each made tests fail, and the code was restored: accepting an unstated basis, an extra 1e-6 epsilon, scoring slots with the 0.05 tolerance, ignoring the PUE citation, counting unscored claims as scored, and letting the agreed completed_work mapping pass clean.

Supersedes: the `unscored_unit` line in `E01_PREPARATION.md` (kW, g/kWh, slot and h are now scored).
Receiving owner and consumer check: Ved, to confirm the unit and basis implementation matches his #24 decisions; Matty, for receiving review.
Next checkpoint: E03 comparison (#61) on November 2.
