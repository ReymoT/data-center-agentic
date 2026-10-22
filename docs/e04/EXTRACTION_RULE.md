# E04 statement extraction and labelling rule (draft 0)

Status: draft for the development review, owned by Nisha (E04). It applies what Nisha and Matty agreed in [issue #22](https://github.com/ReymoT/data-center-agentic/issues/22): every checkable assertion is reviewed, summary included, and repeated assertions share one ID. It is frozen only after both raters have used it on the development cases and the Q10 record is complete. Ved's sampling and analysis agreement is still pending and does not affect this rule.

## 1. What is a checkable assertion

A statement whose truth can be decided from the decision's visible state, the constraint snapshot, the output's own plan, or the reference calculations. It has one subject and one claim about it:

- a number about something (an emissions value, a load, a forecast intensity, a slot);
- a fact about a job, slot or constraint ("J2 arrived at slot 0", "the deadline is slot 6");
- what the plan does ("J1 starts now", "J2 is deferred");
- a comparison ("slot 2 is lower than slot 0");
- a stated reason that rests on a fact ("because J3 cannot finish by its deadline");
- a claim that a check or calculation was performed ("the capacity check passed").

Not extracted: intentions or goals ("to reduce emissions"), generic caveats ("forecasts may be wrong"), and assumptions about information nobody can see yet ("assumes no new jobs arrive"). Those still count towards completeness (section 6).

## 2. Units of review and IDs

1. **Claim records.** Each F02 `Claim` record is exactly one assertion and keeps its `claim_id` (C1, C2, ...). Its cited IDs are the record's `evidence_ids`. If its text holds several facts, it is labelled as a whole (section 4).
2. **Summary.** Split the summary into atomic assertions, one per checkable fact. A sentence with "and" usually holds two. A decision and its reason are separate assertions. Number them S1, S2, ... in order of first appearance.
3. **Limitations.** A limitation that states a checkable fact ("forecasts beyond slot 6 are missing") is an assertion: L1, L2, ... Generic or future-facing limitations are not extracted.
4. **Duplicates.** A summary assertion that states the same fact as a Claim record (same subject and quantity, and a value within the claim tolerance) is not a new assertion. Record it as `restated_in_summary: true` on the claim. If the summary gives a different value, it is a separate S assertion. Repeated summary assertions keep the first S ID.
5. Summary and limitation assertions have no citations, so their `cited_ids` are empty.

## 3. Evidence available to a rater

Use what the deciding system could see: the visible state, visible constraints, visible forecasts and the plan. For a claim about outcomes or realized carbon, use the reference calculation. Never mark a system wrong for not knowing realized values at decision time.

## 4. Labels

- **supported**: the evidence confirms it. A number must be within the agreed tolerance: absolute 0.05 for kWh and kg, 0.05 percentage points for percentages. Other units follow the proposal in issue #24 until it is agreed.
- **contradicted**: the evidence shows it is false.
- **unsupported**: the evidence available can't confirm it. This includes invented checks, facts or citations, a forecast presented as a measured value, a savings claim whose two schedules don't complete the same jobs over the same horizon, and any claim that needs evidence that isn't visible (for example, a carbon value when no forecast is available).

A Claim record with several facts is contradicted if any part is contradicted, supported only if every part is supported, and otherwise unsupported.

Separately from the label, record which cited IDs actually support the assertion (`supporting_cited_ids`). A true statement can still cite the wrong evidence.

## 5. Outputs without an explanation

- **Empty-queue no-op** (an `ok` output with an empty plan and no explanation): not applicable. No assertions, no completeness rating, counted separately.
- **Failed or malformed output, or an `ok` output without an explanation:** no assertions. Completeness is 0 and coverage is 0. Faithfulness and precision are undefined (no denominator), never zero.

## 6. Completeness

Rate each part 0 or 1: **decision** (what starts, defers or is abstained from), **reason**, **evidence** (cites or names the facts used) and **limitations** (states relevant assumptions or missing evidence).

## 7. Metrics per output

- faithfulness = supported / checkable assertions
- coverage = assertions with at least one supporting citation / checkable assertions
- precision = supporting claim-citation pairs / all cited pairs
- completeness = rated parts / 4

Zero denominators stay undefined. Agreement between raters is reported separately for extraction (which assertions each found) and for labels on assertions both extracted (percent agreement and Cohen's kappa).

## 8. Worked examples

These use the hand example (J1 40 kW × 2 slots and J2 30 kW × 2 slots, deadline 6; background 40 kW; capacity 100 kW; forecasts 500, 450, 300, 250, 400, 480 and 520 g/kWh for slots 0–6). They are not part of the rating cases.

**A. Splitting a summary.** "Start J1 now because slot 0 is the cheapest slot, and defer J2." The extracted assertions are:

- S1: J1 starts now (a plan fact);
- S2: slot 0 is the cheapest slot (contradicted, because slot 3 is lower);
- S3: J2 is deferred (a plan fact).

The intention "to save carbon" would not be extracted.

**B. A duplicate.** Claim C3 says "the slot 4 forecast is 400 g/kWh", and the summary says "slot 4 is forecast at 400 g/kWh". That is one assertion: C3 with `restated_in_summary: true`. If the summary had said "slot 4 is forecast at 450 g/kWh", it would be S1 and contradicted.

**C. Right fact, wrong citation.** Claim C2 says "the slot 6 forecast is 520 g/kWh" and cites FACT-CI-s05. The label is supported, because the slot 6 forecast is 520. But FACT-CI-s05 doesn't support it, so `supporting_cited_ids` is empty. That lowers coverage and precision, not faithfulness.

**D. Forecast presented as measured.** "The measured intensity at slot 1 was 450 g/kWh" is unsupported. The value matches the forecast, but nothing measured is visible at decision time.

## 9. Annotation file

Start from `annotation_template.json`. Fill `rater`, every `label`, `supporting_cited_ids` and `restated_in_summary`, add S and L assertions with their text, and rate completeness. `dc_sustainability.evaluation.review.validate_annotation` checks the structure; it never decides whether a label is right.
