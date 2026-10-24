# Master instructions — Reimo

Audit update, instruction 1.26: [active guidance and issue audit](../handoffs/CODER_PLAN_AUDIT_2026-10-24.md) keeps the coder-owned rule unchanged, corrects received K02/readiness facts and routes P02/source/scoring work to #59/#60/#61. Reimo source ownership/blocker reply is received; October 26 is accepted for his evidence inventory only. Scientific acceptance and disputed shared behavior remain gated; ready agreed coding proceeds.

Current manager update, October 24: [coder-owned decisions](../decisions/Q11_CODER_OWNED_DECISIONS.md), authorized by Matty in [the team announcement](https://github.com/ReymoT/data-center-agentic/issues/57). Internal implementation decisions belong to the coder; shared changes go only to affected owners and unresolved shared questions escalate to Matty within 24 elapsed hours. Work on agreed portions proceeds immediately. Existing task assignments, exact merge/main-authority rules and scientific acceptance stay intact. Earlier dated entries are historical where superseded.

Version: 1.26 — 2026-10-24. Repository: https://github.com/ReymoT/data-center-agentic

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

**Start here:** Read [shared rules](01_SHARED_RULES.md), [interfaces](02_INTERFACE_CONTRACTS.md), [responsibility checklist](03_RESPONSIBILITY_CHECKLIST.md), [open decisions](04_OPEN_DECISIONS.md), and your assigned Issue before coding. If shared files are missing, obtain the package or repository copies; do not invent their contracts. Your human teammate is Reimo; you are their assistant, not an autonomous coordinator for other teammates.

This file is an implementation assignment, not permission to modify GitHub now. During implementation, use only actions already authorized by your teammate. Verify the current repository and required upstream commits before changes. Proposed paths below must be reconciled with existing code. Follow the final proposal; broader earlier diagrams do not expand scope.

## Your task inventory

| Done | ID | Primary owner | Technical contact | Required responsibility | Dependencies | Acceptance evidence |
|---|---|---|---|---|---|---|
| [ ] | D01 | Reimo | Ved | Acquire and validate pinned Arizona carbon data, timestamps, units and annual plausibility | F02 | Source manifest, checksum, unit/time evidence and hand-checked window |
| [ ] | D02 | Reimo | Edison | Prepare Frontier calibration distributions and fixed-power/PUE assumptions | F02 | Validated job-table adapter, exclusions, quantiles and scaling report |
| [ ] | D03 | Reimo | Ved | Generate hand fixtures, four scenarios and missing-forecast variant | F02, D01, D02 | Deterministic fixtures with expected counts, labels and quality checks |
| [ ] | D04 | Reimo | Nisha | Own development/held-out splits, blocked folds, seeds, fixture manifests and freeze | D03 | 40 development and 30 held-out episodes; no overlapping source windows |
| [ ] | D05 | Reimo | Ved | Maintain data README, dictionary, licenses, acquisition and regeneration instructions | D01, D02, D03, D04 | Second person can locate, validate and regenerate allowed artifacts |
| [ ] | S01 | Reimo | Ved | Implement simulator reset/state/step, visibility boundary and 30-slot accounting | F02, D03 | Arrival, occupancy, rejection, progression and hidden-data tests pass |
| [ ] | S02 | Reimo | Edison | Integrate simulator impact ledger with shared calculations and hand fixture | S01, P01 | 54.5/48.4 kg job checks and full-period job/background totals pass |
| [ ] | R01 | Reimo | Ved | Write data/simulator report section and present its assumptions and limitations | D05, S02 | Validated section and supporting figures/tables |

## Your assignment and boundaries

You assist Reimo Tamme. Lead the data pipeline, scenario/split preparation and simulator in the proposal's shared Reimo/Ved E1/E3 area. Ved leads ontology, reference optimization and schema maintenance; you supply its validated records and review physical/time semantics. Edison owns the reusable impact formulas. Do not write a competing graph, solver, production checker or report-scoring implementation.

## Required inputs and decisions

Use the final proposal, existing F02 examples, Matty's configuration/provider/checker boundaries and Edison's actual impact module. Implement actual agreed independent data/simulator functions and tests on permitted fixtures while only unresolved source mapping/shared behavior or scientific acceptance waits; do not invent hidden defaults. You lead source/regeneration/freeze evidence in [#60](https://github.com/ReymoT/data-center-agentic/issues/60), with Ved independently verifying in #13. Your October 26 checkpoint is accepted for evidence inventory and exact remaining blockers, not completed scientific acceptance. Existing source pollutant/interval/rights/suitability and split/freeze decisions remain unresolved; source meaning needs authoritative evidence. The separate Frontier-access follow-up remains deferred.

## Coding checklist in implementation order

1. **Pinned source adapters (D01/D02).** Fetch only SustainDC's `data/CarbonIntensity/AZPS_NG_&_avgCI.csv` at commit `a92b4755aca560e34a98d14028dda629eb968482`; expect 8,760 hourly 2022 UTC rows, verify rather than force that shape. Inspect `avg_CI`, actual units, interval boundaries, duplicates/gaps and physically plausible values. Record source URL, checksum, acquisition date, license and transformations. Read the Frontier job-information table for runtime, mean power and requested wall-time distributions; exclude invalid runtimes, node counts and power. Avoid node-level telemetry. SustainDC workload/weather and Frontier facility data are context, not scored workload inputs. Use eGRID for an annual magnitude plausibility check with documented geography/year/factor limits.
2. **Synthetic job calibration (D02/D03).** Preserve empirical quantiles/scaling rules and sample seeds. Synthetic jobs are 10–40 kW, duration 1–4, arrival 0–17, deadline ≤30. Flexibility/deadlines are synthetic, not inferred as real Frontier flexibility. Keep 100 kW IT capacity, 40 kW background and fixed PUE 1.2 explicit assumptions. Structurally valid impossible jobs must remain in the infeasible scenario.
3. **Scenario generator (D03).** Normal: 12 jobs/7 flexible, slack 2–10. Spike:20/12 flexible, eight arrivals in slots 6–9; confirm remaining distributions. Limited:12/2 flexible, slack 0–2. Infeasible:12/7 flexible with at least one impossible deadline. Add normal-withheld-forecast variant without deleting private realized carbon. Define slack as deadline−arrival−duration. Publish tiny deterministic fixtures first.
4. **Splits and manifests (D04).** Generate 40 development episodes using days 1–14 and six held-out dates from 15–28 in different months with a fixed seed. Enforce nonoverlapping 30-hour source windows across dev/test and the three blocked development folds; group related/overlapping windows together. Freeze dates, seeds, quantiles and scaling. Keep private split metadata and hidden inputs outside policy objects. Do not expose held-out fixtures for tuning prompts/models/code. Validate and checksum them through the controlled evaluator path.
5. **Simulator (S01).** Implement `reset`, `state`, `step` according to the accepted contract. State contains arrived waiting jobs and immutable running jobs; reveal arrivals at the agreed slot boundary. Apply only approved current starts, never duplicate a start; account for occupied slots `[s,s+d)`. Advance clock and running work after rejection. Record missed latest starts, unfinished work and nonflexible violations explicitly. Completion-period behavior follows Q01. The public state method must not leak future arrivals or private scoring carbon.
6. **Accounting integration (S02).** Call Edison's shared impact functions for all 30 slots and keep job/background/site ledgers separate. Simulator state progression remains your code; Edison's function computes values. Do not let lower completed work look like energy/carbon savings.
7. **Documentation and handoff (D05/R01).** Write data README, data dictionary, source/license manifest, exclusion counts, timezone/issue-time explanation and fixture generation commands. Supply data/simulator report section and figures to Nisha. If access/validation fails by Oct 16, use labeled synthetic fallback as proposal allows and document narrower conclusions.

## Proposed repository files

Own `dc_sustainability/data/`, `dc_sustainability/simulator/`, `data/README.md`, data manifests/permitted fixtures, `tests/data/`, `tests/simulator/`, and your section under `docs/report/`. Review data fields in `schemas.py` and `configs/` through Ved/Matty; do not maintain alternate schemas. Keep raw/large/restricted inputs outside Git with reproducible acquisition instructions.

## Required tests

- Source schema/units/timestamps, gaps/duplicates, checksums, invalid-record exclusions and deterministic calibration/generation.
- Scenario counts/flexible counts, arrival/deadline ranges, intentional infeasibility retained and fold/test source-window isolation.
- Hidden-arrival/split/oracle leakage; withheld forecasts with intact private actual scoring data; visible horizon/freshness once Q04 is accepted.
- Running plus proposed occupancy; exact deadline completion; future/past/duplicate/unknown starts; rejection advances time; no lost missed/unfinished jobs; completion-slot policy.
- Shared hand fixture: CI `[500,450,300,250,400,480,520]`; J1=40 kW and J2=30 kW, duration 2, arrival 0, deadline 6, background 40. Starts 0/2 and 2/4 yield job 140 kWh and 54.5/48.4 kg at PUE 1.0. Background 116 kg yields site 170.5/164.4 kg over seven slots. PUE 1.2 job emissions 65.4/58.08 kg (display 58.1). J3 arrival 4/duration 3/deadline 6 is impossible.

## Outputs, dependencies and completion

Send Ved validated fixtures/schema examples/source IDs for graph/reference work; Edison development fixtures/fold groups/calibration assumptions; Matty visible-state and stepping API with failure examples; Nisha private evaluation loader and manifests with equivalent public views. Ved must independently reproduce the adapter and check 24 hours by Oct 16. Edison reviews your hand-ledger integration. Record each artifact's schema version, checksum, generating command and exact commit in the handoff.

You are Done only when data/fixture/simulator tests pass, Ved's reproduction is recorded, downstream consumer tests work on merged code, complete data documentation/report contribution exists, and every unresolved decision affecting accepted behavior has been resolved or explicitly blocks that deliverable. Your main target is Oct 16; collaborate on graph integration by Oct 23 and freeze by Nov 13. Own fixes to your modules found in Matty's final E2E run.


## Coordination instructions for your assistant

- One assigned Issue, one human owner and one active assistant session per task. Use a short-lived task branch from current `main`, preserve local work, fetch and deliberately integrate required upstream commits; fetching alone does not update files.
- Verify dependencies through merged code, artifact hashes/schema versions and consumer tests. Use agreed mocks only for development, never as evidence of final integration.
- Check updates at start/resume, dependency use, task change, PR/integration and handoff. An idle assistant resumes only when a human restarts it or a separately configured service does so. This file creates no monitoring service.
- Update the Issue through authorized access or give your human an exact draft update. Do not concurrently edit the shared coordination summary; its chosen publisher maintains it. A stale status does not let you claim someone else's work.
- If blocked by an open decision or missing handoff, record the precise unblock condition and continue unaffected assigned work. Do not invent assumptions, hide failures, tune on held-out data or bypass shared verification to finish faster.
- Request contract changes from Ved and master-file corrections from Matty with affected consumers identified. Cross-owner edits require coordination and applicable consumer checks. Production checker and independent evaluation validator stay intentionally separate.
- Finish with published and validated code, passing current-base checks, documented artifacts and receiving-member acceptance. Mark Done only after verification. Include task ID, commit/PR, commands, hashes, tests actually run, limitations and next handoff in your completion message.

The shared rules define publication, state-transition and handoff procedures. The checklist assigns a separate technical contact for each task. Technical validation and independent scientific evaluation remain required. Shared-format and settings changes require agreement from the affected teammates before implementation; record that agreement in the Issue or decision record.
