# Q10 deterministic sampling for the manual explanation review

Task ID / Issue: Q10 / E04, [issue #22](https://github.com/ReymoT/data-center-agentic/issues/22). Rule: Ved's A3 sampling frame and A2 seeds, confirmed by Nisha and accepted by Matty. The separate abstention-boundary stratum (Nisha's proposal, agreed by Matty and Ved on October 26–30) is implemented as `select_boundary`; see the November 9 update below.
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk); Ved (vedp3705) and Matty (MattyAnd) as affected consumers; Reimo for the frozen D04 manifest.
Objective: select the manual-review decision slots from the frozen run manifest, deterministically and from exogenous inputs only, before any held-out output is opened.
Base commit / branch: reconciled with main `b702fc4`; branch `nisha/q10-sampling`. October 30 checkpoint.

Changed paths:
- `dc_sustainability/evaluation/sampling.py` (new).
- `tests/evaluation/test_sampling.py` (new, 12 tests).
- `docs/handoffs/Q10_SAMPLING.md` (this file).

What it does:
- `latest_start(job)` = `min(deadline_slot, 30) - duration_slots`, capped at `arrival_slot` for a nonflexible job. `eligible_slots(episode)` is every slot t in 0–23 with `arrival_slot <= t <= latest_start` for at least one job. Capacity, forecasts, actual queues and either system's outputs are never read; the module imports only F02 schemas, and a test enforces that.
- `select(episodes, seed=20261019)` picks two distinct eligible slots per episode with `random.Random(seed)` (MT19937), processing episodes by (stratum, episode ID) so input order does not matter. Stratum is `scenario_id|forecast_visibility`.
- Trials 0–2 are rotated through each stratum in turn after a seeded shuffle, so trial counts differ by at most one within every stratum and overall (20/20/20 for 60 selections).
- An episode with fewer than two eligible slots is recorded in `shortfall`; nothing is borrowed from other episodes and the target is not lowered.
- The `SamplingRecord` keeps the algorithm name, generator, Python version, both seeds (selection 20261019, analysis 20261020), a manifest hash, every episode's eligible slots, the selections, shortfall and counts by trial and stratum. `to_jsonable()` gives the private record to save.
- `pair_record(selection, {"agent": state, "plain_llm": state})` records, after the run, both actual queue counts and state hashes. An empty queue never drops the pair: that side is listed in `not_applicable`, and `both_nonempty` marks the both-nonempty reporting stratum.

Tests (synthetic manifests): arrival boundary; latest legal start; first slot after it; nonflexible arrival-only; impossible window; slot 23 and boundary 30 (including a deadline after 30); union of windows and timing-only eligibility with a capacity-infeasible job; 60 selections, two distinct eligible slots per episode, 20 per trial and per-stratum balance; determinism and input-order independence; shortfall without top-up; inconsistent manifests refused; one or both actual queues empty; pair/state mismatch refused; no imports of outputs, runtime or policies.
- Mutation check: five deliberate bugs each made tests fail, and the code was restored: no nonflexible cap, window one slot late, ignoring boundary 30, an extra slot per episode and no trial balance.

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

Tests actually run and observed results after current-main reconciliation: Windows 11, Python 3.12, existing hashed environment. All 12 focused sampling tests and the full suite of 1,468 tests plus 19 subtests passed. Ruff check/format, compileall and setup validation passed. The first full-suite attempt inside the managed Windows sandbox was invalid because local sockets and pytest temporary symlinks were blocked; the same suite passed outside that restriction.

Limitations and open decisions:
- Not a frozen sample. Freezing needs the final D04 held-out manifest (Reimo) and the E04 rule/adjudication gates. The abstention-boundary stratum is separate from `select()` and never changes it (November 9 update below).
- The trial-rotation allocation and tie order are this implementation's choice under the coder-owned rule; they are recorded here and in the record so they can be frozen before any held-out output is opened.
- The paired bootstrap (seed 20261020) is not implemented here; only its seed is recorded with the selection.
- The generator is Python's `random.Random`; its sequence is stable across CPython versions for `sample` and `shuffle` on the same inputs, and the Python version is recorded in case it is not.

Receiving owner and consumer check: Ved and Matty, to confirm the implementation matches A3 and to agree the boundary stratum; Reimo, for the manifest format when D04 is published.
Next checkpoint: run `select` on the frozen held-out manifest once it exists, save `to_jsonable()` privately with its hash, and only then open held-out outputs.

## November 9 update: abstention-boundary stratum

Agreement: [Nisha's proposal](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6427144022), Matty's recommendation and [Ved's agreement](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6514242366) on #22. Ved asked that it stay non-executable until implemented and accepted by the affected owners; this delivery is that implementation, for Matty's and Ved's acceptance.

- `boundary_slots(episode)`: decision slots 0–23 where a job arrives with no legal start by timing alone: no s with `arrival_slot <= s <= 23` and `s + duration_slots <= min(deadline_slot, 30)`; a nonflexible job may start only at arrival. Capacity, forecasts, queues and outputs are never read.
- `select_boundary(episodes)`: every qualifying slot, or 30 drawn with the separate seed 20261021 when more qualify. The record keeps the eligible and selected counts, the manifest hash and the selections.
- It never replaces or tops up the primary sample, and `select()` is unchanged. A slot is in both only if it qualifies for both. Results are reported separately; failures, malformed or missing outputs and one-sided no-ops are kept, as in the primary frame (`pair_record`).
- **Implementation choice for acceptance:** the agreement did not say which trial a boundary slot is reviewed in. Trials are rotated within each scenario/forecast stratum exactly as in the primary sample, using the stratum's own seed 20261021.

Tests: 7 new in `tests/evaluation/test_sampling.py` (19 in total): impossible arrival in the stratum and not the primary frame; feasible, capacity-only and after-slot-23 arrivals excluded; nonflexible and boundary-30 cases; a slot in both frames only when it qualifies for both; census up to 30 with balanced trials; a 30-slot draw from 40 that is deterministic, order-independent and seed-specific; and the primary sample unchanged. No held-out manifest exists, so nothing is selected or frozen.
