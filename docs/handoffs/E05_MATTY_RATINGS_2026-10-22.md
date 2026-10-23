# E05: Matty's original pilot ratings submitted

Task: E05. Owner: Matty Anderson (MattyAnd). Receiving lead: Nisha Mahadev Kolekar (nkolekar-nk), E04/E07. Technical contact: Ved (vedp3705). Track [E05 issue #42](https://github.com/ReymoT/data-center-agentic/issues/42) with [Q10 issue #22](https://github.com/ReymoT/data-center-agentic/issues/22).

Matty supplied `E05_Matty_rating_workfile_2026-10-22.json` and identified it as his ratings. His first annotation pass is submitted. E05 is **Verifying** until the paired original ratings, agreement review and joint adjudication are retained; it is not fully Done.

## Original and validation

- [Original submitted JSON](../e04/ratings/originals/E05_Matty_2026-10-22.json): 41,833 bytes, SHA256 `3b3e0c7509b9bb7c3580f9586260db7c1a9e4356fe570e04fe09a6640e46f16a`.
- [Intake manifest](../e04/ratings/originals/E05_Matty_2026-10-22.manifest.json) binds the original to the exact case file, packet, rubric and validator used.
- Rater: MattyAnd. Rubric: `e04-extraction-draft-0`. All 22 expected output units from 11 synthetic pairs are present exactly once, with no missing or extra output keys.
- There are 96 labeled assertions: 32 Claim records, 57 summary assertions and 7 factual limitations. Both DEV11 outputs remain N/A empty-queue no-ops. All records pass the existing `validate_annotation(..., complete=True)` structural check.
- The original's labels, extracted text, citation-support selections, completeness values and notes are unchanged. The intake checks structure and byte identity; it does not certify that a judgment is correct or calculate agreement from a missing second file.

The underlying cases are synthetic pilot examples, not saved model outputs or held-out results. Matty's general guide and the earlier technical-review generator-exposure disclosure remain recorded in [the E04 handoff](E04_DEVELOPMENT_CASES.md) and [rating guide](../e04/MATTY_RATING_GUIDE.md). This submission does not establish an additional blinding guarantee or change the rubric.

## Next receiving action

1. Nisha preserves her own independent original ratings **before opening Matty's labels or notes**. If she has already seen them, disclose that exposure and resolve the independent-review path with Matty/Ved; do not describe an influenced pass as an independent original.
2. Once both originals are retained, Nisha matches assertions by meaning rather than assuming independently assigned S/L numbers refer to the same fact. Keep extraction agreement separate from label agreement on matched assertions, with counts and undefined values retained.
3. Compare the originals without overwriting either. Record disagreements, evidence and final decisions in a separate adjudication record, retaining unresolved disagreements.
4. Nisha/Ved address the explicit rater-note topics before freeze: the named ASAP baseline and job order, quantity/energy basis, summary/limitation duplicates and partial restatements, citation support granularity and raw malformed-text assertion handling. Matty's local interpretations are rating notes, not newly adopted shared rules.
5. Update #42/#22 with original-file links, receiving check, agreement/adjudication artifacts and the next checkpoint. E05 can be accepted only when its remaining criteria are actually demonstrated; Q10 still requires the remaining design/eligibility agreement.

## Reproduction and publication

The existing complete-annotation validator was run against every submitted entry using current main `448d2e47254de173e00661a3a29950086c6690da` / instruction 1.19 and the unchanged committed development cases. Source bytes are preserved and checked against the committed Git blob so checkout line endings do not silently redefine the original hash. The original Downloads file is not edited.

This intake publishes instruction 1.20 to correct current records that still describe Matty's ratings as pending. All task rows, exact merge/authority policies, shared F02 formats/settings, code/tests, requirements and canonical E04 cases/packet/template remain unchanged. Actual applicable checks, exact PR/main CI, latest-head ancestry/branch deletion and the tagged receiving handoff are recorded in #42 after execution. A01 diagnosis remains deferred; no model call or experiment is performed.
