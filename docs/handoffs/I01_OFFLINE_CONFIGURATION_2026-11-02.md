# I01 common-protocol preparation

Current follow-up: [artifact bindings, explorer and offline readiness](I01_UNIFIED_READINESS_AND_EXPLORER.md).
The current candidate is `RUN-3225d3a29153`, revalidated on November 4 in the
[offline refresh](NOV04_READINESS_AND_STATUS.md). `RUN-92d1438321b9` and
`RUN-0f7d9498db6f` are earlier preparation identities. The earlier
[LF correction and P05 receiving](I01_LOCK_P05_PRIVATE_RECEIVING.md) used
`RUN-3d6ec9e70279`; that earlier candidate and completed
run identities remain retained. Nisha's independent structural review is received,
with its lock correction applied; [Nisha's later private content receiving is
accepted](I01_NISHA_RECEIVING_ACCEPTANCE_2026-11-04.md) for the existing two runs.

Matty prepared a validated six-system RunConfig identity offline using existing
EP-HAND1, the actual C/D binary hashes and the earlier Plain/Agent deployment,
prompt, renderer, seed and budget pins. No provider was constructed or called.

- [Candidate identity](../evidence/i01-offline-config-2026-11-02.json): all six
  systems, one public episode, trial 0 / seed 101 for the LLM units, 24 total
  model attempts, 150-second request timeout and 480-second decision deadline.
  The proposed outer wall limit is 3,900 seconds. These are preparation values
  reused from bounded receiving, not permission to dispatch.
- [Existing evidence index](../evidence/i01-existing-evidence-index-2026-11-02.json):
  six actual units, each result hash and all 180 trace-file hashes, plus original
  run/commit and manifest identities. Every trace parsed under current F02.
  Actual C/D binary hashes were independently reread and matched locally.

The two original runs share the exact bundle and dependency-lock hash. They retain
different names, system lists, model settings/trials and code commits; the new
candidate has a different identity. Its code revision names the reviewed main
base, not a final frozen execution commit. No saved result is relabeled as a
candidate result. The index publishes hashes and opaque file identities only,
not raw responses, source observations, original evaluation ratings or local paths.

This closes the offline configuration/index preparation gap identified in the
[I01 audit](I01_ACCEPTANCE_AUDIT_2026-11-02.md), not I01 itself. A fresh exact
single-use authorization, runtime identity checks, actual receiving and independent
acceptance remain before a new unified run can be claimed. Nothing changes the
300-run held-out protocol, source rights, scientific seed or actual custody/freeze.

## Freeze-pin review fix

PR #153 correctly moved completed development labels/models/calibration from
blocked to pending. Its new handoff-document paths exposed an existing validator
weakness: a freeze commit plus that documentation path could stand in for private
artifact bytes. The validator now requires an actual label-artifact SHA-256 for
frozen candidate labels and a complete `artifact_sha256` map for both
`decision_tree_c` and `random_forest_d` binary hashes when models are frozen.
This is structural pin validation; a custodian still verifies the actual bytes.
No readiness state, scientific setting, existing F02 format or run is adopted.
