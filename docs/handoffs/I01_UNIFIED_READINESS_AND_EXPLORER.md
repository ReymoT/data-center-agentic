# Unified receiving readiness and saved-trace explorer

Both requested branch histories (#157 and #159) are integrated through #160.
The report refresh and measured-artifact audit are complete. The runner now
reloads each pinned artifact at its input boundary and uses that verified model,
rejecting changed bytes and ignoring a forged caller-side fitted object. The
original classifier-factory API is superseded; callers supply
`TrainedPolicy(learned.load_verified(path, expected_sha256=...))`.

The [current candidate](../evidence/i01-offline-config-2026-11-02.json) pins merged
main `c1ad13aec1aa35edb0994a6ed956d00bbb098d03`, including these bindings, and has
identity `RUN-92d1438321b9`. Both earlier offline candidates remain in its history.
All historical completed-run identities, source files and the 180-trace index
remain unchanged.

## Offline checks actually completed

[The readiness record](../evidence/i01-unified-readiness-2026-11-02.json) was
generated using the actual manager-host C/D files. It reconstructs RunConfig,
checks LF lock/bundle/prompt/renderer pins and exact proposed limits, verifies
both binary digests and system bindings, and records execution-source hashes.
It constructs no provider, makes no runtime requests and accesses no held-out
content. Regression tests reject changed hashes, claimed authorization and
changed budgets. Status is **offline pins verified; dispatch blocked**.

Proposed single-use public-development exercise: all six systems on EP-HAND1,
one LLM trial / seed 101, at most 6 Plain requests, 18 Agent requests and 24 total,
150 seconds/request, 480 seconds/decision and 3,900 seconds overall, zero retries
or warmups. The outer controls are explicit requirements, not consequences of
the config identity alone. This is not the 300-run held-out experiment.

Before any live dispatch, obtain fresh Matty authorization for the exact candidate,
revalidate accepted runtime/model/template/native counting and Arc/Vulkan identity,
review the launcher against the new artifact API and enforce per-system caps and
the outer watchdog, stop on uncertain/unsaved attempts or failed identity, persist
all failures, and verify owned-process/port cleanup. None is silently marked done
by this offline record. No new model request was authorized or executed.

## Explorer and report

[The working explorer and report section](../report/UI_VISUALIZATION.md) use only
saved development evidence, with no dispatch or mutation capability. Exporter
tests and actual browser interaction verify filters, stage details and completion
slots. The generated six-unit HTML stays manager-local; only the field-filtered
actual screenshot and implementation are published for report assembly.

Source B1-B3, actual B5 custody/forecast acceptance, private replay transfer and
independent content receiving remain separate open gates in #60. The private packet
is prepared, not sent. Course midnight/project-number/release fields remain open
in #16. #95 remains open for actual held-out reliability.
