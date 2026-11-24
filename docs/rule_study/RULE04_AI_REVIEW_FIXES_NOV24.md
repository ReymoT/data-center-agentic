# RULE04 direct review fixes — November 24

Matty asked us to fix the supplied AI review directly, without returning corrections
to owners. [The original review](../evidence/rule04-ai-review-nov24/source.txt) is
preserved byte for byte. Its reviewer identity was blank; this is AI-assisted review,
not new independent-person scientific receiving. The integration receipt records
each disposition. No development batch, final generation, model or training ran.

## Confirmed fixes

- F2: pass the absolute outer deadline to the batch. Start another pair only when
  its full pair allowance plus three-second cleanup and one-second summary margin
  remain. Write fsynced, atomically published per-pair checkpoints. If the outer
  supervisor kills the child before its summary, the host retains the last completed
  checkpoint and an explicit unknown-partial-work failure summary after cleanup.
- F3: retain pair exception type, message and reserved remaining budget before
  re-raising, plus the root exception message. A killed worker cannot report exact
  partial counters; those stay unknown rather than invented.
- F4: pass the authenticated original request hash to the child. Never replace it
  with the hash of a later read when assembling the command.
- F1/F5: inner supervision scans only the active pair. Outer total-output scans are
  spaced by one second and also run at child exit; time polling remains frequent.
  Cache the batch's already-checked case mapping rather than reloading it per pair.
  The byte threshold remains an observed stop, not a quota.
- F10: comparison rows carry their stratum and `comparison_role`; missing-forecast
  rows say `control_not_ranking`, even if their matched numerical reduction is zero.

The rules, simulator, independent verifier, metrics arithmetic, original inputs,
case order and existing resource ceilings are unchanged. All 163 accepted verification
bindings match. The two changed controller files require replacement runtime pins.
[The revised freeze](RULE04_PROTOCOL_FREEZE_NOV24_REVIEW2.json) preserves the original
freeze as history and supersedes its controller pins; it does not authorize execution.
The original request `f797691d…ec706` is superseded and must not be dispatched with
changed code. Prepare a fresh clean merged-main request, ID and output after CI.

## Resource evidence and remaining uncertainty

All 52 focused tests passed on native Windows. They include 18 small authored
runner/replay fixtures and three contained fixture samples (2/3/4 jobs). Samples
took 4.359/3.875/3.938 seconds and wrote 546842/554236/561593 bytes. These include
test-harness overhead and omit production bootstrap hashing and later inventory
costs; multiplying them is not a valid completion guarantee. The raw sample fields
and limitations are retained in [the fixture record](../evidence/rule04-ai-review-nov24/native-fixture-samples.json).

Full-batch time and size feasibility remain unproven. The proposed 900-second total,
60-second pair, 256 MiB stop threshold and 21600 state/transition caps are unchanged.
Budget exhaustion must stop with retained partial evidence; do not silently increase
caps or retry. Fresh approval must acknowledge that the attempt may finish incomplete.
No successful 360-run result is claimed by these unit checks.

## Other review items

- F6: propose a new non-Temp output under the existing writable evidence workspace,
  outside Git and the canonical one-use ledger. The operator must retain/export the
  actual ledger receipts and output after the attempt. Workspace copies are not an
  independently verified backup. Do not remove ledger markers or reuse IDs.
- F7: keep the frozen case order. An early stop may leave missing-forecast controls
  unevaluated; report actual coverage and never generalize from missing strata.
- F8: original Nisha text stays unchanged. The supported isolation claim is per case:
  hidden weights do not enter that policy view. Four hidden profiles numerically
  coincide with other cases' visible profiles; cross-case uniqueness was not promised
  by the generator. This is not a demonstrated cross-process leak.
- F9: include the original `authored-first-metrics.json` and original checksums in the
  replacement packet. Do not modify the preserved producer output.

Live source/ancestry, environment, unused ID, absent output and authentic fresh approval
remain operator checks immediately before any future dispatch. The offline packet
cannot pre-pass them. Owners will be notified of the repairs, not asked to redo them.
