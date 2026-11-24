# RULE-03 independent bounded verification — report section draft (Nisha)

Owner draft for the working report, November 23, 2026 (America/Phoenix). Part A is
for Section 4 (Architecture and Algorithms), Part B for Section 6 (Evaluation
design) and Part C for Section 7 (results). The primary-domain counts come from the retained
November 22 attempt and the November 23 independent receiving. The later host-failure
update is recorded separately below; evidence keys refer
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

For the closed-at-slot-0 domain, all jobs have arrived at slot 0; this does not grant
visibility of future arrivals in other domains. Rules-v1, the production
checker, the Greedy A fallback and the simulator are all deterministic. The
system's reachable behavior on a case is therefore a single path. We verify the
actual implementation by running its common runner once per case and policy, and
then replaying the saved records against the verifier's reconstruction. The
receiving harness first rebuilds the code bindings itself: the specification, the
hash of every scheduler source file, the generator, the environment lock and the
git commit. It then requires that every decision and result record carries
exactly those bindings, and that every saved state, snapshot, transition and
completion file matches its hash. [E13, E14]

Within each exact authorized attempt, execution and replay share one combined
ceiling of 10,000 states, 50,000 transitions and 600 seconds. A separately
authorized continuation has its own bound and reports cumulative work; it must
not reset or conceal the original counters. Reaching a ceiling gives INCOMPLETE,
never PASS. Statuses are PASS, FAIL,
INCOMPLETE or NOT_RUN, and a property with zero checks is NOT_RUN. [E12, E13]

## Part B — Section 6.x: Verification domains

The primary domain has 64 inputs: two arrival-0, duration-1 flexible jobs with
power in {10, 20} kW and deadline in {1, 2}, capacity 30 kW, background 10 kW,
and slot 0-1 scores in {100, 300}. The authored scenarios are A, B, B-fault (an
injected invalid proposal) and B-progress. Each case runs for rules-v1, Greedy A
and Greedy B; Greedy runs skip the injected-fault case. That gives at most 202
case-policy runs of 30 decisions each. An optional 1,024-input supplement was
deferred. Execution needed one-use authorization on a clean, frozen commit. [E12, E14]

## Part C — Section 7.x: Original November 22 results (preserved)

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
three policies complete every job in them. Greedy B has 51 traces awaiting full
replay across all 64 cases; 43 of these are among the 52 P1-eligible cases. Reading
their recorded completion sets is not replay verification. [E14]

**November 23 host attempt.** A separately approved narrow continuation at host
commit `9621b44` stopped after 54.578 seconds because the host sandbox denied
exclusive hard-link publication of the first authored `case.json`. No authored
run completed, no saved Greedy B replay started, and the new charged state and
transition counts are both zero. Cleanup was verified. This attempt is **FAIL**
for a host I/O error, not a policy safety counterexample. Its one-use ID is
consumed; the original November 22 **INCOMPLETE** result remains unchanged.
File-only probes reproduced the denial in the sandbox and succeeded on the
native host. That earlier pending request was superseded by a freshly approved native-host
attempt, reported separately below. See the [sanitized attempt receipt](../evidence/rule03-nov22/continuation-host-failure-nov23.json)
and [dated issue handoff](https://github.com/ReymoT/data-center-agentic/issues/241#issuecomment-7113732354).

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
scientific freeze. The failed host attempt above did not supply the missing coverage. The later
authorized native-host continuation below supplies a separate scoped result,
now independently received within scope. Synthetic evaluation, accounting and scientific
freeze remain pending. [E14, E15]

## Part D — November 23 native continuation (independent receiving accepted)

The separately authorized native-host attempt at `dbb8e6f` completed with scoped
PASS in 54.265 seconds, exit 0 and verified cleanup. It ran all 10 authored
case-policy runs and replayed the 51 outstanding saved Greedy B traces. New
charged work was 2,130 states/transitions: 300 authored execution steps plus
1,830 replay steps. Cumulative work is 12,130, retaining the original 10,000
and the previously partial replay prefix. Source/evidence bindings stayed stable.

Authored rules-v1 S1-S5/P1/P2 and arithmetic PASS; Greedy A/B S1-S3/S5/P1/P2
PASS, with S4/arithmetic NOT_RUN for those baselines. The saved Greedy B remainder
passes S1-S3/S5/P1/P2 and binding checks; primary S4 remains NOT_RUN. The original
INCOMPLETE and intermediate host FAIL reports are not rewritten. No primary
trace was regenerated, and no model or final unseen-case run occurred.

Nisha independently received this new scope from retained evidence without a
policy or replay rerun. Her original reply and the source/count reconciliation
are preserved in [the accepted receiving record](../handoffs/RULE03_NATIVE_INDEPENDENT_RECEIVING_NOV23.md).
They do not establish generalization, accounting acceptance or
scientific freeze. The 12 zero-start infeasible primary cases remain a limitation.
See [the actual handoff and evidence](../handoffs/RULE03_NATIVE_CONTINUATION_NOV23.md). [E15]

Across the preserved attempts, all 202 planned case-policy traces are completely
replayed: 192 primary plus 10 authored. Greedy B now has 13 + 51 = 64 complete
primary replays and 9 + 43 = 52 eligible P1 cases. Authored rules-v1 S4 has three
checks and no violations; authored arithmetic has eight checks and no mismatches.
The accepted source baseline freezes this bounded verification result only, not
the final metric/input protocol. Optional extended coverage was not executed. [E16]

## Authored metric illustration (not unseen evaluation)

The [partial RULE04 handoff](../handoffs/RULE04_DEVELOPMENT_HANDOFF_REVIEW_NOV23.md)
now supplies files and a corrected read-only projection of the 10 saved authored
runs. Scenario A totals are 8000 artificial score-kWh for rules-v1/Greedy B versus
12000 for Greedy A; B-progress totals are equal. B has no positive baseline, so its
comparison is unavailable. These are authored illustrations, with independent
metric receiving pending, not evidence of unseen generalization, real emissions
savings or policy superiority. No policy has run on the 120 development cases. [E17]
