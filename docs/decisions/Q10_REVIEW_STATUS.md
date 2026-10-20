# Q10: review and sampling agreement status

Recorded October 20, 2026. Partial agreement, not a frozen rubric, algorithm or configuration. Nisha owns E04/E07, Matty is independent second rater, Ved reviews sampling/analysis. Sources: [Nisha's response](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6283887127), [Matty's response](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6298590572). Ved has not replied.

Nisha and Matty agree to at least ten paired development cases with original independent ratings and retained adjudication; 60 held-out decision pairs (120 output units), two per episode across all 30 episodes and 20 per trial index; frozen selection without peeking/replacing failures; blinded labels with limitations disclosed; sampled metrics labeled as sampled; 10000 paired episode-block resamples retaining all slots/three trials, two-sided 95% percentile intervals preserving strata; six-date cluster sensitivity with limited scope stated. Details remain in issue #22. Remaining agreement and implementation are required before freeze.

Matty also accepts raw label percent agreement and Cohen's kappa with joint claim counts (undefined remains undefined), separate sampling seed 20261019 and analysis seed 20261020 with generator/version frozen, and retaining/flagging fallback explanations. These are partial agreements, not adopted code/config.

Two points remain unresolved:

1. Claim scope: Nisha proposes faithfulness labels for structured Claim records, summary completeness separately. Matty recommends including checkable summary assertions with frozen extraction/deduplication, original text and extraction-disagreement counts. A limited structured-only metric would instead need a separately disclosed summary faithfulness audit. Neither option is selected; false summary facts cannot silently disappear from the study's claim.
2. Eligibility: Nisha proposes both queues nonempty. Matty recommends preserving preselected episode/slot/trial pairs, both queue counts/state hashes and explicit not-applicable claim components for empty no-ops, without replacing pairs. A both-nonempty stratum can be reported separately. If fewer ratable pairs exist, agree the rule before freeze; never resample silently after outcomes.

Matty asked Nisha to resolve these points and Ved to confirm analysis/sampling/fallback. No F02 field/unit changes or sampling-map implementation are made. Original blinded ratings and held-out review are future deliverables. Calendar pressure cannot silently reduce the sample, waive two raters or create results.
