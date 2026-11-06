# Final report: assembly outline (R05)

Assembler: Nisha (R05); release package: Matty (R06).

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
| C | Problem statement | 1 | Nisha with Reimo | 0.5 | [Draft](R05_INTRODUCTION_PROBLEM.md); site, jobs, episodes and impact rules ([architecture](../ARCHITECTURE.md)) | Drafted; Reimo's review pending |
| D | Related works | 1 | Matty, Nisha | 0.5 | [Draft](R05_RELATED_WORKS.md); [source review](../SOURCE_REVIEW.md) | Drafted; Matty's review pending |
| E | System architecture and algorithms | 3 | Matty (agent, verification, R04); Ved (knowledge graph, retrieval, references, R02); Edison (Greedy A/B, C/D, R03); Reimo (simulator, R01) | 2 | [R04 draft](../R04_DEVELOPMENT_EVIDENCE.md); [ontology](../../ontology/README.md); [P04 artifacts](../handoffs/P04_REAL_DEVELOPMENT_ARTIFACTS.md) | R04 draft exists |
| F | Datasets: descriptions, sizes, preprocessing | 1 | Reimo (R01) | 0.75 | [data README](../../data/README.md); [D04 materialization](../handoffs/D04_DEVELOPMENT_MATERIALIZATION_112.md) | Not started |
| G | Evaluations: metrics, experiments, findings | **4** | Nisha (R05) with Edison (R03) | 2.5 | [R05 evaluation draft](R05_EVALUATION.md); [I02 matrix](../i02/README.md); held-out results | Design and development reliability drafted; findings wait for I02 |
| H | UI / visualization interface designs | **4** | Matty | 1 | [Working explorer and screenshot](UI_VISUALIZATION.md) | Implemented and browser-checked on saved development evidence; final report acceptance pending |
| I | Division of work and team members' contributions | 1 | All; Nisha assembles | 0.5 | [responsibility checklist](../team/03_RESPONSIBILITY_CHECKLIST.md); PR history | Not started |
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

## Schedule

These are draft report-production targets. Presentation preparation (November 9–11 review, November 13 rehearsal, November 14 email and Canvas submission) is recorded separately. The November 13 scientific freeze target is conditional on its acceptance gates.

| Date | Milestone |
|---|---|
| November 13 | I02 freeze (conditional) |
| November 16 | Class presentation |
| November 23 | Held-out runs, references and annotations complete (plan) |
| November 27 | Section drafts C–F and H due from owners (earlier if you're away over Thanksgiving) |
| December 2 | Demo; evaluation findings and reliability drafts complete |
| December 6 | Full IEEE draft for team review |
| December 7 | Internal PDF submission target; confirm official fields before upload |
| December 9, 11:59 pm | Deadline reported by Nisha; official timezone unconfirmed |
