# Real development C/D artifacts and receiving

Matty instructed direct resolution of #150, without another teammate handoff.
Executed on manager host at main `94839dc4b547c3f1e50fabed0e50b1653173b3ad`.
This is development-only artifact production and technical receiving. It does not
grant source rights, resolve Q05/Q08 scientific acceptance or freeze the study.

## Input resolution

No existing local pinned CSV was located in the inspected project output. The
existing D01 adapter acquired the exact pinned upstream revision into a new local
private directory outside the Git checkout. SHA-256 matched:
`e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4`.
No raw source or derived episode contents are published in this handoff.

All 40 development episodes were materialized, verified, and compared against
the public `d04-development-content-112-v2` receipt. Episode canonical hashes,
file hashes, allocation hashes and folds match exactly. This supplies the manager
host input; it does not claim a file was transferred to Edison's machine.
Rights and physical source semantics remain unresolved in #60. Acquisition and
development execution are recorded manager actions, not evidence of permission
from an external rights holder.

## Actual training

The real pipeline collected visible states, generated features, used O02 certified
labels and the optional private cache, then evaluated the five implemented C/D
configurations across all three blocked development folds. No held-out cohort,
contents or outputs were loaded. Uncertified labels are excluded.

There are 6,046 definite rows: 1,411 positive and 4,635 negative.

| Held-out development fold | Training positives | Training negatives |
|---|---:|---:|
| 0 | 840 | 2,765 |
| 1 | 1,009 | 3,363 |
| 2 | 973 | 3,142 |

Here "held-out development fold" means cross-validation partition, not the private
30-episode final held-out set. Scalers and class weights are fitted on each fold's
training partition. Fifteen candidate/fold results were saved. Selection aggregates
the three folds under the implemented completed/misses/emissions ordering.
Seed: 20261031 (development script setting, not a newly approved scientific seed).

Selected/refitted artifacts:

| System | Selected parameters | Actual binary SHA-256 |
|---|---|---|
| C | Decision tree, depth 8 | `7e9e5769771f045241317d976f142b936f328399df58b040f9bbf67ba77a8f0b` |
| D | Random forest, 100 trees, depth 10 | `37149e530ef8e026b08279bedae1dd95170f70c279dd59d566637f43df94cf6a` |

Both binaries were reloaded and their probabilities matched the in-memory refits
over 100 labeled rows. Private manifests retain source/code/lock/environment,
fold map, class counts, hyperparameters, all fold metrics and binary hashes.
Total materialization/labeling/selection/refit/reload time: 101.375 seconds.
The operational driver and saved intermediate corpus/selection remain local.
Private handoff-summary SHA-256:
`2db2e4c74b809bc38262b5c748e1296b1b0baa5294aef5246f1bd64fa1bbc0f0`.
Private receiving-summary SHA-256:
`cbf771b477c14e0ccf26b947465e24fbcef7088767a985e2b152ffb4c4d87ced`.
Acquisition report SHA-256:
`e9161200ee89a789a14c821c7923e11e9670b715ae7b09ce6be842f66d9ac44e`.
These artifacts are real development models, not synthetic classifier doubles;
their validity for final experiments remains subject to scientific freeze.

## Runner receiving

Actual reloaded artifacts were bound to TrainedInputs/TrainedSettings and run on
the public EP-HAND1 bundle, LF SHA-256
`8bef36ace7bc4a3cf2debdce81c75edd87e175b20592a520a5449ec1fb0cddd6`.
Run ID: `RUN-1f6e4c4c2afb`. Greedy A, Greedy B, C and D each completed 30 slots
and two jobs. Each has 30 durable decision records, zero model calls, zero E01
Option B replay findings and zero EpisodeResult mismatches. The actual checker
and controller mediated execution; no reference solver is used for policy inference.

Earlier [Plain/Agent receiving](EP_HAND1_RECEIVING_F04_F05.md) used this same public
bundle. Together these records cover six real policy paths, but they are separate
runs/commits, not a new unified six-system experiment or an independent final I01
approval. No new LLM run was made. Full I01/I04 and scientific comparisons retain
their independent acceptance, source, frozen-input and evaluation gates.

## Custody and next use

Manager-local custody label: `P04_Private_2026-11-02`, outside the repository.
It contains source/acquisition evidence, verified development contents, private
label cache/intermediates, C/D binaries/manifests and receiving traces/results.
Only the checksums and aggregate observations above are public. Binaries and
source-derived contents are not attached to GitHub or transferred to a teammate.

#150's manager-host input/training blocker is resolved by actual execution. Keep
remote-machine access and any protected transfer as separate explicit actions;
do not tell Edison a local path on his machine exists. Edison and Nisha can consume
this handoff immediately; actual binary access must preserve the existing private
storage and rights boundary. #60, #16 and #95 remain open.
