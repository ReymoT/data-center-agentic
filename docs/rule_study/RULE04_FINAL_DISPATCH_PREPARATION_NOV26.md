# Final-input dispatcher preparation — November 26

Matty owns this direct implementation under #242/#244. This is offline code and
authored-fixture validation, not generation, isolation acceptance, a protocol
freeze, scientific execution or generalization evidence. Instruction 1.30 and all
163 accepted scientific source bindings stay unchanged.

## Problem and fix

The existing development dispatcher accepts only the exact retained development
pair or its authenticated unfinished suffix. It cannot evaluate final inputs.
`scripts/prepare_rule_study_final.py` supplies a separate fixed backend, reusing
the same contained supervisor, opaque episode mapping, runner, independent replay
and accounting. The development path retains its default behavior. No scheduler,
policy, simulator, metric, verifier, accepted specification or original output is
changed. `scripts/rule04_final_generation.py` is an explicitly separate final
orchestrator using the existing draw order/predicates and actual retained-case
exclusion, not an unlock of the historical development generator.

Review also reproduced a retained-input double-read defect: hashing a file and
then reopening it for parsing did not bind the parsed object to the verified
bytes. Both paths now parse the single verified read. The new regression fails
before the fix and passes afterward; accepted input bytes/hashes are unchanged.

## Three separate releases

1. **Generate only.** A clean merged code/lock/specification snapshot, unchanged
   scientific baseline, actual retained development files, whole-protocol freeze,
   absent external output and new single-use ID are mandatory. Fresh exact host
   approval precedes ledger reservation and stdin-gated Windows containment. Only
   then does this dispatcher construct its fixed-seed RNG. This is a local workflow
   guard, not proof that nobody computed the public deterministic stream elsewhere.
   The output is 120 synthetic cases, 40 per
   stratum, plus a separate evaluator-only sidecar and receipt. No policy runs.
2. **Independent isolation receiving.** Nisha checks actual predicates/labels,
   counts, actual development/authored full-case overlap and accounting/visibility.
   Workload-only diversity/overlap must be reported separately: the accepted rule
   excludes full-case overlap, not every repeated workload. Her actual record and
   the generation receipt are hash-bound. A JSON PASS or URL cannot authenticate
   the person or source of that record; the trusted host must do that explicitly.
3. **Evaluate in two fixed stages, each freshly authorized.** The accepted
   original per-stratum case order and three-policy order are retained. The revised
   proposal uses indices00-19 of each stratum in stage0 and20-39 in stage1: each
   half is20/20/20 cases (180 pairs). Each stage has exactly
   10,800 states AND transitions for execution plus replay, for 21,600 combined.
   Stage 1 requires the authentic complete first-stage receipt, exact same code,
   inputs and receiving, and verified cleanup. A failed/incomplete stage is not
   retryable or silently replaced. Unknown partial work is never assumed zero.

The host authenticates freeze, exact approval, actual generation/isolation record
and, for stage 1, actual parent-stage evidence. The request cannot supply an
approval callback, command, module or interpreter. The public CLI only drafts or
inspects; it has no execute action. Earlier consumed IDs cannot be reused.

## Bounds still need a reviewed exact request

Generation requests must explicitly supply wall time, output threshold, proposal
count and conservative feasibility-assignment reservations. Implementation maxima
are 900 seconds, 256 MiB observed output, 30,000 proposals total and 2,430,000
reserved Cartesian assignments. Every stratum also retains its 10,000-attempt
ceiling. These maxima are not approved run settings. Reservations charge each
proposal's complete legal-start product before invoking feasibility, even when
search exits early. They are not actual explored-state measurements.

Each evaluation stage separately declares at most 900 seconds total, at most 60
seconds per pair, an observed-output stop threshold at most 256 MiB and a separate
3-second cleanup allowance. Output monitoring is a threshold, not a filesystem
quota. Runtime can still exceed the available budget and stop incomplete. Two
successful 180-pair stages are not promised by this code or by CI.

No final-generation or evaluation request is approved here. The new stage layout,
receiving fields and resource semantics must be reviewed with affected consumers
and pinned in the actual freeze before any release. The final set is never used
to tune rules. If code changes after generation, the equality gate fails rather
than pretending that the old cases remain unseen under a new system.

## Offline use after publication

```
python scripts/prepare_rule_study_final.py draft --phase generate
python scripts/prepare_rule_study_final.py draft --phase evaluate
python scripts/prepare_rule_study_final.py inspect <reviewed-request.json>
```

Drafts retain blank limits, ID, output and freeze/receiving fields. Inspection is
preparation only. Do not replace blanks with guessed acceptance or treat a READY
preflight as permission to run. Existing scientific commands remain unchanged.

## Tests and remaining work

Offline tests use authored A fixtures, the known development seed for draw-stream
equivalence, manually enumerated fixture profiles,
malicious relabelled development copies and mocked authorities/supervisors. They
never draw either final study input from its seed or create actual scientific
authority. They exercise hash/key drift, hidden-weight accounting, no-authority
refusal, strict counts/bounds, same-freeze stages, failed cleanup, consumed IDs and
ordinary runner/replay behavior under both scope labels. Fixture PASS is not
unseen isolation, separate-person acceptance or a policy result.

Next: affected-boundary review and actual frozen generation request, exact Matty
approval, actual generated files, Nisha isolation receiving, then separately
authorized evaluation stages and receiving. Ved's saved-result numerical
reproduction and Nisha's current report integration proceed in parallel; no repeat
of the already accepted 360-pair development receiving is needed. Matty fixes
defects directly and performs final PDF/demo/release review.

## Review correction: fixed seed and procedural isolation

The final seed2026111902 was fixed publicly by the November19 specification. It is
not newly drawn or secret at release. Final content is deterministic from pinned
code and retained inputs. This workflow has not invoked final generation; prior
computation elsewhere is not known and cannot be excluded by hashes or artifacts.
Held-out status is procedural, not cryptographic. No fresh seed or specification
change is adopted. Earlier seed-not-drawn statements describe the recorded local
workflow only, not global non-exposure.

The revised stage layout remains a proposal pending affected-boundary review and
actual freeze, not accepted evaluation settings. Generation counts and budgets
are unchanged. A single global duplicate set is equivalent to per-stratum sets:
missing-forecast identities have null scores, and feasible versus infeasible
strata cannot share an identical full case. The development-seed equivalence test
checks this behavior without constructing the final RNG.

Generated metadata now reports full-case/workload diversity per stratum, attempt
ceilings, label provenance, request authorization ID and a distinct orchestrator
source hash. Independent receiving must still recompute diversity/overlap and
accounting; metadata alone does not establish acceptance.
