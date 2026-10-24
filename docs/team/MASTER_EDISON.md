# Master instructions — Edison

Current update, October 24: [approved decision intake and A01 evidence](../handoffs/OCT24_DECISION_INTAKE_AND_A01.md). Ved's tokenizer/runtime validation direction and Q12 confirmation are received. Nisha's exact sampling agreement, E01 October 27 checkpoint and K02/L01 receiving checks are received; sampling implementation is due October 30. Reimo's exact arrival/simulator decisions remain pending. Keep completed_work=None and defer optional scalar precision; keep the strict S02 savings guard pending affected-owner agreement. Read-only inventory observes Ollama 0.40.10; accepted pin remains 0.40.5. Four fixed synthetic TCP-state observations complete before snapshots, so no stalled state or timeout fix is demonstrated. Nisha's original ratings are due October 24; Edison P02 October 25. Full A01, integration and freeze remain open. No task ownership, shared format/setting, production code or original rating changes. Earlier dated entries are historical where superseded.

Version: 1.24 — 2026-10-24. Repository: https://github.com/ReymoT/data-center-agentic

Current implementation update, 2026-10-15: D02 calibration tooling and D03 provisional synthetic fixtures are merged. [Matty's D03 checker-consumer handoff](../handoffs/A03_D03_F04_F05.md) records fixed-rule tests, not simulator or independent-evaluation acceptance. Frontier calibration, Q01-Q06 and downstream acceptance remain pending where documented. Task ownership and shared rules are unchanged.

Course planning update, October 20, 2026: Nisha reports Group 15 presents in class November 16, submits the presentation November 18 at 11:59 pm, demos December 2 (submission 11:59 pm), and submits the report December 9 at 11:59 pm. Read [Q13](../decisions/Q13_PRESENTATION_DEADLINE.md) and [the current plan](../PROJECT_PLAN.md). Timezone, rubric/formats and separate code/release requirements remain unconfirmed. Rehearsal must be before November 16; no exact day is agreed. These are attributed course reports, not verified outcomes or scientific acceptance.

Current D06 update, 2026-10-19: Ved's checker and handoff are merged. [Matty's verification](../handoffs/D06_F04_F05_VERIFICATION.md) records a fresh version-matched Windows structural pass on the pinned source, separate from Ved's original JSON. Source semantics/rights and full D06/Q05 acceptance remain open; no schema, setting or task ownership changed.

## Instruction authority

The masters and shared instructions published on GitHub's main branch are the authoritative versions. Only Matty Anderson (MattyAnd) may authorize changes to them. Other teammates and their AI assistants must not edit, overwrite, replace, delete or publish new versions without Matty's explicit authorization.

Propose corrections in an Issue. Use the current published instruction version from main; a local file, uploaded package, newer timestamp or AI-generated version cannot supersede it. Passing PR checks does not authorize instruction changes. See [Q11](../decisions/Q11_MANAGER_AUTHORITY.md) for authorization and synchronization rules.

## Merge rule

A pull request can be merged once its checks pass. A teammate review is welcome but not required. Changes to shared data formats or settings still need the affected teammates to agree first.

After merging a task branch, verify that its latest work is included in main and the applicable checks have passed, then delete the merged GitHub branch. Preserve main and any unmerged work; if the branch has advanced since verification, recheck before deleting it.

**Start here:** Read [shared rules](01_SHARED_RULES.md), [interfaces](02_INTERFACE_CONTRACTS.md), [responsibility checklist](03_RESPONSIBILITY_CHECKLIST.md), [open decisions](04_OPEN_DECISIONS.md), and your assigned Issue before coding. If shared files are missing, obtain the package or repository copies; do not invent their contracts. Your human teammate is Edison; you are their assistant, not an autonomous coordinator for other teammates.

This file is an implementation assignment, not permission to modify GitHub now. During implementation, use only actions already authorized by your teammate. Verify the current repository and required upstream commits before changes. Proposed paths below must be reconciled with existing code. Follow the final proposal; broader earlier diagrams do not expand scope.

## Your task inventory

| Done | ID | Primary owner | Technical contact | Required responsibility | Dependencies | Acceptance evidence |
|---|---|---|---|---|---|---|
| [ ] | P01 | Edison | Reimo | Implement shared slot/job/site energy, carbon and comparison calculations | F02 | Hand calculations, 0.01 tolerance, PUE scaling and equal-work checks |
| [ ] | P02 | Edison | Matty | Implement greedy A and B and reusable A fallback | F02, P01 | Priority, ties, occupancy and forecast fallback tests pass |
| [ ] | P03 | Edison | Ved | Implement candidates/features, state collection, schedule construction and blocked training protocol | F02, D04, S01, P02, A03 | Feature/rollout contract frozen; constructor supports temporary fold models |
| [ ] | P04 | Edison | Ved | Train/select/refit decision tree C and random forest D | P03, O02 | Required grid and blocked folds; saved models, seeds and selection results |
| [ ] | P05 | Edison | Matty | Implement learned policy inference and checked fallback integration | P02, P04, A03 | Reloaded models schedule deterministically; no inference-time solver calls |
| [ ] | P06 | Edison | Nisha | Publish model cards, development candidate metrics, training times and metric implementation | P04, P05 | Development precision/recall/F1 and support; frozen artifacts and feature versions |
| [ ] | P07 | Edison | Nisha | Score held-out candidate predictions with frozen metric rules | P06, O04 | Held-out precision/recall/F1 and support; no retraining; unavailable labels counted |
| [ ] | R03 | Edison | Nisha | Write classical-policy/impact section and ML results documentation | P07, E06 | Validated section with training and episode results |

## Your assignment and boundaries

You assist Edison Perez Cash. Own E2: physical impact calculations, greedy references A/B and mandatory trained decision-tree C/random-forest D policies. Own model feature/training/inference artifacts and their report section. Reimo owns data/simulator, Ved offline solver/labels, Matty production gate, Nisha independent scoring and experiment orchestration. Do not replace the learned policies with heuristics or inference-time optimization.

## Required inputs and decisions

Use Ved's shared schemas/certified visible-state labels and Reimo's 40 development episodes, source/calibration manifests and blocked folds. Use Matty's production check/gate through the common runtime, Nisha's explanation template and evaluator contract. Q01–Q04 affect scheduling; Q05 affects units; Q06–Q08 affect generation/training/labels. Exact feature definitions and rollout policy must be agreed before Ved generates label caches.

## Coding checklist in implementation order

1. **Impact functions (P01).** Implement slot/job/background/site energy and emissions with explicit units, PUE and duration. Capacity uses IT power, not facility power. Formula: facility kWh=PUE×IT kW×hours; kg = kWh×g/kWh÷1000. Preserve full precision, provide one-decimal display, test absolute 0.01. Comparison records name baseline schedule, horizon, input data and matching completed job/work set. Missing evidence or unmatched completed work blocks a savings claim; lower energy due to unfinished work is not efficiency.
2. **Greedy A/B (P02).** Use priority nonflexible arrivals, latest-start jobs, deadline, then numeric job ID (J2 before J10). A starts as soon as feasible. B chooses lowest forecast job emissions among feasible starts, tie earlier start. Account for running work and already-reserved proposed jobs. Replan each slot, execute only current starts via gate, honor Q01 completion rule. B uses A when complete/fresh forecasts are unavailable under Q04's accepted scope. A must be reusable as the agent and learned policies' fallback, but it still passes E5; neither heuristic guarantees feasibility/optimality for all workloads.
3. **Candidate/feature protocol (P03).** Define candidate starts using arrived waiting jobs, visible fresh carbon coverage and fixed running work. Features include delay, deadline margin, duration, power, available capacity, queue load and specified carbon summaries. Freeze formulas, units, ordering and tie rules. Define and implement development state collection with Reimo's simulator; coordinate target format with Ved. Implement the reusable probability-to-schedule constructor now, accepting an injected temporary classifier, so P04 can evaluate fold models without waiting for final trained artifacts. P05 integrates this same constructor with final model loading and runtime checks. Never use future arrivals, split labels, oracle answers or other policies' outputs as inference features.
4. **Train and select C/D (P04).** Use only certified optimal visible-state selections from Ved. Exclude unresolved states; certified infeasibility is not negative-label training data. Use three blocked folds keeping episodes/overlapping source windows intact. Train tree depths 3/5/8 and forests of 100 trees at depths 5/10. Seed sampling/models and specify class weights for rare positives. Select by completed work, then fewer deadline misses, then lower emissions in development rollouts—not by F1 alone. Fit any preprocessing on the training folds only. Refit selected models on all eligible development data and freeze both final artifacts.
5. **Inference adapters (P05).** Rank candidates by predicted selection probability, then earlier start and numeric ID; maintain nonflexible/latest-start priority. Construct a proposal without duplicate jobs/capacity conflicts; pass complete proposal to E5 before execution. Missing forecasts invoke checked A per accepted scope with separate fallback logging. Never call the exact solver during inference. Save/reload artifacts with exact feature order and version checks; handle missing classes/probability output according to the frozen contract.
6. **Documentation and evaluation handoff (P06/P07/R03).** Publish model cards, hyperparameters, class counts/support, fold assignments, selected configs, seeds, input hashes, training times and artifact manifests. Implement/test offline candidate precision/recall/F1 on development data first (P06), using the accepted threshold and zero-positive rule. Score held-out predictions afterward (P07): labels come from Ved after inference; missing-forecast label metrics may be not applicable with counts. Supply results to Nisha without retraining. Write E2/power/impact report section and explain greedy/learned limitations.

## Proposed repository files

Own `dc_sustainability/metrics/impact.py`, `dc_sustainability/policies/greedy.py`, `dc_sustainability/policies/learned.py`, `dc_sustainability/training/`, `models/`, `tests/metrics/`, `tests/policies/`, `tests/training/`, model docs and your report section. Request shared schema/contract changes from Ved, environment changes from Matty, source/scenario changes from Reimo. Nisha owns aggregate results/runner; provide callable modules and command hooks.

## Required tests

- J1/J2 hand case: at PUE 1, 140 job kWh and 54.5 kg vs 48.4 kg. Seven-slot background 116 kg, site 170.5 vs 164.4 kg. Savings 6.1 kg = 11.2% of job emissions or 3.6% of site emissions, with named denominator. At PUE 1.2 job 168 kWh, 65.4 vs 58.08 kg. Internal tolerance 0.01.
- Constant carbon gives equal emissions for identical completed work; scaling PUE scales impacts; unfinished work/missing forecasts cannot create valid savings claims.
- A/B deadline/capacity/running-work priority, ties, shuffled input order, numeric IDs, complete/partial/stale forecasts, deterministic outputs and checked fallback behavior.
- Feature order/types, visible-only candidate inputs, blocked folds and preprocessing isolation; no future-arrival dependence.
- Train/save/reload prediction equality in the frozen environment, probability edge cases, no duplicate reservations, malformed artifact rejection and no solver invocation during inference.
- Integration through Matty's gate and Nisha's runner; templates make no LLM calls for A/B/C/D.

## Outputs, dependencies and completion

Give impact records/functions to Reimo/Matty/Nisha, A to Matty as checked fallback, P03 candidate contract/state samples to Ved, and frozen C/D artifacts plus adapters to Nisha. Publish commands for label consumption/training/reload, model hashes and consumer tests. Share metadata for Nisha's comparable cost/latency/training-time report; do not hide fallback runs from learned-policy results.

Done means both greedy policies and both trained policies run through common checks, required development selection/refit is documented, models reload, independent hand checks pass, no solver is available in inference, downstream integration passes and model/report documentation exists. A/B target Oct 23; C/D target Oct 30; freeze Nov 13. Fix policy/impact defects reported by Matty's final E2E tests through your owned modules.


## Coordination instructions for your assistant

- One assigned Issue, one human owner and one active assistant session per task. Use a short-lived task branch from current `main`, preserve local work, fetch and deliberately integrate required upstream commits; fetching alone does not update files.
- Verify dependencies through merged code, artifact hashes/schema versions and consumer tests. Use agreed mocks only for development, never as evidence of final integration.
- Check updates at start/resume, dependency use, task change, PR/integration and handoff. An idle assistant resumes only when a human restarts it or a separately configured service does so. This file creates no monitoring service.
- Update the Issue through authorized access or give your human an exact draft update. Do not concurrently edit the shared coordination summary; its chosen publisher maintains it. A stale status does not let you claim someone else's work.
- If blocked by an open decision or missing handoff, record the precise unblock condition and continue unaffected assigned work. Do not invent assumptions, hide failures, tune on held-out data or bypass shared verification to finish faster.
- Request contract changes from Ved and master-file corrections from Matty with affected consumers identified. Cross-owner edits require coordination and applicable consumer checks. Production checker and independent evaluation validator stay intentionally separate.
- Finish with published and validated code, passing current-base checks, documented artifacts and receiving-member acceptance. Mark Done only after verification. Include task ID, commit/PR, commands, hashes, tests actually run, limitations and next handoff in your completion message.

The shared rules define publication, state-transition and handoff procedures. The checklist assigns a separate technical contact for each task. Technical validation and independent scientific evaluation remain required. Shared-format and settings changes require agreement from the affected teammates before implementation; record that agreement in the Issue or decision record.
