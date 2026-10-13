# Q09: accepted Ollama and Qwen3 development direction

Decision ID: Q09, partial resolution. Status: runtime/model direction and listed development settings accepted; deployment and experiment freeze pending.

Driver: Matty Anderson (MattyAnd). Affected LLM owner: Nisha Mahadev Kolekar (nkolekar-nk). Contract contact: Ved Patil (vedp3705).

Human authority: Matty explicitly accepted Nisha's recommendation in this project session on 2026-10-12 and separately selected temperature 0.2. His authorization includes publishing this decision and notifying the correct owners. [Nisha's recommendation](https://github.com/ReymoT/data-center-agentic/issues/2#issuecomment-6136185617) and [the acceptance/owner notification](https://github.com/ReymoT/data-center-agentic/issues/2#issuecomment-6136759988) are recorded in issue #2.

## Accepted direction

Use local Ollama with `qwen3:8b`, Q4_K_M, as the initial shared model for agent and plain LLM. The [official Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B) lists Apache 2.0; the [Ollama model entry](https://ollama.com/library/qwen3:8b) identifies the packaged model. Capture the actual installed artifact's digest, model metadata/license and runtime version before live experiment readiness; a mutable tag alone is insufficient.

Both LLM systems use the same model artifact and matched generation settings. Temperature is 0.2, not the original temperature-0 example in Nisha's comment. Use fixed, matched per-trial seeds; the exact seed list remains to be recorded before freeze. Nisha's 101/102/103 example is a proposal, not a silently adopted list.

The accepted development settings from the recommendation are:

| Setting | Value / rule |
|---|---|
| Streaming / thinking | `stream=false`, `think=false` |
| Sampling | `temperature=0.2`, `top_p=1`; matched per-trial seeds pending |
| Context / generated-token target | `num_ctx=16384`, `num_predict=1536` |
| Keep-alive | `30m` |
| Call timeout target | 120 seconds for both systems; validate on the target machine |
| Concurrency | `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1` |
| Output | JSON-schema-constrained output using agreed F02 projections; schema validity does not approve execution |
| Evidence | Save runtime/model/SDK versions, model digest, settings, schema version, request status, token counts, latency and failures |

These are development decisions, not a runnable or frozen experiment configuration. Exact SDK/runtime versions, seed list, validated context-overflow detection/threshold, warm-up/accounting rules and measured resource budget still require a recorded deployment configuration. No artificial defaults may fill those gaps. Use [Ollama's API specification](https://docs.ollama.com/api/chat) during implementation and verify the installed version's behavior.

Agent orchestration remains controlled by LangGraph/controller code. It retrieves evidence and invokes deterministic checks; the LLM proposes, optionally repairs and explains. The LLM does not execute simulator actions. The plain LLM must produce its recommendation and explanation in its single allowed request, not one request for each. Agree the output projection with Ved and Nisha using existing F02 records; the informal field sketch in the comment does not replace those schemas.

## Call limits and failure behavior

The existing hard limits remain 3 model attempts per agent decision and 1 per plain-LLM decision, including transport retries and explanation requests. Disable hidden SDK retries. Nisha's suggested transport retry is allowed only within remaining attempt budget; once the plain LLM attempts its request, it cannot retry. Preserve uncertain request status rather than treating a timeout as proof no request ran.

Malformed or invalid plain output receives no repair, feedback or fallback. The agent retains its one verified repair and checked greedy-A fallback rules. Budget exhaustion or missing verification cannot permit execution. A transport retry cannot bypass these rules or increase the experiment's call ceiling.

Local API spend is not an evidence-based compute cost estimate. Record actual token counts, latency, failures and machine/resource use; report any API spend separately. Hardware estimates and throughput in the recommendation are planning estimates until measured. Do not claim measured GPU-hours or energy savings from this decision.

Qwen3 14B remains an optional development comparison requiring matched-system agreement before a model change. It is not an automatic failure fallback. Freeze one selected artifact/settings configuration before held-out runs; do not switch models or tune on held-out fixtures.

## Owners may proceed

| Owner / tasks | Work authorized to proceed | Remaining integration requirements |
|---|---|---|
| Matty, A01/F03 | Shared Ollama adapter and attempt/accounting design, offline failure tests, SDK compatibility/version-lock preparation and provider/F02 consumer checks | Exact SDK/runtime/artifact pins, run limits and demonstrated compatibility; no full A01 acceptance yet |
| Nisha, L01/L02 | Plain path and explanation preparation, shared output-schema coordination and mock integration with Matty's adapter | Actual A01 adapter, K02 equivalent flat context, relevant checker/impact interfaces and independent verification |
| Ved, F02 | Support shared-record/output-projection compatibility and record consumer adoption with Matty/Nisha | Affected consumers validate actual examples; a merged schema is not adopted by assertion |

No task ownership is transferred, no second provider adapter is authorized, and no task is marked Done by this acceptance. Reimo/Edison continue their existing assignments. Shared-format/settings changes still require affected teammates' agreement first. Matty's main instruction authority and the checks-based merge rule remain intact.

## Evidence and remaining decisions

Current base `a61a7f2` includes Ved's F02 schemas (contract 1.0.0) and examples, plus Reimo's D01 carbon loader. Read [the implemented F02 documentation](../Interfaces%20F02), [schemas](../../dc_sustainability/schemas.py) and [examples](../../tests/contracts/examples/). The older interface blueprint is not evidence of a missing implementation; consumer adoption remains pending.

The existing contract, data-loader and offline-provider-mock suites pass locally: 193 tests and 19 subtests. This validates those existing suites, not a production provider, accepted output projection or real development episode.

Matty will supply target GPU/VRAM details. The target machine, driver, runtime/SDK versions, installed model digest, exact matched trial seeds, context boundary rule and resource/run authorization remain open. Do not mark Q09 fully frozen, begin held-out/cloud/paid experiments, or claim model inference was tested from this approval alone. Development preparation can proceed without those final run details.

Effective instruction deployment: 1.7. No shared schema, dependency lock, runtime configuration or experiment output was changed by this decision publication.
