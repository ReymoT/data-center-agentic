# Unified receiving readiness and saved-trace explorer

Current update, November 4: [Nisha's independent receiving of the existing six
development units is accepted](I01_NISHA_RECEIVING_ACCEPTANCE_2026-11-04.md).
This resolves the private packet transfer/content-review dependency described
below. Earlier offline preparation records retain their historical flags; they
are not new claims that receiving is still absent. No new model run is authorized.

Both requested branch histories (#157 and #159) are integrated through #160.
The post-P06 refresh includes the changed training source and a new pending
approval template. The [pre-P06 records](../evidence/i01-pre-p06-2026-11-02/i01-unified-readiness-2026-11-02.json)
are preserved, including the earlier actual dry-run evidence. No previous or
current pending template is dispatch authorization.
The report refresh and measured-artifact audit are complete. The runner now
reloads each pinned artifact at its input boundary and uses that verified model,
rejecting changed bytes and ignoring a forged caller-side fitted object. The
original classifier-factory API is superseded; callers supply
`TrainedPolicy(learned.load_verified(path, expected_sha256=...))`.

The [current candidate](../evidence/i01-offline-config-2026-11-02.json) pins merged
source commit `5773295700c3792afe4eec2de48572ccb1aa0a66`, including P06, and has
identity `RUN-0f7d9498db6f`. All earlier offline candidates remain in its history.
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
and use the prepared `scripts/run_i01_public_receiving.py` launcher with matching
LF readiness/launcher hashes. It enforces the Plain cap and provider/run ceilings,
requires an approved single-use receipt before startup, consumes its ID exclusively,
stops on uncertain/error attempts, retains failures, checks all six saved units
with independent replay, and publishes success only after cleanup/deadline checks.
Its outer watchdog terminates only the retained owned process. These controls are
unit-tested; the actual local `--dry-run` checks pins/models/tokenizer without
starting the runtime. Fresh live identity, cleanup and model results are not
silently inferred from that dry run.

The [unapproved authorization template](../evidence/i01-authorization-template-2026-11-02.json)
binds the exact candidate, bounds, readiness and launcher hashes. Its status and
approval fields are deliberately pending/empty; it cannot authorize a run.
The [actual launcher dry-run record](../evidence/i01-launcher-dry-run-2026-11-02.json)
is separate from the offline pin report. Neither is a spent model request or a
fresh human approval. No new model request was authorized or executed.

The launcher is Windows/Arc development tooling, not cross-platform deployment
certification. Supply explicit runtime, model-store, isolated tokenizer/package,
accepted-inventory, C/D artifact, candidate, readiness and fresh output paths;
use `--dry-run` for local checks without starting a service. Live mode additionally
requires the exact approved receipt. Neither the pending template nor an old
approval can be reused; consumption is recorded exclusively by single-use ID
in the manager workspace before startup. The no-startup dry run creates no run
output directory and consumes no approval.

## Explorer and report

[The working explorer and report section](../report/UI_VISUALIZATION.md) use only
saved development evidence, with no dispatch or mutation capability. Exporter
tests and actual browser interaction verify filters, stage details and completion
slots. The generated six-unit HTML stays manager-local; only the field-filtered
actual screenshot and implementation are published for report assembly.

Source B1-B3 and actual B5 held-out custody/forecast acceptance remain open in #60.
The existing development packet was received and reviewed by Nisha; its scoped
acceptance is recorded above. Course midnight/project-number/release fields remain open
in #16. #95 remains open for actual held-out reliability.
