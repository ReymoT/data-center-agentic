# RULE-05: focused rule-system study methods

Reimo Tamme, issue [#243](https://github.com/ReymoT/data-center-agentic/issues/243).
Reviewed November 23, 2026 against main `91e23b6f85c6240ec22d2a23e14f1eaf924427c4`,
instruction 1.30. This is methods and implementation documentation with accepted bounded verification
and partial authored metric illustrations; full unseen evaluation remains pending. It supplements the historical [R01 methods](R01_DATA_AND_SIMULATOR_METHODS.md)
and the [working report](VERIFIED_EVIDENCE_WORKING_DRAFT.md); it does not replace
teammates' sections or complete the IEEE PDF. Editable figures are in
[RULE05_WORKFLOW_DIAGRAMS.md](RULE05_WORKFLOW_DIAGRAMS.md).

## Research question and scope

Can explicit rules reproduce safe, explainable scheduling decisions and generalize
to unseen synthetic scenarios? The [November 19 plan](../decisions/NOV19_RULE_STUDY_PLAN.md)
replaced the active source-dependent Agent-versus-Plain study because source
permissions, provenance and verified episode-plus-forecast inputs were unavailable.
Issue #60 was closed NOT_PLANNED; B1–B3 remain unresolved and B4 provisional.
The original question remains unanswered. Historical development observations
are retained evidence, not matched results for this new study.

The new study uses independently authored artificial inputs, a deterministic rule
scheduler, independent bounded verification and a prospective comparison with
unchanged Greedy A/B. It makes no LLM call, learned-model or real-site savings claim.
Inspectability means recorded rule IDs and reproducible arithmetic; it does not
establish human faithfulness or universal explainability.

## Rule development and permitted material

The [accepted specification](../decisions/NOV20_RULE01_SPECIFICATION_ACCEPTANCE.md)
freezes the design, including all three affected-owner replies. Its canonical
[JSON](../rule_study/specification.json) hash is
`9597931fcee09bc895605b65401483c9c3658da9e0bdf7c954f8669dfa8542bd`.
Old pending-response fields in that immutable snapshot are superseded by the
acceptance record, not evidence of missing design agreement.

The specification identifies newly authored A/B assumptions as its illustrative
inputs. The permitted public [cb85 fallback record](../handoffs/A01_PAIRED_CLAIM_VALIDATION_RESULT_2026-11-09.md)
motivates separating proposal, checking, fallback and execution; its workload was
not copied into a training or evaluation set. No private episodes, restricted
source CSV, old sealed inputs or metadata are inputs to this deliverable.
Matty specified R01–R09 by hand from declared constraints and these illustrations;
Ved implemented them. They are neither automatically extracted nor learned rules.

| Rule | Specified behavior and basis |
| --- | --- |
| R01 | Validate visible state/version, unique jobs and authoritative constraints; fail closed on malformed or out-of-scope inputs. |
| R02 | Start arrived waiting jobs no earlier than now; meet deadlines and the 30-slot horizon; no starts after slot 23. |
| R03 | Nonflexible work starts at arrival; no duplicate or restarted work. |
| R04 | Check background + running + selected IT kW in every occupied half-open interval against IT capacity; PUE does not scale the capacity limit. |
| R05 | Enumerate bounded joint assignments with an unscheduled choice for each job. |
| R06 | Deterministically maximize work inclusion before minimizing artificial score and completion time, with explicit tie-breaking below. |
| R07 | Recheck against current state and execute current starts only; future starts are advisory. |
| R08 | Unusable forecast or failed proposal routes to checked Greedy A; failed approval starts no new work. Public fallback evidence motivates this boundary. |
| R09 | Preserve fired IDs, arithmetic, errors and distinct unscheduled/missed/completed outcomes. |

See the [rule table and assumptions](../rule_study/RULE01_SPECIFICATION.md) for the
normative definitions. The authored site is capacity 60 kW including background
20 kW, PUE 1 and hourly slots; these differ from historical R01's 100/40 kW and
PUE 1.2 assumptions. Forecast-present cases deliberately have perfect artificial
forecasts with simulated issue times. This is a toy assumption, not measured
forecast accuracy. Policies see arrived waiting jobs, running/completed state and
permitted forecast/constraint facts. Future arrivals and evaluator-only accounting
weights for missing-forecast cases stay outside policy inputs. Published artificial
seeds are reproducible; this boundary does not claim secrecy.

## Executable scheduler and execution path

The actual [scheduler](../../dc_sustainability/rule_study/scheduler.py) is a pure
VisibleState/ConstraintSnapshot-to-proposal function using unchanged F02 records.
It accepts at most four waiting jobs and absolute candidate starts 0–5. Each job's
legal starts plus an unscheduled choice form a Cartesian product, bounded by
7^4 = 2,401 assignments. No jobs or assignments are silently sampled or truncated;
unsupported scope is rejected. Capacity filtering includes existing running load
for the whole duration. Integral power and weights support exact arithmetic.

Among feasible assignments R06 lexicographically selects:

1. Maximum scheduled-job count.
2. Maximum inclusion vector ordered by nonflexible first, earliest latest-start,
   earlier deadline, then job ID.
3. Minimum sum of scheduled jobs' artificial score-kWh.
4. Minimum sum of completion slots.
5. Minimum start vector in the same priority order; unscheduled is encoded as 99.

These are `ObjectiveTuple.sort_key`, `priority_key` and `propose_rules_v1` in the
scheduler. A future placement counts in the proposal but is not a reservation:
receding-horizon decisions recompute it. There is no optimality claim with unknown
future arrivals.

The [common runner](../../dc_sustainability/rule_study/runner.py) applies the unchanged
[production checker](../../dc_sustainability/verification/checker.py) to rules-v1,
Greedy A and Greedy B. A failed rules proposal or R08 forecast condition attempts
unchanged [Greedy A](../../dc_sustainability/policies/greedy.py), which must also pass.
The runner's trusted control path rereads state/snapshot, performs a latest-state
production recheck, then reads state/snapshot again. Only unchanged reads and a
passing recheck allow it to mint `ApprovedActions`. A changed live state stops
without stepping; a changed snapshot or failed recheck refuses new starts and
drains. Only current-slot starts execute in the
[simulator](../../dc_sustainability/simulator/core.py).
Without approval, `step(None)` starts nothing and advances running work and time
once. Changed live state or rejected rules input stops without another step;
indeterminate effects require reconciliation, not automatic retry.

The [implementation handoff](../handoffs/RULE02_IMPLEMENTATION.md) records the key
Scenario B discrepancy with a naive reading of the initial design: although either
job fits alone, the unchanged individual-abstention gate rejects a partial joint
selection and Greedy A fallback. Do not weaken the gate in prose or promise that
one job executes. B-progress is the separate feasible delayed-work example;
B-fault deliberately injects an invalid proposal.

[Records](../../dc_sustainability/rule_study/records.py) bind specification, case,
adapter, generator, lock and code identities. The runner persists hash-addressed
states/snapshots, decision stages, checks, transitions, intents and completion
commitments using canonical JSON and exclusive publication. Replay verifies
saved commitments without stepping again. These immutable-by-interface records
detect changed evidence; hashes are not signatures or runtime authentication.

## Independent safety and progress verification

Nisha owns the separate [verifier and trace reader](../rule_study/RULE03_VERIFIER.md).
The [kernel](../../dc_sustainability/evaluation/rule_study_verifier.py) independently
implements timing, capacity and expiry without importing the production checker,
scheduler, simulator or shared schemas. Its legal-action graph enumerates all
legal subsets to establish joint feasibility, cross-checked against brute-force
joint assignments. That oracle graph is distinct from the actual policy-induced
reachable path used to assess the system.

S1–S5 separately cover arrived/unique starts, timing/deadlines, joint capacity,
rejection of invalid execution and clock/drain behavior. P1 requires fault-free,
forecast-present, closed-at-slot-0, jointly feasible work and completion by its
deadlines. A safe refusal preventing completion on an eligible case is P1 FAIL.
Infeasible, later-arrival, missing-forecast or faulted cases outside that scope
receive an explicit NOT_RUN reason, never an inferred P1 PASS. P2 checks terminal
completed/missed accounting; it does not establish successful completion.

The primary domain contains 64 inputs: two flexible arrival-0 duration-1 jobs,
power {10,20}, deadline {1,2}, capacity/background 30/10 kW and four two-slot score
profiles from {100,300}. The optional 1,024-input domain adds arrival {0,1} and
flexibility {false,true}. It includes the primary 64; never pool these as 1,088
unique inputs. Primary coverage alone does not exhaustively cover delayed arrivals
or nonflexibility. Primary runs first. Within each exact authorized attempt,
execution and replay share a combined allowance of 600 seconds, 10,000 states and
50,000 transitions; a ceiling hit is INCOMPLETE. A continuation needs fresh exact
authorization, preserves the original consumed ID/result and reports cumulative
work instead of silently resetting counters. These are charged steps, not a
count of unique physical states. Actual method/domain counts and overlap must
accompany findings.

The historical verifier documentation reports specification-oracle counts: 52 of 64
primary inputs jointly feasible and 12 infeasible, with zero cross-check mismatches.
Its optional-domain facts are 420 feasible/604 infeasible with zero mismatches;
these are oracle facts, not rules-v1 coverage or progress results. The reported
6,389 states/5,297 transitions cover all three oracle domains including authored
cases, not a current-policy verification run or new work in this methods handoff.
These are attributed oracle/harness figures; accepted actual policy coverage is
recorded separately below. Deliberately broken fixture policies
exercise counterexample detection; they are not counterexamples to rules-v1.

The [historical receipt](../handoffs/RULE02_EVIDENCE_RECEIVING_NOV22.md)
remains an old `176361a` archive check, not verification of corrected main.
The accepted [RULE-03 report](RULE03_VERIFICATION_SECTION.md) and
[verification baseline](../rule_study/RULE03_VERIFICATION_BASELINE_NOV23.json)
now record complete required bounded coverage, independently received within scope
in merged PR #270. Across preserved attempts, all 202 required traces were
completely replayed: 192 primary (64 per policy) plus 10 authored. Greedy B has
13 + 51 = 64 complete primary replays, including 9 + 43 = 52 eligible P1 cases.

The [original attempt](../handoffs/RULE03_BOUNDED_ATTEMPT_NOV22.md) at `3daf00f7`
remains INCOMPLETE at 10,000 charged states; the intermediate sandbox host attempt
remains FAIL with zero new states/transitions. Neither record is overwritten.
The [native continuation](../handoffs/RULE03_NATIVE_CONTINUATION_NOV23.md) at
`dbb8e6f` supplied the 10 authored runs and remaining 51 saved primary replays,
charging 2,130 new states/transitions (300 execution + 1,830 replay).
Cumulative work is 12,130, retaining the prior partial replay prefix.
[Nisha's accepted independent receiving](../handoffs/RULE03_NATIVE_INDEPENDENT_RECEIVING_NOV23.md)
inspected retained evidence without rerunning policies or replay.

Primary S1–S3/S5/P1/P2 pass within their checked/eligible scopes; primary S4 stays
NOT_RUN because no invalid proposal occurs there. Authored rules-v1 S1–S5/P1/P2
and arithmetic pass, including three S4 checks without violations and eight
arithmetic checks without mismatches. Authored Greedy A/B S4 and arithmetic remain
NOT_RUN. Optional extended coverage was not executed.

All three policies start zero jobs in the 12 jointly infeasible primary cases;
both jobs are missed even though either alone fits. Complete-plan and fallback
gates refuse partial work: safety here does not salvage a feasible subset and
these cases are outside P1 eligibility. Finite bounded verification is complete
and independently received within scope, not universal proof, unseen
generalization, independent accounting acceptance or the final evaluation freeze.

## Isolated synthetic evaluation and reporting

Edison owns RULE-04. The isolated [generator](../../dc_sustainability/evaluation/rule_study_generator.py)
uses its own standard-library random stream and declared draw order, importing no
scheduler, production checker, simulator or independent verifier. Development and
final seed domains differ. Freeze specification/rules/verifier/metrics before final
generation; retain failed results and require a fresh untouched cohort after any
evaluation-driven rule revision. The accepted target is 40 cases in each of three
strata (120 cases), compared on identical inputs by rules-v1, Greedy A and Greedy B
(360 rollouts, 30 steps each). These are prospective counts, not observed support.

Normal-feasible and missing-forecast cases draw 2–4 jobs; overload draws 3–4 and
includes the fixed conflicting J1/J2 pair. Powers are {10,20,30}, durations 1–2,
arrivals 0–2 and deadlines at most 6. Normal/missing cases require joint feasibility,
a flexible job and a nonconstant six-slot profile. Weights are {100,200,300} with
remaining slots 200. Rejection sampling has a 10,000-attempt ceiling per stratum.
Publish actual accepted/rejected attempts, full-case and workload-only diversity;
do not assume 40 distinct workloads. The [independent case checker](../../dc_sustainability/evaluation/rule_study_cases.py)
checks labels, strata, counts and supplied-set overlap; generator labels are claims.
Full-case duplicates/overlap with development/final/authored examples are rejected;
workload-only overlap is reported. Pair comparisons match case hash, workload,
profile, policy/code binding and completed-job identities, not just a display ID.

Missing-forecast inputs expose null scores; their weights are in a separate
evaluator-only sidecar. The [accounting checker](../../dc_sustainability/evaluation/rule_study_accounting.py)
checks supplied-pair identity/coverage/weights and reference arithmetic separately
from schedule safety. A pair PASS does not authenticate provenance, freeze history,
actual routing or policy metric totals. Rules R08 and Greedy B both route to Greedy A
here: this is a safety/fallback/accounting control, not evidence of ranking advantage.

| Quantity | Definition and required denominator/limits |
| --- | --- |
| Safety violations | Count by property with actual checked decisions/executed starts and excluded/refused/partial traces; never assume zero for missing checks. |
| Completed work | Completed job IDs/count out of all case jobs; report completed facility kWh separately from observed execution energy. Missed, unscheduled and started-not-completed IDs accompany it. No scalar total alone establishes equal work. |
| Turnaround | (End slot − arrival slot) × 1 hour for completed jobs; waiting delay is (start − arrival) × 1 hour. State completed-job support and missed/unfinished counts. For comparison use matched completed-job sets and report exclusions; unfinished turnaround is unobserved, never zero. |
| Artificial job score | Sum over occupied slots of power kW × 1 hour × PUE 1 × artificial weight, in score-kWh. Runner `synthetic_impact_total` sums completed jobs only. Report that scope explicitly. |
| Site score/energy | Site score includes background and all actual job load over the same 30 slots using the sidecar weights. Runner exposes energy ledgers, but its completed-job score total is not a site-score total. Independent metric recomputation is still required. |
| Paired reduction | 100 × (Greedy A score − policy score) / Greedy A score, only with positive baseline, identical input/profile/horizon, replay and accepted equal-work/completed-set gates. Missing, failed or unmatched comparisons are unavailable with reason, not zero. |
| Fallback | Record attempted fallback decisions / observed decisions per case/policy/stratum and reasons, separately from approved fallback / attempted fallback and actual executed fallback starts. A rejected fallback is not a successful fallback. Final aggregation needs Edison's accepted metric records. |

In `build_result`, `unfinished_job_ids` means every noncompleted job, so it can
overlap `missed_job_ids`; these are not disjoint bins to add. `unscheduled` means
never started. A result `status=complete` denotes a complete decision sequence,
not completion of every job. Partial traces have shorter observed horizons and
cannot silently enter a full-horizon comparison. Show per-stratum paired differences
and support before aggregate claims. No interpolated frontier or invented uncertainty
interval is warranted. No artificial score is measured g/kWh, kg CO2e, avoided
emissions or a validated physical carbon factor, even if a legacy adapter uses a
carbon-shaped field.

The [generator receiving note](../rule_study/RULE04_GENERATOR_RECEIVING.md) is dated:
its statement that no sidecar checker exists is superseded by the merged accounting
checker and [current handoff](../handoffs/NOV22_MANAGER_READINESS_AND_HANDOFFS.md).
The [PR #271 development handoff review](../handoffs/RULE04_DEVELOPMENT_HANDOFF_REVIEW_NOV23.md)
retains 120 development cases and their evaluator-only sidecar plus partial metrics
from 10 saved authored runs. The corrected [reviewed projection](../evidence/rule04-dev-nov23/authored-metrics-reviewed.json)
reports Scenario A totals of 8,000 artificial score-kWh for rules-v1/Greedy B versus
12,000 for Greedy A; B-progress is equal, and B has an unavailable zero-baseline
comparison. These are authored illustrations, not unseen findings or superiority.
Original producer metrics stay preserved. Independent accounting acceptance is
pending; no policy has run on the 120 development cases. Full unseen evaluation,
input/metric/isolation freeze and exact rollout authorization remain pending.
Final generation is disabled in the current generator. No new cohort, rollout,
model call or dispatcher execution was performed for RULE-05.

## Limitations, feedback and contributions

Finite bounded verification is not universal proof. Generalization can concern
only the accepted artificial domain, not physical operations, arbitrary workloads,
real forecasts or operational emissions savings. Historical Agent/Plain evidence
is not a matched new-study result and supports no LLM superiority claim. Policy
unit tests, archived trace checks and implementation CI are distinct from accepted
independent verification and authorized evaluation.

All four [#231 dispositions](PROFESSOR_FEEDBACK_FOLLOWTHROUGH_NOV17.md) remain:
grouped ten-fold ML refits are future work; structured rule arithmetic is implemented
in scheduler/records while the earlier LLM repair ablation was not run; ML warm-start
is future work; turnaround/artificial-score trade-offs await valid measured matched
accounting and otherwise remain unavailable. Keep these labels in report and demo.

Reimo's historical contribution remains D01 source adapters/validation, D02
calibration tooling (not empirical calibration), D03 provisional synthetic scenarios,
D04 allocation/materialization and custody foundation, D05 source evidence/documentation,
S01 simulation and S02 integration with Edison's shared impact formulas. The retained
[R01 contribution](R01_DATA_AND_SIMULATOR_METHODS.md) preserves the limits and separates
Matty's selector/bundle work and Nisha's private metadata selection/receiving.
RULE-05 adds this scoped methods adaptation, editable workflows, evidence-linked
report integration and demo handoff. Ved owns RULE-02, Nisha RULE-03 and report
assembly, Edison RULE-04, Edison/Ved RULE-07, and Matty specification/authorization/
final audit. Documentation does not supply their approval or independent acceptance.
