# Nisha calibration submission

Nisha reports saving her CAL01 X/Y calibration on October 31, 2026 for #22,
independently and before seeing Matty's file. The original is
`E04_Nisha_original_2026-10-31.json`, unchanged. Its LF-normalized SHA-256 is
`525bb4a5748b374d31adbdbd07756320e9c1dd91b90168c30dfc21d3b55ddee8`,
matching the value posted on #22. A Windows CRLF checkout has a different raw-byte
hash; comparison tooling consistently uses LF. It passes `agreement.load_original`
structurally, so no separate normalized annotation copy is needed. Structural
validation does not establish that every required assertion was extracted.

Disclosure: Nisha prepared the packet (#123), so her extraction was not blind to how the outputs were written.

## Extraction-only comparison

Command:

```powershell
.venv\Scripts\python.exe scripts/compare_e05_ratings.py --cases docs/e04/calibration/calibration_cases.json --a docs/e04/calibration/ratings/E04_Nisha_original_2026-10-31.json --b docs/e04/calibration/ratings/E04_Matty_normalized_2026-10-31.json
```

There are no S/L/R matches to agree: Nisha's file has no summary, limitation or raw-text assertions.

| | Nisha (a) | Matty (b) | Agreement |
|---|---|---|---|
| Summary/limitation assertions | 0 | 9 (6 S, 3 L) | 0 of 9 |
| Raw-text assertions (CAL01/X) | 0 | 5 | 0 of 5 |
| `reference_kind` recorded | 0 | 3 on matched claims | n/a |
| Claim labels (C1–C3) | 3 supported | 3 supported | 3 of 3 |
| Completeness (both outputs, 4 parts) | | | 8 of 8 |

**Reading this for the rule text.** The difference is not a disagreement about labels: every shared judgment agrees. It's the same one-sided extraction gap the development round showed. Rule 11.1 asks for "a recorded decision" for every summary sentence and limitation, but nothing in the annotation format enforces that, so an original can skip extraction silently and still pass validation. That's the clarification this calibration points to (proposal 6 below).

## Proposed answers to Matty's rule questions (for agreement on #22)

1. **Plan facts in raw text with no parsed plan.** Check them against the output's own proposal as far as the raw text states it, including any JSON fragment. That's what Matty did for R1/R2. A raw plan statement is never checked against what a correct plan would be: that's accuracy, not faithfulness.
2. **`reference_kind` for energy with an unstated basis.** Leave it empty and record `basis_unstated` in `notes`. Kind agreement already counts only pairs where both raters recorded a kind. That's what Matty did for S3.
3. **FACT-JOB-J1/J2.** Each job row in the packet is the record `FACT-JOB-<job id>`. Add that sentence to rule section 3, and show the fact ID in the packet's job table for the held-out packet.
4. **Job-record deadlines without a CON-DL constraint.** The job record's `deadline_slot` is authoritative evidence. `CON-DL-*` constraints are additional, not required. So L2 is supported from the job record.
5. **Deadline boundary.** Use the shared task rule the systems are given: a job occupies [s, s + d) and must satisfy start + duration ≤ deadline. With deadline 6 and duration 2, start 4 meets it and start 5 misses it, as Matty labeled L3.
6. **Making 11.1 checkable (new, from this comparison).** The annotation records one decision per summary sentence and per limitation: `extracted` (with its S/L IDs), `repeats C<n>` or `not checkable` (goal, intention or generic caveat). `review.validate_annotation` then refuses a complete original that leaves a sentence undecided. Optionally, raw text gets the same treatment, one decision per sentence.

Both originals stay unchanged. Agreed answers go into the rule text, never into either extraction. #22 stays open until the clarifications are recorded.

## Matty technical review

Reproduced the comparison from both retained files. The extracted-assertion gap is
9 summary/limitation assertions and 5 raw assertions, all present only in Matty's
file. The three shared claims have 100% label agreement, but Cohen's kappa is
undefined because both marginals contain only supported. Raw-text label agreement
and reference-kind agreement are undefined with zero matched rated pairs. This
is extraction-only calibration evidence, not a held-out reliability result or
evidence that the rubric has been applied consistently.

No empty extraction has been filled automatically and no original judgment changed.
Proposals 1-5 remain explicit until adopted in the rule; proposal 6 changes the
annotation format/validator and requires the existing affected-owner agreement
before implementation. Merging this submission supplies the missing original;
it does not close #22, freeze the rubric or authorize opening held-out outputs.
