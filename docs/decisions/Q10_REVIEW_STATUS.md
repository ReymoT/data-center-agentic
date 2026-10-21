# Q10: review and sampling agreement status

Current October 20 update (America/Phoenix): [Nisha withdrew her original A1/A3](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6306080316), and [Matty answered](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6306238057). This supersedes the historical description below; Q10 is still partial, not frozen. Nisha owns E04/E07 and the rubric/selection implementation; Matty supplies independent second ratings; Ved's design agreement remains missing.

Matty and Nisha now agree that primary faithfulness/precision/coverage cover every checkable assertion, including summary facts. A frozen extraction/deduplication rule gives repeated assertions the same ID. Retain original text and both raters' independent extractions and labels before adjudication. Report extraction agreement separately from label percent agreement/kappa on jointly extracted assertions, with counts. Structured-Claim-only metrics are secondary; completeness is separate. Freeze worked examples after at least ten paired development cases and before held-out review. No F02 field is added.

They also agree to retain every preselected episode/slot/trial pair, including failures, malformed/missing outputs and one-sided empty queues. Record both queue counts and state hashes, count no-op claim components as not applicable, report all selected pairs plus a separate both-nonempty stratum, and disclose any ratable shortfall without topping up the primary sample. The existing 60-pair/two-rater target and baseline paired-analysis agreement below remain in place.

One selection decision is still open: Nisha proposes input-only eligibility when a job has arrived and its deadline has not passed. Matty recommends retaining the original slots 0–23 manifest frame until Ved checks an exact alternative, including deadline boundary and expired/infeasible-job behavior. Neither a new filter nor sampling-map code is frozen by this update. Ved must confirm the sampling/analysis/fallback treatment and remaining eligibility choice. No held-out outputs or ratings exist for these future tasks.

## Historical October 20 record before Nisha's revision

Recorded October 20, 2026. Partial agreement, not a frozen rubric, algorithm or configuration. Nisha owns E04/E07, Matty is independent second rater, Ved reviews sampling/analysis. Sources: [Nisha's response](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6283887127), [Matty's response](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6298590572). Ved has not replied.

Nisha and Matty agree to at least ten paired development cases with original independent ratings and retained adjudication; 60 held-out decision pairs (120 output units), two per episode across all 30 episodes and 20 per trial index; frozen selection without peeking/replacing failures; blinded labels with limitations disclosed; sampled metrics labeled as sampled; 10000 paired episode-block resamples retaining all slots/three trials, two-sided 95% percentile intervals preserving strata; six-date cluster sensitivity with limited scope stated. Details remain in issue #22. Remaining agreement and implementation are required before freeze.

Matty also accepts raw label percent agreement and Cohen's kappa with joint claim counts (undefined remains undefined), separate sampling seed 20261019 and analysis seed 20261020 with generator/version frozen, and retaining/flagging fallback explanations. These are partial agreements, not adopted code/config.

Two points remain unresolved:

1. Claim scope: Nisha proposes faithfulness labels for structured Claim records, summary completeness separately. Matty recommends including checkable summary assertions with frozen extraction/deduplication, original text and extraction-disagreement counts. A limited structured-only metric would instead need a separately disclosed summary faithfulness audit. Neither option is selected; false summary facts cannot silently disappear from the study's claim.
2. Eligibility: Nisha proposes both queues nonempty. Matty recommends preserving preselected episode/slot/trial pairs, both queue counts/state hashes and explicit not-applicable claim components for empty no-ops, without replacing pairs. A both-nonempty stratum can be reported separately. If fewer ratable pairs exist, agree the rule before freeze; never resample silently after outcomes.

Matty asked Nisha to resolve these points and Ved to confirm analysis/sampling/fallback. No F02 field/unit changes or sampling-map implementation are made. Original blinded ratings and held-out review are future deliverables. Calendar pressure cannot silently reduce the sample, waive two raters or create results.
