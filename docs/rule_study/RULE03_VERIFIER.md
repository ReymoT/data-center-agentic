# RULE-03 independent verifier: harness status

Owner: Nisha, issue #241. Built November 20, 2026 against main c6ca364 (instruction 1.30,
RULE-01 [review-2](../decisions/NOV19_RULE01_REVIEW_REVISION.md)) and
[RULE01_SPECIFICATION.md](RULE01_SPECIFICATION.md).

**Status: harness ready; no rules-v1 code has been verified yet.** RULE-02 code and the exact
adapter serialization are still pending.

## What it is

[`rule_study_verifier.py`](../../dc_sustainability/evaluation/rule_study_verifier.py) uses only
the Python standard library. It does not import the production checker, simulator, shared
schemas or any rules-v1 code. It re-implements the timing, capacity and expiry rules from the
shared rules, so a defect in production code shows up as a disagreement instead of being copied.

Two methods are named separately in every result, as review-2 decision 3 requires:

- **`legal_action_graph_for_joint_feasibility`** (the oracle). From each input it enumerates
  every reachable state under every legal current-start subset, including starting nothing. It
  decides only which inputs can complete all their work, and therefore P1 eligibility. A separate
  brute-force joint-assignment search must give the same answer.
- **`policy_induced_graph_for_properties`.** It follows the system under test's own decisions
  from slot 0 and checks S1-S5 at every state the system reaches, then P1 at the end. Arbitrary
  legal actions are never treated as the policy's behavior.

**Budget (review-2 decision 2).** One combined ceiling covers every domain and both methods:
10,000 states, 50,000 transitions and 600 s. Counters are kept per domain and method. Domains run
in order, primary first; the optional supplement uses only the remaining allowance. A domain that
stops early is INCOMPLETE, never PASS, and the earlier domains keep their results. Overlap with
earlier domains is counted, never pooled: the extended domain contains all 64 primary inputs.

| Property | Checked as |
|---|---|
| S1 | Starts name an arrived waiting job, each at most once |
| S2 | Nonflexible start at arrival; start + duration <= min(deadline, 30) |
| S3 | Background + running + new kW <= capacity in every occupied slot, with arithmetic terms, total, limit and signed excess |
| S4 | An invalid proposal, including the slot-0 injected fault, is never the executed set. Counted only where an invalid proposal existed; otherwise NOT_RUN with a reason, never a vacuous PASS |
| S5 | No new starts in slots 24-29; system errors fail closed. Drain-slot decisions are counted |
| P1 | Only inputs that are fault-free, forecast-present, closed at slot 0 and oracle-feasible. Refusal that prevents completion is a FAIL. Other inputs are counted by scope reason, never as a PASS |
| P2 | Trace mode only: the result record's completed/missed/unfinished sets must match the reconstruction, with every job completed or missed |

## Oracle results (offline, specification inputs only)

These are oracle facts from the specification's own authored inputs, not system results. All
three domains together use 6,389 states and 5,297 transitions.

| Domain | Inputs | Complete-feasible | Not feasible | P1-eligible | Outside P1 scope | Cross-check mismatches |
|---|---:|---:|---:|---:|---|---:|
| Primary (RULE-01) | 64 | 52 | 12 | 52 | 12 not jointly feasible | 0 |
| Extended (optional supplement) | 1,024 (64 overlap primary) | 420 | 604 | 148 | 768 not closed at slot 0; 108 not jointly feasible | 0 |
| Authored A, B, B-fault, B-progress | 4 | 2 (A, B-progress) | 2 | 2 | B infeasible; B-fault faulted | 0 |

- **Primary 52/12 matches a hand count.** Only 20 kW is free, and two deadline-1 jobs must share
  slot 0, so only the 10 kW + 10 kW pair fits. That makes 3 of 16 job-type pairs infeasible,
  across 4 score profiles.
- **Case B fault arithmetic:** 20 + 30 + 30 = 80 kW against a 60 kW limit, an excess of 20 kW.
- **B-progress witness:** J1 at slot 0, then J2 at slot 1.

**Policy budget after manager review.** The former9,462-state fixture estimate used an idle-policy shortcut and is historical, not a current budget margin. Policy exploration now calls the untrusted function through all30 slots, including empty-queue and drain states. This catches late restarts/starts that the shortcut missed. The optional supplement can therefore become INCOMPLETE under the unchanged combined ceilings; preserve the completed primary result and report actual counts rather than promise it fits.

**Finding: timing is enforced by expiry.** A nonflexible job not started at arrival, or any job
past its latest start, is marked missed at the next boundary. So no reachable state ever offers
a late start, and an R02/R03 timing violation can only come from starting a job that is not
waiting. That also triggers S1.

## Trace mode (recorded runs)

[`rule_study_trace.py`](../../dc_sustainability/evaluation/rule_study_trace.py) reads
`rule_study_decision_v1` and `rule_study_result_v1` records under
[proposal-1](ADAPTER_RECORD_PROPOSAL.md), which Nisha and Ved accepted in #239. It replays them
with the same independent predicates. It never uses a reported check result or status as an independent safety verdict. Source labels and hashes are not authenticated merely because they are syntactically valid.

**Fail closed.** The whole trace is refused, counted, and leaves the other results INCOMPLETE if
it has any of these:

- an unknown kind, version, study, policy or field;
- a malformed or differing binding, or a case hash that doesn't match the supplied case input;
- a spec hash that doesn't match the published specification;
- decision hashes not bound by the result record;
- a gap in the decision sequence;
- a nonzero model-call count.

The illustrative example JSON is refused.

**Checks on each trace:**

| Property | Checked as |
|---|---|
| S1-S3 | On the executed current starts |
| S4 | Invalid stages are never executed; executed starts must equal the selected stage's current starts; nothing executes without a selected stage |
| S5 | One decision per slot in order, state_version equal to slot, state_after.slot equal to slot + 1, consistent execution status. `indeterminate` stops the trace as partial |
| P1 | On oracle-eligible inputs |
| P2 | As described above |

Results are reported per policy (rules-v1, greedy_a, greedy_b).

**Informational, never a safety verdict:**

- **R04 arithmetic consistency:** the reported total, limit, signed excess and term sum compared
  with an independent recomputation.
- **State-hash continuity:** whether state_after matches the next state_before.

**Reader assumptions still to confirm against RULE-02's actual output:**

- the result field names (`decision_sha256s`, `completed_job_ids`, `missed_job_ids`,
  `unfinished_job_ids`, `accounting`, `status`);
- the execution fields `transition_ref` / `transition_sha256` and `state_after.state_sha256`;
- the case input shape (specification scenario fields, with `scores` or `first_scores` +
  `remaining_score`, plus optional `fault_starts`);
- the folder layout (`case.json`, `result.json`, `decisions/*.json`);
- whether the two state hashes cover the same object.

## Tests

The focused [exploration tests](../../tests/evaluation/test_rule_study_verifier.py) and [trace tests](../../tests/evaluation/test_rule_study_trace.py) now contain80 passing synthetic-fixture cases after direct manager review. They include the original harness tests and added false-pass/malformed-evidence/budget/no-op regressions. These are not actual rules-v1 or Greedy results.
They cover the oracle counts, predicates and expiry, fail-closed inputs, the combined budget with
its per-scope counters and overlap, and the rule that a later ceiling hit leaves the primary
result intact. They also check that deliberately correct or broken fixture systems are
classified correctly:

- an earliest-deadline fixture passes S1-S3, S5 and P1, with S4 NOT_RUN on primary;
- an ID-order fixture is safe but refutes P1;
- start-everything fails S3;
- never-start fails P1 on all 52 inputs;
- executing the injected fault fails S4, while blocking it passes;
- drain-slot starts fail S5;
- restarting a missed job fails S1 and S2;
- an exception fails closed;
- a ceiling hit gives INCOMPLETE.

The fixtures are not rules-v1, Greedy A or Greedy B.

## Run

```
python scripts/verify_rule_study.py --domain primary --domain extended --domain authored
python scripts/verify_rule_study.py --domain primary --system pkg.module:function --system-id rules-v1 --rules-v1 --out <new file>
python scripts/verify_rule_study.py --traces <folder of trace subfolders> --out <new file>
```

## Remaining for #241 (due November 23, 18:00 Arizona)

1. Confirm the trace-reader assumptions above against Ved's first real RULE-02 records and
   adjust the reader if the field names differ.
2. Wrap Ved's RULE-02 scheduler as a `SystemView -> SystemDecision` callable at his frozen
   commit. Run primary, then the supplement and the authored cases, and publish the reports with
   code hashes.
3. Freeze the verifier commit before Edison generates the final synthetic set. Then
   independently confirm that set's feasibility labels and check for overlap with the
   development and authored cases, using the case-set checker below.

## Case-set checker (review-2 decision 6)

[`rule_study_cases.py`](../../dc_sustainability/evaluation/rule_study_cases.py) and
[`check_rule_study_cases.py`](../../scripts/check_rule_study_cases.py) independently check
generated case sets before evaluation. Generator labels are treated as claims, not as an oracle.
Like the verifier, they use only the standard library and import no generator, scheduler,
checker or simulator.

| Check | How |
|---|---|
| Feasibility labels | Recomputed with the brute-force joint-assignment oracle and compared with each case's `feasibility_label`. The legal-action-graph oracle cross-checks them under its own budget |
| Stratum predicates | The review-2 generator proposal: site 60/20 kW; job count 2-4 (overload 3-4); power {10,20,30}, duration {1,2}, arrival {0,1,2}; deadline = min(6, arrival + duration + slack) with slack {0,1,2}; contiguous job IDs; slot 0-5 scores in {100,200,300} with drain score 200; at least one flexible job and a nonconstant profile for normal cases; the fixed J1/J2 30 kW conflict pair for overload; no visible scores for missing-forecast cases; feasible normal/missing cases and infeasible overload cases |
| Counts | Actual cases per stratum against the expected count (default 40). Full-case and workload-only diversity are counted, never assumed |
| Duplicates | Repeated full-case hashes or case IDs within a set fail |
| Overlap | Any full-case overlap between sets (final, development) or with authored cases A, B and B-progress fails. Workload-only overlap is reported, not rejected |

**Identity hashes.** The workload hash covers the sorted jobs plus capacity, background and the
30-slot horizon. The full-case hash adds the visible score profile, or null when none is visible.
Case IDs and generator metadata are excluded. Both use the canonical JSON convention.

**Input shape.** This is the checker's assumption until RULE-04 publishes its format:
`{"set_id", "cases": [...]}`, with trace-reader case fields plus `stratum` and
`feasibility_label`.

**Exit codes:** 0 PASS, 1 FAIL, 2 INCOMPLETE. Output files are created exclusively. The checker
has 25 tests, all on hand-built cases.

```
python scripts/check_rule_study_cases.py --set final.json --set development.json --expected final=40 --expected development=none --out <new file>
```

## Manager direct review and fixes — November20

The review reproduced13 failing synthetic regressions before correction (plus two already rejected inputs). These are unit fixtures, not actual rules-v1 or research results. Fixes preserve the independent standard-library predicates and do not import the production checker/simulator/schemas/scheduler.

- Policy exploration no longer skips empty/drain decisions. An attempted restart at slot24 now fails S1/S5 instead of being missed. No property with zero exercised checks is labeled PASS after a callback failure. Oracle disagreement blocks PASS certification.
- Capacity/background/score types, budget limits and system-return shapes fail closed. Trace mode now uses the shared budget and bounded four-job cases. Joint-assignment cross-checks check elapsed time cooperatively.
- Trace replay accepts a genuinely selected empty plan as an executed no-op; it still refuses starts without a selected stage or a different executed set. Full selected current/future placements are checked independently, so an invalid future reservation cannot authorize current execution.
- Float/bool model-call counts, unknown start/plan fields, malformed/nonfinite arithmetic and invalid state_after versions are rejected. Arithmetic reporting checks actual job terms/units in addition to totals, exposing its own PASS/FAIL/NOT_RUN diagnostic without pretending it is a human-faithfulness judgment.
- CLI output creation is exclusive, so a race cannot overwrite a prior report. Limits may only reduce the published prospective caps; primary precedes supplements. Exit1 means FAIL/refused trace or oracle disagreement; exit2 means incomplete checks/bindings/ceiling; exit0 is diagnostic/check success, not study acceptance. Failing reports are preserved.

**Critical evidence limits:** raw external state/snapshot/transition bytes and adapter/generator/environment/code artifacts are not supplied to this reader. It verifies case content, expected specification when supplied, decision-list hashes and within-trace consistency; `binding_validation` remains INCOMPLETE for the unauthenticated external artifacts. State-hash continuity remains informational until the runner defines and supplies the exact hashed objects. A physical-property PASS is conditional on the supplied input/action records, not proof that a real runner produced them. Accounting totals are not independently recomputed here. Nested legacy F02 check-result semantics are not used as verdicts.

Callback exploration models time with the verifier's own state machine. Actual runner transition/clock verification needs accepted trace semantics and authenticated artifacts. The time budget is cooperative: an in-process callback cannot be preempted, and input/module isolation is not implemented by this CLI. A real frozen run requires the separately approved process supervisor, bounded inputs and exact authorization before execution. This harness review makes no new run authorization or final #241 acceptance.

The result/folder field assumptions above still need compatibility receiving against Ved's first actual RULE-02 records. The PR is a usable reviewed verifier harness, not a claim that rules-v1 is implemented or verified. The original primary-domain oracle hand-count facts are retained; no new scientific system run was performed by this review.

The reader validates the documented trace envelope and start/plan-field subset, not every legacy F02 check-result/abstention semantic. It must still receive actual adapter fixtures before claiming complete serialization compatibility. Actual policy/runner source identity cannot be authenticated by --rules-v1 alone; the report records that study acceptance is not established by the harness or the caller flag.
