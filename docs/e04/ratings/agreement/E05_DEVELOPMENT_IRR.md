# Inter-rater reliability: development faithfulness ratings (before adjudication)

Task: E07/R05 reliability report requested by the professor ([#95](https://github.com/ReymoT/data-center-agentic/issues/95), [#42](https://github.com/ReymoT/data-center-agentic/issues/42); requirement in [PROFESSOR_FEEDBACK_IRR.md](../../../decisions/PROFESSOR_FEEDBACK_IRR.md)). Owner: Nisha Mahadev Kolekar. Second rater: Matty Anderson.
Scope: the 11 synthetic E04 development cases (22 output units), rubric `e04-extraction-draft-0`. This is development protocol evidence. The same report is required again for the frozen held-out review.

## Inputs (unchanged)

| Rater | Original | SHA256 (LF) |
|---|---|---|
| a: Nisha | `../originals/E05_Nisha_2026-10-26.json` | `cf8543ae205bf83d5679d917739bb65733e51d74b573771aac040ea6e69ef4b3` |
| b: MattyAnd | `../originals/E05_Matty_2026-10-22.json` | `3b3e0c7509b9bb7c3580f9586260db7c1a9e4356fe570e04fe09a6640e46f16a` |

Both pass the complete structural check. Neither was edited, and every number below comes from the independent originals, before any adjudication.

## Method

- **Matching** (`matching.json`): claim assertions are matched by their shared F02 claim ID. Summary and limitation assertions are numbered by each rater, so they match only through explicit pairs the raters agree; none were supplied, because rater a's original has no summary or limitation assertions to pair. Every unmatched assertion is listed.
- **Extraction agreement**: over summary and limitation assertions only (claims are given to both raters): matched ÷ (matched + found by a only + found by b only).
- **Label agreement**: on matched assertions; raw percent agreement and Cohen's kappa, κ = (pₒ − pₑ)/(1 − pₑ), with pₑ from each rater's label marginals. Kappa is reported as undefined when there are no pairs or pₑ = 1.
- **Completeness**: per part, over reviewed outputs, as a supplement.
- **Tooling**: `dc_sustainability/evaluation/agreement.py` (tested in `tests/evaluation/test_agreement.py`), run with:

```powershell
.venv\Scripts\python.exe scripts/compare_e05_ratings.py --a docs/e04/ratings/originals/E05_Nisha_2026-10-26.json --b docs/e04/ratings/originals/E05_Matty_2026-10-22.json --confirmed-by Nisha --out-dir docs/e04/ratings/agreement
```

## Denominators

| | Count |
|---|---|
| Output units | 22 |
| Empty-queue no-ops excluded (DEV11 X and Y, both raters) | 2 |
| Reviewed outputs | 20 |
| Missing ratings | 0 |
| Assertions, rater a / rater b | 32 / 96 |
| Matched assertions (all claim records) | 32 |
| Unmatched: rater a | 0 |
| Unmatched: rater b (57 summary, 7 limitation) | 64 |

## Results

**Extraction agreement (summary/limitation assertions):** 0 matched, 0 only a, 64 only b, **agreement 0.00**.

**Label agreement on the 32 matched claim assertions:** 24 agreed, **raw agreement 75.0%**, **Cohen's kappa 0.00**.

Label marginals:

| Label | Rater a (Nisha) | Rater b (Matty) |
|---|---|---|
| supported | 32 | 24 |
| contradicted | 0 | 4 |
| unsupported | 0 | 4 |

Confusion matrix (rows: rater a; columns: rater b):

| a \ b | supported | contradicted | unsupported |
|---|---|---|---|
| supported | 24 | 4 | 4 |
| contradicted | 0 | 0 | 0 |
| unsupported | 0 | 0 | 0 |

**Completeness agreement (20 reviewed outputs, supplementary):**

| Part | Agreed | Raw | Kappa |
|---|---|---|---|
| decision | 20/20 | 100% | 1.00 |
| reason | 18/20 | 90% | 0.44 |
| evidence | 18/20 | 90% | 0.46 |
| limitations | 19/20 | 95% | 0.90 |

## Interpretation (plain language)

- **Labels.** The raters agreed on 24 of 32 claims (75%), but kappa is 0. Kappa measures agreement beyond what the two raters' label frequencies would produce by chance. Rater a labelled every claim "supported", so the chance-expected agreement (pₑ = 24/32 = 0.75) equals the observed agreement, and kappa is exactly 0. With one rater using a single label, kappa is 0 whatever the other rater does, so it cannot show agreement here; the 75% raw agreement on its own would overstate consistency. This is a prevalence/label-imbalance effect, not evidence of random labelling. The informative result is the confusion matrix: all 8 disagreements are claims rater b found contradicted (4) or unsupported (4) and rater a found supported, so the raters applied the rubric differently on exactly the claims where it matters most.
- **Extraction.** This is the largest difference. Rater b extracted 64 summary and limitation assertions; rater a extracted none and rated claim records only. Extraction agreement is 0, so the summary/limitation faithfulness denominators of the two originals are not comparable. The rubric's summary-splitting instruction (rule §2) was not applied consistently and needs clearer worked examples and a short calibration before the held-out review.
- **Completeness.** Agreement is high for decision (perfect) and limitations (κ 0.90), and moderate for reason and evidence (κ about 0.45, with 2 disagreements each among 20 outputs).

## Limitations

- Small sample: 32 matched claim assertions and 20 reviewed outputs; a single disagreement changes percentages by about 3–5 points. No confidence intervals are given at this size.
- Synthetic development cases under a draft rubric. They were written as part of Nisha's E04 work, so rater a had prior exposure to the cases (disclosed in #42); rater b did not author them.
- Before adjudication. Adjudicated labels will be reported separately and are never used to recompute these statistics.
- Development evidence only. The same report will be produced for the frozen held-out review.

## Next

Joint adjudication of the 77 open items in `adjudication.json` (8 label, 64 extraction, 5 completeness), with both originals unchanged. Before the held-out review: clarify summary extraction in `EXTRACTION_RULE.md` with worked examples.

## Artifacts in this folder

| File | SHA256 |
|---|---|
| `agreement_report.json` | `6b41053d5a985e7e3875b1a3b29931621f8198a7af65a34c95b02a85aadb2991` |
| `matching.json` | `4e3980b051de5838f4c8eb90b39f16cf34a196eae9c8469d3d279d3ac4ec9de4` |
| `adjudication.json` (empty, to be filled jointly) | `81332131c1aef95ae7d5679d895abecfd20c9b0df58f1f9140ec76e3176e03fa` |
