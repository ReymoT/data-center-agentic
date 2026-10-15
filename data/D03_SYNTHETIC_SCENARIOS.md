# D03 synthetic scenario generation

Owner: Reimo; technical contact: Ved. Implementation and local verification only;
no publication or receiving-member acceptance is claimed.
Reviewed authoritative main `21451ac4eb2efad2007a116af98ff0faea4c968e`, instruction
deployment 1.9, F02 contract 1.0.0. The existing task branch is
`feature/d03-synthetic-scenario-generation`; main is an ancestor. The open GitHub
Issue listing contained no D03 Issue. No Issue was created or changed.

## Implemented acceptance evidence

| Requirement | Implementation / verification |
| --- | --- |
| Normal demand | 12 jobs, exactly 7 flexible, slack 2–10 |
| Workload spike | 20 jobs, exactly 12 flexible, exactly eight arrivals in slots 6–9 |
| Limited flexibility | 12 jobs, exactly 2 flexible, slack 0–2 |
| Infeasible | 12 jobs, exactly 7 flexible, exactly one marked flexible job with slack −1 |
| Bounds | Constant IT power 10–40 kW, duration 1–4 hourly slots, arrivals 0–17, deadlines ≤30 |
| Episode timing | Existing F02 PrivateEpisode, 24 decision slots and six completion slots |
| Hand fixture | J1/J2/J3 match existing F02 examples, retaining impossible J3 |
| Missing forecasts | Normal variant uses `forecast_visibility="withheld"`; all 30 private actual observations remain unchanged |
| Reproducibility | Explicit integer seed, isolated Python Random instance, deterministic ordered output and canonical episode hash |
| Labels and provenance | F02 PrivateJob keeps scenario/seed/split/synthetic/impossible labels; private sidecar records generator version, source, distribution specification and episode hash |
| Quality checks | 100 seeds per scenario; counts, bounds, slack, impossibility, determinism, RNG isolation, F02 round trips, actual-carbon coverage, variant, provenance, catalog regeneration and exclusive writes |

Slack means deadline minus arrival minus duration. Nonflexible jobs still must
start at arrival, even when their deadline has positive slack. Only the deliberately
impossible job violates earliest completion. The generator does not certify joint
capacity feasibility: random concurrent demand may also be infeasible. It neither
filters difficult episodes nor invokes a solver to manufacture feasible labels.

## Provisional distributions and boundaries

`d03-provisional-v1` independently samples integer power uniformly from 10–40 kW,
duration uniformly from 1–4 slots, and arrivals uniformly from 0–17. Flexible
indices are sampled uniformly without replacement to enforce exact counts.
Slack is discrete uniform within the scenario range, with its upper bound capped
at `30 - arrival - duration`. Spike uses slack 2–10 provisionally; its first eight
job IDs sample arrivals uniformly from 6–9, and the other twelve uniformly from
0–5 and 10–17. Job order is stable ID order, not chronological order.
The infeasible scenario changes the first selected flexible job's slack to −1.
All these sampling choices are explicit development assumptions pending Q06.

There are no Frontier observations, quantiles or calibrated correlations here.
D02's proposed scaling function is not called. Globus access, verified Frontier
field/unit/license evidence (Q05), and affected-teammate agreement on calibration,
distributions and freeze choices (Q06) remain required. No decision is resolved by
this implementation. User authorization permits provisional development; it does
not establish scientific agreement. Exact regeneration is verified with CPython
3.12.15; preserve generator version, Python version and original artifact bytes.

The checked catalog is a tiny synthetic development job artifact, not D04's
40/30 episode allocation or a frozen research dataset. Its SHA-256 is
`ea8f414bf21035db04d75ca8ff1815aae94e940d02295ee7dd99a41e0dc38ad5`.
Existing F02 hand carbon values remain in `tests/contracts/fixtures.py`; the D03
tests repeat that synthetic series across 30 slots solely to test assembly.
No synthetic carbon is presented as SustainDC data.

`generate_jobs` returns only F02 PrivateJob records. `generate_episode` requires
an explicit caller-supplied constraint snapshot and 30 slot-mapped private actual
observations whose source IDs resolve in that snapshot. Callers retain authority
and responsibility for source semantics and consistent applicable constraints;
this module does not infer timestamp conventions, issue times or forecast freshness.
`private_manifest` is a local provenance sidecar, not a shared interface revision.
Persist it with the episode for workload-generator provenance.

The complete episode/catalog is private input. Never pass its complete job list
to a policy. Existing F02 Job has no private labels, and VisibleState rejects a
PrivateEpisode payload. This module introduces no simulator-facing public export;
S01 must reveal only arrived jobs and project constraints with F02's visibility
helpers. Runtime leakage/integration acceptance remains for S01. Q01–Q04 behavior
is not selected. No D04, E3, simulator, agent or shared-schema changes are included.

## Reproduction and validation

From the repository root, using the existing Python 3.12 environment:

```sh
python -m dc_sustainability.data.scenarios /tmp/d03-jobs.json --seed 42 --split development
cmp /tmp/d03-jobs.json data/manifests/d03-provisional-jobs.json
python -m pytest tests/data/test_scenarios.py -q
python -m pytest tests -q
python -m ruff check dc_sustainability scripts tests
python -m ruff format --check dc_sustainability scripts tests
python scripts/validate_setup.py
python -m compileall -q dc_sustainability scripts tests
```

The catalog command requires a new output path and refuses overwrites. The API
accepts caller-provided split labels without allocating dates/folds or reading
held-out inputs. `generate_episode("normal", withhold_forecast=True, ...)` produces
the normal missing-forecast variant without modifying private actuals or jobs.

Observed checks in `/private/tmp/d02-venv`: 416 D03 tests; full suite 713 tests and
19 subtests passed. The first sandboxed full run had 39 loopback-bind setup errors;
rerunning with permission passed all tests. Lint, format, compilation and repository
setup validation passed. No real model calls or external data downloads occurred.
This macOS test environment does not certify the Windows lock or resolve Q13.

For Ved/Edison/Nisha: review the provisional workload rules and reproduce the
catalog before agreeing to Q06/freeze. Full D03 integration acceptance still needs
that agreement, empirical calibration or an accepted synthetic-only scope,
independent reproduction and downstream consumer evidence. The implementation is
uncommitted as requested; no final Done, merge or receiver acceptance is claimed.
