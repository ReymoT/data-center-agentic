# Q09: October 20 development setup agreement

Status: agreed development setup with technical gates; not a frozen experiment or inference authorization. Instruction deployment 1.15. Sources: [Nisha's agreement and additions](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6278309369), [Ved's agreement](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6283858363), [Matty's confirmation](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6298590019). Earlier recommendation/acceptance remains in [issue #2](https://github.com/ReymoT/data-center-agentic/issues/2).

| Item | Agreed development rule |
|---|---|
| Transport | One shared Python standard-library REST adapter and run ledger; no second SDK or hidden retries. Keep the existing LangGraph candidate; validate the eventual integrated environment. |
| Runtime | Ollama 0.40.5, with full artifact/license/template/default-parameter evidence. A later change needs both-system revalidation and affected-owner agreement. |
| Model | qwen3:8b, Q4_K_M, digest 500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41. |
| Generation | Both systems: temperature 0.2, top_p 1, stream=false, think=false, num_ctx=16384, num_predict=1536, keep_alive=30m. |
| Seeds | Matched trial seeds 101, 102, 103; every agent call in a trial uses its seed. Save original responses because seeds do not guarantee deterministic text. |
| Outputs | Agent propose/repair: F02 Plan; explanation: Explanation. Plain: one combined PolicyOutput request. Parsed records do not approve execution. |
| Context | Temporary ContextContent JSON until K02's equivalent projection is validated. No hidden answers or future arrivals. |
| Context ceiling | Candidate 12000 prompt tokens for both systems, subject to a validated pinned tokenizer/template counter and measurements of both request shapes, including the larger plain schema. Not yet validated. |
| Failure | Oversize blocks before dispatch and remains an incorrect required decision. No trimming facts, selective retries or replacing failures. |
| Concurrency | Serial. Verify OLLAMA_NUM_PARALLEL=1 and OLLAMA_MAX_LOADED_MODELS=1 in the actual run environment. This record does not claim they are configured. |
| Caps | Three agent attempts per decision including explanation, one plain attempt; ledger counts failed/uncertain requests. |

## Current runtime mismatch

[Fresh metadata-only inventory](../evidence/ollama-qwen3-8b-2026-10-20.json) observes 0.40.6. Model digest, template and parameter-text hashes match the [0.40.5 inventory](../evidence/ollama-qwen3-8b-2026-10-18.json); runtime does not. Zero model calls. Preserve both records and historical 0.40.3 evidence. The agreed 0.40.5 deployment check must reject the current installation.

Matty proposed revalidating 0.40.6 for both systems in his linked reply. [Nisha agreed to revalidation with conditions](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6306094258), and [Matty accepted those conditions](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6306237802). Ved's agreement and actual validation are pending. Preserve both inventories, use identical runtime/artifact/template/default parameters for both systems and reject drift. No automatic-update/service settings were changed. No silent pin change or downgrade occurs here. The [setup guide](../OLLAMA_SETUP.md) and [hardware record](../HARDWARE.md) retain actual evidence; no dedicated 16 GB GPU, offload, throughput, energy measurement or successful inference is inferred from Intel shared RAM.

## Prepared bounded probe and remaining gates

Exactly two maximum attempts on the same public development state, seed 101: plain through actual PlainLLMPolicy.propose, agent through shared transport with Plan output. One ledger, serial calls, 2 MiB per response, 120 seconds per call, five-minute overall deadline. Stop on timeout and retain failures; no selective reruns. No warm-up; latency labeled cold/unknown-cache. This probes transport/plain consumption, not the full A02 agent or an integrated episode.

[prepare_q09_probe.py](../../scripts/prepare_q09_probe.py) uses the actual plain renderer and public F02 synthetic hand fixture, with the same ContextContent facts for both requests. [Prepared inputs](../evidence/q09-probe-preparation-2026-10-20.json) contain bodies, hashes and byte/character sizes, **not token counts or model responses**. There is no dispatch path. The agent Plan probe prompt is a minimal compatibility prompt, not a frozen A02 prompt. Rendering plain input is not running PlainLLMPolicy.propose; the later probe must use that real consumer.

Before dispatch: resolve runtime drift; implement/validate a pinned tokenizer/template-aware counter covering actual rendered prompts and schema behavior; measure both requests and validate the 12000-token ceiling with generation reserve; verify serial service settings; record explicit bounded run authorization. No constant, mock or character counter can satisfy those gates. Ollama's [chat API](https://docs.ollama.com/api/chat) reports prompt_eval_count after a request; it is not pre-dispatch protection. The proposed [tokenization endpoint PR](https://github.com/ollama/ollama/pull/12030) does not establish a validated counter in this installation. Another tokenizer/dependency/runtime needs coordination and environment evidence.

For evaluation, one identical public-development warm-up per paired trial is reported separately from decision budgets and counted in run totals; fix agent/plain order before freeze because cache state affects latency. No warm-ups, held-out, cloud or paid calls are authorized here. Empty-queue no-call handling is merged for plain L01 through PR #30; the agent/runner path and saved runtime records still need implementation. This does not establish both-system runtime acceptance.

Matty owns A01/F03 adapter, counter/context validation, pin checks and probe preparation; Nisha owns L01/L02 plain/explanation integration and E02 accounting; Ved supports unchanged F02/K02 compatibility. Full A01/F03/L01 acceptance still needs real evidence and the remaining prerequisites. Configuration examples stay blank and non-runnable. No schema, lock or generation implementation changed.

## Counter research follow-up, October 20

[The eight-priority handoff](../handoffs/OCT20_EIGHT_PRIORITIES.md) records a real isolated tokenizers 0.23.3/Go-template candidate, measured request shapes and a direct GGUF/reference vocabulary/merge comparison. Counts are candidate-only, not validated runtime counts. No production callback, new shared dependency, context ceiling or runtime pin is adopted. Exact runtime rendering/tokenization equivalence and affected-owner dependency agreement remain required; the prepared probe remains blocked with zero model calls.
