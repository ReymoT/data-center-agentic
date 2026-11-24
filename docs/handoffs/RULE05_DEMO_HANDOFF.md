# RULE-05 materials for Edison and Ved — #246

Prepared by Reimo Tamme for #243, November 23, 2026. Main reviewed:
`91e23b6f85c6240ec22d2a23e14f1eaf924427c4`, instruction 1.30.
Review draft; teammate receipt and final integration are not claimed. Edison coordinates visuals
and package; Ved owns executable wiring/replay. Reimo supplies methods/figures.

Use [docs/report/RULE05_FOCUSED_STUDY_METHODS.md](../report/RULE05_FOCUSED_STUDY_METHODS.md)
for narration, [docs/report/RULE05_WORKFLOW_DIAGRAMS.md](../report/RULE05_WORKFLOW_DIAGRAMS.md)
Figure 1 for the research introduction and Figure 2 for the check/fallback/execution
walkthrough (rules-v1 candidate/fallback path; baseline routing is described in
the caption). Both are editable Mermaid. Their captions and status labels travel
with any export. Report links are in the working draft, README and evidence index.

| Scene | Supported interpretation and caption limit |
| --- | --- |
| A | Authored feasible case: rules-v1 and Greedy B start J2 now and defer J1 to lower-score slot 1; Greedy A starts both at slot 0 in the received records. Future selections are advisory; show actual current-slot execution and recorded turnaround/score separately. RULE-05 supplies no new measured trade-off or savings result. |
| B | Two rigid jobs jointly require 80 kW including 20 background against 60 kW. Each alone fits. Current main's unchanged abstention gate rejects the partial plan and fallback; retain blocked/no-start and eventual missed outcomes. Do not label a proposed single-job 50 kW load as an executed 80 kW violation, or claim successful fallback/progress. |
| B-fault | Explicitly injected simultaneous invalid starts, not a natural rules-v1 output. Show proposal/check/fallback/execution separately; invalid starts must not execute. A blocked outcome is not completion. |
| B-progress | Separate feasible subcase: J2 flexible, deadline 2; expected sequential J1 at 0/J2 at 1. Use actual replay evidence for a completion claim; it does not make impossible B a progress success. |

The [current RULE02 handoff](RULE02_IMPLEMENTATION.md) controls these semantics.
[Historical static receiving](RULE02_EVIDENCE_RECEIVING_NOV22.md) covers 10 traces /
300 decisions bound to old `176361a`, not corrected main. Do not reuse its labels
as a new current-system finding.

PRs #260/#261 are merged; the [executable demo handoff](RULE07_EXECUTABLE_DEMO.md)
records saved-package wiring and replay limits. Use the accepted
[RULE-03 report](../report/RULE03_VERIFICATION_SECTION.md) and
[independent receiving](RULE03_NATIVE_INDEPENDENT_RECEIVING_NOV23.md): all 202
required traces (192 primary + 10 authored) are completely replayed across preserved
attempts and independently received within scope. Original INCOMPLETE and sandbox
host FAIL records remain unchanged. Primary S4 is NOT_RUN; authored rules-v1 S4 has
three checks without violations. All three policies start zero jobs in the 12
infeasible primary cases; do not claim subset salvage. Optional extended coverage
was not executed, and finite verification is not unseen generalization.

The [RULE-04 development review](RULE04_DEVELOPMENT_HANDOFF_REVIEW_NOV23.md)
supplies 120 development cases/sidecar and corrected partial authored metrics.
A has 8,000 versus 12,000 artificial score-kWh for rules-v1/Greedy B versus Greedy A;
B-progress is equal; B's zero-baseline comparison is unavailable. Use the reviewed
projection and retain original producer records. Independent accounting acceptance
is pending; no policy has run on the development set. These are authored
illustrations, not unseen performance or emissions results.

Remaining receiving and final demo gates:

- Nisha #241: retain the accepted bounded baseline and property-specific limits;
  new or extended verification needs separate exact authorization and receiving.
- Edison/Nisha #242: independent receiving of the retained development pair and
  corrected metrics, hidden-weight accounting, matched support/exclusions and
  final input/metric/isolation freeze. Full unseen evaluation remains pending.
- Matty #244 and demo owners: accepted freezes, exact bounded release if execution
  is needed, clean reproduction and actual replay/binding outcomes for the selected
  saved package. A local test result is not independent verification or permission.

Every demo must retain: artificial score-kWh is not measured emissions; finite
bounds are not universal proof; historical Agent/Plain is not a matched comparison;
safe refusal is not completion; missing-forecast cases are fallback/accounting
controls. Carry all four #231 dispositions: ten-fold refits and ML warm-start are
future work; structured rule arithmetic is implemented but the LLM repair ablation
was not run; matched turnaround/score results are pending unless actual evidence
supports the displayed point. No fake zero, trace, screenshot or frontier.

Review handoff: @MattyAnd @nkolekar-nk @epez7 @vedp3705; use these exact paths. No teammate receipt or approval is implied
by this prepared handoff. RULE-07 production remains with Edison and Ved.

Manager review: resource ceilings are per exact approved attempt with cumulative
charged-work reporting; the execution figure includes the post-recheck state and
snapshot read and is explicitly scoped to rules-v1 fallback routing. HTML line
breaks replace literal backslash-n labels. Mermaid source and local links are
checked; final exported-figure layout remains report/demo assembly work.
