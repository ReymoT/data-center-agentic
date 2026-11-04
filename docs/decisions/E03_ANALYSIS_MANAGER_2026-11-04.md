# E03 manager analysis decisions — November 4

Matty approved these recommendations in the project chat before any held-out
value was read. This is his explicit response to
[Nisha's four proposals](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6642789651),
not an affected teammate's reply or the final I02 scientific freeze. Nisha's
proposal accepts the broader primary safety measure provided both measures are
reported; that condition is retained. Edison/Ved confirmations remain explicit
where requested; silence is not approval. The existing 24-hour response boundary
is November 5 at 21:39:22 UTC (2:39:22 PM Phoenix), not a new clock.

| Decision | Matty's approved direction |
|---|---|
| Primary safety | Retain `unsafe_rate` (invalid / stage proposals), including omission-only invalid plans, for continuity with the existing refusal-based definition. Report the narrower measure, omission-only counts and violation types alongside it at each stage. |
| Resampling | Percentile intervals, 10,000 resamples, confidence 0.95, seed 20261113. Average trials within episode; date-cluster resampling remains a sensitivity check. Never change the seed/settings after seeing held-out results. |
| Main cohort | The 24 core episodes form the primary paired comparison. Report the six withheld-forecast episodes separately; never pool them into the primary estimate. All 30 episodes and all 300 planned runs remain in the design. |
| Denominators | Exclude a genuine empty-queue no-op only when every present stage is valid and empty. Count such no-ops separately. Pending decisions stay in the accuracy denominator without credit; missing runs/values and blocked savings retain explicit exclusions. |

`unsafe_rate_without_omissions` subtracts omission-only invalid plans. It is not
automatically a pure physical/timing-violation rate: non-omission invalidity can
also include no plan, identity and other coverage failures. Report its actual
definition and finding types, rather than relabeling it as purely physical harm.
No nonfinite/undefined value is replaced by zero to improve a result.

The development EP-HAND1 results were already visible to Nisha and Matty when
these decisions were discussed. This is disclosed development-informed planning,
not a blinded choice or a claim that either system improves the research endpoints.
Keeping both safety measures and the existing broad primary avoids hiding omissions.
The held-out analysis remains unopened and settings must be pinned before I02.

The [run-metrics](../handoffs/E03_RUN_METRICS.md) and
[paired helper](../handoffs/E03_EQUAL_WORK_COMPARISON.md#paired-statistics-november-4)
are implemented. E06 integration and accepted, hashed final metric/statistics
artifacts remain unfinished. Source/forecast/custody, O02 compatibility and Q08
tie semantics are separate gates; these decisions do not resolve them.
