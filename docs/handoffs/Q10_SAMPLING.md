# Q10 deterministic sampling for the manual explanation review

Task ID / Issue: Q10 / E04, [issue #22](https://github.com/ReymoT/data-center-agentic/issues/22). Rule: Ved's A3 sampling frame and A2 seeds, confirmed by Nisha and accepted by Matty; Nisha's abstention-boundary stratum proposal (pending Ved).
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk); Ved (vedp3705) and Matty (MattyAnd) as affected consumers; Reimo for the frozen D04 manifest.
Objective: select the manual-review decision slots from the frozen run manifest, deterministically and from exogenous inputs only, before any held-out output is opened.
Base commit / branch: base `96345d5` on main; branch `nisha/q10-sampling`. October 30 checkpoint.

Changed paths:
- `dc_sustainability/evaluation/sampling.py` (new).
- `tests/evaluation/test_sampling.py` (new, 14 tests).
- `docs/handoffs/Q10_SAMPLING.md` (this file).

What it does:
- `latest_start(job)` = `min(deadline_slot, 30) - duration_slots`, capped at `arrival_slot` for a nonflexible job. `eligible_slots(episode)` is every slot t in 0–23 with `arrival_slot <= t <= latest_start` for at least one job. Capacity, forecasts, actual queues and either system's outputs are never read; the module imports only F02 schemas, and a test enforces that.
- `select(episodes, seed=20261019)` picks two distinct eligible slots per episode with `random.Random(seed)` (MT19937), processing episodes by (stratum, episode ID) so input order does not matter. Stratum is `scenario_id|forecast_visibility`.
- Trials 0–2 are rotated through each stratum in turn after a seeded shuffle, so trial counts differ by at most one within every stratum and overall (20/20/20 for 60 selections).
- An episode with fewer than two eligible slots is recorded in `shortfall`; nothing is borrowed from other episodes and the target is not lowered.
- The `SamplingRecord` keeps the algorithm name, generator, Python version, both seeds (selection 20261019, analysis 20261020), a manifest hash, every episode's eligible slots, the selections, shortfall and counts by trial and stratum. `to_jsonable()` gives the private record to save.
- **Abstention-boundary stratum (proposed in #22, pending Ved):** arrival slots of jobs with no permissible window (`latest_start < arrival_slot`), as a census in canonical order with rotated trials. If more than 30, a fixed subset of 30 is drawn with seed 20261021. It is stored separately in `record.boundary`, never mixed into or used to fill the primary selections. A job that fails only on capacity is not in it.
- `pair_record(selection, {"agent": state, "plain_llm": state})` records, after the run, both actual queue counts and state hashes. An empty queue never drops the pair: that side is listed in `not_applicable`, and `both_nonempty` marks the both-nonempty reporting stratum.

Tests (synthetic manifests): arrival boundary; latest legal start; first slot after it; nonflexible arrival-only; impossible window; slot 23 and boundary 30 (including a deadline after 30); union of windows and timing-only eligibility with a capacity-infeasible job; 60 selections, two distinct eligible slots per episode, 20 per trial and per-stratum balance; determinism and input-order independence; shortfall without top-up; inconsistent manifests refused; the boundary stratum kept apart, as a census and capped at 30; one or both actual queues empty; pair/state mismatch refused; no imports of outputs, runtime or policies.
- Mutation check: six deliberate bugs each made tests fail, and the code was restored: no nonflexible cap, window one slot late, ignoring boundary 30, an extra slot per episode, no trial balance, no boundary cap.

Input and output contract/config versions: F02 1.0.0, unchanged. No schema, setting, prompt or other owner's module changed.
Artifact locations and checksums: none. No real manifest exists yet; the record is not frozen.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/evaluation/test_sampling.py -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe scripts/validate_setup.py
```

Tests actually run and observed results: Windows 11, Python 3.12.10, hashed lock. Full suite 1,332 tests and 19 subtests passed (1,318 on main before); Ruff check/format, compileall, setup validation and pip check passed.

Limitations and open decisions:
- Not a frozen sample. Freezing needs the final D04 held-out manifest (Reimo), Ved's agreement on the boundary stratum, and the E04 rule/adjudication gates.
- The trial-rotation allocation and tie order are this implementation's choice under the coder-owned rule; they are recorded here and in the record so they can be frozen before any held-out output is opened.
- The paired bootstrap (seed 20261020) is not implemented here; only its seed is recorded with the selection.
- The generator is Python's `random.Random`; its sequence is stable across CPython versions for `sample` and `shuffle` on the same inputs, and the Python version is recorded in case it is not.

Receiving owner and consumer check: Ved and Matty, to confirm the implementation matches A3 and to agree the boundary stratum; Reimo, for the manifest format when D04 is published.
Next checkpoint: run `select` on the frozen held-out manifest once it exists, save `to_jsonable()` privately with its hash, and only then open held-out outputs.
