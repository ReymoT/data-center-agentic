# Matty's E05 pilot rating guide

Submission update, October 22: Matty has now supplied his completed first-pass workfile. The [original and validation handoff](../handoffs/E05_MATTY_RATINGS_2026-10-22.md) supersede the earlier pending-Matty state below. Do not edit that original during comparison. Nisha first preserves her own original; paired agreement and separate joint adjudication follow. E05 remains Verifying.

Status: guidance and a blank personal workfile, not completed ratings. Matty asked for recommendations to review before filling his own ratings. These recommendations explain the draft rule; they do not assign labels to DEV01-DEV11. Nisha owns E04, Matty supplies his own second ratings, and Ved is the technical contact. Read [the draft extraction rule](EXTRACTION_RULE.md), [packet](RATER_PACKET.md) and [technical handoff](../handoffs/E04_DEVELOPMENT_CASES.md).

## Recommended approach

1. Work through X and Y separately, using only the decision facts and output shown in the packet. Do not use the notional system or intended category as an answer key. The packet is synthetic pilot material, not saved model output.
2. Keep every prelisted Claim. Independently extract every additional checkable summary and limitation fact. A summary restating the same Claim uses that Claim's ID and `restated_in_summary: true`; do not count it twice. Preserve the original wording. Use S1, S2 for new summary assertions and L1, L2 for new factual limitations. Note ambiguous cross-field duplicates; their complete worked rule is not frozen yet.
3. Choose **supported** when the available evidence confirms the assertion, **contradicted** when it shows the assertion is false, and **unsupported** when confirmation is unavailable. A claim that a check ran needs evidence that it actually ran. A matching forecast number does not establish that a measurement was taken.
4. Judge citations separately. List only cited IDs that actually support that assertion in `supporting_cited_ids`, once each. A true fact may cite the wrong source: its label can be supported while its supporting-citation list is empty. The script checks structure, not your judgment of truth or source support.
5. Rate completeness separately: decision, reason, evidence and limitations, each 0 or 1. Faithfulness is not a completeness score. An output can be detailed and wrong, or brief and accurate.
6. A no-text no-op is N/A only when the actual waiting queue is empty. Missing or malformed required output remains in the packet. Do not replace it with a successful example. The pilot scorer does not extract raw malformed-text assertions; flag any such text requiring review for Nisha before freeze.
7. Use the agreed 0.05 kWh/kg and 0.05-percentage-point tolerances. Other unit/reference rules and the stricter ambiguous-energy-basis proposal are still pending in [issue #24](https://github.com/ReymoT/data-center-agentic/issues/24#issuecomment-6354628003). Record uncertainty in notes; do not silently adopt a proposed tolerance, guess a quantity or call an unresolved rating final. The existing draft accepts only the three labels, so leave a genuinely pending judgment blank and note why until the owners resolve it.

## Separate worked examples

These examples are not answers to the pilot packet.

- The visible record says a job arrives at slot 2. The assertion says it arrives at slot 2: recommend **supported**. If it instead says slot 1: recommend **contradicted**.
- An output says a safety checker approved the plan, but there is no performed-check record: recommend **unsupported**. A constraint's existence alone does not show that the checker ran.
- The visible forecast is 320 g/kWh. The output calls 320 g/kWh a measured value with no observation available: recommend **unsupported** for the measurement claim.
- The correct arrival fact cites a source about an unrelated job: recommend **supported** for the fact, with an empty supporting-citation list. Correctness and citation support are different questions.
- An energy claim does not identify IT versus facility energy: my proposed direction is to require an unambiguous basis in the claim or cited evidence. Until affected-owner agreement, note the ambiguity rather than choosing whichever reference happens to match.

## Your workfile and original ratings

A local copy of [annotation_template.json](annotation_template.json) was prepared outside Git as `output/E05_Matty_rating_workfile.json` in Matty's Codex workspace, with `rater` set to MattyAnd and every judgment blank. It contains 22 output units: 11 pairs, including the N/A no-op pair. The personal file is not a new shared schema and is not a submitted rating set.

Fill labels, supporting IDs, restatement flags, added assertions, completeness and notes yourself. Preserve a dated original before any comparison with Nisha or adjudication. Keep each rater's original separately; do not overwrite originals with a consensus file. Do not publish proposed labels as though they were independently supplied by Matty.

The technical review session already inspected the generator/categories; Nisha co-authored the pilot. Record each actual rater's exposure. AI-suggested labels for these same pilot cases would make the resulting pass AI-assisted, and a human approving them would not turn them into independent original ratings. If that assistance is wanted, label it as practice and arrange new unexposed material or an agreed alternative with Nisha/Ved before claiming E05 acceptance. No fresh blind packet or alternative protocol is invented here.

Next checkpoint: Nisha's original ratings retained before viewing Matty's submitted labels, followed by paired extraction/label agreement and retained separate adjudication. Q10 and E04/E05 remain open; the rubric is not frozen.
