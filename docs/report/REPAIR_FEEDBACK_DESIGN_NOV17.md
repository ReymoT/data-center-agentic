# Structured repair arithmetic and deltas — exact offline proposal

Owner: Matty (A03/A02). Tracking: #231. Status: design only; no schema, verifier, prompt or runtime change. Nisha (evaluation) and Ved (F02/check contract) must agree the proposed boundary before implementation. Current `render_repair` passes the initial StageRecord plus errors; structured arithmetic is the enhancement, not the first introduction of feedback.

## Proposed sidecar contract

Use a separately versioned `repair-feedback-v1` payload rendered from existing policy-visible verifier inputs. Do not add fields to F02 Violation/CheckResult or change verdicts in this preparation. Bind schema version, episode ID, decision slot, state version, snapshot ID/hash, candidate plan hash, existing check hash and stage. Every entry identifies `(constraint_id, rule, affected_slot, sorted_job_ids)` plus `status` available/missing and provenance references. If a check is skipped or lacks evidence, mark it unavailable with the existing reason, not a computed pass.

Capacity entries contain the exact active IT load terms (background, already running jobs and newly proposed starts), each with job/source ID, occupied interval, value and kW unit. Evaluate every occupied slot, respecting the existing start/end convention; do not double count a job in running and starts. Bind the limit to the capacity constraint. Report total, limit and signed margin `total - limit`; positive excess is `max(0, margin)`. Keep stored precision and the existing check tolerance; display rounding must not change the verdict. Missing capacity or nonfinite inputs produce no arithmetic assertion. No source CSV, private future arrivals or realized future carbon may enter this sidecar.

Timing/deadline entries use the existing integer slot boundaries: proposed start, arrival, duration, finish, latest permitted finish and decision-window limit. Nonflexible entries show required versus proposed start. Identity/schema/missing-job failures report stable identifiers and reasons without inventing numeric magnitudes. Keep the existing check result authoritative; a feedback-construction error withholds structured feedback and retains the failure, rather than replacing the check or authorizing execution.

## Concrete synthetic illustration (not an actual trace reconstruction)

For synthetic slot 0, background 40 kW, J1 40 kW and J2 40 kW:
`40 + 40 + 40 = 120 kW; limit 100 kW; signed margin +20 kW; excess 20 kW`.
Removing J2 yields `40 + 40 = 80 kW; signed margin -20 kW; excess 0 kW`.
These are illustrative quantities only. The public cb85 excerpts establish initial/repaired/fallback stage identities and starts, but omit full violation details. Do not relabel the initial empty-start failure as an overload or claim this arithmetic was natively returned. Exact saved-state/violation access would require a separately permitted input review.

## Delta semantics and the single repair

The initial invalid plan's feedback enters the one repair prompt. After that repair, compare only checks bound to the same snapshot/state; otherwise mark the comparison stale and require the existing latest-state gate. Stable entry keys produce resolved, persistent and introduced sets. For persistent capacity/timing entries report old/new margin, while preserving each original verdict and count. Changed job sets create introduced/resolved keys; do not treat them as directly comparable magnitudes. Counts use existing Violation counts, not expanded per-slot arithmetic entries, so 1-to-2 remains the original count rather than a new denominator.

A repair delta is post-repair audit evidence; it cannot be fed into a second retry. A failed repair still routes to independently checked Greedy A or no execution. Explanations must not imply an unexecuted repaired plan ran. The controller and independent evaluator remain unchanged. Sidecar/prompt identities and canonical hashes must be frozen for any later authorized run.

## Required implementation verification (not completed here)

Use synthetic public-fixture derivatives: overlap and non-overlap slots; already-running occupancy; duplicate terms; background inclusion; exact/near-limit tolerance; deadline boundary; missing capacity; nonfinite values; stable/changed-key delta sets; stale snapshot; bounded sorted feedback; input immutability; no private fields; original pass/fail unchanged; no extra model call, retry or controller bypass. A matched feedback/no-feedback experiment is separate from deterministic unit tests and needs fixed initial failures, budgets and affected evaluation agreement.

Acceptance: proposed payload/tolerance/identity rules agreed, deterministic implementation and meaningful tests pass, prompt/code/config pins reviewed, then fresh bounded authorization if a model run is needed. Until then, all runtime behavior and original traces stay unchanged.
