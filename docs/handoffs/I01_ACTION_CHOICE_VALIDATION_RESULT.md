# Shared action-choice validation result

Matty explicitly approved `RUN-fd87c6c8a9cb` in the project chat (“Ok get it done”)
immediately after its exact bounded proposal. A separate approved receipt was
recorded, the prelaunch offline check passed and the single-use ID
`I01-EPHAND1-fd87c6c8a9cb-20261104-choices-v3` was consumed once. The original
pending template is unchanged. No retry or warmup occurred.

## Actual completed public validation

- All six EP-HAND1 systems completed: Greedy A/B, decision tree C, random forest D,
  Plain and Agent. Six results, 30 traces each, 180 total.
- Requests: Plain 5, Agent 12, total 17. Duration: 445.156 seconds, about 7 minutes
  25 seconds. Every attempt returned HTTP 200 with no error or uncertain outcome.
- Offline/native prompt counts agreed. Runtime/model/template identity checks
  passed before and after execution; the pinned Arc/Vulkan path was used.
- E01 replay implementation found zero execution findings and zero saved-result
  mismatches in all six units. Matty rechecked saved results, attempt accounting,
  action categories, latency limits, identities and cleanup separately.
- Owned process exited, isolated port 11439 was released and the overall deadline
  was respected. No failure record exists.

Bounds were 6 Plain / 18 Agent / 24 total requests; 150 seconds/request,
480 seconds/Agent decision and 3,900 seconds total. No remaining call allowance
authorizes another execution. Source base is
`18f2cba0252e215e94ae7c2b54de0b3df8b810d5`; checkout was
`1f32bdc7b46a8a0e03b338c9d318ff415cc28e84`. Exact config, readiness and launcher
identities remain in the [preparation](ACTION_CHOICE_OFFLINE_FOLLOWUP.md).

The [unchanged sanitized summary](../evidence/i01-action-choice-validation-2026-11-04.json)
has raw SHA-256 `c1daedc2fadaebdfd5d934c807d3391f4e2f9f8ad685f42af3970d418a3f378f`.
Raw requests, responses, traces, logs and the approved receipt remain outside Git.

## Model behavior is separate from protocol completion

The [offline behavior audit](../evidence/i01-action-choice-behavior-2026-11-04.json)
uses original response JSON before defaults and gate-bound trace stages:

| Observation | Actual result |
|---|---|
| Raw plan responses | 12, all with explicit action arrays; 11 with nonempty actions |
| Action-category conflicts / duplicate job entries | None observed in these 12 responses |
| Agent completed jobs | J1 and J2; J3 missed as expected from the intentionally infeasible fixture |
| Agent executed job starts | J1 from checked fallback at slot 0; J2 from model-initial proposal at slot 3 |
| Agent repairs and fallback | Two repairs, both failed their checks; both subsequent fallback stages passed |
| Plain completed jobs / executed job starts | None / none; five model decisions failed their checks |

Stage counts include valid no-ops, so 22 passing Agent initial stages are not 22
successful model recommendations. Proposal/repair entries may repeat intentions;
their counts are not executed-job counts. A nonempty plan is not necessarily valid,
and absence of structural conflicts is not proof of faithfulness or general safety.
The two unsuccessful repairs remain reported, not hidden by successful fallback.

The observed prior start/abstention contradiction did not recur in this run. That
does not prove the prompt change caused a general improvement. The earlier empty
plans and failed `RUN-15e69e6129b7` remain unchanged. These public development
exercises are not a held-out comparison or a positive answer to the research question.

## Receiving and remaining acceptance

A new offline receiving package is prepared for Nisha with the original evidence,
source references, verifier, instructions and a blank report. Manager checks are
not her independent receiving judgment. Her accepted earlier receipt applies to
`RUN-e670485639c9`, not this run. Delivery and a new report are not assumed.
The package contains 491 files; ZIP SHA-256 is
`e4d6b0bb487c0388d460c034f924b96c8502ae0a66f076606894e2bc1e349b84`.
Its offline verifier passed locally, including raw request/response hashes,
complete replay, prompt hashes, counts, latency/tokens and action-category checks.
Archive integrity and every indexed file hash were verified. This is still a
manager-side package check, not Nisha's receiving result.

Full I01, prompt/schema scientific freeze, source/forecast compatibility, actual
held-out custody, final evaluation/reliability and I03/I04 remain separate gates.
No source-CSV acquisition, held-out execution, training or further run is authorized
by this result. Continue only the ready work and preserve the stated limits.
