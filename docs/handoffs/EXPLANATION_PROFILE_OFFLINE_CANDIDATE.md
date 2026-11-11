# Explanation settings: offline candidate

November 10 superseding decision: [the prospective study profile is adopted](../decisions/NOV10_PROFILE_ADOPTION_AND_FORECAST_SCOPE.md), with Nisha/Ved agreement and Matty authorization. The opt-in implementation and old runtime defaults remain unchanged; final configuration binding, I02 acceptance and separate run authorization remain required. The failed candidate below and later corrected cb85 PASS are both preserved. Earlier preparation-only statements below are historical.


November 9 outcome: the explicitly authorized native validation failed closed on a value/unit claim inconsistency. Its ID is consumed; no retry occurred. See the [outcome](A01_EXPLANATION_VALIDATION_OUTCOME_2026-11-09.md). The preparation below is historical; candidate adoption remains pending.

Nisha and Ved explicitly agreed in issue #185 to test a 256-character explanation limit and 4,096 output tokens. This implementation is opt-in. Existing runs retain 96 characters and 1,536 output tokens, including their existing configuration identities.

The candidate bounds summary, each claim text and each limitation to 256 characters for both Plain and Agent. Plan deferral and abstention details remain at 96 characters. Claim, limitation, evidence and plan-entry counts are unchanged. Context remains 16,384 tokens; the candidate prompt ceiling is 12,288. The renderer is not changed to conceal earlier cap hits.

Set explanation_characters=256, output_tokens=4096 and max_prompt_tokens=12288 explicitly in model.deployment. Record an honest candidate context_policy_ref: native rendering, grammar compilation and timing have not been validated for this candidate. Neither the legacy deployment nor a prior single-use authorization adopts these settings automatically.

The public receiving launcher now reads the exact deployment pins from the prepared candidate and accepts --code-revision for its frozen code commit. It still requires the fixed runtime/model, fresh candidate/readiness/launcher hashes, clean execution files and explicit single-use authorization before server startup. Existing request, decision and wall-time limits are unchanged. prepare_i01_readiness.py and --dry-run perform offline checks; a dry run does not establish native inference success.

Next: prepare fresh candidate and readiness hashes using the merged code; inspect them and obtain fresh bounded authorization. Only then validate native counts, grammar, timing and stop controls. No new inference, held-out evaluation, scientific freeze or performance improvement is established by this patch.

CF60 comparison is a separate gate. Its pending authorization remains incomplete until the permitted real extract and any saved visible-state inputs are identified and pinned. No source read, solver, rollout, relabeling or training was performed for this change.

The November 4 launcher is preserved verbatim as docs/evidence/i01-legacy-launcher-2026-11-04.txt. Historical readiness hashes bind that archived text, not the new launcher. Old preparation is intentionally stale for dispatch through the new launcher.
