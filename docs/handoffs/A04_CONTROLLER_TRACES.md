# A04 controller and durable traces

Owner Matty; issue #17; Reimo technical contact. October 24, instruction 1.26,
F02 1.0.0. Based on merged A03 main 7d57bcac. Matty authorized the recommended
independent implementation; the exact scope was posted in #17 before coding.

`ExecutionController.execute_step` consumes a validated unexecuted F02
DecisionRecord and selected stage, not a direct ApprovedActions capability.
It rechecks the actual selected plan using current state and authoritative
constraints, preserves the original proposal hash, binds the current version,
and applies only current-slot starts. Future intentions never execute early.
No selected passing check, stale version, changed constraints, failed recheck,
exceeded caps or forbidden plain repair/fallback means no new starts. S01's real
refusal path advances running work and the clock once. Old-slot/different-episode
requests and completed replays do not advance another slot.

`TraceStore(directory)` has no default external storage configuration. It writes
existing F02 DecisionRecord JSON, validates reads, and refuses conflicting
replacement. A flushed/fsynced temporary file is published exclusively by a
same-directory hard link; unsupported filesystem operations fail explicitly.
Private intent reservations precede effects and prevent duplicate run/system/
episode/slot execution. An intent without a final trace is ambiguous after a
process failure: raise IndeterminateExecution and reconcile actual state rather
than repeat the effect. This is internal storage, not a new shared trace schema.

One controller must be the simulator's sole mutator. Its lock protects its own
calls; it does not claim safety against unrelated code directly mutating S01.
The files support process-failure ambiguity detection, not a promise about every
filesystem/power-loss scenario. Replaying a saved trace does not restore a newly
reset simulator or implement Nisha's experiment checkpoint/resume system.

Actual evidence: 103 focused runtime/verification tests pass in 0.62s; one full
offline suite passes 1,173 tests and 19 subtests in 7.78s. Setup/links/policies,
Ruff lint/format (97 files), compile and whitespace pass. Tests use real A03 and
S01, not an approving checker stub. They cover stale/duplicate/bypass/race,
capacity changes, immutable/corrupt traces, interrupted writes, restart ambiguity,
plain restrictions and all 30 real synthetic slots with clock/drain/completion.
Test-only staged fallback inputs check preservation; they do not implement P02 or
prove a model-driven repair/fallback episode. Earlier A01 failures are retained.

No schema, dependency, runtime pin, prompt, source fixture, original rating or
independent evaluator implementation changes. Full A04 receiving/runner/Option B
integration still needs actual consumer evidence. Exact PR/main CI, merge and
branch cleanup are recorded in #17 after execution. No model call occurred.
