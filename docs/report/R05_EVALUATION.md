# Evaluation design and reliability (R05 draft)

Owner: Nisha. **Status: development draft.** The design must be frozen before
I02; it is not frozen yet. Results in §3 are retained development evidence.
Report held-out results separately after frozen runs and the reliability repeat
(#95), preserving the originals and development findings.

Later development addition: [P06 blocked-fold candidate metrics](../../models/DEVELOPMENT_FOLD_METRICS.md)
provide measured confusion cells, support, precision/recall/F1 and timings for five
configurations across the three fixed development folds. These are post-selection
descriptive classification scores on saved definite rows, not final study findings
or a change to rollout-based selection. Original exclusion counts are unavailable
from that corpus and remain explicitly unknown. No held-out rating is added here.

## 1. Evaluation design

**Comparison.**
- The main comparison is `agent` against `plain_llm`, given the same visible facts, model and generation settings.
- Greedy A and B, decision tree C and random forest D are scheduling references, not separate hypotheses.
- Classical ML baselines (C, D) and modern AI systems (agent, plain LLM) are evaluated on the same episodes through the same checker and controller.

**Matrix (I02, [checked by `experiments/matrix.py`](../i02/README.md)).**
- 30 held-out episodes: 24 core, covering 6 Phoenix dates × 4 demand scenarios (normal, limited, spike, infeasible) once each, plus 6 normal-demand episodes with withheld forecasts.
- Greedy A/B and C/D run once per episode; the two LLM systems run three trials each, which gives **300 runs**.
- The design's theoretical call ceilings are 2,160 Plain and 6,480 Agent calls.
  These are not authorized runtime budgets; actual runs require exact bounded
  authorization and frozen settings. Receiving calls are separate evidence.
- Any reduction must be matched across systems and frozen before execution.

**Accuracy.** Measured against saved execution records and independently replayed (E01):
- executed-schedule validity;
- completed work, deadline misses and unfinished jobs;
- facility energy and emissions;
- emissions against hindsight and visible-state references (O03/O04).

Savings are reported only between schedules that complete the same work under the same inputs.

Source lineage, pollutant/system boundary, physical intervals, rights and actual
private custody/freeze remain gated by #60. Until accepted, carbon quantities are
development proxy arithmetic, not verified site emissions or causal savings.
The six systems have separate receiving records, not one completed frozen study.

**Forecast limitation.** The study forecast is not adopted yet. The proposal,
[CF60-v1](../handoffs/ISSUE60_CAUSAL_STUDY_FORECAST_PROPOSAL.md), repeats one
recent value across the whole visible horizon, as the development persistence
forecast does. Under a flat forecast every start has the same forecast emissions
for a given job, so Greedy B's `(emissions, start)` key always resolves to the
earliest feasible start, the same rule as Greedy A. No system then receives a
signal about which future hour is cleaner. If a flat forecast is frozen, this
evaluation cannot test selection of cleaner hours from forecast variation.
Realized emissions may still differ, but those differences must not be attributed
to forecast-driven selection of cleaner hours. A shaped same-hour
alternative is an [open team question](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6622770964).
Any comparison of forecast methods uses development dates only.

**Safety:**
- constraint violations in proposed and executed plans;
- unsafe advice (a proposal the checker would refuse);
- appropriate abstention;
- reliance on the checked fallback.

**Faithfulness** (blinded human claim review, under the frozen E04 extraction rule):

| Measure | Definition |
|---|---|
| Faithfulness | supported ÷ checkable assertions |
| Coverage | assertions with a supporting citation ÷ checkable assertions |
| Precision | supporting claim–citation pairs ÷ all cited pairs |
| Completeness | decision, reason, evidence, limitations (0/1 each) |

An empty explanation has 0 completeness and coverage; zero-denominator faithfulness and precision stay undefined. Raw-text assertions from malformed outputs are reported separately (rule 11.7).

**Statistics.**
- Scenario mean, standard deviation, minimum and maximum for all six systems, with explicit counts, denominators and missing values.
- Paired differences, with confidence intervals resampled by episode, keeping each LLM's three trials together.
- A date-cluster sensitivity check, given only 6 dates.
- Planned, not yet implemented: the forecast-tie rate, the share of Greedy B job decisions where every feasible start has equal forecast emissions.
- No tuning on held-out results.

## 2. Reliability method

The professor asked for an inter-rater reliability report (#95).

1. Two raters (Nisha, and Matty as the independent second rater) annotate independently. Their originals are kept unchanged, identified by SHA-256.
2. **Before adjudication**, we report:
   - matched assertion counts;
   - label marginals and the confusion matrix;
   - raw percent agreement and Cohen's κ (undefined when chance agreement is 1 or there are no pairs, with a plain-language explanation of label imbalance);
   - extraction agreement, separately.
3. Disagreements are then decided jointly, with a rationale each. Adjudicated labels are a separate record and never recompute reliability.
4. For held-out work, each annotation records a decision for every summary sentence, limitation and raw-text unit (`text_review`). Comparisons run with `--require-text-review`, so an original can't skip extraction silently.

## 3. Development evidence

### 3.1 Development round (11 synthetic cases, 20 reviewed outputs)

Source: [E05 development IRR](../e04/ratings/agreement/E05_DEVELOPMENT_IRR.md).

| Measure | Result |
|---|---|
| Matched claim assertions | 32 |
| Raw label agreement | 75.0% (24 of 32) |
| Cohen's κ | 0.00 |
| Extraction agreement (summary/limitation) | 0.00: 64 assertions found by the second rater only |
| Completeness κ (decision / reason / evidence / limitations) | 1.00 / 0.44 / 0.46 / 0.90 |

- **κ is 0 even though raw agreement is 75%.** One rater labeled every claim
  supported, so expected chance agreement equals observed agreement. The label
  marginals explain the calculation; neither statistic alone establishes reliable
  annotation or determines the raters' underlying labeling process.
- **All 8 label disagreements go the same way.** Each is a claim the second rater found contradicted (4) or unsupported (4).
- **Adjudication.** The joint adjudication ([record](../e04/ratings/agreement/E05_DEVELOPMENT_ADJUDICATION_2026-10-29.json)) decided all 77 items. It resolved all 8 label items and all 5 completeness items to the second rater's original, and kept 63 of the 64 extraction items.

### 3.2 Calibration round (rule 11.8, two practice outputs)

Source: [calibration ratings](../e04/calibration/ratings/NISHA_SUBMISSION.md).

| Measure | Result |
|---|---|
| Claim labels | 3 of 3 agree |
| Completeness | 8 of 8 agree |
| Summary/limitation extraction | 0 of 9 (one-sided) |
| Raw-text extraction | 0 of 5 (one-sided) |

**What the two rounds show together:** calibration's three matched claim labels
and eight completeness decisions agree. Development includes eight claim-label
disagreements and five completeness adjudication items. Extraction also differs:
one original contains fewer summary, limitation and raw-text assertions. The six
approved clarifications (#149), including per-text-unit decisions, address that
gap prospectively; their effectiveness still needs held-out evaluation.

### 3.3 Limitations of this evidence

- **Small samples:** one changed agreement among 32 pairs shifts raw agreement
  by 3.125 percentage points; among three calibration pairs it shifts it by about
  33.3 points. No confidence intervals are reported in these development records;
  this is a reporting limitation, not a claim that intervals cannot be calculated.
- **Synthetic cases.** The first rater wrote both the development cases and the calibration packet, which is disclosed.
- **Not a study result.** The held-out reliability report (#95) is the result for the study.

### 3.4 Execution receiving (public EP-HAND1, two separate runs)

Source: [unchanged receiving report](../evidence/I01_RECEIVING_NISHA_2026-11-03.txt),
[scoped manager acceptance](../handoffs/I01_NISHA_RECEIVING_ACCEPTANCE_2026-11-04.md)
and [manager corroboration](../evidence/I01_RECEIVING_MANAGER_CORROBORATION_2026-11-04.json).
The receiver's [public confirmation](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6623003586)
is retained separately.

Nisha received the six original results and 180 traces, verified the committed
archive digest and all 186 evidence files, and replayed the executed starts with
E01 under `Q03_OPTION_B`. Each unit covers slots 0–29 exactly once.

| System | Run | Executed starts | Completed | Missed and unfinished | Model calls | Replay findings | Result mismatches |
|---|---|---|---|---|---:|---:|---:|
| `greedy_a` | `RUN-1f6e4c4c2afb` | J1 at 0, J2 at 2 | J1, J2 | J3 | 0 | 0 | 0 |
| `greedy_b` | `RUN-1f6e4c4c2afb` | J1 at 2, J2 at 4 | J1, J2 | J3 | 0 | 0 | 0 |
| `decision_tree_c` | `RUN-1f6e4c4c2afb` | J1 at 0, J2 at 4 | J1, J2 | J3 | 0 | 0 | 0 |
| `random_forest_d` | `RUN-1f6e4c4c2afb` | J1 at 2, J2 at 4 | J1, J2 | J3 | 0 | 0 | 0 |
| `agent` | `RUN-646ddd3a1142` | J1 at 0, J2 at 2 | J1, J2 | J3 | 12 | 0 | 0 |
| `plain_llm` | `RUN-646ddd3a1142` | None | None | J1, J2, J3 | 5 | 0 | 0 |

The Agent has 4 records with a repaired stage and 4 with a fallback stage. Stage
presence is not repair success.

What this does and does not show:
- **Consistency, not quality.** Zero findings means the saved executions and
  results agree with an independent reconstruction. It says nothing about
  explanation faithfulness, and it isn't a safety finding.
- **No comparison.** This is one episode, with one trial (trial 0) per LLM and
  one deterministic execution per classical system, across two runs with
  different identities and code revisions. The table can't rank systems, and the
  Plain outcome is not an estimate of Plain's performance.
- **Forecast differs from the study.** EP-HAND1 uses a shaped perfect-foresight
  forecast, which is why Greedy B moved work later here. This doesn't predict its
  behavior under a flat study forecast (§1).
- **Replay independence.** E01 is separate from the production simulator and
  checker, but its author performed this review. It isn't a second implementation.
- **Completed work.** `completed_work` is absent from the original results, so
  that comparison is reported as absent, not as a match.
- **Run manifests.** They weren't in the packet. Matty checked them separately.

### 3.5 Classical-model fold scores

Source: [P06 blocked-fold metrics](../../models/DEVELOPMENT_FOLD_METRICS.md).

| Selected model | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---|
| Decision tree C (depth 8) | 0.394 | 0.578 | 0.469 | 1,411 positive, 4,635 negative |
| Random forest D (100 trees, depth 10) | 0.456 | 0.618 | 0.525 | 1,411 positive, 4,635 negative |

These are pooled post-selection classification scores on development folds. They
aren't scheduling outcomes or final performance, and they don't show that either
model improves a research endpoint. Selection used rollouts, so a shallower
candidate with a higher F1 isn't a new selection criterion. Both models were
trained on the flat development forecast, so `carbon_mean_g_per_kwh` and
`carbon_min_g_per_kwh` were equal in every row and didn't differ between candidate
starts at a decision. Compatibility with whichever study forecast is eventually
adopted must be assessed before freeze.

## 4. Held-out results

*To be written after the I02 freeze, the 300 runs, the O04 references and the held-out review (#95).*
