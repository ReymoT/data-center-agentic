# Context and private comparison readiness

## Explanation candidate context accounting

The proposed 256-character explanation limit and 4096-token output reserve are
still awaiting affected-owner agreement in #185. With the existing 16384-token
context, the prompt ceiling must be at most 12288. Retaining the current ceiling
of 14848 would permit a 2560-token over-allocation.

[The offline checker](../../scripts/check_explanation_context.py) re-rendered all
17 original requests from RUN-fd87c6c8a9cb with the pinned Qwen3 tokenizer. Every
count matched the recorded native prompt count. The largest was 3017 tokens,
leaving 9271 context tokens after reserving 4096 for output. The synthetic 20-job
Plain and Agent proposal prompts used 2356 and 2211 tokens respectively.

The candidate grammar specifications change only summary, limitation and claim
text lengths. Regression checks retain all plan limits and leave the original
schema untouched. The accepted template renders the message history while format
is a separate grammar argument. These are offline candidate counts and schema
specifications, not a compilation or timing measurement of a new runtime grammar.
New runtime parity and timing still require an explicitly authorized validation.
The per-request context guard must enforce 12288 before the new reserve is adopted.
Runtime defaults are unchanged.

[Measured context evidence](../evidence/explanation-context-2026-11-08.json)
retains the counts and candidate schema hashes. Use the existing isolated
tokenizers 0.23.3 environment and pinned tokenizer when reproducing the script.

## Comparison input readiness

The pinned 40-episode allocation implies 340 unique forecast-input rows across
the legacy and both CF60 interval hypotheses. Repeated episode windows share
input rows; do not multiply that union by the number of scenarios.
The [metadata-only readiness record](../evidence/cf60-input-readiness-2026-11-08.json)
pins the canonical row-set hash and the pending private authorization draft.

A candidate source CSV exists in the prior P04 private workspace. It was identified
by path and file metadata only. Its current bytes were not opened, hashed or
treated as new source authorization. The source's expected pinned hash remains
the existing D01 identity. B1–B3 and OS custody gates still require evidence.

No approved row extract is ready. The inspected training label cache records
state hashes and labels, not the full F02 states needed for feature comparison.
No complete saved-state input was identified in those registered artifacts.
A forecast-only first pass can explicitly report all 1200 states unavailable;
it cannot complete feature, O02 or C/D compatibility acceptance.

The local authorization draft is pending, with a proposed private extract and
output path, exact row indices, driver pins, 2400-issue/7200-lookup bounds,
1800 seconds, and zero retries, solver calls or model requests. Extract checksum
and final approval remain unset. It will be refused by the driver's approval gate.
No private source path or source values are published in this record.

Next obtain a permitted extract or explicit separate source-ingestion approval,
verify the resulting extract hash, and finalize the single-use authorization.
Add a verified state export or separately approved state preparation for feature
comparison. The [comparison driver guide](CF60_COMPARISON_DRIVER.md) controls
execution; this readiness note grants none.
