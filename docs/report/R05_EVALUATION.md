# Evaluation design and reliability (R05 draft)

Owner: Nisha. **Status: development draft.** The design is frozen at I02. Results in §3 are development evidence. Held-out results replace or extend them after the frozen runs and the reliability repeat (#95).

## 1. Evaluation design

**Comparison.**
- The main comparison is `agent` against `plain_llm`, given the same visible facts, model and generation settings.
- Greedy A and B, decision tree C and random forest D are scheduling references, not separate hypotheses.
- Classical ML baselines (C, D) and modern AI systems (agent, plain LLM) are evaluated on the same episodes through the same checker and controller.

**Matrix (I02, [checked by `experiments/matrix.py`](../i02/README.md)).**
- 30 held-out episodes: 24 core, covering 6 Phoenix dates × 4 demand scenarios (normal, limited, spike, infeasible) once each, plus 6 normal-demand episodes with withheld forecasts.
- Greedy A/B and C/D run once per episode; the two LLM systems run three trials each, which gives **300 runs**.
- The run attempt budget equals the planned maxima: 2,160 Plain and 6,480 Agent calls.
- Any reduction must be matched across systems and frozen before execution.

**Accuracy.** Measured against saved execution records and independently replayed (E01):
- executed-schedule validity;
- completed work, deadline misses and unfinished jobs;
- facility energy and emissions;
- emissions against hindsight and visible-state references (O03/O04).

Savings are reported only between schedules that complete the same work under the same inputs.

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

- **κ is 0 even though raw agreement is 75%.** One rater labeled every claim supported, so chance agreement equals observed agreement: a prevalence effect, not random labeling.
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

**What the two rounds show together:** where both raters judged the same item, they agreed, except on the 8 development claims above. The consistent gap was **extraction**: one rater extracted far fewer assertions from summaries, limitations and raw text. The six rule clarifications from calibration (#149), including the required per-sentence decision record, target exactly that gap before the held-out review.

### 3.3 Limitations of this evidence

- **Small samples:** 32 matched claims, and 3 claims in calibration. One disagreement moves a percentage by 3–5 points or more, so no confidence intervals are given.
- **Synthetic cases.** The first rater wrote both the development cases and the calibration packet, which is disclosed.
- **Not a study result.** The held-out reliability report (#95) is the result for the study.

## 4. Held-out results

*To be written after the I02 freeze, the 300 runs, the O04 references and the held-out review (#95).*
