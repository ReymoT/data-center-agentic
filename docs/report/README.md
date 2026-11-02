# Final report: assembly outline (R05)

Due **December 9, 2026, 11:59 pm**. Assembler: Nisha (R05); release package: Matty (R06).

Course requirements (#16):
- 15–20 pages, written like a paper for a good venue, plus all supplemental material (data, code, etc.);
- the detailed contributions of each team member;
- a clear statement of which parts we wrote and which come from third parties.

The proposal outline the report extends: problem definition, data sets, state of the art, research plan (classical DM/ML baselines **and** modern AI), evaluation plan, timeline, division of work, references.

**Ground rules for every section:**
- Every number cites saved evidence: a file, trace, receipt or PR.
- Development evidence is labeled as development. Held-out results appear only after the frozen runs (I02), the held-out references (O04) and the reliability repeat (#95).
- A claim the evidence doesn't support is left out, not softened.

## Sections, owners and budget

| # | Section | Owner (task) | Pages | Source to build from | Status |
|---|---|---|---:|---|---|
| — | Title, abstract, keywords | Nisha | 0.5 | Proposal; research question | To write last |
| 1 | Introduction and research question | Nisha | 1.5 | [README](../../README.md), [architecture](../ARCHITECTURE.md) | Not started |
| 2 | State of the art and related systems | Matty, Nisha | 1.5 | [source review](../SOURCE_REVIEW.md) | Not started |
| 3 | Problem, data and simulator | Reimo (R01) | 2 | D01–D06 docs in [data/](../../data/README.md); [D04 materialization](../handoffs/D04_DEVELOPMENT_MATERIALIZATION_112.md) | Not started |
| 4 | Knowledge graph, retrieval and reference schedules | Ved (R02) | 2 | [ontology README](../../ontology/README.md); [O03 export](../handoffs/O03_HINDSIGHT_EXPORT.md) | Not started |
| 5 | Classical policies: Greedy A/B, decision tree C, random forest D | Edison (R03) | 1.5 | [P04 artifacts](../handoffs/P04_REAL_DEVELOPMENT_ARTIFACTS.md) | Not started |
| 6 | Agent, plain LLM and verification | Matty (R04) | 2.5 | [R04 draft](../R04_DEVELOPMENT_EVIDENCE.md) | **Draft exists** |
| 7 | Evaluation design | Nisha (R05) | 2 | [R05 evaluation draft](R05_EVALUATION.md); [I02 matrix](../i02/README.md) | **Draft started** |
| 8 | Results | Nisha with Edison (R05, R03) | 3 | Held-out runs (pending) | Waits for I02 |
| 9 | Faithfulness and inter-rater reliability | Nisha (R05) | 1.5 | [R05 evaluation draft](R05_EVALUATION.md) §3 | **Development part drafted** |
| 10 | Limitations and threats to validity | Nisha with all | 1 | Each section's limits; source gates #60 | Not started |
| 11 | Conclusion and future work | Nisha | 0.5 | — | To write last |
| — | Contributions of each team member | All (Nisha assembles) | 0.5 | [responsibility checklist](../team/03_RESPONSIBILITY_CHECKLIST.md); PR history | Not started |
| — | Own code vs. third-party code and data | Matty (R06), Nisha | 0.5 | [requirements](../../requirements/README.md); data source licenses | Not started |
| — | References | All | 1 | — | Not started |
| | **Total** | | **~20** | | |

## Contributions and third-party disclosure

The professor asks for "detailed contributions of each team member" and a statement of "which parts are written by you and which are from the 3rd-party."

- **Contributions:** each owner writes 3–5 lines on what they built and owned, in task IDs (for example R01, D04, S01), with representative PRs. Nisha merges them into one table.
- **Third-party:** list libraries (LangGraph, rdflib/pySHACL, scikit-learn, Ollama and Qwen3 8B, and others), datasets (SustainDC carbon, the Frontier job table, EPA eGRID) and their licenses. The source-rights questions still open on #60 are stated as open, not assumed.

## Supplemental material

The repository (code, `data/` manifests, `evaluations/`) is the supplement. Restricted or private inputs stay out of Git, under the Q13 boundary. The supplement index is assembled with R06.

## Schedule

| Date | Milestone |
|---|---|
| November 13 | I02 freeze |
| November 16 | Class presentation (uses sections 1–7 at outline level) |
| November 23 | Held-out runs, references and annotations complete (plan) |
| November 27 | Section drafts 3–6 due from owners (earlier if you're away over Thanksgiving) |
| December 2 | Demo; results and reliability drafts complete |
| December 6 | Full draft for team review |
| December 9 | Submission |
