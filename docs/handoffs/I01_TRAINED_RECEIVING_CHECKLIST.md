# I01 and trained-artifact receiving checklist

Audited at main `227d2ebabd863d58f0a1b7bf2e56b6acdb02e1d4`.
The [current acceptance audit](I01_ACCEPTANCE_AUDIT_2026-11-02.md) reconciles every
system and the [P04 handoff](P04_REAL_DEVELOPMENT_ARTIFACTS.md) records actual
training, provenance, counts, all 15 fold cells, refit/reload and runner/replay.
These manager-host development checks supersede the old missing-artifact inventory.
Actual source permission/scientific freeze, independent final I01 acceptance and
protected remote access are not established. Load only trusted local joblib bytes,
verify their actual digest, and preserve the private manifests and inputs.

## Six-system I01 matrix

Use one agreed development bundle, explicit configuration identity and fresh output
directory. Keep all policy runs under matching scenario/forecast/protocol inputs.
Scientific comparison requires frozen settings and separately authorized model calls.

| System | Existing evidence | Next acceptance step |
|---|---|---|
| greedy_a | Checked policy and fallback receiving | Public EP-HAND1 run/replay exists; reconcile final I01 evidence |
| greedy_b | Policy receiving and E02 A/B runner | Public EP-HAND1 run/replay exists; reconcile final I01 evidence |
| decision_tree_c | Actual trained/reloaded binary and public EP-HAND1 replay | Reconcile final I01 evidence; retain scientific-freeze limit |
| random_forest_d | Actual trained/reloaded binary and public EP-HAND1 replay | Reconcile final I01 evidence; retain scientific-freeze limit |
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
All six real paths have receiving evidence in separate runs; full I01 is pending consolidated acceptance; I04 remains final release acceptance after
reproduction, held-out evaluation and reporting dependencies are complete.

Next sequence: consolidate existing P04 and Plain/Agent evidence -> independent I01
record -> scientific freeze/run readiness -> separately authorized experiments.
Calibration #22 is closed. Source acceptance #60 and verified course requirements
#16 remain separate gates; #95 remains open for held-out reliability.
