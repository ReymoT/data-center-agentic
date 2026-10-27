# E03 equal-work savings comparison

Task ID / Issue: E03, [issue #61](https://github.com/ReymoT/data-center-agentic/issues/61). Rule: Nisha's proposal, agreed by Reimo (with conditions 4 and 5), Ved and Edison; Matty's request for implementation and tests.
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk); Reimo for S01/S02, Ved for reference comparisons, Edison for P01.
Objective: give a savings or exact-gap value between two paired runs only when they did the same work under the same inputs; otherwise block it with every reason recorded, never as zero savings.
Base commit / branch: base `8eb3682` on main; branch `nisha/e03-equal-work-comparison`. November 2 checkpoint.

Changed paths:
- `dc_sustainability/evaluation/comparison.py` (new): `Run`, `compare_savings`, `SavingsComparison`, `WorkCounts`, `summarize`, `ComparisonSummary`.
- `tests/evaluation/test_comparison.py` (new, 12 tests).
- `docs/handoffs/E03_EQUAL_WORK_COMPARISON.md` (this file).

What it does:
- `compare_savings(baseline, candidate)` takes two `Run`s (system, trial, and E01's independent `Replay` of that run's executed starts). The baseline is always named. It is **comparable** only when all of these hold; otherwise it is **blocked** with every failed reason, in this order:
  1. `completed_set_differs`: completed job-ID sets differ;
  2. `unfinished_set_differs`: unfinished or deadline-missed job-ID sets differ (no exemption for missed-on-arrival jobs);
  3. `inputs_differ`: the private episodes differ by canonical hash (episode, site including PUE, capacity, jobs, horizon and realized carbon), or the replay protocol, slot count or trial index differs;
  4. `unfinished_job_occupied`: an unfinished job has executed occupancy in either replay;
  5. `carbon_missing`: a realized carbon value either run's completed work needs is absent. Nothing is filled in.
- Emissions are E01's own arithmetic (`claims.schedule_emissions_kg`, job load with PUE, background excluded) on private realized carbon at the replayed starts. A blocked comparison has `savings_kg = None`, never 0.
- Every comparison carries completed, unfinished and missed counts for both runs. `summarize` gives total, comparable and blocked counts and the count per reason (a comparison blocked for two reasons counts under both).
- With equal completed and unfinished sets on the same episode, background energy and emissions are identical in both runs, so job emissions give the exact savings.

Not changed: the strict S02 savings helper and P01, which are not imported (a test enforces this). `claims.compare_emissions` stays as E01's simpler claim-level check. No F02 schema or setting changed.

Tests (hand truth): the hand schedules give 54.5 kg and 48.4 kg, savings 6.1 kg, with both runs missing impossible J3 (the infeasible-scenario case is comparable); less completed work is blocked with `savings_kg` None; a different trial, PUE, capacity record, realized carbon or protocol is `inputs_differ`; an unfinished job shown running in a hand-edited trace is `unfinished_job_occupied`; a missing realized slot is `carbon_missing` with no emissions reported; several reasons recorded together; summary counts; no imports of P01, S02, the simulator, policies or runtime.
- Mutation check: six deliberate bugs each made tests fail, and the code was restored: blocked reported as zero savings, trial pairing ignored, no occupancy check, missing carbon swallowed, only the episode ID compared, wrong emissions arithmetic.

Input and output contract/config versions: F02 1.0.0, unchanged.
Artifact locations and checksums: none.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/evaluation/test_comparison.py -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe scripts/validate_setup.py
```

Tests actually run and observed results: Windows 11, Python 3.12.10, hashed lock. Full suite 1,368 tests and 19 subtests passed (1,356 on main before); Ruff check/format, compileall, setup validation and pip check passed.

Limitations and open decisions:
- A replay with findings (for example a capacity overload that did execute) is still compared, because the agreed rule has no reason for it; its findings stay on the `Replay`. Raise it in #61 if it should block.
- `unfinished_job_occupied` cannot arise from the replay of legal starts under the current rules; it guards traces and future rule changes, and is tested on a hand-edited trace.
- No real saved runs exist yet. Episode tables and the paired bootstrap are later E03/E02 work.

Receiving owner and consumer check: Reimo and Ved, to confirm the conditions match their #61 agreements; Matty, for receiving review.
