# I01 bounded public validation — November 4

Matty explicitly approved the exact single-use validation in the project chat
after the repeated offline check passed: “I approve it.” The separate approved
receipt records that actual message; the original pending template is unchanged.
Authorization `I01-EPHAND1-e670485639c9-20261104-v1` was consumed once.

## Actual execution and verification

- Candidate: `RUN-e670485639c9`; configuration SHA-256
  `e670485639c93d0bf1b539f0c9aa04220b35c166ed04812eca03a4a65a12b30b`.
- Checkout: `f5aa35df7bbf89cbda3c9ac7c93121090db0e78b`; execution source base
  `40dcd800babf0964e718a8a538548e454d9c0e3c`. Readiness and launcher LF hashes
  match the [reviewed packet](NOV04_LATENCY_LABELS_AND_READINESS.md).
- Runtime: isolated Ollama 0.40.5, Qwen3 8B, Intel Arc 140V through Vulkan.
  Model/runtime/template identities matched before and after execution.
- Six systems completed the public EP-HAND1 fixture: Greedy A/B, decision tree C,
  random forest D, Plain and Agent. Each has 30 distinct slot records, 180 total.
- Actual requests: Plain 5, Agent 12, total 17. Each request returned HTTP 200,
  with no recorded error or uncertain outcome and matching offline/native prompt
  counts. Total elapsed time: 326.125 seconds. No retry or warmup occurred.
- Independent E01 replay implementation found zero execution findings and zero
  saved-result mismatches across all six units. Matty separately checked the
  saved summary, counts, replay records, request limits and cleanup.
- Owned runtime exited, isolated port 11439 was released and the overall deadline
  was not exceeded. No failure record exists. Repository code remained unchanged.

Approved limits were 6 Plain / 18 Agent / 24 total requests; 150 seconds/request,
480 seconds/Agent decision and 3,900 seconds overall, with zero retries/warmups.
Actual runtime capture spans November 5, 01:44–01:49 UTC, November 4 in Phoenix.

The [sanitized summary](../evidence/i01-unified-validation-2026-11-04.json)
has raw SHA-256
`14bc7a1038bbe29e372f7f2b5c24d54ae50d26a941a13b21467fd4e419556043`.
Raw requests/responses, traces, logs and approved receipt remain outside Git.
The summary's `stage_counts` report presence, not successful repairs or job starts.

## Separate receiving and limits

A private package was prepared for Nisha with unchanged evidence, pinned replay
source, an offline verifier, instructions and a blank report. The packaged verifier
passes locally; it makes zero model calls. Package SHA-256:
`5e74b38470843d21b0b5fa30fa2f40d82e0514e396411c6dac8c9ba8e29d4bf9`.
The package was made available to Matty in the project chat. Actual delivery to
Nisha and her independent receiving judgment for this new run are not yet recorded.
Her [earlier accepted receipt](I01_NISHA_RECEIVING_ACCEPTANCE_2026-11-04.md)
still applies only to the earlier separate runs.

This completes one authorized public integration validation, not final I01,
scientific freeze, held-out evaluation, explanation faithfulness or an improvement
claim. J3 is intentionally infeasible; a missed J3 is not itself a receiving defect.
Source rights/semantics, production forecast, custody, compatibility and final
acceptance remain separate. No further model request is authorized by this receipt.
