# I01 and trained-artifact receiving checklist

Prepared from main `6c288c0978597fb7fd5b5dd01bea70fed3f4879e`, instruction 1.28.
This checklist records required evidence; blank results are not passes.
Use existing contracts, seeds and scientific rules. No new model run is authorized.

## P04/P05 receiving: Edison to Matty and Nisha

Before loading trusted local artifacts, retain the producer's manifest and bytes.
Verify the actual file SHA-256 against the manifest and frozen TrainedSettings;
do not trust the declared digest alone. Load only the expected trusted producer
artifact because joblib deserialization executes Python objects.

| Check | Required record | Result |
|---|---|---|
| Input provenance | Authorized pinned source hash, development allocation/content receipt, code revision, environment/lock hash | Pending |
| Certified labels | O02 settings and certification, definite/unknown counts, positive/negative counts per training partition | Pending |
| Fold isolation | Every row belongs to development fold map; evaluation episodes excluded from that fold's fit, scaler and weights; held-out contents untouched | Pending |
| Selection | Every candidate evaluated on all three blocked folds; aggregated metrics and deterministic tie-break; no skipped fit failures | Pending |
| Refit | Selected C/D parameters, frozen seed, all eligible development rows, feature order and class weights recorded | Pending |
| Artifacts | Both binary hashes, manifests, size, producer identity/access location and actual reload validation | Pending |
| Probability boundary | Finite probabilities in [0,1], feature identity, known candidate keys and repeatable predictions after reload | Pending |
| Runner boundary | TrainedInputs uses actual reload factory; digest matches TrainedSettings; wrong hash/missing policy refused | Pending |
| Runtime | No inference-time reference solver; policy output traverses production checker/controller; failures retained without hidden fallback | Pending |

Existing entry points: `training.train.load_artifact`, `classifier_for_factory`,
`experiments.trained.TrainedPolicy`/`TrainedInputs`, `TrainedSettings` and
`experiments.runner.run`. Artifact manifests alone do not establish actual
training or receiving. PR #138 delivered implementation; the real handoff is pending.

## Six-system I01 matrix

Use one agreed development bundle, explicit configuration identity and fresh output
directory. Keep all policy runs under matching scenario/forecast/protocol inputs.
Scientific comparison requires frozen settings and separately authorized model calls.

| System | Existing evidence | Next acceptance step |
|---|---|---|
| greedy_a | Checked policy and fallback receiving | Record same-bundle I01 run and replay |
| greedy_b | Policy receiving and E02 A/B runner | Record same-bundle I01 run and replay |
| decision_tree_c | Training implementation and E02 trained units | Actual P04 artifact checks above, then same-bundle run/replay |
| random_forest_d | Training implementation and E02 trained units | Actual P04 artifact checks above, then same-bundle run/replay |
| plain_llm | EP-HAND1 5 requests, 30 traces, zero replay findings/mismatches | Reuse bounded receiving evidence; new matrix calls require authorization |
| agent | EP-HAND1 12 requests, repairs/fallback, 30 traces, zero replay findings/mismatches | Reuse bounded receiving evidence; new matrix calls require authorization |

For each actual matrix unit retain config/run identity, input/artifact hashes,
original outputs, 30 immutable traces, attempt ledger where applicable,
EpisodeResult and independent E01 replay findings/result comparison. Record PASS
only with the evidence location and exact tested commit. Preserve failures and
unknown attempts; never silently rerun or replace them.

Exercise stale-state, duplicate/replay, wrong context/hash, missing capacity,
malformed response, unknown/unsaved request and exhausted budget boundaries through
the existing offline tests. Offline fixtures establish boundary behavior only.
Full I01 is pending all six real paths; I04 remains final release acceptance after
reproduction, held-out evaluation and reporting dependencies are complete.

Next sequence: Edison real P04 handoff -> Matty/Nisha receiving -> six-system I01
record -> scientific freeze/run readiness -> separately authorized experiments.
Calibration #22, source acceptance #60 and verified course requirements #16 remain
their own gates; #95 remains open for held-out reliability.
