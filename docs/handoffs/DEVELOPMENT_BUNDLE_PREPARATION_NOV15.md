# Development legacy forecast-bundle preparation

Matty authorized this missing assembly step and offline synthetic verification on
November 15, 2026 (America/Phoenix), against main
3e9cf87a8f70c279fb2794985222c7bfaf7c1e18 and instruction 1.29. No actual source,
extract or episode values were read. The earlier byte-integrity check is separate.

## Implemented behavior

[The pure assembler](../../dc_sustainability/data/development_bundles.py) preserves
the existing 40 episodes and builds the existing capture shape: episode,
slot0_utc, forecasts_by_slot. It uses the preceding recorded row at each issue,
the unchanged legacy persistence horizon, fact IDs, UTC issuance, source marker,
semantics and unvalidated quality. Every bundle passes state_export.decode_bundle.
It does not regenerate episodes, recover original states, choose dates, change
folds/interval mapping or adopt CF60 as the study forecast.

[The supervisor/worker](../../scripts/prepare_development_bundles.py) takes only
explicit JSON inputs. There is no CSV loader, download, model, solver, simulator,
training or hidden persistence_forecasts(source) fallback. It checks fresh scope,
clean revision/imported-code pins, fixed receipt file hashes, input aliases and
aggregate sizes before consuming separate supervisor/worker one-shot ledgers.
References must be authenticated by the operator: nonempty strings/checksums alone
are not human approval, source permission or historical provenance.

## Exact prospective live scope, not authorization

- 40 receipt-bound full episode JSON files plus one separately authorized extract
  JSON: 41 explicit named inputs, at most 128 MiB aggregate. Full episode parsing
  includes source-derived realized-carbon fields for immutable validation; this
  needs its own access basis beyond the earlier byte-hash-only check.
- The extract must contain exactly the existing sorted 340-row union of legacy,
  start-CF60 and end-CF60 development histories. All values are validated; only
  preceding-row legacy values are used for these bundles. The actual extract has
  not been supplied or created. An alleged source marker is not source lineage.
- Exactly 40 new legacy bundles plus provenance/output hashes, at most 32 MiB
  complete output; a new private output and dispatch location, zero retries.
- At most 900 seconds work, preparation time deducted before gated release, with
  the established Windows Job Object and at-most-three-second cleanup. OS process
  creation itself is not interruptible; late workers are not released. No portable
  containment fallback is provided.
- Zero raw CSV opens, downloads, model/solver calls, simulator steps, label writes,
  classifier inference, fitting, policy rollouts, episode regeneration or held-out
  access. No automatic chaining into state capture or comparison.
- Bad/missing/changed inputs or code, nonfinite/duplicate rows, invalid UTC/cohort,
  existing output, reused ID, caps or deadlines fail closed with failure/partial
  records retained. The parent verifies exact output names, input/approval bindings
  and actual bundle hashes before success. Actual independent receiving is still
  required for provenance, visibility, coverage and authorized scope.

The [pending template](../evidence/development-bundle-authorization-pending.json)
cannot dispatch. Source-use/full-content access, exact extract and episode paths/
hashes, executor/environment/storage/custody, final code pins, sufficient bounds,
new destinations and fresh exact Matty approval remain required. Extraction,
assembly, capture and comparison are distinct authorized operations/budgets; older
consumed approvals cannot silently cover or combine them. New production code also
changes all-production-code pin inventories; refresh pins before any approval.

Only after those gates, the implemented entry point is:

    python scripts/prepare_development_bundles.py --authorization APPROVED_PRIVATE_MANIFEST --out NEW_APPROVED_PRIVATE_DIRECTORY

This command is not permission to execute. No actual assembly or export ran.

## Verification and remaining status

Synthetic tests use the explicit row-index carbon double and synthetic episode
commitments, never retained data. All40 schedules match the existing legacy helper
and the real capture decoder. Negative cases cover incomplete/extra/duplicate/
nonfinite/boolean/wrong-source rows, episode/UTC changes, pending approval, scope,
code, footprint and size gates, changed checksums, dispatch/one-use guards and
output tampering. Launcher wiring uses a supervised test double; real Windows
containment is tested by the existing bounded-worker tests, not a real full-cohort
bundle run. The combined focused suite passes 45 tests. The actual published
pending template is tested to refuse before any input open. Exact PR/main CI follows.

Source B1/B2/B3 remain unresolved, B4 provisional. I02 is unfrozen. The fallback is
prepared but inactive; the November 22, 18:00 Arizona feasibility checkpoint stands.
#95 waits for actual ratings; Matty availability is confirmed. #16 retains November
20-or-new-guidance. #164/O04 and #166/I04 remain correctly blocked by final inputs.
No duplicate task or repeat scope reply is requested. Keep incomplete issues open.
