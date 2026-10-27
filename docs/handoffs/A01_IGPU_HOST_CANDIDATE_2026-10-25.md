# A01: concrete Arc/Vulkan host candidate

The CPU-only A01 request remains a spent uncertain attempt. It timed out at the
accepted 120-second limit, returned no response or API usage, and was not retried.
The Plan request was not sent. This handoff does not replace or rewrite that result.

## Host constraint investigation

The failed run already showed why the local Arc GPU was unused. Ollama 0.40.5
detected the Intel Arc 140V through its bundled Vulkan backend, then logged that it
was dropping the integrated GPU unless `OLLAMA_IGPU_ENABLE=1` was set. The runtime
therefore selected CPU even though `OLLAMA_VULKAN=true` was present.

Matty authorized resolving the host constraint before the F04/F05 refresh. A new
isolated metadata-only process used the same accepted Ollama 0.40.5 binary and
model store, with `OLLAMA_IGPU_ENABLE=1` and `OLLAMA_VULKAN=1`. It listened only
on `127.0.0.1:11436`. No model was loaded and no inference request was sent.

The runtime retained the Arc 140V as its inference compute device:

- library: Vulkan;
- device type: integrated GPU;
- runtime-reported memory: 18.0 GiB total and 17.2 GiB available;
- loaded models: zero;
- model requests: zero.

The isolated server and its console child exited, and no listener remained on the
isolated port. The active desktop service and accepted model files were not changed.
The sanitized evidence is in
[`a01-igpu-host-2026-10-25.json`](../evidence/a01-igpu-host-2026-10-25.json).
Raw local logs stay outside Git.

## Resolution and remaining boundary

This resolves the missing concrete-host question at the candidate level: Matty's
existing Windows host has an available accepted-runtime Vulkan path to the Arc
140V. It avoids changing the accepted model, runtime, context, generation settings,
call timeout or model budgets.

It is not yet a successful A01 inference environment. The reported memory is shared
integrated graphics memory, not dedicated VRAM, and no model load occurred. Layer
offload, full 16,384-token context fit, native counts, latency and completion inside
120 seconds remain unverified. The runtime also reported driver and compute fields
as `0.0`; this record does not interpret those fields as validated driver metadata.

Enabling integrated-GPU use is a run-environment setting. Nisha and Ved are the
directly affected owners for comparator/runtime and context/contract receiving, so
their explicit agreement or exact blocker is required before adopting it for the
next paired validation. Silence is not approval. Another model request also needs
new, explicit bounded authorization because the earlier real attempt failed.

Full A01 remains open. No model call, retry, scientific result, schema change,
dependency change, runtime pin change, timeout extension, context reduction or
task transfer is claimed here.

## F04/F05 status refresh

The same publication refreshes the current plain-language project documents and
architecture drawing after PRs #77 and #81. They now state that greedy A/B and the
probability-to-schedule constructor exist, while trained C/D models, reviewed
renderers, the common runner, successful matched LLM evidence and study results do
not. Q07 #82 is a proposal awaiting the directly affected Ved/Nisha replies.

The README still begins with equally formatted teammates and roles, keeps Matty and
Nisha together, and retains the reviewed-system comparison and evidence-based design
rationale. The architecture image is regenerated from its source and visually
checked. No master version, task allocation, F02 contract, accepted scientific rule,
model/runtime pin, original rating or teammate implementation is changed.

Actual checks on this branch:

- complete offline suite: 1,310 tests and 19 subtests passed;
- setup validator: 50 task records, role inventories, dependencies, links, versions,
  canonical interface pointer, placeholders and seven-file policies passed;
- Ruff lint and formatting: 114 Python files passed;
- dependency smoke passed SHACL/SPARQL, a tiny certified integer program, both
  classifier save/reload paths and a bounded LangGraph route with no model call;
- Python compilation and dependency consistency passed;
- Git whitespace validation passed.
