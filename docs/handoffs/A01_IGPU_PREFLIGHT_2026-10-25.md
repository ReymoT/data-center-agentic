# A01: offline Arc/Vulkan preflight

The reusable A01 preflight is ready and was dry-tested on Matty's Windows host.
It starts the accepted Ollama 0.40.5 runtime on an unused loopback port with the
Arc/Vulkan candidate settings, checks the accepted model identity twice, confirms
the runtime executable hash, confirms that no model is loaded, validates the exact
Arc 140V Vulkan discovery line, and
then stops only the process handle it created. It refuses occupied ports and
existing output files.

The launcher has a fixed metadata-only endpoint allowlist: `/api/version`,
`/api/tags`, `/api/show` and `/api/ps`. There is no chat, generate, embedding,
pull, tool, simulator or experiment path. The successful dry test made eight
metadata requests, loaded no model and made zero model requests. Its owned server
exited and no listener remained on port 11437. Sanitized evidence is in
[`a01-igpu-preflight-2026-10-25.json`](../evidence/a01-igpu-preflight-2026-10-25.json).
Raw logs remain outside Git.

Two earlier launcher-development attempts could not reach the isolated loopback
server from the restricted command sandbox. Both stopped before identity
inspection, loaded no model, made zero model requests and left no listener. Their
failure records are retained outside Git; the successful dry test used explicit
local-socket permission.

Example metadata-only invocation from the repository root:

```powershell
.venv\Scripts\python.exe scripts\a01_igpu_preflight.py `
  --runtime <isolated-runtime>\ollama.exe `
  --models <isolated-model-store> `
  --accepted-inventory docs\evidence\ollama-qwen3-8b-2026-10-18.json `
  --output-dir <new-empty-evidence-directory> `
  --port <unused-loopback-port>
```

This preparation does not adopt the iGPU setting for experiments and does not
authorize a model call. Nisha and Ved's required setting agreement remains pending
in issue #6. Because the earlier real CPU attempt failed, any later inference also
requires a new explicit bounded authorization from Matty. A01 therefore remains
open until those gates are satisfied and a separate authorized validation succeeds.
