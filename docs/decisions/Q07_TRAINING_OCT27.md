# Q07 development feature and training protocol

Status: accepted October 27, 2026. Edison owns implementation. Ved is the O02
label consumer and Nisha is the development/held-out metrics consumer.

The accepted record is Edison's proposal in issue #82, corrected by Ved's four
clarifications, Nisha's two metrics clarifications and Edison's explicit
acceptance of both replies.

## Accepted behavior

- The eight feature names and order are `delay_slots`,
  `deadline_margin_slots`, `duration_slots`, `power_kw`,
  `available_capacity_kw`, `queue_load_count`,
  `carbon_mean_g_per_kwh` and `carbon_min_g_per_kwh`.
- `deadline_margin_slots = deadline_slot - start_slot - duration_slots`; zero
  means the candidate finishes exactly at its deadline.
- Missing capacity or missing/stale carbon excludes the Q07 row only. It does
  not establish physical infeasibility, invalidate a checked-A schedule or
  permit imputation.
- Candidate scheduling uses the full deterministic order already implemented
  by the constructor: nonflexible first, earlier latest feasible start, higher
  selection probability, earlier start, smaller numeric job ID, then job-ID
  text as the final tie-break.
- Three blocked folds use development data only. Episodes and overlapping
  source windows stay within one fold. Preprocessing is fitted on each training
  partition and applied unchanged to its validation partition. Held-out data
  never enters folds, preprocessing, class counts or threshold selection.
- Balanced class weights use training-partition counts only. A partition with
  an empty class gets no invented weight and never borrows held-out labels.
- The single positive threshold is 0.5. With no predicted positives, precision
  and F1 are not applicable. Recall is zero only when true positives exist;
  otherwise it is also not applicable. Excluded rows/folds are counted and
  not scored as zero or silently averaged.

## Implementation boundary

PRs #86 and #90 provide visible-input feature rows and unlabeled development
state collection. They do not provide Ved's certified Q08 labels, fitted
preprocessing, trained decision-tree/random-forest artifacts, scheduling study
results or held-out acceptance. Those downstream tasks remain open.
