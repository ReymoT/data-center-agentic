# E04/E07 study rating packets

Owner: Nisha (E04, E07). Second rater: Matty. Status: offline tooling, tested on public fixtures and the saved public RUN-cb85f5a3425c (EP-HAND1). No held-out output exists or was read.

## What it does

1. `scripts/build_review_sample.py` draws the Q10 main sample and the separate boundary stratum from the frozen episode bundles, using the recorded seeds (job timing only). Both records go to private evaluator storage. The output files must be new, and the script prints only counts and hashes.
2. `scripts/build_study_packets.py` turns those selections and the saved Agent and Plain run units into rater material:
   - `cases.json`, `RATER_PACKET.md` and `annotation_template.json` (text review on, cap limit 256 by default) go in a new rater folder;
   - the **unblinding key** is written separately and is refused if it would sit inside the rater folder.

`dc_sustainability/evaluation/packets.py` holds the logic:
- **Own state per output.** Agent and Plain follow different trajectories, so each output is shown with the visible state its own system faced. The state is rebuilt by replaying that system's executed starts.
- **Hard check against what the model saw.** A replayed state must reproduce the record's saved `input_hash` (the Context hash). Otherwise the pair is withheld and listed with its reason. On RUN-cb85f5a3425c all 48 Agent and Plain decisions reproduce.
- **Recommended plan.** Raters see the last stage that produced a plan (fallback, else repaired, else initial). The stage is recorded only in the key. Raw text is shown only when no plan could be read (rule 11.7).
- **Blinding.** X/Y order and case order are shuffled with the recorded `--order-seed`. Case files carry no system, stage, trial, stratum or sample kind.
- **Nothing dropped quietly.** A selection whose unit or record is missing is listed in the key with its reason, never replaced. A pair drawn by both the main and boundary samples is rated once, with both kinds recorded.

## Case format change (additive)

`review.ReviewCase` now accepts `states: {X, Y}` in place of the shared `state`. Development and calibration case files are unchanged: `build_e04_cases.py --check` and `build_e04_calibration.py --check` both pass, byte for byte.

## Open decisions (#95, before the freeze)

- Matty's confirmation of the own-state-per-output format and of "raters see the recommended plan". One line for EXTRACTION_RULE.md §11 follows once he confirms.
- Rater workload: up to 180 outputs per rater (60 main plus up to 30 boundary pairs).

Still to build: the report renderer for the study-tables JSON.

## Matty receiving and direct fixes — November 13

Matty accepts own-state-per-output with the matching immutable snapshot and the final recommended plan as documented in EXTRACTION_RULE section 11.10. A plan shown is not an execution verdict. Personal rater availability remains unconfirmed; no assistant commits Matty's time or ratings. Fixed the packet path that previously admitted missing input hashes, incomplete units or mapping-key identity drift. Those pairs are withheld with reasons. Added regression tests; included the rubric in the rater folder, rejected key/output path equality and removed private values from CLI failure summaries. Recovered/rerun public checks are separate from any future held-out authorization. The table renderer is tracked in PR #216.
