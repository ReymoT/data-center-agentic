# Actual development attempt and direct adapter fix — November 24

Matty approved and dispatched request e887b995db9575f22da1bfb02ee695acf0071218448f88f249aa638e633305bc
on clean merged ed819a31a5adef8f7e7e3eed6984ffb523ee8052, after checking hashes,
ancestry, environment, unused ID and absent output. Authorization
rule04-dev-reporting-ed819a31a5ad-20261124 is consumed. No retry occurred.

The worker failed after 3.719 seconds; cleanup was verified. Zero validated
case-policy runs completed. The first case produced EP-RCVdevelopmentnormalfeasible00,
rejected because PrivateEpisode episode IDs must be opaque and cannot contain dev.
This is an adapter failure, not a failed safety property or a policy result.
Raw root/pair failures and a receipt are preserved in
[the failure evidence](../evidence/rule04-nov24-failed-development/attempt-receipt.json).
Original approval, consumed ledger, request and output remain unchanged outside Git.
Zero completed charged steps is not proof that no partial work occurred.

The controller now supplies a stable neutral digest as the receiving mapper's
temporary identity and restores the exact retained case ID before bindings and
episode construction. Opaque IDs contain no split tokens. Scheduling facts and
case JSON stay unchanged. All120 mappings are schema-checked and checked for
identity collisions during input preparation, before ID reservation or dispatch.
No token guard is relaxed, and no policy receives hidden weights or split labels
through its episode ID. The original receiving implementation, scientific163
bindings, rules, simulator, verifier, metrics, case order and caps are unchanged.

Offline tests cover all120 retained cases without executing their policies,
including missing-forecast isolation, determinism, uniqueness and formerly
colliding sanitized/truncated names. Ordinary semantic runner/replay and stop-control
fixtures remain separate from research execution. CI is required before merge.
Native focused verification passed77 tests; setup validation, lint and formatting
also passed. Full exact PR and merged-main CI results are recorded on the PR/issues.

The new [prospective protocol record](RULE04_PROTOCOL_FREEZE_NOV24_ID_FIX.json)
replaces the historical reporting freeze only for future requests. Keep every old
request and attempt as history. A corrected clean merged source, new unused ID,
absent output and fresh exact informed authorization are required before another
attempt. No retry, final generation, model call or training is authorized here.
The900-second/256MiB full-batch feasibility remains unproven; incomplete results and
zero missing-forecast rollout coverage remain possible. No new study result is claimed.

Report assembly continues now with accepted202-trace finite verification, authored
accounting, methods and saved demo. The new comparison and its independent receiving,
clean reproduction and final audit remain pending. Nov25 18:00 Arizona core checkpoint;
Nov26-27 repairs/reproduction; Nov28 18:00 audited candidate. No extra ML experiments.
