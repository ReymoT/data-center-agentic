# E04 statement extraction and labelling rule (draft 0)

Status: draft for the development review, owned by Nisha (E04). It applies what Nisha and Matty agreed in [issue #22](https://github.com/ReymoT/data-center-agentic/issues/22): every checkable assertion is reviewed, summary included, and repeated assertions share one ID. It is frozen only after both raters have used it on the development cases and the Q10 record is complete. Ved's sampling and analysis agreement is still pending and does not affect this rule.

Sections 1–10 are the draft 0 text both development originals were rated under; they are left unchanged so those ratings stay interpretable. Section 11 proposes the clarifications for draft 1, from the development reliability report and the #24 decisions. Matty and Ved agreed to 11.6–11.8 on October 30, 2026 ([#22](https://github.com/ReymoT/data-center-agentic/issues/22)). Draft 1 becomes the rule for the held-out review at the E04 freeze, after the 11.8 calibration.

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

- **supported**: the evidence confirms it. A number must be within the agreed tolerance: absolute 0.05 for kWh and kg, 0.05 percentage points for percentages. Tolerances and reference selection for other units remain proposals in issue #24; this draft does not adopt them. Record an unresolved basis in the pilot notes and resolve it before freezing the rule or reporting final ratings.
- **contradicted**: the evidence shows it is false.
- **unsupported**: the evidence available can't confirm it. This includes invented checks, facts or citations, a forecast presented as a measured value, a savings claim whose two schedules don't complete the same jobs over the same horizon, and any claim that needs evidence that isn't visible (for example, a carbon value when no forecast is available).

A Claim record with several facts is contradicted if any part is contradicted, supported only if every part is supported, and otherwise unsupported.

Separately from the label, record which cited IDs actually support the assertion (`supporting_cited_ids`), listing each supporting ID once. A true statement can still cite the wrong evidence.

## 5. Outputs without an explanation

- **Empty-queue no-op** (the case has no waiting jobs, and an `ok` output has an empty plan, no explanation and no raw response text): not applicable. No assertions, no completeness rating, counted separately. An empty plan while jobs wait is not exempt.
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

## 10. Limits before freeze

The structural validator cannot decide whether the rater extracted every fact, whether two differently worded assertions are duplicates, or whether a citation supports an assertion. Those checks require independent human review and retained adjudication. A successful validation is not rubric acceptance.

This pilot scorer handles structured explanations. It preserves raw failed/malformed text in the packet but does not extract assertions from it. Before real-output review, Nisha and Matty must resolve how any checkable assertions in that text are reviewed so they do not silently escape the agreed full-assertion audit. Repeated facts across Claim, summary and limitation text also need explicit worked deduplication examples before freeze. No final metric or completed E04/E05 review is established by the synthetic packet or scorer alone.

## 11. Proposed clarifications for draft 1

Status: proposed by Nisha on October 28, 2026, after the [development reliability report](ratings/agreement/E05_DEVELOPMENT_IRR.md). Extraction was the largest difference between the two development originals (0 of 64 summary/limitation assertions matched), so most of this section is about extraction. Agreed decisions from #24 (11.4, 11.5) are recorded here so the rule matches E01. Items 11.6–11.8 change the annotation format or the review protocol; Matty and Ved agreed to them on October 30, 2026 (#22).

### 11.1 Read every summary sentence and every limitation

Every summary sentence and every limitation is read and decided one by one, even when the claim records look complete. For each checkable fact in it, exactly one of these applies:

- it repeats a claim record with the same subject and a value within tolerance: set that claim's `restated_in_summary: true`, and add nothing;
- it repeats an earlier summary assertion: add nothing (it keeps the first S ID);
- anything else: add a new S assertion (or L for a limitation).

A plan fact ("J2 is deferred"), a reason that rests on a fact ("because slot 3 is lower") and a total or comparison ("total emissions are …") are checkable even when every number in them also appears in the claims. If an output's summary and limitations really add nothing new, write `summary: no new assertions` in that output's `notes`, so an empty extraction is a recorded decision, not an omission.

### 11.2 Worked example: one summary, every outcome

Hand example (J1 40 kW × 2 slots, J2 30 kW × 2 slots, deadline 6; forecasts 500, 450, 300, 250, 400, 480, 520 g/kWh for slots 0–6). The plan starts J1 now and J2 at slot 2. The claim records are:

- C1: "J1 at slots 0–1 has forecast emissions of 38.0 kg." (40 × (500 + 450) / 1000 = 38.0)
- C2: "J2 at slots 2–3 has forecast emissions of 16.5 kg." (30 × (300 + 250) / 1000 = 16.5)

Summary: "Start J1 now and J2 at slot 2, so both finish well before slot 6. J1 is forecast at 38.0 kg and the schedule totals 54.5 kg, to reduce emissions."

| Text | Decision | Why |
|---|---|---|
| "Start J1 now" | S1, supported | plan fact |
| "J2 at slot 2" | S2, supported | plan fact; "and" joins two facts |
| "both finish well before slot 6" | S3, supported | a fact the plan implies: J1 ends at 2, J2 at 4 |
| "J1 is forecast at 38.0 kg" | C1 `restated_in_summary: true` | same subject and value as C1 |
| "the schedule totals 54.5 kg" | S4, supported | a new quantity: the total is not any claim (38.0 + 16.5) |
| "to reduce emissions" | not extracted | intention (section 1) |

If the summary had said "J1 is forecast at 40.0 kg", that would be a new S assertion, contradicted, and C1 would stay `restated_in_summary: false`.

### 11.3 The same fact in a claim, the summary and a limitation

One fact gets one assertion, in this order of precedence: claim record, then summary, then limitations.

- **Claim and summary:** as in 11.1, the claim gets `restated_in_summary: true`.
- **Claim and limitation:** C3 says "no forecast is available for slot 7" and a limitation says "forecasts after slot 6 are missing". Same fact, so no L assertion. Write `L repeats C3` in `notes`.
- **Summary and limitation:** S2 says "slot 7 has no forecast" and a limitation repeats it. No L assertion; note `L repeats S2`.
- **Different values or a different subject** are separate assertions: "forecasts after slot 8 are missing" next to C3 is its own L1.

### 11.4 Units and tolerances (agreed in #24)

This replaces the tolerance sentence in section 4 for draft 1:

- kWh, kg, kW and g/kWh: supported when the absolute difference from the reference is at most 0.05, inclusive, with no extra margin.
- slot and h: supported only when exactly equal to the whole-number reference.
- percentages: F02 has no percent unit, so raters apply 0.05 percentage points by hand; percentage results are reported separately and never counted as automatically scored.

### 11.5 Energy basis (agreed in #24, confirmed by Ved in #87)

An energy (kWh) assertion is checked only against the basis its text or its cited evidence states:

- **IT energy, before PUE:** the text says "IT", "before PUE", "excluding PUE" or "without PUE".
- **Facility energy, with PUE:** the text says "facility", "including PUE", "with PUE" or "after PUE", or the claim cites `FACT-SITE-PUE` for its value.
- **Neither, or both:** unsupported, noted `basis_unstated`, even if the value matches one basis.

Worked examples with PUE 1.2 (J1: 80 kWh IT, 96 kWh facility):

| Assertion | Label | Why |
|---|---|---|
| "J1 uses 80 kWh of IT energy." | supported | stated IT basis, 80 |
| "J1 uses 96 kWh including PUE." | supported | stated facility basis, 96 |
| "J1 uses 96 kWh." citing `FACT-SITE-PUE` | supported | the PUE citation states the facility basis |
| "J1 uses 80 kWh." citing `FACT-SITE-PUE` | contradicted | facility basis stated by the citation; 80 ≠ 96 |
| "J1 uses 80 kWh of facility energy." | contradicted | the other basis never rescues a stated one |
| "J1 uses 80 kWh." | unsupported (`basis_unstated`) | no basis stated, although 80 matches IT |

The pronoun "it" is not "IT". A PUE fact cited elsewhere in the output, not for this value, does not state the basis.

### 11.6 Reference kinds (Ved's closed list, agreed in #24)

For each numeric assertion, raters decide which of these quantities it describes, and check it against that reference: job IT energy before PUE; job facility energy with PUE; job emissions; schedule emissions; savings versus a named baseline; carbon intensity at a slot; power, load or capacity at a slot; slot or duration. A savings assertion without a named baseline, or whose schedules don't complete the same jobs under the same inputs, is unsupported.

**Agreed (#22, October 30):** raters may record the kind per numeric assertion in an optional, annotation-only `reference_kind` field (not F02), checked by `review.validate_annotation`. The values are, in the order above: `job_it_energy`, `job_facility_energy`, `job_emissions`, `schedule_emissions`, `savings_vs_baseline`, `carbon_intensity`, `power_load_capacity`, `slot_or_duration`. Agreement on kind is reported over matched assertions where both raters recorded one, with the counts recorded by only one rater.

### 11.7 Malformed or raw-text outputs (agreed in #22, October 30)

Section 10 leaves open how checkable assertions in raw failed or malformed text are reviewed. Agreed:

- Raters extract checkable assertions from the `raw_response` text of an output without an explanation as R1, R2, … with source `raw`, using sections 1–4, with no citations.
- Completeness for a failed or malformed output stays 0 (section 5).
- Raw-text faithfulness is reported separately from structured-output faithfulness and is never mixed into it, with its own counts.
- The annotation format accepts `source: "raw"` in `review.validate_annotation`. Raw-text extraction and label agreement are reported in their own `raw_text` section of the agreement report.

### 11.8 Calibration before the held-out review (agreed in #22, October 30)

Before any held-out output is opened, both raters independently extract assertions on two or three new practice outputs, which are neither development nor held-out cases, and compare extraction only, using this section. Disagreements are resolved by changing the rule text, never by changing either development original. The held-out reliability report is then computed in the same way as the development report. The practice outputs never enter the development or held-out sets, and calibration does not open any held-out output or freeze the evaluation sample.
