# RULE-03 independent verifier: harness status

November 22 receiving status: Ved's current scheduler is merged through #257 and historical trace evidence through #258. Actual code is no longer missing. #241 still requires current-code mapping, accepted binding/freeze and independent bounded verification; the old 176361a archive is not that result. See [current handoffs](../handoffs/NOV22_MANAGER_READINESS_AND_HANDOFFS.md). Earlier dated pending-code notes remain historical.

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
| Feasibility labels | Recomputed with the brute-force joint-assignment oracle and compared with each case's `feasibility_label`. The legal-action-graph oracle cross-checks them under one combined supplied-set budget |
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

**Exit codes:** 0 PASS, 1 FAIL, 2 INCOMPLETE. Output files are created exclusively. The checker has 51 tests, all on hand-built fixtures. A local PASS covers only the supplied cases and comparisons, not study acceptance.

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


## Case-set checker manager review — November 20

The review reproduced 18 failing regressions on the submitted version before fixes.
The updated case-set suite has 51 passing tests; the case/verifier/trace/supervisor
focused suite has 144. These are authored unit fixtures, not generated research sets.

- Empty collections are refused; empty sets or skipped counts cannot produce an
  overall PASS. Counts must be strict positive integers no greater than the
  recorded 40 per stratum, or None for an explicitly incomplete diagnostic.
- All supplied sets share one budget (at most 10,000 states, 50,000 transitions,
  600 seconds). Assignment search also checks this cooperative budget; out-of-domain
  cases are rejected before expensive enumeration. Actual counters, unfinished
  label IDs and graph-disagreement case IDs are retained. These defaults do not
  grant another run allowance or authorization; actual callers must use the exact
  authorized remaining combined budget and process supervision.
- The checker supports only canonical specification hash
  `9597931fcee09bc895605b65401483c9c3658da9e0bdf7c954f8669dfa8542bd`.
  A changed specification requires reviewed matching checker assumptions, rather
  than silently hashing a protocol this implementation does not enforce.
- Unknown case/job fields and competing score encodings are refused. Only explicit
  case `metadata` and `generator_attempt` fields are ignored for identity. This
  checker-local shape remains provisional until Edison's actual generator format
  is received; it does not change F02 or establish shared-format acceptance.
- Reader resource limits are two supplied sets, 120 cases per set and 8 MiB per
  input file. These are defensive parser limits, not new experimental counts.
  Duplicate JSON keys and nonfinite JSON constants are refused. CLI malformed
  input reports are preserved with exit1; INCOMPLETE returns2. Existing output
  paths and racing creation cannot be overwritten. `--max-states`,
  `--max-transitions` and `--max-seconds` can only reduce the prospective ceilings.
- Reports include the checker, verifier and parser source hashes. CLI summaries
  state that study acceptance is NOT_ESTABLISHED. A single supplied set cannot
  establish development/final isolation. Even two sets do not authenticate their
  roles, seeds, generation history, freeze chronology or source provenance.
- Missing-forecast cases expose no scores. Their hidden accounting weights and
  the nonconstant pre-removal profile cannot be checked from this input shape;
  no claim of complete generator/metric/accounting validation is made. Workload
  overlap remains reported, not silently treated as independent sampling.

The original no-overlap, feasibility and diversity work is preserved. Actual
RULE-02 compatibility, generator receiving, frozen-system verification and final
study acceptance remain open in #239/#241/#242. No actual generator, scheduler,
model, source or research batch was run for this review.

## Accounting-sidecar checker — November 21

This closes the gap noted above: missing-forecast weights and the hidden
nonconstant profile can now be checked, using the evaluator-only sidecar that
RULE-04 writes (`rule_study_accounting_weights_v1`, #253). Code:
`dc_sustainability/evaluation/rule_study_accounting.py`, CLI
`scripts/check_rule_study_accounting.py`. It does not import the generator.

Checks on one supplied visible-set/sidecar pair:

- **well_formed:** exact sidecar and entry fields, `record_kind`, 30 integer
  (not bool/float) weights, lowercase 64-hex hashes and a bool visibility flag.
- **binding:** same `set_id`, `case_set_sha256` equals the canonical hash of the
  supplied visible set, and `generator_source_sha256` matches the set metadata.
- **coverage:** every visible case appears exactly once in the sidecar, with no
  extra or duplicate IDs.
- **identity:** full-case and workload hashes are recomputed with the case
  checker's own identity functions (full identity uses visible scores, so null
  for missing-forecast cases).
- **weight_domain:** slots 0-5 in {100, 200, 300}, drain slots 6-29 equal 200.
- **visibility:** `weights_visible_to_policy` is false exactly for
  missing-forecast cases; visible scores equal the sidecar weights; hidden
  declared scores stay null and known accounting fields are absent from visible metadata. This does not prove arbitrary information-flow isolation or actual policy routing.
- **hidden_profile:** normal and missing-forecast weights are nonconstant over
  slots 0-5. Overload profiles may be constant.

`job_impact` and `site_impact` give independent reference arithmetic for the
declared unit (power kW x 1 h x PUE 1.0 x weight, score-kWh; site adds 20 kW
background over all 30 slots), so Edison's metric records can be recomputed
once they exist. Empty inputs are NOT_RUN/INCOMPLETE, never PASS. Exit codes and
exclusive output follow the case checker.

Nisha reported local development receiving in PR #255 (development seed only, files not supplied or committed): her 120-case pair passed the sidecar and visible-set checks. This is her reported local observation, not a manager receipt of retained files. The manager review separately tests hand-built pairs and one development case per stratum. This is consistency of a supplied pair,
not seed/provenance/freeze authentication, metric acceptance or any policy
result. No final seed, scheduler, model, source or research batch was run.


## Accounting-sidecar manager review — November 21

The review reproduced 19 failing regressions before correction. The updated
accounting suite has 59 tests; the combined accounting/generator/case/trace/verifier
and dummy-dispatch focused suite has 278. These are unit fixtures, not final-set
or policy results. The production checker and generator are not imported by the
accounting implementation; generator compatibility is exercised only in tests.

- Duplicate visible IDs no longer silently overwrite each other. Coverage checks
  both sides; an extra sidecar entry still fails when there are no visible cases.
  A known failure is FAIL even when the checked-item count is zero.
- Matching malformed generator hashes cannot pass binding. The supported claimed
  specification and visible-set artificial-unit label are checked when present.
  Header visibility must identify an evaluator-only sidecar. Weight units must
  be the actual generator's artificial score-kWh convention or the explicit
  weight-only fixture label; physical-emissions labels are not silently accepted.
- Known accounting fields in nested visible metadata are flagged. Scores/null
  and visibility flags are still checked, but no claim is made that this detects
  arbitrary encodings, prevents seed reconstruction or proves runtime routing.
- Arithmetic helpers refuse bool/float/NaN/infinite/negative/nonnumeric weights,
  malformed lengths and unsupported start/case shapes. They calculate exact
  synthetic integer arithmetic over the supplied starts; they intentionally do
  not reject away unsafe execution evidence or certify capacity/deadline safety.
  Callers still need independent schedule checks and accepted completed-job sets.
- CLI malformed-input failures produce preserved FAIL reports with exit1;
  INCOMPLETE returns2. Existing/racing outputs are never overwritten. Reports
  include checker/case-parser/verifier source commitments and explicit scope.

A pair PASS is not a feasibility/stratum/count/overlap verdict: run the separate
case checker too. `study_acceptance` and external binding authentication remain
NOT_ESTABLISHED. Matching a hash claim in supplied metadata does not authenticate
who generated the pair or its seed/freeze/source bytes. Independent impact-total
recomputation against actual metric records, retained input receiving and actual
RULE-02/frozen-policy verification remain pending in #241/#242/#244. The accepted
specification task #239 is closed; this review does not reopen it or approve a run.
No final seed, policy/model/source/private-data operation ran. Only synthetic
hand-built and development-seed unit fixtures were used.

## Current-code receiving of RULE-02 — November 22

For #241 after #257/#258. Code: `dc_sustainability/evaluation/rule_study_receiving.py`,
CLI `scripts/receive_rule_study_system.py`, tests
`tests/evaluation/test_rule_study_receiving.py` (29 tests).

**Why runs, not a separate policy model.** For a closed case every arrival is known and
rules-v1, the production checker, the Greedy A fallback and the simulator are
deterministic, so the policy-induced graph of the actual system is one path per case.
Verifying the system on a domain is therefore one run of the real common runner per
case and policy, followed by independent replay. No reimplementation of rules-v1 is
used as the system under test.

**Independent pin.** `reconstruct_pin` rebuilds, without calling the runner's
`make_bindings`: the canonical specification hash, the adapter map hash over every
`dc_sustainability/rule_study/*.py` (LF-normalized), the generator and Windows Python
3.12 lock hashes, git HEAD and clean-tree status. At main `759a8c3` it gives adapter
`6b4c4350...1a1c8c`, spec `9597931f...a8542bd`, generator `ab795084...df4072`, lock
`38562754...f9034c`; these equal the runner's own bindings (a test checks this).

**Domain mapping.** `case_spec_for` maps verifier cases (primary 64, extended 1,024,
authored A, B, B-fault, B-progress) to the runner's `CaseSpec` with PUE 1 and a perfect
artificial forecast when scores exist. The authored mapping reproduces the runner's own
authored `case.json` byte-for-byte. Baselines skip the injected B-fault case.

**Artifact and binding check.** Every decision and result record must carry exactly the
pinned bindings; `case.json` must hash to its case binding; every referenced raw state,
snapshot and transition file must exist and hash to its reference; every decision needs
its completion commitment. Binding status is PASS only for a git pin on a clean tree;
a test-only commit or a dirty tree is INCOMPLETE, any finding is FAIL.

**Replay.** The merged trace reader replays the records against the verifier's own
reconstruction (S1-S5, P1, P2 and R04 arithmetic). Overall is FAIL on any run error,
refused trace, property/arithmetic FAIL or artifact finding; PASS needs a clean binding
PASS and only PASS/NOT_RUN properties; otherwise INCOMPLETE.

**What has run.** Only unit tests with a test-only commit on the authored cases and the
first three primary cases (rules-v1 and Greedy A): no run errors, no refused traces, no
artifact findings, S1/S2/S3/S5/P1/P2 PASS, rules-v1 arithmetic PASS and authored S4 PASS.
These are implementation checks, not the frozen-system verification result.

**Bounded plan (not run).** `python scripts/receive_rule_study_system.py --domain primary
--domain authored` prints it without running anything:

| Domain | Cases | rules-v1 runs | with Greedy A/B |
| --- | --- | --- | --- |
| primary (required) | 64 | 64 | 192 |
| authored A/B | 4 | 4 | 10 |
| extended (optional supplement) | 1,024 | 1,024 | 3,072 |

At most 30 decisions per run. Replay uses one shared budget of 10,000 states, 50,000
transitions and 600 s; the extended supplement is likely to hit it and would then be
reported INCOMPLETE, separately from the primary result. Runs take roughly 2 s each
locally. `--execute` needs a new `--out` directory and should be used only for an
approved run on a clean checkout of the pinned commit.
