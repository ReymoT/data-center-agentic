# Final report: assembly outline (R05)

Assembler: Nisha (R05); release package: Matty (R06).

Active scope: [development-evidence-only delivery activated November 18](../decisions/NOV18_EVIDENCE_ONLY_ACTIVATION.md). Final comparative held-out study and its dependent tasks are deferred outside this delivery. Complete actual evidence text, limitations, layout, reproducible public-artifact checks, contribution attribution and release/submission; do not wait for #60 source acceptance.

November 15: [an evidence-first working report](VERIFIED_EVIDENCE_WORKING_DRAFT.md),
[claim/source index](VERIFIED_EVIDENCE_INDEX.md) and
[draft delivery manifest](EVIDENCE_FIRST_DELIVERY_MANIFEST.json) now assemble the
available methods, development evidence and figures. Original owner drafts remain
editable sources. Held-out findings, final PDF/layout, I03/I04 and final R05/R06
acceptance remain pending. The earlier inactive status is superseded by the November 18 activation. Ready
methods/contribution handoffs are coordinated in [#223](https://github.com/ReymoT/data-center-agentic/issues/223).

**Official instructions as reported by Nisha** ([source on #16](https://github.com/ReymoT/data-center-agentic/issues/16#issuecomment-6589886278)):
- **Due December 9, 2026, at 11:59 pm.** 20% of the course grade.
- **5–10 pages**, written as a paper submission to a good conference, using the **IEEE conference template** (Overleaf).
- **One PDF per group**, uploaded to Canvas under Assignments › Final Project Report, named `Group15-Project21-F26-Final Project Report.PDF` (project number 21 confirmed by Nisha, [#16](https://github.com/ReymoT/data-center-agentic/issues/16)).
- The detailed contributions of each team member are required.
- The earlier course outline also asks for supplemental material (data, code) and a statement of which parts are ours versus third-party. The repository and the disclosure section below cover these.

Nisha reports project number 21 and an end-of-day deadline of 11:59 pm on December 9
in her [November 4 confirmation](https://github.com/ReymoT/data-center-agentic/issues/16#issuecomment-6639775165).
Arizona timezone is her working assumption, not separately confirmed official guidance.
December 7 is Matty's conservative internal submission target,
not an asserted official deadline. [Current course record](../decisions/Q13_OFFICIAL_REPORT_2026-11-02.md).

**Ground rules for every section:**
- Every number cites saved evidence: a file, trace, receipt or PR.
- Development evidence is labeled as development. Held-out results appear only after the frozen runs (I02), the held-out references (O04) and the reliability repeat (#95).
- A claim the evidence doesn't support is left out, not softened.

## Sections, owners and budget (official sections and points)

IEEE two-column pages are dense, so the budget below is about 9.5 pages, under the 10-page limit.

| § | Section | Points | Owner | Pages | Source to build from | Status |
|---|---|---:|---|---:|---|---|
| — | Title | — | Nisha | — | Proposal | — |
| A | Abstract | 1 | Nisha | 0.25 | Research question; findings | Write last |
| B | Introduction | 2 | Nisha | 0.75 | [Draft](R05_INTRODUCTION_PROBLEM.md); research question | Drafted; findings wait for I02 |
| C | Problem statement | 1 | Nisha with Reimo | 0.5 | [Draft](R05_INTRODUCTION_PROBLEM.md); site, jobs, episodes and impact rules ([architecture](../ARCHITECTURE.md)) | Drafted; manager reconstructed simulator/source limits without requiring another Reimo review |
| D | Related works | 1 | Matty, Nisha | 0.5 | [Draft](R05_RELATED_WORKS.md); [source review](../SOURCE_REVIEW.md) | Integrated wording reviewed against retained source review; final bibliography formatting/check pending |
| E | System architecture and algorithms | 3 | Matty (agent, verification, R04); Ved (knowledge graph, retrieval, references, R02); Edison (Greedy A/B, C/D, R03); Reimo (simulator, R01) | 2 | [R04 draft](../R04_DEVELOPMENT_EVIDENCE.md); [ontology](../../ontology/README.md); [P04 artifacts](../handoffs/P04_REAL_DEVELOPMENT_ARTIFACTS.md) | R04/Edison R03 and corrected [Ved R02](R02_ONTOLOGY_AND_REFERENCE_METHODS.md) available; [R01 reconstructed by Matty](R01_DATA_AND_SIMULATOR_METHODS.md) available; personal attribution not invented |
| F | Datasets: descriptions, sizes, preprocessing | 1 | Reimo (R01) | 0.75 | [data README](../../data/README.md); [D04 materialization](../handoffs/D04_DEVELOPMENT_MATERIALIZATION_112.md) | R01 methods reconstructed from verified records; source limits retained |
| G | Evaluations: metrics, experiments, findings | **4** | Nisha (R05) with Edison (R03) | 2.5 | [R05 evaluation draft](R05_EVALUATION.md); [I02 matrix](../i02/README.md); held-out results | Design and development reliability drafted; findings wait for I02 |
| H | UI / visualization interface designs | **4** | Matty | 1 | [Working explorer and screenshot](UI_VISUALIZATION.md) | Implemented and browser-checked on saved development evidence; final report acceptance pending |
| I | Division of work and team members' contributions | 1 | All; Nisha assembles | 0.5 | [responsibility checklist](../team/03_RESPONSIBILITY_CHECKLIST.md); PR history | Matty, [Nisha](NISHA_CONTRIBUTIONS.md) and [Edison R03](R03_CLASSICAL_POLICIES_AND_ML.md) statements received; Reimo R01 handoff and remaining personal/final confirmations pending |
| J | Conclusions | 1 | Nisha | 0.25 | — | Write last |
| K | References | 1 | All | 0.5 | [Reference list](REFERENCES.md) | Started; software and data entries pending |
| | **Total** | **20** | | **~9.5** | | |

Matty owns the authorized read-only saved-trace explorer for section H and the
demo. It will show actual retained development records; it will not dispatch
policies/models, modify traces or turn development evidence into study findings.

## Contributions and third-party disclosure

- **Contributions (§I):** each owner writes 3–5 lines on what they built and owned, in task IDs (for example R01, D04, S01), with representative PRs. Nisha merges them into one table.
- **Third-party:** distinguish libraries and runtime, model weights, data actually used, comparators and proposed sources. Record applicable terms and notices separately for LangGraph, rdflib/pySHACL, scikit-learn, Ollama and Qwen3 8B. SustainDC is the pinned carbon proxy; EPA eGRID is a plausibility comparator. Frontier empirical calibration has not been established and must not be listed as an observed training-data source. Source-rights questions in #60 remain open, not assumed.

## Where the report is written

Drafts of each section live in this folder (or are linked here) as their source of truth, so every claim stays reviewable next to its evidence. The final PDF is set in the IEEE conference template on a shared Overleaf project that Nisha created. Access is by email invitation, and its edit link stays out of this public repository. The repository is the supplemental material; restricted or private inputs stay out of Git under the Q13 boundary.

## November 16 handoff and feedback

[Matty Overleaf handoff](MATTY_OVERLEAF_HANDOFF_2026-11-16.md) records the inserted agent/verification, UI/figure and contribution text with compilation limits. [Presentation feedback assessment](NOV16_PRESENTATION_FEEDBACK.md) records proposed cross-validation, repair-feedback ablation, expert ranking and scale checks. These are not adopted experiments or new execution approvals. Final study findings and remaining owner handoffs stay pending.

## Schedule

These are conditional report-production targets, reconciled to the manager's
November 22 feasibility checkpoint and reserved November 26-27 dates. Older
November 13 freeze/November 23 completion targets are superseded. This update
does not restart presentation work or change official course requirements.

| Date | Milestone |
|---|---|
| November 17, 6 PM Arizona | Ready methods/contribution draft or concrete blocker on #223; internal status checkpoint |
| November 22, 6 PM Arizona | Explicit feasibility decision; I02 freeze only if acceptance gates pass |
| November 23-24 | Frozen execution only if freshly authorized and ready |
| November 25 and 28-30 | References/scoring/ratings/reliability/adjudication as exact prerequisites permit |
| November 26-27 | Reserved; no work required by this plan |
| December 1 | Consolidated evidence-backed text/tables; unavailable results remain pending |
| December 2-3 | Ved I03 reproduction only with actual accepted final artifacts |
| December 4 | Matty I04 and R06 checks only after accepted prerequisites |
| December 5-6 | Repair/revalidation, IEEE layout and final review buffer |
| December 7 | Internal PDF submission target; confirm official fields before upload |
| December 9, 11:59 pm | Deadline reported by Nisha; official timezone unconfirmed |

## Required presentation-feedback coverage

Nisha integrates all four [November 17 feedback items](PROFESSOR_FEEDBACK_FOLLOWTHROUGH_NOV17.md) into methods/results or explicit limitations/future work: grouped ten-fold C/D validation (Edison), structured repair arithmetic/deltas (Matty), ML warm-start variant (Matty with Edison candidates), and paired turnaround versus equal-work reduction plot (Nisha). Reimo covers the same dispositions in the demo. Track exact agreements/evidence in #231. No unavailable finding or protocol adoption is implied.

## Ready offline designs and accepted handoffs

Matty prepared the [repair-feedback design](REPAIR_FEEDBACK_DESIGN_NOV17.md) and [ML warm-start design](ML_WARMSTART_DESIGN_NOV17.md) for #231. These do not adopt a schema/prompt/variant or authorize execution. The assembled report now incorporates accepted Edison R03 methods and Nisha contribution evidence; original owner files remain unchanged.

## November 17 R02 integration and checkpoint

Corrected R02 methods from #235 are integrated into the working report and evidence index. The original #234 file was empty; repaired prose retains scientific/tie/source limits and does not invent Ved personal attestation. Reimo R01 and #60 actual evidence/input gates remain outstanding after the recorded 6 PM Arizona checkpoint. The #231 response window remains unchanged (November 18, approximately 10:25 AM Arizona); designs are not shared-protocol adoption.

## Current delivery schedule

The full-study execution/ratings/reproduction windows above are historical conditional planning, not active prerequisites. Evidence-only text and demo assembly proceed now; November 20 official-field checkpoint and December 7 internal target remain. Final evidence-only artifact checks and submission receipt are still required; former study I03/I04 completion is not claimed.
