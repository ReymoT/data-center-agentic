# A01 Arc/Vulkan bounded validation

Matty authorized one bounded development validation in
[issue #6](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6455375516):
at most two serial local requests, Plain first and Plan only after a successful
Plain result, 120 seconds per request and 300 seconds overall. There were no
retries, warm-up calls, tools, simulator actions or study runs.

The first launcher attempt stopped during metadata comparison because of a local
quoting defect. It sent zero model requests and the exact isolated listener was
stopped. The defect was corrected without changing either reviewed request,
model setting or bound. The same unused authorization then resumed.

## Actual result

Exactly one Plain request was sent through the real `PlainLLMPolicy` and shared
provider, using the reviewed request SHA256
`264630e066a9bc96f9cee6b0666e30168154d622cff7d35cbf3c75f0a3b42b90`
and seed 101.

The isolated accepted Ollama 0.40.5 runtime loaded `qwen3:8b` on the Intel Arc
140V Vulkan backend. Runtime logs report 37/37 layers offloaded, context 16384,
temperature 0.2 and `top_p` 1. The loaded-model API reports
`size_vram == size == 7,536,965,058` bytes. This is full runtime-reported
offload; the iGPU uses shared system memory and the value is not dedicated VRAM.

The request returned HTTP 200 after 65,382.44 ms. The provider reported 2,291
prompt tokens, matching the pinned offline candidate count, and 720 completion
tokens. The 3,085-byte response is retained outside Git with SHA256
`e80c30131a923277962dfe038eb503b72d99b91475a01bb9255575723b822d4f`.

The response omitted the required top-level `schema_version`. It therefore
failed strict `PolicyOutput` parsing and is retained as a schema-invalid spent
response, not repaired or rewritten. The driver stopped as required. The Plan
request was not sent and no retry was attempted.

Before/after runtime, model, template and parameter identities match. The
isolated server and runner are stopped; final recheck found no runtime process
from the isolated installation and no listener on port 11437.

[Sanitized evidence](../evidence/a01-igpu-validation-2026-10-27.json) records the
measured fields. Full A01 is still open: one schema-invalid Plain response does
not establish a usable paired validation, production counter adoption, an
integrated episode or study results.
