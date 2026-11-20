# November 19 focused rule-system study and November 28 delivery

Status: manager-approved plan, not implemented results. Instruction deployment 1.30, authorized by Matty in this chat on November 19, 2026. Professor Hasan's reply was supplied by Matty; this document paraphrases its research guidance without publishing private email addresses or claiming new course deadline confirmation.

## Why the plan changes

The original source-dependent Agent-versus-Plain held-out study remains unperformed. Source permissions, provenance and verified episode-plus-forecast inputs were not established by #60; closing that issue as not planned did not resolve them. November 18 evidence-only delivery protected the deadline. Hasan recommends a stronger focused alternative: lift explicit rules from a few representative examples, lower them into an executable discrete system, independently verify safety and progress, and, if feasible, test on new synthetic cases not used to develop the rules. Demonstrate at least two scenarios and compare against existing systems where feasible.

New question: Can a small set of explicit rules reproduce safe, explainable scheduling decisions and generalize to unseen synthetic scenarios?

This is a separately scoped study, not completion of the original held-out protocol. Keep existing permitted development evidence as a backup. No positive outcome is promised. Source B1-B3 remain unresolved and B4 provisional. Do not repurpose the 40 private development episodes, restricted source CSV, old held-out selection, dates or nonce for this study.

## Smallest complete study

Scenario A: independently authored synthetic jobs fit capacity; a lower artificial carbon-score slot exists within a flexible job's deadline. Demonstrate valid time-aware scheduling and its delay/score trade-off.

Scenario B: an independently authored overload or impossible deadline triggers checked fallback or explicit rejection. Demonstrate that an invalid proposal does not execute. Distinguish rejection from completion; include a feasible delayed-work subcase to exercise progress.

Lift rules from permitted public illustrative traces and declared assumptions. Record which example/assumption supports each rule; do not claim automatic learning. Use existing public fallback behavior as motivation, not an unverified reconstructed training set. The rule system covers visible arrivals, capacity, legal starts, deadlines, deterministic carbon-score preference/ties and checked fallback. Explanations must identify fired rule IDs, relevant state and exact arithmetic. This establishes inspectability/trace consistency only; human faithfulness or universal explainability claims require separate evidence.

Reuse compatible simulator/contracts and Greedy A/B implementations. Do not silently modify old policies, schemas, runtime defaults, old data or sealed scientific records. No new ML training, raw-source recovery or live LLM experimentation is on the critical path. Existing Agent evidence is illustrative unless genuinely comparable on identical inputs under an accepted protocol.

## Owners and deadlines

All dates below are November 2026, 18:00 America/Phoenix (UTC-07:00). Dates are latest completion deadlines, not permission to wait. Start ready work immediately, publish working handoffs early and report concrete blockers as soon as found.

| Task | Accountable owner | Deadline | Required handoff |
|---|---|---|---|
| RULE-01 / #239 | Matty | Nov 20 | Question, two cases, rule table, state bounds, metrics, synthetic provenance and agreed consumer boundaries |
| RULE-02 / #240 | Ved | Nov 22 | Executable scheduler, trace/explanations, checked fallback, negative tests and exact working commit; Matty supplies rule logic |
| RULE-03 / #241 | Nisha | Nov 23 | Independent verifier, bounded reachable-state evidence/counterexamples and explicit progress assumptions |
| RULE-04 / #242 | Edison | Nov 25 | Frozen isolated synthetic test set, rule vs Greedy A/B results, denominators and reproducible tables/plots |
| RULE-05 / #243 | Reimo | Nov 25 | Methods, workflow diagram and report integration; provide requested materials to Edison/Ved |
| RULE-06 / #244 | Matty | Nov 28 | Nov 26-27 direct fixes/reproduction, then final audit and delivery candidate; Ved reproduces and Nisha checks independence |

| RULE-07 / #246 | Edison and Ved | Nov 25 | Two-scenario demo; Edison coordinates package/visuals, Ved executable wiring/replay; both proactively request needed teammate materials |

Matty's specification is first on the critical path. Nisha starts the verification harness, Edison the generator/evaluation harness and Reimo the report skeleton in parallel; they do not wait for the entire scheduler. RULE-02 implementation acceptance needs RULE-01's stable boundaries. RULE-03 final acceptance needs exact executable code. RULE-04 scoring needs rule/verifier freeze; RULE-05 final tables need RULE-04 evidence. RULE-07 demo preparation starts immediately in parallel; its final execution needs RULE-02, independent findings need RULE-03 and displayed comparison results need RULE-04. Edison and Ved request exact materials from Matty, Nisha, Reimo and other affected owners rather than waiting for unsolicited handoffs. November 26-27 is protected repair time. November 28 is the internal delivery candidate, not a newly asserted official submission deadline. Existing course/release confirmation stays in #16.

## Demo responsibility: final manager amendment

Matty explicitly assigns demo production jointly to Edison and Ved. Edison coordinates the storyboard, visuals and delivery package; Ved leads executable wiring, repeatable commands and replay. Both must proactively ask teammates for the exact materials they need and record requests/checkpoints in #246: Matty supplies rule/scenario specifications, Nisha independent verification/bounds, Reimo methods/diagrams, and relevant owners the permitted result artifacts. Reimo retains report/methods ownership, not demo production. Do not let a missing optional visual block executable preparation. The demo must show both scenarios with actual evidence; unimplemented or untested behavior stays labeled, never presented as a result.

## Evidence gates and evaluation isolation

Before execution, Matty records the bounded synthetic protocol: exact state-space bounds and case counts, generator/version/seeds, code/specification hashes, runtime/resource/stop ceilings, expected outputs and separate-use authorization. This plan authorizes preparation, implementation and ordinary offline synthetic tests, not unspecified research batches, old source operations or live calls. Affected consumers agree on exact new shared boundaries; existing merge and instruction-authority rules remain.

Independent verification must not call the production checker to obtain its verdict. Use a separately implemented oracle and enumerate all reachable states within the declared small finite domain where practical. Report number of states/transitions, exhaustive versus sampled coverage, violated properties and counterexamples. Property tests/simulation alone are not a proof; bounded exhaustiveness establishes only those stated bounds and assumptions.

Safety: no invalid starts execute; respect arrivals, capacities, unique starts, deadlines/explicit failure status and completion-only slots. Progress: under declared finite arrivals, feasible jobs, horizon and scheduling/fairness assumptions, accepted work completes within the stated bound; otherwise report rejection/deadlock/counterexample honestly. Greedy carbon preference must not silently starve work. Do not equate eventual rejection with successful work completion.

Author new artificial workload and carbon-score inputs with explicit provenance; never infer real-world CO2e or calibrated distributions. Use distinct development and evaluation generation/seeds. Freeze rules, metrics and verifier before generating unseen evaluation cases. Record case hashes and counts, include normal and infeasible strata, and never tune on the final set. If failures cause rule changes, retain the failed results and use a fresh untouched set for generalization claims.

Report violations, completed/rejected/unfinished quantities, turnaround delay with denominator/censoring, modeled score and fallback frequency. Compare identical workloads/profiles across rule scheduler and Greedy A/B; equal-work reduction is reported only when its accounting gate passes. Otherwise show blocked/not comparable, not zero or a misleading Pareto improvement. Confidence statements require an appropriate design and sample count. Generalization is limited to the documented synthetic distribution; physical operations, arbitrary scale and the original research question remain untested.

## Overdue work and direct fixes

Matty preauthorizes his AI assistant to reassign only unfinished scope after a recorded deadline passes. At its next execution, the assistant checks actual delivered artifacts and CI, preserves current work, selects an available capable teammate, records old/new owner and reason, and tags both with the exact remaining artifact and revised checkpoint. Matty is the fallback implementer when no suitable available owner is established. A verifier must not independently certify code they wrote; preserve separation by assigning an uninvolved verifier. Missing external evidence, human judgments or independent acceptance cannot be fabricated.

This is an automatic decision rule when the assistant is running, not an installed unattended timer or promise of work while the assistant is inactive. No task-monitor automation has been installed. Start early; deadlines do not replace handoffs or authorize waiting. Fix technical defects directly, run affected checks and notify the original owner of the issue/fix/evidence; do not send the job back for another correction round.

## Update every local instruction copy

Main is authoritative. Teammates and their AI assistants must fetch origin/main and read deployment 1.30 in AGENTS.md, PROJECT_MASTER.md, all numbered 00-04 files and their role master before continuing. Preserve dirty/unpushed work and unmerged branches. If clean, fast-forward the local main safely; otherwise read current main instructions using git show without resetting local code. Copy the published files into any separate assistant instruction location verbatim, recording the main commit/version; do not independently rewrite or publish masters. Confirm version/commit in the assigned issue. Authority to synchronize local copies does not grant authority to edit GitHub masters. Merge code only after exact checks pass; verify main CI and inclusion before deleting merged branches.

## Issue disposition and preserved work

#95 old held-out human IRR repeat, #164 old P07 held-out scoring and #166 original full-study I03 are superseded, closed NOT_PLANNED with history intact; no completion is claimed. Their relevant verification/reproduction work is explicitly scoped in RULE-03/06. #60 remains closed NOT_PLANNED. #16 official requirements/release and #223 report integration remain open. #231 stays as professor-feedback traceability: grouped ML CV/hybrid rankers are outside this narrow critical path; arithmetic rule explanations and supported delay-impact reporting are incorporated without claiming earlier proposed experiments ran. Keep Reimo's unmerged PR #237 intact for a separate content review; this plan does not delete or merge it.

## Plan checks performed before assignment publication

Pass 1, scope: two scenarios, explicit lift/lower/independent verification, isolated new synthetic testing and bounded comparison match supplied professor guidance; old research question remains distinct.

Pass 2, dependencies: RULE-01 through RULE-06 each have one accountable owner; RULE-07 has explicitly authorized Edison/Ved joint demo ownership with a defined coordination/technical split; parallel preparation precedes sequential freeze/verification/evaluation; no waiting loop or missing handoff is intentionally introduced.

Pass 3, science: independent implementation, finite proof bounds, nontrivial progress assumptions, unseen-test isolation, permitted input provenance, honest failures and equal-work gates are specified before scoring.

Pass 4, delivery: core artifacts due Nov 25, protected Nov 26-27 repair buffer, Nov 28 audited candidate; preserve old work, course/release checks and evidence-only fallback. These are manager planning checks, not teammate acceptance or scientific results.
