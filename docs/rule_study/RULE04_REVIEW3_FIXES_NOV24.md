# RULE04 second review: direct fixes — November 24

Matty requested direct fixes without returning work to owners. The supplied
[AI review](../evidence/rule04-review2-ai-nov24/source.txt) is preserved byte for byte,
with an integration receipt; it is not independent-person scientific receiving.
No development batch, generator, model or training ran.

## Confirmed corrections

- F-A: the earlier short workspace folder was still too long after BOTH runner
  nesting levels were included. This was our path-selection error. Preflight now
  computes all 360 complete case-policy artifact paths, including the longest
  hashed snapshot filename, and refuses any reaching 260 characters before ID
  reservation. A replacement user-home output example has maximum path length 216
  versus the superseded workspace output's 286. A native Windows fixture writes
  and reads the actual nested layout under a short user-home test directory. No
  registry change or long-path assumption is needed.
- F-C: output inventory checks its deadline between filesystem operations, including
  during traversal; initial inventory is inside the total clock. An inventory
  timeout returns a timed-out result and triggers cleanup. Python cannot interrupt
  an individual blocking filesystem call, so this is not a hard real-time OS guarantee.
- F-D: pair success/failure records carry the original authenticated request hash
  separately from the reserialized pair-request hash. Checkpoints and host/root
  failure records also retain original request provenance.
- F-E: each pair child validates/loads the 120-case accounting pair once, then passes
  that loaded value to the existing runner path. Source/input drift guards remain.
- F-F: batch failures and atomic checkpoints include completed coverage by stratum
  and policy, expected counts and zero counts for unexecuted strata. A killed pair
  may have additional unknown partial work; no missing result is counted as complete.

## Informed decision remains, not a coding defect

F-B remains a resource risk. The three ordinary fixtures do not establish actual
batch speed or a precise 190–216 completion count: they contain test overhead and
do not reproduce all production work. The review predicts the attempt may finish
incomplete before missing-forecast cases are reached. Fresh approval must explicitly
accept that missing-forecast and hidden-weight rollout coverage may remain entirely
unexercised. We have not silently increased limits or reordered the frozen cases.

The 900-second/60-second pair/256 MiB/21600-state-and-transition proposal, zero
retries/warmups, separate three-second cleanup and independent scientific limitations
remain unchanged. The original 163 accepted verification bindings still match.
The [revision 3 controller freeze](RULE04_PROTOCOL_FREEZE_NOV24_REVIEW3.json) replaces
the earlier controller pins. Request `d39deb5f…e5382` is superseded: refresh the exact
clean merged-source request, short output and unused ID before fresh approval.

57 focused tests passed, including real Windows path-layout, interrupted-inventory,
provenance, child-load and partial-coverage regressions. These are ordinary tests,
not a new scientific finding or independent-person receiving. Final source/environment,
ancestry, ID and absent-output gates remain live checks before any future dispatch.
For evidence export, keep relative archive paths and recheck the complete extraction
destination length; do not assume an arbitrarily deep delivery folder is safe.
