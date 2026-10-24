# S01 Option B and Q01 implementation handoff

Reimo-owned local change, October 24, 2026. No commit, push, Issue update or
teammate message was made. Branch: `feature/s01-scheduling-simulator`, base
`a1d848f`. Authoritative main fetched/read:
`bd805ff5bcbeb4b52698a0ad70772bd240d75176`, instruction deployment 1.25;
F02 contract 1.0.0. Local instruction copies are older (1.10) and were preserved;
main's published instructions governed this work. This supplements the historical
[S01 handoff](S01.md); its former arrival/completion-choice descriptions are
superseded for this implementation by the behavior below.

## Recorded agreement and scope

[Issue #7](https://github.com/ReymoT/data-center-agentic/issues/7), including
[Reimo's exact agreement](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6390021386),
records Option B, Q01 and Q04. Affected consumer replies include
[Nisha](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6352137381),
[Matty](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6354628267),
[Edison](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6373028481)
and [Ved](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6380268504).
Reimo's confirmation satisfies the simulator condition in their Option B replies.
This is implementation evidence, not independent receiving-owner acceptance.

Only simulator code, its tests and this handoff changed. No E2/E3/E4/E5/E03,
checker, evaluator, policy, D03 generator, F02 schema, shared instruction, setting
or dependency changes were made. Existing simulator/schema/generator files had no
difference from fetched main before this change; newer unrelated main work has
not been integrated into this older task branch.

## Implemented behavior

`_mark_missed()` now retains impossible deadline arrivals in waiting at their
arrival boundary, including reset at zero, and marks them missed at the next
boundary. Ordinary latest-start expiry is unchanged. Start validation still
rejects impossible intervals; one illegal start rejects all new starts, with no
new occupancy. Existing running work advances and completes normally. Missed jobs
remain unfinished and receive no completion credit.

Q01 is enforced unconditionally: starts only at 0–23, completion/accounting at
24–29, with all 30 SlotRecords retained. `allow_completion_starts=False` remains
accepted and required; `True` now raises ValueError at construction. Consumers
using True must switch to False; it no longer selects an alternative experiment.
A schema-valid seven-slot job starting at 23 can finish exactly at boundary 30
(the longer duration is a boundary test, outside D03's generated 1–4 durations).
Future plans remain intentions; the simulator accepts only current starts and
continues to require runtime-approved actions. It does not issue approvals or
interpret policy deferral/abstention records.

## Q04 inspection and consumer integration

Projection is unchanged. `reset(forecasts_by_slot=...)` validates supplied F02
CarbonForecast records, source resolution and each view's horizon; `state()`
exposes only that boundary's supplied batch. Visible slots are
`[t, min(t + 24, 30))`; absent entries appear in missing_carbon_slots. Private
realized carbon is never substituted. Withheld episodes still retain private
actuals and reject exposed forecasts. Issue times are preserved verbatim. No
carry-forward, age calculation or fallback is performed. There is no explicit
episode UTC origin in the current simulator API; freshness requires a consistent
trusted mapping from episode slots to UTC in the consumer/release layer.

Required downstream work, owned by the corresponding consumers:

- Matty's checker/runtime and Edison's policies must derive required coverage from
  the union of occupied slots of every otherwise-legal candidate start, using
  current visible state, running reservations, capacity and Q01 start limits.
  Do not truncate candidate windows to available forecasts. Detect required slots
  beyond the visible horizon separately from missing entries inside it.
- Check freshness against decision time: age exactly two slots is allowed;
  greater than two is stale and future-issued evidence is invalid. B/C/D need
  whole-decision checked-A fallback for missing/stale/future-issued/beyond-horizon
  coverage, with reasons and origin counts. Missing carbon is not physical
  infeasibility. This patch does not implement that consumer logic or change
  schemas to encode it.
- Policies/checker/context/reference consumers must account for the newly visible
  impossible arrival with justified per-job no_legal_start, never start/defer it,
  and continue covering feasible jobs. The simulator enforces executed starts,
  not proposal coverage. Arrival decisions are not empty-queue no-ops.
- Nisha's runner/evaluator must retain the arrival decision, next-boundary miss,
  no completion credit, all 24 decision outputs and all 30 accounting slots.
  Validators retain independent implementations. Completion slots cannot create
  new starts or model decisions. Ved's reference/context tests must use the same
  arrival and legal-start boundaries. No F02 migration is needed.

## Verification and remaining acceptance

Environment: existing `/private/tmp/s02-check-venv/bin/python` (Python 3.12).
Commands run from repository root:

```sh
python -m pytest tests/simulator tests/contracts -q
python -m pytest tests -q
python -m ruff check dc_sustainability scripts tests
python -m ruff format --check dc_sustainability scripts tests
python scripts/validate_setup.py
git diff --check
```

Focused: 211 passed. Full: 785 passed and 19 subtests passed, 3.35 seconds.
Ruff lint/format (43 files), setup validation and whitespace checks passed.
The sandboxed full attempt had 39 existing HTTP fixture errors because loopback
binding was denied; the permitted rerun passed. No model calls occurred. An older
S01 temporary environment lacked importable pytest, so the existing S02 check
environment was used. Initial regression fixture expectations were corrected for
ordinary misses and redundant constraint consistency before the final green runs.

Regressions cover impossible arrivals at 0/4/17, flexible/nonflexible impossible
jobs, mixed queues, no-start next-boundary misses, atomic rejection with unchanged
new occupancy and advancing running work, F02 JSON round trips, deterministic
30-slot replay, True rejection, slot 23/24 and finish-at-30 boundaries, explicit
forecast issue-time preservation and horizon projection. Existing expiry,
nonflexible, D03, capacity, visibility and F02 suites also pass.

Remaining acceptance: current-main integration and its full CI; Ved's independent
reproduction; actual checker/runtime/policy/reference/runner consumer regressions;
Q04 freshness/occupied-window fallback and recording in the owning components;
independent scientific evaluation and other separately tracked research gates.
No full S01/pipeline/scientific acceptance or resolution of remaining Q08 questions
is claimed. The older local instructions should be reported to Matty for authorized
synchronization; they were not overwritten or externally reported by this session.
