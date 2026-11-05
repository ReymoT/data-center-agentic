# CF60 development compatibility check plan

Matty approved preparing this offline plan on November 4. It does not adopt CF60,
authorize new source reads, solver calls, relabeling, training or held-out access.
Reimo retains the production broker work; Ved owns O02/Q08 certification and
Edison the C/D compatibility response. Existing work and ownership are preserved.

## Inputs and prerequisites

Use the [CF60 proposal](ISSUE60_CAUSAL_STUDY_FORECAST_PROPOSAL.md), the existing
40 development episodes, allocation/fold map and immutable original forecast,
label/cache and C/D artifact hashes. Start from the
[read-only legacy audit](LEGACY_LABEL_AUDIT_2026-11-04.md); do not repeat it as
proof of CF60 compatibility. Record exact broker/selector versions before any
comparison. Preserve the recorded-index mapping and both interval hypotheses.

First obtain/pin the production broker's restricted source-read behavior and its
independent receiving. Before new source reads or solves, record an explicit
bounded development-only execution plan with input/output paths, permitted rows,
solver limits, stop conditions and authorization. This document supplies no such
execution authorization. Do not choose a physical interval interpretation through
implementation convenience; B1–B3 remain unresolved and B4 provisional.

## Comparison outputs to prepare

| Check | Required evidence |
|---|---|
| Forecast values and eligibility | Legacy versus CF60 per episode/issue/hypothesis; selected source rows, completion/availability times, age and full read footprint; no future reads, wraparound or invented backfill |
| Q04 evidence | Coverage/freshness pass, failure and missing counts, with exact reasons and no missing-to-zero conversion |
| Candidate features | Same episode/job/decision identities; changed forecast-derived features, feasible candidate sets and numerical differences |
| O01/O02 | Certified status, objective and positive/negative/uncertified changes; unavailable cases remain exclusions, never negatives |
| Ties and Q08 | Distinguish multiple local candidates from alternative globally optimal schedules; report unknown multiplicity as unknown until a separately bounded method measures it |
| Existing C/D artifacts | Verify unchanged binaries and feature contract; assess prediction/rollout implications on development only; no automatic replacement or retraining |
| Custody | Union legacy plus CF60 read footprints across all 40 development episodes, recorded mapping plus both interval hypotheses; versioned selector checks bidirectional separation before any nonce |

## Acceptance and handoff

Record matched comparison counts and missing inputs for every row above. A feature
contract pass or unchanged predictions is not sufficient scientific compatibility.
Ved supplies the exact O02/Q08 finding, Edison the C/D implications, and affected
owners record agreement on any shared change. Escalate the smallest unresolved
choice to Matty; silence supplies no acceptance. Keep failures and old artifacts.

Hand Nisha the accepted, hashed compatibility report for I02 only after actual
checks exist. The shaped same-hour forecast alternative is deferred unless this
development assessment justifies reopening it; it is not silently substituted.
No final source acceptance, held-out content or frozen result follows from this plan.
