# P02 partial A: capacity correction and actual receiving

Edison owns P02; Matty is its technical contact and receiving owner. Matty
explicitly authorized fixing PR #75 and notifying Edison. Starting PR head was
f325232ddda707b258fbf02f919eb599d6a1bf46 on main c864f105. Instruction 1.27 and
F02 1.0.0 remain unchanged. The fix preserves Edison's implementation and commits.

## Correction

The original occupancy map counted running and proposed jobs but omitted the
site's background IT load. That conflicts with the existing S01 and A03 capacity
rule. With 40 kW background, a 40 kW J1 and 30 kW J2 cannot both occupy the same
slot under a 100 kW limit. Greedy A now reserves background in every remaining
physical slot before adding running and proposed work. PUE scales facility
energy; it does not scale the IT kW limit. No new shared decision is introduced.

The old background test also changed the state after constructing its Context.
Its replacement constructs matching state/context from the same snapshot and
checks both the exact capacity boundary and a one-kW excess at PUE 2.

## Actual receiving evidence

Six new parameterized E2E cases use actual K02 retrieval, greedy A, A03,
ExecutionController, S01 and immutable TraceStore records:

- The hand jobs are scheduled J1 at 0 and J2 at 2, including background and
  earlier proposed reservations; both PUE 1 and 2 pass the real checker.
- At 70 kW, J1 receives an individually supported capacity abstention and J2
  starts at 0; the complete proposal passes the actual checker.
- Two complete 30-slot executions at PUE 1/1.2 replan around real running work,
  execute only current starts, preserve every trace and drain completion slots.
  Actual S02 accounting records 140 completed IT kWh and 1,340 times PUE site kWh.
- The real agent harness receives two deliberately invalid synthetic HTTP
  proposals, then calls the actual greedy A function. Its fallback passes the
  real checker and execution recheck, executes J1 only at slot 0, and preserves
  separate initial/repair/fallback records and the two spent HTTP attempts.

The last case uses explicitly test-only HTTP, message renderers and token counts.
It is not model inference, reviewed production prompts or a scientific result.
There is no approving checker/provider stub or manufactured execution capability.

The corrected regression setup failed seven assertions against the unchanged
original policy (eight other tests passed). After the production fix, the policy,
E2E, agent, runtime and verification selection passes **137 tests in 6.54s**.
Initial receiving-test API/fixture mistakes were corrected before that original
policy comparison; both logs are retained outside Git.

One ordinary full suite retains **1,239 passes, 19 passing subtests and one
existing object-plain A01 timeout in 26.15s**. It is not rerun until green or
attributed to this policy fix. Original provider/test/payload/deadline/pins are
unchanged. Exact updated PR/main CI and receiving publication are recorded in #59
after execution. Hosted success does not establish an A01 transport fix.

```powershell
.venv\Scripts\python.exe -m pytest tests/policies tests/e2e/test_p02a_receiving.py tests/agent tests/runtime tests/verification -q
.venv\Scripts\python.exe -m pytest tests -q
```

Setup/50-task/policy/link/version/README checks and Ruff lint/format (105 Python
files) pass. Compile, dependency consistency, whitespace, preservation checks and
exact CI are recorded with publication after they run. F02, independent evaluator,
original ratings, locks, prompts, accepted runtime and Matty's provider are untouched.

## Receiving boundary

The real fallback callable is now `dc_sustainability.policies.greedy.propose`.
Pass it explicitly as `fallback=propose` when constructing AgentHarness, together
with the real controller/provider and required reviewed renderers. The injected
fallback remains subject to actual A03 checks and the final A04 recheck; a policy
proposal is never execution permission. No automatic production wiring or missing
renderer/token-counter default is supplied.

This is partial P02 A delivery and bounded technical receiving, not full P02,
A02, A04 or I01 acceptance. Greedy B/forecast routing, Q08, reviewed L02 renderers,
Nisha's runner and accepted runtime/counter plus separately authorized real model
episode remain where applicable. The heuristic does not guarantee a feasible
complete schedule for every workload. Edison continues P02/B; #59 stays open.
Nisha's independent replay fix still gates S01 PR #64. No shared format, setting,
scientific rule or task ownership changed. Delete a merged branch only after
its latest head is included in green main; preserve all unmerged work.
