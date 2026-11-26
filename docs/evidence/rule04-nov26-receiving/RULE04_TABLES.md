# RULE-04 development comparison tables

Coverage: **COMPLETE** (run status `COMBINED_COVERAGE_ONLY`).
Stop reason recorded by the run: Original incomplete attempt retained; coverage is not study acceptance.

Impact unit: artificial score-kWh (not g/kWh, not emissions).

## Per stratum and policy

| Stratum | Policy | Runs | Violations / starts | Jobs | Completed | Missed | Unfinished | Turnaround mean (n) | Delay mean (n) | Fallback runs | Blocked runs | Job impact |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| missing_forecast (control) | rules-v1 | 40/40 | 0 / 117 | 118 | 117 | 1 | 1 | 1.6068 (117) | 0.094 (117) | 40 | 0 | 642000.0 |
| missing_forecast (control) | greedy_a | 40/40 | 0 / 117 | 118 | 117 | 1 | 1 | 1.6068 (117) | 0.094 (117) | 0 | 0 | 642000.0 |
| missing_forecast (control) | greedy_b | 40/40 | 0 / 117 | 118 | 117 | 1 | 1 | 1.6068 (117) | 0.094 (117) | 40 | 0 | 642000.0 |
| normal_feasible | rules-v1 | 40/40 | 0 / 96 | 106 | 96 | 10 | 10 | 1.7917 (96) | 0.3438 (96) | 0 | 4 | 436000.0 |
| normal_feasible | greedy_a | 40/40 | 0 / 106 | 106 | 106 | 0 | 0 | 1.5566 (106) | 0.1132 (106) | 0 | 0 | 545000.0 |
| normal_feasible | greedy_b | 40/40 | 0 / 96 | 106 | 96 | 10 | 10 | 1.7917 (96) | 0.3438 (96) | 0 | 4 | 436000.0 |
| overloaded_impossible | rules-v1 | 40/40 | 0 / 48 | 143 | 48 | 95 | 95 | 2 (48) | 0.375 (48) | 0 | 40 | 243000.0 |
| overloaded_impossible | greedy_a | 40/40 | 0 / 48 | 143 | 48 | 95 | 95 | 1.8125 (48) | 0.1875 (48) | 0 | 40 | 267000.0 |
| overloaded_impossible | greedy_b | 40/40 | 0 / 48 | 143 | 48 | 95 | 95 | 2 (48) | 0.375 (48) | 0 | 40 | 243000.0 |

## Equal-work comparison against Greedy A

| Stratum | Policy | Available / rows (not evaluated) | Reduction median [min, max] | Turnaround shift mean (n) | Unavailable reasons |
|---|---|---|---|---|---|
| missing_forecast (control) | rules-v1 | 40/40 (0) | 0.0 [0.0, 0.0] | 0.0 (40) | — |
| missing_forecast (control) | greedy_b | 40/40 (0) | 0.0 [0.0, 0.0] | 0.0 (40) | — |
| normal_feasible | rules-v1 | 36/40 (0) | 0.0 [0.0, 0.5455] | 0.2454 (36) | job_outcome_sets_differ: 4 |
| normal_feasible | greedy_b | 36/40 (0) | 0.0 [0.0, 0.5455] | 0.2454 (36) | job_outcome_sets_differ: 4 |
| overloaded_impossible | rules-v1 | 36/40 (0) | 0.0 [0.0, 0.6667] | 0.1667 (36) | greedy_a_impact_not_positive: 4 |
| overloaded_impossible | greedy_b | 35/40 (0) | 0.0 [0.0, 0.6667] | 0.1714 (35) | greedy_a_impact_not_positive: 4, source_bindings_differ: 1 |

## Notes

- Development cases only; not unseen generalization or final-set evaluation.
- Per stratum; no pooled ranking. Missing-forecast rows are a control.
- Missed and unfinished counts overlap and are not summed.
- Unavailable comparisons keep their reason; none is shown as zero.
- Reductions are descriptive (median/min/max); no resampling interval.
- Retained artifact consistency/recomputed arithmetic only; saved replay is attributed, not newly executed or independent-person acceptance.
- Recovered pairs beyond the last checkpoint are explicit; failed/in-flight work is not counted as complete.

## Inputs

- `union_receipt` sha256 `b46a161cddf4fe834a20628b3483cfe770b5d91dcf7e3664ce6831f5f53aed13`
