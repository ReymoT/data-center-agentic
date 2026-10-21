# E01 independent episode replay

Task ID / Issue: E01, [issue #24](https://github.com/ReymoT/data-center-agentic/issues/24) (independent episode/state replay item). Rules from [issue #7](https://github.com/ReymoT/data-center-agentic/issues/7) as recorded in [Q01-Q04 status](../decisions/Q01_Q04_AGREEMENT_STATUS.md).
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk); technical contact Ved (vedp3705); Reimo for S01 consumer questions; Matty for runtime traces.
Active assistant session / instruction version: one Claude Code session for Nisha; instruction deployment 1.14.
Objective: Rebuild each slot's state from a private episode and the starts that were actually executed, independently of the simulator, so simulator or trace defects show up as mismatches.
Base commit / branch / PR: base `b06cda7` on main; branch `nisha/e01-episode-replay`; [PR #28](https://github.com/ReymoT/data-center-agentic/pull/28).

Changed paths:
- `dc_sustainability/evaluation/replay.py` (new): `replay_episode`, `executed_starts`, `compare_result`, `compare_state` and `Replay.state_at`.
- `tests/evaluation/test_replay.py` (new, 22 tests).
- `docs/handoffs/E01_REPLAY.md` (this file).

What it does:
- `replay_episode(episode, executed, protocol)` walks boundaries 0-30. At each boundary it retires finished work, marks missed jobs, lists waiting jobs, then applies that slot's executed starts and records started/running/completed IDs and job load.
- `executed_starts(records, episode_id)` collects executed starts by slot from one run's `DecisionRecord`s. Records from another episode, mixed runs/systems/trials, or two records for one slot are refused as trace defects.
- `compare_result` and `compare_state` list every place a recorded `EpisodeResult` or `VisibleState` differs from the replay. Nothing recorded is used as truth or corrected.
- `Replay.state_at(t)` gives the replayed visible state, so `validator.facts_from_state` and `validate_plan` can judge a decision against replayed state rather than the state the runtime supplied.
- Completed work follows Q03.5: completed job IDs and completed IT energy (power Ãƒâ€” duration Ãƒâ€” slot hours, before PUE). Missed and unfinished jobs earn no credit; missed jobs are also listed as unfinished.

Rules applied (from the shared rules, S01 handoff text and `Q03_DRAFT`, not from simulator code):
- Occupancy is `[start, start + duration)`; a job completes at boundary `start + duration`; everything ends by boundary 30.
- New starts only through slot 23 (Q01).
- A waiting job is missed at the first boundary where no legal start remains (deadline, slot 23, boundary 30, nonflexible at arrival). A job already impossible when it arrives is missed at its arrival boundary, as the S01 handoff states. Consequence: such a job is never shown as waiting, so a policy never gets to abstain from it in a simulated run. Per-decision abstention credit for it is only exercised through supplied states (Q02 allows either an abstention or a deadline-miss record).
- An executed start for an unknown job, a job that is not waiting (not arrived, running, completed, missed or started twice in one slot), or with a start slot different from its decision slot is reported and not applied, because that job cannot have run then.
- An executed start that overloads capacity is applied, because the job did run, and every overloaded slot is reported. Capacity is the strict limit (exact 100 kW passes, 100.0000000001 kW fails). A start without a capacity constraint is reported as unverifiable.
- Load comparisons with recorded values allow only float-summation differences (relative 1e-12); this is a reporting comparison, never a feasibility boundary.

Independence: `replay.py` imports only F02 schemas and E01's own validator (`Protocol` and its legal-start rule). It does not import `verification`, `simulator`, `metrics`, `policies` or `runtime`; a test enforces this. The simulator appears only in one consumer test.

Input and output contract/config versions: F02 1.0.0, unchanged. No schema, setting, prompt or other owner's module changed.
Artifact locations and checksums: none.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/evaluation/test_replay.py -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m pip check
```

Tests actually run and observed results: Windows, Python 3.12.10, hashed lock. 928 tests and 19 subtests passed (906 on main before, 22 new); all 112 evaluation tests pass. Ruff check/format, compileall, setup validation and pip check passed.
- Hand truth: boundary states and slot outcomes for the hand schedule (J1@0, J2@2; J3 missed on arrival at 4; 140 kWh completed IT energy, unchanged at PUE 1.2), missed timing after the last legal start, Q01 slot-24 miss, nonflexible miss, capacity overlap (110 kW in slots 0 and 1), exact-capacity boundary, impossible executions, missing capacity, and result/state mismatches.
- S01 consumer check: a greedy driver over the four D03 scenarios Ãƒâ€” 3 seeds, including a batch the simulator rejects. The replay found no findings and no mismatches with the simulator's `EpisodeResult` or any decision-slot `VisibleState`.
- Mutation check: five deliberate bugs (missed one slot late, non-strict capacity, completion one slot late, duplicate starts allowed, PUE in completed energy) each made tests fail; the code was restored afterward.

Limitations and open decisions:
- Not E01 acceptance. Edison's Q01-Q04 reply, joint infeasibility/Q08, claim units/reference selection and Q10 remain open in #24.
- No real saved run exists yet. The consumer check uses synthetic `ApprovedActions` and a test driver, not the runtime, gate or any policy.
- Forecasts are not part of the episode; `state_at` takes them from the caller.
- Energy and emissions per slot are not compared, because S02/P01 do not supply them yet.

Receiving owner and consumer check: Reimo, to confirm the replay's reading of S01 timing (especially miss-on-arrival); Matty, to confirm `DecisionRecord.executed_starts` is the trace field E02/I01 will save; Ved, to review the independence boundary.
Next checkpoint: run the replay over the first real saved development run once the runtime writes `DecisionRecord`s and `EpisodeResult`s, keeping every finding and mismatch.

## Matty review addendum

Matty explicitly requested review and merge if sound. Nine hand-derived regressions reproduced missing authoritative site/snapshot/visible-constraint comparison, contradictory/unknown job-constraint input, nonhourly input and unverified completed-work scalar handling. The bounded fixes preserve raw F02, independent logic and Nisha's original commits. All 121 focused evaluation tests pass after correction.

Comparison scope is explicit: job-state/identity/load structure is checked; forecast issuance and mutation-version history are not derivable from executed starts alone. Per-slot/total energy/emissions remain outside this structural comparison. A supplied completed_work scalar raises an explicit unverified-mapping error until the unit/definition/reference mapping is agreed; no arbitrary numeric truth is selected. The separate derived completed-job IDs and before-PUE IT energy remain available. Illegal unknown/nonwaiting/slot-mismatched starts are reported and omitted under the existing draft reconstruction; this is not a physical reconstruction of arbitrary corrupt executions. Full scientific acceptance remains open.

The missed-on-arrival question remains with Reimo/protocol agreement. Matty confirmed the existing DecisionRecord.executed_starts field as actual confirmed execution, not proposed future starts. A04/E02 real persistence and saved-output validation remain future work. Final current-base full checks and merge/CI evidence are recorded in PR #28 and issue #24 after execution.

Current-base review validation before L01 merge: all 949 tests and 19 subtests passed; all 121 evaluation tests passed; Ruff lint/format (65 files), setup/links/version/task/policy checks and whitespace passed. The nine new regressions failed against the original implementation and pass after correction. No production-checker/simulator/impact import was added.
