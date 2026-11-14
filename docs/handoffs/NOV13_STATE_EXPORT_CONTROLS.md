# Offline state-export controls and scoped agreement intake

Manager: MattyAnd. Instruction 1.29. Nisha, Reimo, Ved and Edison have supplied
[their directly affected scope/bounds positions](../evidence/nov13-scoped-owner-agreements.json).
They agree with the recovery-first plan and conditional new no-start diagnostic
history, preserving source/custody/fresh execution gates, exact provenance,
controller-only effects, missing counts and separate O02/C-D/rollout acceptance.
Their replies are received. Do not request the same positions again. The
contingency is not activated; no source or state operation is approved here.

## Real implementation, tested only on synthetic inputs

- [state_export.py](../../dc_sustainability/data/state_export.py) validates recovered
  F02 state/snapshot pairs against approved original-state commitments and the
  fixed development snapshot receipt. Missing coverage stays missing. It decodes
  checksum-bound episode bundles, requiring development identity, original content,
  exact UTC anchor, explicit 30-position legacy forecasts and no future issuance.
- [export_development_states.py](../../scripts/export_development_states.py) is the
  operational supervisor/worker. Fresh authorization must name the exact source-use,
  custody, executor/machine/storage, provenance, trajectory agreement and input/output
  bindings, clean code revision and all production/imported code hashes. Pending
  approvals fail before input access. Private JSON allowlists stay outside Git,
  symlink/junction/Git aliases are refused, and inputs are bounded to 128 MiB.
- [bounded_worker.py](../../dc_sustainability/runtime/bounded_worker.py) reuses the
  established stdin-gated Windows Job Object containment algorithm with an explicit
  at-most-900-second work deadline and separate at-most-three-second cleanup budget.
  Parent preparation time is deducted before worker release. OS process creation
  itself is not interruptible; late setup is never released. No portable fallback.

Recovery accepts at most 40 explicit JSON state-list files and requires canonical
hash commitments for every supplied pair plus authenticated original provenance.
New capture takes exactly 40 combined episode-plus-forecast bundle JSONs (within
the earlier at-most-80-file ceiling), not a raw CSV or an implicit forecast loader.
No live paths, source values, held-out metadata or private inputs are published.
A combined bundle read decodes the complete authorized PrivateEpisode, including
its realized-carbon fields for immutable content validation and trusted simulator
operation, plus its forecasts. This is a separate source-derived JSON footprint;
it is not covered automatically by an earlier 340-numeric-row extract approval.
Exact bundle hashes/full-content access and custody must be explicitly reviewed
in the fresh state-export authorization. Future realized values never become
policy-visible state facts or training labels through this exporter.

The exact new diagnostic trajectory is
`new-no-start-controller-refusal-drain-v1`: at each of slots 0-29 the real
ExecutionController receives a no-candidate intention (stage None), records its
blocked outcome, and alone invokes S01's refusal-and-drain path. No ApprovedActions
is forged, no passing checker is stubbed, no policy or model is called and no new
job is started. It emits pre-step visible-state/snapshot pairs and real controller
traces. Its F02 trace channel is greedy_a solely because F02 has no diagnostic
system ID; provenance explicitly says this is not a Greedy A performance run.
Never score these diagnostic traces as policy study outputs. The new path is not
the historical P04 approval callback and is never labeled recovered originals.
Exact trajectory/input review remains a condition before any live approval.

## One-shot, output and failure controls

The supervisor consumes a stable private ledger ID before spawning. The worker
requires that reservation and independently consumes the same ID in its own
ledger before input reads, so direct-worker reuse also fails. Authorization bytes
are snapshotted and checksum-bound. Never reuse an ID with another output/ledger
location; the exact output and storage are part of the authenticated approval.
Existing outputs/dispatch receipts are refused; partial/failure records are kept.
There is no retry or resume path.

Inputs are read once with an aggregate cap; byte hashes are checked before JSON
use. Code identity is checked before input access and again before publication.
State entries are limited to 1200 allowed development positions. Capture requires
all 40 x 30; recovery reports coverage n and missing 1200-n without filling.
Artifacts are serialized with finite JSON and a 32 MiB output bound. Trace/tree
size is checked after each episode and after publication; an over-cap failure may
retain its last partial artifact, which is unusable evidence, never success.
Failure summaries contain only exception type. Values/paths are not printed.

Only a succeeded dispatch with verified process-tree cleanup, matching approval,
state/provenance hashes and no failure artifact is eligible for independent
receiving. A timeout, crash, missing result, leftover child, changed code/input or
partial output fails closed. An apparently complete file after failure is not
accepted. This is containment and integrity, not an OS evaluator-credential or
human/source-permission authentication boundary.

Outputs are states.json (existing comparison list shape: state and snapshot),
provenance.json (origin, trajectory, approved refs, hashes, coverage and limits),
controller traces for new capture, and separate dispatch/worker-consumption
receipts. Provenance marks `pending_independent_receiving` and no scientific
compatibility. Nisha's separate-person receiving offer is accepted in principle;
its actual authorized packet/coverage/provenance/visibility checks come later.
The output alone does not certify source rights, O02/Q08 labels, C/D prediction
changes or changed-policy rollouts. Those need their own bounded checks.

## Review and availability updates

PR #215 now requires complete hash-verified rating inputs, own-state blinded
outputs and documented final-recommended-plan treatment. Failed plans remain
separate from execution/scoring evidence; originals/calibration files are intact.
PR #216 has fixed LaTeX escaping, nonfinite-value refusal and private-detail
handling. Both fixes were made directly and explained to Nisha.

Matty personally confirmed availability for November 25 and 28-30 (about 45 outputs
per day, up to 180 total) plus adjudication. This is a personal time commitment,
not completed ratings or a guarantee the full sample/results are ready. Original
independent ratings and human judgments must not be invented by the assistant.

## Evidence and current limits

Tests use explicitly synthetic hand episodes and state files. They exercise the
real controller refusal path through all 30 positions, matching/tampered recovery
commitments, partial coverage and duplication, strict pending/reference/code gates,
input mismatch failure preservation, non-overwrite, dispatch reservation,
future/missing forecast mapping checks, real Windows gated success and
child-plus-grandchild timeout/cleanup. Synthetic mocked cohort/revision bindings
in recovery tests are not authentic development approval or a 40-episode result.
No real 1200-state export or end-to-end real cohort capture has been run.

Real source-use evidence, actual private input availability, exact operational
custody and trajectory bindings, fresh single-use Matty approval, sufficiency of
bounds on those exact inputs, independent export receiving and subsequent
compatibility/freeze still remain pending. The plan and this implementation do
not silently grant source reads, state generation, solver, training or model runs.

## Offline validation record

The native full suite passed 2333 tests, 3 host symlink skips and 19 subtests before
the final strict file-size guard and added future-issue/input-size regressions.
The updated focused export tests, full lint/format and setup/I02 validation are
run on the final changes, with ordinary exact PR/main CI required for publication.
Those synthetic results are not a real cohort export or scientific acceptance.
The [pending authorization template](../evidence/state-export-authorization-pending.json)
is intentionally incomplete and is regression-tested to refuse dispatch.

Final focused export suite: 17 passed. Full lint/format, setup/local-link/policy
and I02 checks pass. The final exact hosted suite runs after publication.
