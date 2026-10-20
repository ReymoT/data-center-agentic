# Local Qwen model setup

Current update, October 20, 2026: [Nisha/Ved/Matty agreed development setup](decisions/Q09_DEPLOYMENT_OCT20.md), including Ollama 0.40.5, digest, seeds and projections. The [new read-only inventory](evidence/ollama-qwen3-8b-2026-10-20.json) instead observes 0.40.6 with unchanged model/template/parameter hashes. Comparison to the 0.40.5 record is expected to fail. Do not overwrite history or silently accept drift. Counter/context validation and bounded run authorization remain required; no model calls. The dated entries below retain earlier setup evidence.

Matty completed this independent A01/F03 setup on 2026-10-12, following the accepted
[Q09 direction](decisions/Q09_OLLAMA_QWEN3.md). Installation and identity checks are
complete. Full provider/environment and experimental acceptance remain pending.

Update 2026-10-18: the local CLI/API now report Ollama 0.40.5. The [dated inventory](evidence/ollama-qwen3-8b-2026-10-18.json) has the same model digest, size, quantization, license and template hashes as the original inventory, but different runtime and rendered default-parameter-text hashes. The original comparison correctly rejects this drift. No automatic runtime update/downgrade, model call or deployment acceptance was performed by this work. [Q09's concrete proposal](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6257425665) awaits affected-member agreement.

## Original installation evidence, 2026-10-12

| Item | Observed value |
|---|---|
| Runtime | Ollama 0.40.3, verified through CLI and local API |
| Model | `qwen3:8b`, GGUF, Q4_K_M, 8.2B as reported by Ollama |
| API model digest | `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41` |
| Installed bytes reported by API | 5,225,388,164 |
| Weight-blob SHA256 | `a3de86cd1c132c822487ededd47a324c50491393e6565cd14bafa40d0b8e686f` |
| License | Apache-2.0, checked in the installed license and upstream model card |
| Model calls / GPU measurements | Zero model calls; inference, offload and throughput untested |

[The model card](https://huggingface.co/Qwen/Qwen3-8B) and
[Ollama package page](https://ollama.com/library/qwen3:8b) support the license/model
identification. Actual local evidence is saved in [the inventory](evidence/ollama-qwen3-8b.json),
including license/template/default-parameter text hashes. The observed inventory does
not approve an experiment configuration or automatically select a deployment pin.

Ollama's pull completed successfully with SHA256 verification. An independent local
hash/size check also verified all six stored blobs, including weights, license,
template, parameters, config and the original manifest. [Storage evidence](evidence/ollama-qwen3-storage.json)
records those checks without local paths or device identifiers.

The local storage manifest hash is different from the API digest because this
runtime stores a wrapper that also references the original manifest blob. Both are
recorded separately; do not substitute one for the other in the provider's model pin.
The API digest matches the verified original manifest blob. The parameters hash in
the inventory hashes `/api/show`'s rendered text; the storage record hashes the raw
parameter JSON blob. These are different representations, not interchangeable hashes.

## Reproduce or check another installation

Ollama must already be installed. Pulling the accepted tag downloads the model into
Ollama's storage, not the repository. The tag is mutable, so compare the full digest
after downloading rather than trusting the name or short ID.

```powershell
ollama --version
ollama pull qwen3:8b
ollama list
.venv\Scripts\python.exe scripts/inspect_ollama.py --compare docs/evidence/ollama-qwen3-8b-2026-10-18.json
ollama ps
```

`inspect_ollama.py` reads only local version/tags/show endpoints and does not generate,
load, install, retry or change models. It rechecks identity to detect a tag changing
during inspection, compares saved runtime/artifact/license/template/parameter metadata,
and reports errors on mismatches. Optional `--out NEW_FILE` records a new inventory
and refuses to overwrite an existing file. Local file paths and full license/template
text are excluded. The endpoint descriptions are in [Ollama's show API](https://docs.ollama.com/api-reference/show-model-details).

Use the original `ollama-qwen3-8b.json` only when comparing against the historical 0.40.3 installation. Comparing today's 0.40.5 runtime against it is expected to fail; do not edit the saved record to hide that mismatch. The new inventory is observational evidence, not an approved pin.

A mismatch requires investigation; do not silently accept a different artifact,
runtime or model. No model weights, user-specific paths or raw machine identifiers
belong in GitHub. The pre-existing `llama3.2:3b` model is preserved and is not an approved
substitute for this project's selected Qwen model.

## What is still required

The packaged defaults report temperature 0.6 and top_p 0.95. Those defaults are not
the project's accepted settings: the shared adapter explicitly sends temperature
0.2, top_p 1, thinking disabled and the other Q09 settings. Model metadata advertises
40,960 context tokens; the accepted development request target remains 16,384. This
metadata is not proof of a safe prompt boundary or measured GPU memory capacity.

The shared REST adapter uses Python's standard library; this installation adds no
SDK or dependency and preserves the existing hashed Python environment. Framework/SDK
selection and its final lock remain pending where required for integration.

Before live runs, record accepted runtime/artifact pins, exact matched trial seeds,
agreed F02 output projections, validated tokenizer/template/context handling,
warm-up/accounting rules and explicit run limits. Then authorize and measure a bounded
development run on the actual hardware. Nisha can use this installation evidence for
her provider/context preparation, but full L01/L02 integration still needs its own
prerequisites. No Q01-Q04 rule, shared format or generation setting changed here.
