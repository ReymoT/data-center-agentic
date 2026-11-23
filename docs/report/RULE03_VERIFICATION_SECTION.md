# RULE-03 independent bounded verification — report section draft (Nisha)

Owner draft for the working report, November 23, 2026 (America/Phoenix). Part A is
for Section 4 (Architecture and Algorithms), Part B for Section 6 (Evaluation
design) and Part C for Section 7 (results). Every number comes from the retained
November 22 attempt and the November 23 independent receiving; evidence keys refer
to the [index](VERIFIED_EVIDENCE_INDEX.md). This text adds no new run, replay,
freeze or generalization claim.

---

## Part A — Section 4.x: Independent bounded verification

The rule scheduler is checked by a verifier written separately from it. The
verifier does not call the production checker, the scheduler or its success
verdicts. It has its own model of the discrete site: 30 hourly slots, new starts
only in slots 0-23 and drain slots 24-29. A job may start only after it arrives,
must finish by its deadline and slot 30, and a nonflexible job may start only at
its arrival slot. In every occupied slot, background load plus running and newly
started jobs must not exceed the IT capacity. Scores are artificial integer
weights, not emissions. [E12, E13]

It checks five safety properties and two progress properties:

- **S1:** only arrived, waiting jobs start, and each job starts at most once.
- **S2:** nonflexible timing and deadlines hold.
- **S3:** per-slot joint capacity holds, with the exact kW arithmetic recorded.
- **S4:** an invalid or injected proposal is never executed.
- **S5:** the clock and state version advance correctly, and nothing starts in a
  drain slot.
- **P1:** on closed, fault-free, forecast-present and jointly feasible inputs,
  every job completes. A safe refusal that prevents completion counts as a P1
  failure.
- **P2:** each run's reported completed, missed and unfinished jobs match the
  verifier's own reconstruction.

Joint feasibility comes from a brute-force oracle that enumerates every legal
start assignment, and the legal-action graph is explored separately as a
cross-check. That oracle is kept apart from verification of the policy itself.
[E12, E13]

For a closed case every arrival is known in advance, and rules-v1, the production
checker, the Greedy A fallback and the simulator are all deterministic. The
system's reachable behavior on a case is therefore a single path. We verify the
actual implementation by running its common runner once per case and policy, and
then replaying the saved records against the verifier's reconstruction. The
receiving harness first rebuilds the code bindings itself: the specification, the
hash of every scheduler source file, the generator, the environment lock and the
git commit. It then requires that every decision and result record carries
exactly those bindings, and that every saved state, snapshot, transition and
completion file matches its hash. [E13, E14]

All work shares one combined ceiling of 10,000 states, 50,000 transitions and
600 seconds. Reaching it gives INCOMPLETE, never PASS. Statuses are PASS, FAIL,
INCOMPLETE or NOT_RUN, and a property with zero checks is NOT_RUN. [E12, E13]

## Part B — Section 6.x: Verification domains

The primary domain has 64 inputs: two arrival-0, duration-1 flexible jobs with
power in {10, 20} kW and deadline in {1, 2}, capacity 30 kW, background 10 kW,
and slot 0-1 scores in {100, 300}. The authored scenarios are A, B, B-fault (an
injected invalid proposal) and B-progress. Each case runs for rules-v1, Greedy A
and Greedy B; Greedy runs skip the injected-fault case. That gives at most 202
case-policy runs of 30 decisions each. An optional 1,024-input supplement was
deferred. Execution needed one-use authorization on a clean, frozen commit. [E12, E14]

## Part C — Section 7.x: Verification results (partial)

The approved attempt ran once on frozen main `3daf00f7` on November 22. It
stopped at the combined 10,000-state ceiling after 107 s, with no run errors and
no retry. The total is 5,760 steps executing the 192 primary runs (192 × 30) plus
4,240 replay steps. Running and replaying the full 202-run scope would need
12,120 steps, so the ceiling, not a scheduler defect, caused the stop. The overall
result is **INCOMPLETE**. [E14]

| Domain / policy | Runs | Fully replayed | S1-S3, S5 | S4 | P1 | P2 |
| --- | ---: | ---: | --- | --- | --- | --- |
| Primary, rules-v1 | 64 | 64 | PASS (1,920 checks each) | NOT_RUN | PASS (52 eligible) | PASS (64) |
| Primary, Greedy A | 64 | 64 | PASS (1,920 checks each) | NOT_RUN | PASS (52 eligible) | PASS (64) |
| Primary, Greedy B | 64 | 13 | INCOMPLETE | INCOMPLETE | INCOMPLETE | INCOMPLETE |
| Authored A/B | 0 of 10 | 0 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

Rules-v1 capacity arithmetic was compared 141 times with zero mismatches. No
counterexample was found in the completed replays. S4 is NOT_RUN, not PASS: no
invalid proposal occurs in the primary domain, and the authored fault case did
not run. Of the 52 P1-eligible Greedy B cases, 9 are fully replayed and 43
remain. [E14]

**Independent receiving.** I inspected the retained evidence without rerunning
any policy. The archive hash, all 29,569 file hashes and the extraction safety
checks pass. My own rebuild of the frozen commit's bindings matches the report.
All 192 traces have 30 decisions and carry exactly those bindings, and every
referenced file matches its hash, with zero findings. My brute-force oracle also
finds exactly 52 jointly feasible primary cases, and in the result records all
three policies complete every job in them. For Greedy B, 51 of those records are
not replay-verified. [E14]

**Limitation: no partial progress on infeasible inputs.** In all 12 jointly
infeasible primary cases, all three policies start no job, so both jobs are
missed, even though either job alone would fit. For example, 10 kW and 20 kW jobs
that must both run in slot 0 (deadline 1) need 40 kW together with the 10 kW
background, against a 30 kW capacity.
The complete-plan gate and the fallback both refuse a partial plan. This keeps
execution safe and is outside P1's scope, but the system does not salvage a
feasible subset of work. [E14]

**What this does and does not show.** Within the 64-input primary domain, the
actual rules-v1 and Greedy A implementations satisfied every checked safety and
progress property. This is finite-domain evidence for one frozen implementation.
It is not a proof for larger or unseen inputs, a generalization result or a
scientific freeze. The authored cases, Greedy B and S4 still need the separately
authorized continuation: 51 saved Greedy B replays plus 10 authored runs. Synthetic
evaluation and accounting against Greedy A/B remain pending. [E14]
