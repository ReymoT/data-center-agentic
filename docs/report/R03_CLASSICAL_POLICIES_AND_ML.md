# R03 — Classical policies, impact rules and C/D development metrics

Owner: Edison Perez Cash (`epez7`). Technical contact: Nisha.
Tip base for this handoff: `74dc167bbca52d15126de5ecfbf853c7738ee32c`.
Status: methods and verified **development** evidence for report assembly (#223).
This is not P07, not held-out scoring, not CF60/C/D scientific certification, and
not an I02 freeze. Unavailable counts stay unavailable; development scores are
not substituted for final study results.

## 1. Impact accounting (P01)

Shared slot, job, background and site energy/emissions use explicit units, PUE and
duration. Capacity uses IT power, not facility power.

- Facility kWh = PUE × IT kW × hours.
- Modeled kg = kWh × intensity in g/kWh ÷ 1000. The code uses emissions
  fields, but exact pollutant basis/source applicability remain unresolved; do
  not interpret the proxy arithmetic as verified real-site CO2e or causal savings.
- Preserve full precision; one-decimal display is presentation only.
- Internal absolute tolerance for hand checks is 0.01.

Equal-work savings comparisons require matched completed and unfinished/missed
job sets, equivalent inputs/pairing, and present realized carbon. Missing
evidence, unmatched completed work, unfinished occupancy that invalidates the
comparison, or independent replay findings that invalidate execution block a
savings claim with explicit reasons. Lower energy from unfinished work is not
efficiency. Nonfinite or undefined values are never replaced by zero to improve a
result.

## 2. Classical policies (P02)

**Greedy A.** Earliest feasible starts among waiting jobs, respecting capacity,
running work and already-reserved proposals. Priority order: nonflexible
arrivals, latest-start jobs, deadline, then numeric job ID (J2 before J10).
Replans each slot; executes only current starts through the shared gate.

**Greedy B.** Among feasible starts, choose lowest forecast job emissions; ties
break to earlier start, then the same ID rule. When Q04 finds required forecast
coverage/freshness unavailable, B uses checked A with separate fallback logging.

A is the reusable checked fallback for Agent and learned policies. Neither
heuristic guarantees feasibility or optimality for all workloads.

## 3. Candidates, training and inference (P03–P05)

Candidates use arrived waiting jobs, visible fresh carbon coverage and fixed
running work. Features, in model order:

`delay_slots`, `deadline_margin_slots`, `duration_slots`, `power_kw`,
`available_capacity_kw`, `queue_load_count`, `carbon_mean_g_per_kwh`,
`carbon_min_g_per_kwh`.

Training uses only certified optimal visible-state selections from O02. Unresolved
and insufficient-evidence states stay exclusions, not negative labels. Certified
infeasibility is not training data. Development used three blocked folds that keep
episodes and overlapping source windows intact (16/12/12). Grid: tree depths 3/5/8;
forests of 100 trees at depths 5/10. Seed `20261031`. Selection used development
rollouts (completed work, then fewer deadline misses, then lower emissions), not
post-hoc largest classification F1.

Selected full-data development refits (legacy forecast path):

| System | Configuration | Artifact SHA-256 |
| --- | --- | --- |
| Decision tree C | max_depth 8 | `7e9e5769771f045241317d976f142b936f328399df58b040f9bbf67ba77a8f0b` |
| Random forest D | 100 trees, max_depth 10 | `37149e530ef8e026b08279bedae1dd95170f70c279dd59d566637f43df94cf6a` |

Schema `p04-artifact-v1`. Classification metrics use threshold 0.5; the schedule
constructor ranks candidates rather than filtering at that threshold. Its ordering
is nonflexible jobs first, then latest-start urgency, descending predicted
selection probability, earlier start, numeric job ID and full ID. At most one
start is reserved per job, with cumulative occupancy checked. Proposals pass through
common checks with no solver calls at inference time. Missing forecasts invoke
checked A under accepted Q04 scope.

These binaries remain **legacy-forecast** artifacts until an authorized CF60
development comparison and affected-owner C/D assessment exist (#60). Schema
sameness alone is not scientific compatibility. No silent retrain or replacement
is authorized by this handoff.

## 4. Development candidate metrics (P06)

Public card and measured fold metrics:

- [models/development_candidate_card.md](../../models/development_candidate_card.md)
- [models/DEVELOPMENT_FOLD_METRICS.md](../../models/DEVELOPMENT_FOLD_METRICS.md)
- [models/development_fold_metrics_2026-11-02.json](../../models/development_fold_metrics_2026-11-02.json)

Support on the definite development corpus: 6046 rows; 1411 positive; 4635
negative. Pooled validation-fold scores for the **selected** configurations
(threshold 0.5):

| Selected model | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| Decision tree, depth 8 | 0.394 | 0.578 | 0.469 |
| Random forest, 100 trees, depth 10 | 0.456 | 0.618 | 0.525 |

These are descriptive classification scores on blocked development folds after
selection. They are not scheduling outcomes, unbiased final estimates, held-out
study results, or evidence that Model D improves research endpoints. Original
excluded-candidate counts are unavailable from the saved definite-row corpus;
zeros in that field must not be invented. Total recorded
materialize/label/select/refit/reload time for the published receiving package is
101.375 seconds.

## 5. Held-out scoring (P07) — blocked

P07 remains blocked on accepted I02 scientific freeze, frozen C/D held-out
inference outputs, then Ved’s O04 certified labels (#164). Missing-forecast and
unavailable label metrics stay not-applicable with explicit counts. Development
fold F1 must not be copied into held-out result tables.

## 6. Contribution statement (3–5 lines)

Edison owns shared impact accounting (P01), greedy A/B and reusable checked-A
fallback (P02), candidate/feature protocol and blocked-fold training plumbing
(P03), decision-tree C and random-forest D development training/selection/refit
(P04), learned reload and checked fallback integration (P05), and published
development model cards/candidate metrics (P06). Public evidence for those items
is on main; private binaries and corpora stay in recorded custody outside Git.
R03 report prose for classical/learned methods and development metrics is this
handoff. P07 held-out scoring and any CF60-certified C/D claim remain pending
their documented gates.

## Limits (do not over-claim)

- Source rights/semantics (B1–B3 unresolved; B4 provisional) stay open in #60.
- CF60 adoption, authorized extract/state comparison and C/D compatibility
  certification are unfinished.
- I02 remains a pre-freeze checklist on tip main; no frozen held-out results.
- This document supplies assembly text only. It does not authorize private reads,
  model calls, solver runs, retraining or publication of private paths.

## Matty factual review

Reviewed against `dc_sustainability/training/schedule.py`, the greedy implementation and the public P04/P06 records. The source record remains methods/development evidence only; no binaries, private data, inference or scoring were loaded or run for this review.
