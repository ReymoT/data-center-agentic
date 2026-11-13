# Development visible-state recovery and generation plan

November 13: [Nisha's scoped conditions and future receiving offer are accepted by Matty; the backward feasibility plan is recorded](../decisions/NOV13_SAFEGUARDS_AND_FEASIBILITY.md). Other affected-owner replies remain pending. No contingency, trajectory or execution is adopted by that acceptance.

Owner: Matty for this preparation/direct fixes; Ved receives O02/Q08 implications,
Edison C/D implications, Nisha evaluation/I02. Reviewed main:
`f6c4d09b1b062c2cd13bb52f3ad2aae4f924485e`, instruction 1.29.
Status: offline proposal only. No private state/episode/source file is opened,
no collector/simulator/solver/training/policy/model is executed, and no real state
export or compatibility finding is produced by this plan.

## What is implemented and what is missing

[collect_decisions](../../dc_sustainability/training/collect.py) returns 30
CollectedDecision objects per episode with VisibleState, Context, trusted UTC
decision time and candidate rows. The supplied ConstraintSnapshot is the episode's
snapshot. The [training pipeline](../../dc_sustainability/training/pipeline.py)
filters to candidate-bearing samples, attaches O02 labels and retains training
rows. Neither a feature matrix nor label-cache key reconstructs all original
VisibleState/ConstraintSnapshot objects or the full operational trajectory.
The historical training callback is _empty_approve; that fact does not authorize
using a training callback to bypass the production controller.

The [comparison](../../dc_sustainability/data/cf60_comparison.py) expects an optional
JSON list of entries with exactly the plan's two fields, state and snapshot, in
existing F02 JSON representation. Its coverage key is (episode_id, current_slot).
The 40 fixed development episodes times slots 0-29 require 1200 unique pairs,
including 240 completion positions at slots 24-29 and any empty/no-candidate state.
No held-out record/seed/date/path belongs in these inputs. Completion positions
are not new scheduling opportunities. The current comparison has no supplied
state file. No complete provenance-bound state-export artifact or operational
state-export entry point has been established by this preparation.

## Route A: recover existing original states first

Before reading any private candidate artifact, authenticate source-use and custody
permission plus a bounded explicit file allowlist and executor/storage. Search
only those authorized candidate files, never a recursive scan of evaluator B5 or
held-out material. Bind original generating commit, development content receipt,
forecast schedule, collection callback/seed/parameters and existing run/approval
receipts. Do not substitute a current training run's feature rows for saved states.

Validate actual F02 JSON state/snapshot/context consistency, all 40 allowed IDs,
all 30 slots once each, state-version lineage, exact UTC slot mapping, input snapshot
hash and reproducible running/waiting/completed histories against the recorded
trajectory. Preserve duplicates/mismatches/missing counts in a failure report;
never fill a missing state with a synthetic placeholder. Recovered states may be
partial; they remain partial and cannot satisfy the complete-coverage gate.

Do not infer original history or rewrite a timestamp/snapshot to pass. A hash
without the authenticated generating provenance is integrity only, not historical
identity. If original state artifacts do not exist or cannot be authenticated,
record the missing positions and use Route B only under its separate approval.

## Route B: generate a new development fixed-history export

This is new evidence, never described as recovered originals or relabeled as the
old P04 run. First agree the exact collection trajectory with affected consumers.
Recommended starting proposal: the documented historical no-new-start training
trajectory, recorded explicitly, with immutable existing development jobs/snapshot
and pinned legacy forecast schedule. It does not represent a completed policy
rollout or all possible states. If another trajectory is needed, specify it before
execution; do not choose whichever makes compatibility look best.

Inputs must be the exact approved 40 private development episodes and their pinned
forecast-by-slot bundles, fixed allocation/content receipt, snapshot/UTC mapping,
collector/simulator/controller and authorization code pins, dependency lock and
actual environment. Bundle/forecast availability is not established here. Missing
forecast bundles must not trigger persistence_forecasts(source) or a CSV load.
No call to build_labeled_corpus, run_selection or training is permitted: those can
open the source, invoke O02 solves and/or train. No fake ApprovedActions capability
or constant successful checker is an acceptable operational capture path.

An operational capture driver still needs explicit authorization/preflight,
exclusive ID consumption, private file bounds, controller-compatible action
provenance and externally enforced deadline/cleanup. Existing collector capability
is not that driver. Do not invent a runnable CLI or claim its implementation in
this document. Matty implements/fixes it directly after the scoped design and
inputs are agreed; it is not sent back for another owner correction round.

## Proposed bounds for a later exact approval — not accepted limits

- Recovery: at most 40 explicitly named existing state files, 128 MiB aggregate
  input, 32 MiB new export, 900 seconds total; no simulator steps.
- New capture: at most 40 episode and 40 forecast JSON inputs, 128 MiB aggregate
  input, exactly 40 serial trajectories of 30 steps (at most 1200 transitions and
  1200 pre-step snapshots), 32 MiB export, 900 seconds total.
- Both: one fresh output directory; zero retries, source CSV opens, downloads,
  model/solver calls, label-cache writes, fitting, classifier inference or policy
  performance rollouts; private values never printed. No run authorization ID is
  proposed yet. Bounds must be verified for sufficiency and agreed before execution.
- Fail closed on permission/identity mismatch, changed development content,
  unexpected file/episode/slot, invalid state/context, inability to establish
  trajectory provenance, cap/timeout, existing output or unverified cleanup.
  Preserve partial output and failure receipt; no automatic repair/retry of data.

## Output and acceptance contract

The new private export is a UTF-8 JSON list with F02 state and snapshot entries,
ordered by the fixed public allocation order then slot. Provenance stays in a
separate manifest binding source/episode/forecast hashes, original or regenerated
origin, collection trajectory, exact code/environment/approval/dispatch identities,
input and output byte hashes, count/coverage, missing positions, timing and cleanup.
The comparison consumes the list hash and states_provenance_ref through its
existing interface; shared F02 and classifier feature contracts are unchanged.
The source-derived export stays outside Git and evaluator-only metadata storage.

Before use, independent receiving verifies hashes/provenance, exact 40 x 30 coverage,
state/snapshot/context identities, temporal visibility and trajectory lineage.
Missing positions are excluded/countable, never fabricated. A passing list is
fixed-history feature input only; it does not certify O02/Q08 labels or C/D changes.
Existing binaries, labels and content receipts remain immutable. Separate bounded
approvals and actual results are required for reference solving, prediction or
changed-policy rollouts. Report why withheld forecasts/candidate gaps are unavailable.

## Sequence and current deliverables

1. Confirm scientific fallback/ingest requirements; retain source/custody gates.
2. Authenticate the explicitly scoped original-state inventory and input provenance.
3. Prefer recovery; if unavailable, agree the new trajectory and exact source-derived
   input/permission bindings, implement/test the capture controls offline, then obtain
   fresh exact authorization. No private reads or state generation are approved now.
4. Validate/receive actual exported states; bind its real checksum in a separately
   approved comparison along with the actual permitted extract.
5. Hand actual findings to Ved/Edison/Nisha; keep missing/uncertified outcomes explicit.

This plan closes a planning gap only. The 1200 states remain unavailable; no
scientific freeze or successful compatibility finding is asserted.

[Code-inspection pins and zero-execution record](../evidence/nov12-state-plan-inspection.json) identify the implementation reviewed for this plan.
