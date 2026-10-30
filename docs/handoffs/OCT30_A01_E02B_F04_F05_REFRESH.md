# October 30 A01, E02-b and F04/F05 status

Owner: Matty Anderson (`MattyAnd`). This is a factual documentation refresh. It does not change a shared interface, model setting, evaluation rule or task owner, and it does not authorize inference.

## Merged implementation

- PR #116 merged one request-local response-bound function for Plain `PolicyOutput` and Agent `Plan`/`Explanation`. It uses visible-state counts and fixed constants, preserves a disposition for every waiting job, applies matched claim/limitation/text limits and still requires `done_reason=stop`.
- The pinned offline maximum valid shapes are 1,264 BPE tokens for Plain, 931 for Agent Plan and 298 for Agent Explanation. The largest leaves 272 tokens below `num_predict=1536`.
- PR #113 merged the E02-b Plain/Agent units into the experiment runner. Model inputs remain explicit; the command-line runner supplies none and therefore refuses model systems.
- An uncertain or unsaved attempt now stops its unit for reconciliation, prevents later model dispatch and stays counted in the run budget. The merged change used synthetic loopback responses only and made no model request.

## Verification

PR #113 exact head `4f461c59a09ea98cb43b564d906e40f0571b0539` passed 44 focused tests. The full local suite passed 1,548 tests and 19 subtests. Ruff check/format, setup validation and dependency consistency passed. It merged as `6730ab616291d585d898c0491a51f3fba1feedf8`; exact merged-main workflow 41124004492 passed. The merged branch was deleted after head-in-main verification.

PR #116 and its exact merged-main workflow also passed before its branch was deleted. Its measurements remain in [the A01 response-bound handoff](A01_RESPONSE_BOUNDS_2026-10-29.md) and evidence JSON.

## Still unresolved

- The October 28 Plain request remains a spent timeout; Agent was not called and there was no retry.
- Matty proposed 150 seconds per request and 330 seconds for the paired validation. Nisha and Ved have not both accepted those exact values. The accepted setting has not changed, and no fresh model call is authorized.
- A01 still needs exact affected-owner deadline agreement, a fresh bounded authorization and valid paired development evidence.
- A02/E02 still need reviewed production renderers and an actual authorized model-driven development episode.
- Reimo's 40 allocated development episodes lack materialized contents under issue #112, blocking P04/O02. No trained C/D artifact or study result exists.

## Documentation scope

This refresh updates the README, plain-language architecture and project plan to match merged PRs #113/#116. Historical run records remain unchanged. The research question, F02 contracts, accepted runtime/model/sampler, task ownership, masters and independent evaluation boundaries are unchanged.
