# Q09 acceptance and owner handoff

Owner: Matty Anderson (MattyAnd). Instruction deployment: 1.7, 2026-10-12.
Preparation branch: matty/q09-accepted. Upstream base: a61a7f2.

Matty accepted Nisha's local Ollama/Qwen3 8B Q4_K_M recommendation and chose temperature 0.2 for both LLM systems. [The decision](../decisions/Q09_OLLAMA_QWEN3.md) defines the accepted development direction, hard call limits and remaining inputs. [Acceptance was posted to issue #2](https://github.com/ReymoT/data-center-agentic/issues/2#issuecomment-6136759988), naming the responsible owners.

## Next owner actions

- Matty: prepare A01's shared adapter and attempt/accounting behavior, offline failure tests, F02 consumer checks and F03 dependency/version-lock evidence.
- Nisha: prepare L01's plain path and L02 explanations against the shared adapter and agreed F02 projections. Full integration also needs the actual adapter, equivalent flat context and other task prerequisites.
- Ved: support F02 output-projection compatibility and record actual consumer adoption with Matty/Nisha. Keep existing task ownership and shared-format agreement requirements.

The notification authorizes this preparation. It does not mark the adapter or consumers complete, approve a second provider, or authorize held-out/cloud/paid experiments.

## Verification evidence

All upstream teammate work is preserved. Base a61a7f2 contains D01's carbon loader and F02's contract 1.0.0 schemas/examples. The following existing suites passed locally:

```powershell
.venv\Scripts\python.exe -m pytest tests/contracts/test_schemas.py tests/data/test_carbon_source.py tests/llm/test_provider_mocks.py -q
```

Result: 193 tests and 19 subtests passed. In this sandbox, TEMP and TMP were set to the writable workspace tmp directory; a first attempt could not create data-test temporary files in the default Windows temp directory. No product code change was required.

Schema unit tests do not prove consumer adoption. Offline provider mocks do not exercise Ollama, model inference or live SDK behavior. No source attachments, schema fields, dependency locks, runtime configuration or experiment output changed in this publication.

## Inputs still required

Matty will provide GPU/VRAM details. Record the actual machine/driver, runtime and SDK versions, model digest/license metadata, exact matched per-trial seeds, agreed output projections, context-boundary and warm-up/accounting rules, measured limits and resource/run authorization before live-run readiness. Nisha's example seeds are not frozen defaults. Keep all remaining Q01-Q13 decisions and integration prerequisites visible.
