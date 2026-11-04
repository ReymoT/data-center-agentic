# Existing development label and tie audit

Matty performed this read-only audit on November 4, using the existing,
authenticated manager-produced P04 corpus and its development-only label cache.
[Aggregate evidence](../evidence/legacy-label-audit-2026-11-04.json) records the
corpus hash, historical source revision/hashes, actual counts and scope limits.
No source CSV was read, solver/model called, held-out content accessed, or
original label/model changed. All 1,143 protected corpus/cache/model files were
rehashed unchanged after the audit. No private paths or raw rows are published.

## Answers to Nisha and Ved

1. **The historical pipeline did use flat persistence forecasts.** Source revision
   `94839dc4b547c3f1e50fabed0e50b1653173b3ad` calls `persistence_forecasts` when
   collecting O02 inputs. Its adapter repeats the preceding row's value across
   the visible horizon. This is verified against historical source, not inferred
   only from today's code or from a new regeneration.
2. **The saved labels mark the selected schedule, not every alternative optimum.**
   All 6,046 corpus labels exactly match the 570 cached certified visible solver
   results and their checksummed label entries. Historical labeling marks a
   candidate positive exactly when it appears in the one selected schedule.
   Positives total 1,411 and negatives 4,635, across 40 development episodes.
3. **The cache does not count alternate global optima.** It records one schedule,
   objective/bound/gap and the stable-backend tie description. Exact global
   optimum multiplicity remains unknown. No percentage of globally tied optima
   can be recovered merely by counting positives or local candidate choices.

## What the saved features establish

There are 1,411 job-decisions, of which 1,075 have multiple candidate starts.
Within every job-decision, the saved carbon mean/minimum feature pair is constant
across its candidates. These are local feature-equivalent choices, not proof of
multiple jointly feasible global optima: capacity couples waiting jobs.

Mean and minimum are exactly equal in 5,974 of 6,046 rows. All 6,046 agree within
relative tolerance 10^-12; 72 have floating-point roundoff differences. This
corrects the earlier report wording that they were exactly equal in every row.
The tolerance here only describes saved-feature roundoff. It is not an adopted
solver tolerance, tie rule, label change or forecast-tie classification threshold.

## Consequences and remaining work

The lack of a relative cleaner-hour signal already affects the legacy labels;
it is not a new phenomenon unique to CF60-v1. Their selected-schedule targets
must not be described as a uniquely optimal start or as membership in all
optimal schedules. Backend selection can affect positives where alternate
optima exist; this audit does not claim how often that occurs.

Preserve original labels, model binaries, folds and reported development metrics.
This audit does not certify CF60-v1 compatibility, require automatic relabeling
or retraining, or choose Q08. After the production broker/versioned inputs exist,
the bounded development-only comparison proposed by Ved can measure coverage,
features, objective/label changes and tie behavior under the legacy method and
both CF60 interval hypotheses. Existing unavailable/excluded cases must remain
explicit; this definite-row corpus cannot recover all original exclusion counts.
