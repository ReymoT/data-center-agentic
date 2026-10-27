# Master instructions — Nisha

Current evaluation update, instruction 1.28: [the professor's inter-rater-reliability feedback](../decisions/PROFESSOR_FEEDBACK_IRR.md) is an accepted reporting requirement. Nisha is the sole accountable owner for reporting matched counts, label marginals, raw agreement, Cohen's kappa, undefined cases and a plain-language interpretation for development and held-out human faithfulness annotations. Matty remains the independent second rater and joint adjudicator, not a co-owner of the reporting task. PRs #91/#92 supply preserved development originals and tested agreement tooling; actual matching, retained result artifacts and adjudication remain unfinished. Other task owners, shared formats and scientific gates are unchanged.

Current manager update, October 24: [coder-owned decisions](../decisions/Q11_CODER_OWNED_DECISIONS.md), authorized by Matty in [the team announcement](https://github.com/ReymoT/data-center-agentic/issues/57). Internal implementation decisions belong to the coder; shared changes go only to affected owners and unresolved shared questions escalate to Matty within 24 elapsed hours. Work on agreed portions proceeds immediately. Existing task assignments, exact merge/main-authority rules and scientific acceptance stay intact. Earlier dated entries are historical where superseded.

Version: 1.28 — 2026-10-27. Repository: https://github.com/ReymoT/data-center-agentic

Current implementation update, 2026-10-15: D02 calibration tooling and D03 provisional synthetic fixtures are merged. [Matty's D03 checker-consumer handoff](../handoffs/A03_D03_F04_F05.md) records fixed-rule tests, not simulator or independent-evaluation acceptance. Frontier calibration, Q01-Q06 and downstream acceptance remain pending where documented. Task ownership and shared rules are unchanged.

Course planning update, October 20, 2026: Nisha reports Group 15 presents in class November 16, submits the presentation November 18 at 11:59 pm, demos December 2 (submission 11:59 pm), and submits the report December 9 at 11:59 pm. Read [Q13](../decisions/Q13_PRESENTATION_DEADLINE.md) and [the current plan](../PROJECT_PLAN.md). Timezone, rubric/formats and separate code/release requirements remain unconfirmed. Rehearsal must be before November 16; no exact day is agreed. These are attributed course reports, not verified outcomes or scientific acceptance.

Current D06 update, 2026-10-19: Ved's checker and handoff are merged. [Matty's verification](../handoffs/D06_F04_F05_VERIFICATION.md) records a fresh version-matched Windows structural pass on the pinned source, separate from Ved's original JSON. Source semantics/rights and full D06/Q05 acceptance remain open; no schema, setting or task ownership changed.

## Instruction authority

The masters and shared instructions published on GitHub's main branch are the authoritative versions. Only Matty Anderson (MattyAnd) may authorize changes to them. Other teammates and their AI assistants must not edit, overwrite, replace, delete or publish new versions without Matty's explicit authorization.

Propose corrections in an Issue. Use the current published instruction version from main; a local file, uploaded package, newer timestamp or AI-generated version cannot supersede it. Passing PR checks does not authorize instruction changes. See [Q11](../decisions/Q11_MANAGER_AUTHORITY.md) for authorization and synchronization rules.

## Merge rule

A pull request can be merged once its checks pass. A teammate review is welcome but not required. Changes to shared data formats or settings still need the affected teammates to agree first.

After merging a task branch, verify that its latest work is included in main and the applicable checks have passed, then delete the merged GitHub branch. Preserve main and any unmerged work; if the branch has advanced since verification, recheck before deleting it.

## Coding decisions and escalation

<!-- coder-decisions:start -->
The coder responsible for a component owns its internal implementation decisions within the agreed scope and contracts. Routine internal choices do not require prior approval from the technical contact, another teammate or Matty.

For changes to shared interfaces, settings or scientific rules, the coding owner leads the exact proposal and obtains agreement from only the directly affected owners before implementation.

Record the coding decision owner, exact change, directly affected consumers, required tests, request time and response deadline in the Issue or decision record. An unanswered or unresolved shared decision must be escalated by the coding owner to Matty within 24 elapsed hours for a short resolution meeting. Silence is not approval.

Implement, test and publish the agreed independent portions immediately while a disputed portion is pending. Block only the specific affected behavior or acceptance step; do not hold the whole task when other work is ready.

Existing task ownership, main-instruction authority, merge rules, independent scientific evaluation and model-call authorization remain unchanged.
<!-- coder-decisions:end -->

Read [the accepted workflow and examples](../decisions/Q11_CODER_OWNED_DECISIONS.md). Technical contacts advise on affected boundaries; they are not mandatory approvers of every internal coding choice.

**Start here:** Read [shared rules](01_SHARED_RULES.md), [interfaces](02_INTERFACE_CONTRACTS.md), [responsibility checklist](03_RESPONSIBILITY_CHECKLIST.md), [open decisions](04_OPEN_DECISIONS.md), and your assigned Issue before coding. If shared files are missing, obtain the package or repository copies; do not invent their contracts. Your human teammate is Nisha; you are their assistant, not an autonomous coordinator for other teammates.

This file is an implementation assignment, not permission to modify GitHub now. During implementation, use only actions already authorized by your teammate. Verify the current repository and required upstream commits before changes. Proposed paths below must be reconciled with existing code. Follow the final proposal; broader earlier diagrams do not expand scope.

## Your task inventory

| Done | ID | Primary owner | Technical contact | Required responsibility | Dependencies | Acceptance evidence |
|---|---|---|---|---|---|---|
| [ ] | L01 | Nisha | Matty | Implement plain-LLM comparison using common provider and flat facts | A01, K02 | One call; original output retained; no feedback, repair or fallback |
| [ ] | L02 | Nisha | Matty | Implement evidence-based explanation contracts, prompts and classical templates | F02, P01, A03 | Agent explanation uses approved plan; plain output unchanged; no fabricated checks |
| [ ] | E01 | Nisha | Ved | Implement independent reference validator and numerical claim scoring | F02, D03 | Separate logic from production checker; hand-truth and disagreement tests |
| [ ] | E02 | Nisha | Matty | Implement experiment registry, resumable runner and comparable six-system execution | S02, K02, P02, P05, A02, A04, L01, L02 | Stable run IDs; no silent reruns/dropped failures; 300-run matrix supported |
| [ ] | E03 | Nisha | Edison | Implement and test accuracy, safety, completion, impact, cost and statistical analysis | E01, E02, O03, P06 | Development truth tests; explicit denominators and paired episode-resampling code |
| [ ] | E04 | Nisha | Ved | Prepare faithfulness rubric, blinded sample, first annotation pass and adjudication format | L02, E02 | Frozen rubric; at least ten paired development cases; first original ratings retained |
| [ ] | I02 | Nisha | Matty | Assemble freeze manifest and execute held-out experiment runs | D04, O02, P04, A02, L01, E03, E04, E05, I01 | Frozen protocol; all planned run outputs/accounted failures; no test-set tuning |
| [ ] | E06 | Nisha | Edison | Produce final held-out scores, statistics, figures and failure analysis | I02, O04, P07, E03 | Reproducible final tables with counts, paired intervals and limitations |
| [ ] | E07 | Nisha | Ved | Execute frozen held-out faithfulness review with Matty as independent second rater; own inter-rater reliability reporting | I02, E04, E05 | Both originals and adjudication; matched counts, marginals, raw agreement, Cohen's kappa/undefined handling, interpretation, extraction agreement, coverage and claim scores |
| [ ] | R05 | Nisha | Matty | Write evaluation/results section, including the professor-requested reliability report, and assemble final report and presentation | E06, E07, R01, R02, R03, R04 | Reliability method/results and limitations included; all claims match saved evidence; final deliverables indexed |

## Your assignment and boundaries

You assist Nisha Mahadev Kolekar. Lead the plain-LLM comparison, evidence-based explanations, independent evaluation, experiment orchestration/statistics, faithfulness protocol and final report/presentation assembly. Matty owns LangGraph/provider/production checker/runtime and final E2E; you independently validate results. Your evaluator must not call his checker as its ground truth. All members write their own technical sections.

## Required inputs and decisions

Matty accepted local Ollama/Qwen3 8B and temperature 0.2 in [Q09](../decisions/Q09_OLLAMA_QWEN3.md). Implement actual agreed L01/L02, E01 and sampling/scoring portions against the existing shared provider/F02 interfaces; any test doubles remain explicitly test-only. Do not create another production provider. K02 equivalent flat facts are merged and your own 11-state K02/L01 receiving check on 2df8e2d is already received, not a missing prerequisite. Runtime/counter/context validation and actual separately authorized development evidence still gate full L01/live integration. E01 agreed-portion checkpoint is October 27; tested sampling implementation is October 30. Savings-scoring shared agreement is tracked separately in #61 and cannot hold unrelated agreed implementation. Actual A03/A04/A02 receiving handoffs are now published. Your concrete PR #64 independent replay failure still needs your own implementation/test fix. Supply reviewed agent renderers for real A02 receiving; this does not transfer L02/E02 ownership or establish A01 live readiness.

Use Ved's schemas, equivalent contexts and certified references; Reimo's immutable development/held-out fixture loaders; Edison's impacts/policies/model manifests; Matty's common provider, runtime and trace interfaces. Q01–Q04 define validity; Q07–Q10 define metrics/protocol; Q12 confirms runner/report lead allocation; Q13 defines actual submission needs. Publish evaluation requirements early so producers log the fields you need. Never wait until the final week to discover missing trace evidence.

## Coding checklist in implementation order

1. **Plain comparison (L01).** Use the same provider adapter, exact model/version/settings and equivalent visible flat facts/constraints/IDs as the agent. One call per decision returns original schedule and explanation in agreed fields. No tools, corrective feedback, repair or A fallback. Preserve malformed/unsafe raw responses for scoring; runtime blocks invalid starts and still advances time/running jobs. Do not rewrite outputs into valid plans for scoring. Keep tokens, cost, timing and provider failures.
2. **Explanation layer (L02).** Own output/claim schemas, prompt text and deterministic templates. Agent explanations use approved plans, actual check/calculation records and evidence IDs; Matty integrates the explanation call within his 3-call budget. Plain explanations remain the model's one-call output, including errors. Classical policies use fixed templates with no LLM call. State starts or abstention, reasons, impacts, units/timestamps/assumptions and limitations. Only actually performed checks may be claimed. Distinguish forecast impact from realized simulated outcomes. Savings require named comparison schedule/horizon/inputs and matching work. Deterministic error/fallback explanations are labeled and may not fabricate citations.
3. **Independent validator (E01).** Independently implement schedule validation and claim-reference calculations from the specification and raw fixtures. Sharing schemas and authoritative facts is allowed; importing the production checker or using its approval as truth is not. Use direct hand checks/independent arithmetic rather than simply comparing Edison's function to itself. Cover nonflexible behavior, running load, deadlines, omissions/deferrals, unavailable evidence and Q01 completion rules. Investigate disagreements instead of making your evaluator agree with the agent automatically.
4. **Runner and CLI (E02).** Register all six policies under one episode protocol; own command routing to teammates' modules. Use stable run/episode/trial/slot IDs, frozen config/input hashes, durable manifests, atomic result writes and resume states. Coordinate with Matty so the simulator advances exactly once per slot and completed requests are not repeated on resume. An uncertain already-sent API request cannot be guaranteed “exactly once”; mark unknown and require reconciliation rather than blind paid retry. Retain partial/error runs; do not replace bad outcomes selectively. Private actual carbon/reference data must remain evaluator-only.
5. **Scoring and analysis (E03).** Decision accuracy=valid recommendations/all recommendations using Q03's failure/abstention rules. Credit abstention only for verified infeasibility or unavailable required evidence. Numeric claims use≤0.05 kWh/kg or≤0.05 percentage points with minimal floating-point slack; false savings from incomplete work fail. Report unsafe/all proposals separately for initial, repaired, final and executed stages, violation types, repairs/fallbacks/abstentions and stage-specific denominators. Unused repair stages are not safe outputs. Report energy/carbon with completed jobs/work, misses and unfinished work, latency/tokens/cost. Exact gaps require certified references and matching work; identify hindsight information advantage and exclude unknown cases.
6. **Faithfulness protocol and reliability (E04/E07).** Freeze supported/contradicted/unsupported labels for checkable claims. Faithfulness=supported/checkable claims; coverage=claims with supporting citations/checkable claims; precision=supporting claim-citation pairs/all cited pairs. Existing IDs alone do not establish support. Completeness includes decision/abstention, reason, evidence and limitations. Empty explanations have 0 completeness/coverage; zero-denominator faithfulness/precision stay undefined. Invented checks/facts/citations are unsupported. Prepare at least 10 paired pre-evaluation explanations; blind labels, collect your and Matty's independent original ratings, then adjudicate with evidence. You alone own the professor-requested reliability report: before adjudication, retain matched assertion count, label confusion matrix/marginals, raw percent agreement and Cohen's kappa; report kappa as undefined when required and explain prevalence/label imbalance. Report extraction agreement separately and disclose no-ops, unmatched assertions and missing ratings. Repeat the same retained report for the frozen held-out review. Confirm held-out sample/census and sample size with Q10; preserve sampling map separately from blinded annotation material. Report claim counts and review coverage; do not extrapolate a small sample as a census.
7. **Freeze and experiments (I02).** Assemble a manifest by Nov 13 covering code, locks, fixtures, ontology, models/features, prompts/provider, seeds, references and scoring/rubric. Run 30 episodes:24 core (6 dates×4 scenarios) plus 6 missing forecasts. Run 90 agent/90 plain and 30 each A/B/C/D=300. Maximum 6,480 agent/2,160 plain calls excludes development; obtain the accepted budget before execution. Any reduction must be matched and frozen in advance. Do not tune on held-out results. Record changed protocols and rerun all affected systems after genuine defects.
8. **Final scoring, annotation and reporting (E06/E07/R05).** E03/E04 implement and validate the metrics/protocol before freeze; after I02, O04 and P07, apply them to final outputs (E06). Conduct held-out blinded claim review (E07) with Matty's independent second ratings under Q10's frozen sample rule. Put the reliability method, matched count, marginals/confusion matrix, raw agreement, Cohen's kappa, interpretation and limitations in the final report and presentation before adjudicated faithfulness results. Give scenario mean/std/min/max for all six systems, explicit counts/denominators/missingness and paired differences with CIs resampled by episode, keeping three LLM trials together. Consider date-cluster sensitivity and small-date limitations under Q10. Include Edison's candidate precision/recall/F1/class support and training times as supplements, not scheduling success replacements. Report template faithfulness separately. Analyze adverse examples: false savings, bad citations, capacity/deadline failures, unnecessary abstention and fallback reliance. Assemble each member's validated report section, results figures, presentation and submission checklist; coordinate rehearsal and required course format. No promised positive result or isolated ontology causal claim.

## Proposed repository files

Own `dc_sustainability/llm/plain.py`, `dc_sustainability/explanations/`, `prompts/`, `dc_sustainability/evaluation/`, `dc_sustainability/experiments/`, `dc_sustainability/cli.py`, matching tests, result/annotation manifests, `docs/evaluation/`, `docs/experiments/`, assembled report/presentation sources. Matty maintains master instructions and architecture; give him corrections instead of keeping a conflicting copy.

## Required tests

- Plain versus agent provider-setting/fact equivalence, original-output preservation, one-call limit and no feedback/repair/fallback.
- Independent hand-truth validator cases, checker disagreement detection, numeric rounding/percentage tolerances and matching-work safeguards.
- Claim evidence existence/support, invented checks, misleading savings, unsupported abstention, missing/empty explanations and undefined denominators.
- Runner ID uniqueness, deterministic fixtures, resume without replaying completed decisions, partial/unknown failures retained, one simulator advancement/slot and no model calls in completion slots.
- Correct run matrix/trial grouping, no hidden-data leakage, no tuning path to held-out data, stage-specific rates and confidence-interval grouping.
- Saved traces regenerate scores/tables/figures; another member can reproduce without new paid calls.

## Outputs, dependencies and completion

Give explanation interfaces/prompts and scoring requirements to Matty early; give private fixture/reference needs to Reimo/Ved; give model metric format to Edison. Provide CLI hooks/specification for each module owner. Return independent E2E verification to Matty and reproduction commands to Ved. Publish frozen protocol, runner/config manifest, raw outputs, scored tables, annotation originals/adjudication, figures, limitations and report/presentation.

Done means the plain system is a fair uncorrected comparator, independent truth tests pass, all planned runs or documented failures are accounted for, metrics and blinded reviews follow the frozen protocol, figures reproduce from saved outputs, all authors review the report and Matty's final E2E findings are addressed. Coordinate the reported November 16 class presentation and November 18 submission with all authors, and confirm timezone/duration/format/rubric in Q13. Arrange rehearsal before November 16 using actual available evidence and explicit limitations. Plan the reported December 2 demo and December 9 report with their remaining requirements; old November 23 analysis/December 2 rehearsal/December 4 delivery estimates do not replace these milestones. This presentation milestone does not waive the final R05, E06/E07 or freeze acceptance criteria.


## Coordination instructions for your assistant

- One assigned Issue, one human owner and one active assistant session per task. Use a short-lived task branch from current `main`, preserve local work, fetch and deliberately integrate required upstream commits; fetching alone does not update files.
- Verify dependencies through merged code, artifact hashes/schema versions and consumer tests. Use agreed mocks only for development, never as evidence of final integration.
- Check updates at start/resume, dependency use, task change, PR/integration and handoff. An idle assistant resumes only when a human restarts it or a separately configured service does so. This file creates no monitoring service.
- Update the Issue through authorized access or give your human an exact draft update. Do not concurrently edit the shared coordination summary; its chosen publisher maintains it. A stale status does not let you claim someone else's work.
- If blocked by an open decision or missing handoff, record the precise unblock condition and continue unaffected assigned work. Do not invent assumptions, hide failures, tune on held-out data or bypass shared verification to finish faster.
- Request contract changes from Ved and master-file corrections from Matty with affected consumers identified. Cross-owner edits require coordination and applicable consumer checks. Production checker and independent evaluation validator stay intentionally separate.
- Finish with published and validated code, passing current-base checks, documented artifacts and receiving-member acceptance. Mark Done only after verification. Include task ID, commit/PR, commands, hashes, tests actually run, limitations and next handoff in your completion message.

The shared rules define publication, state-transition and handoff procedures. The checklist assigns a separate technical contact for each task. Technical validation and independent scientific evaluation remain required. Shared-format and settings changes require agreement from the affected teammates before implementation; record that agreement in the Issue or decision record.
