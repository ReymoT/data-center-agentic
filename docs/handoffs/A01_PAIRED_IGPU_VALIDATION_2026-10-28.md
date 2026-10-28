# A01 paired iGPU validation

Matty authorized the exact bounded validation in [issue #6](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6475169542). It used current main commit `726e2e91737fdf3076adef1d96869d393b52369e`, accepted Ollama 0.40.5 and `qwen3:8b`, the Intel Arc 140V Vulkan backend, context 16384, temperature 0.2, `top_p` 1 and seed 101.

The bound allowed at most two serial requests, Plain first and Agent only after a valid Plain output plus identity, native-count and full-offload gates. Each request had 120 seconds, the sequence had 300 seconds, and there were no retries, warm-up requests, tools, simulator actions or study runs.

## Actual result

Exactly one Plain request was dispatched through the production `PlainLLMPolicy` and shared provider. Its current-main request SHA256 was `59bf1f9f167e7e10d10b6c848180f9169253871d9b5132fa3cd9b72382a7f56d`; the pinned offline candidate count was 2,291 tokens.

The accepted runtime reported the Arc 140V as a Vulkan iGPU, 37/37 layers offloaded, context 16384 and `size_vram == size == 7,536,965,058` bytes. This is runtime-reported full offload using shared memory, not a claim of dedicated VRAM.

Plain timed out after 119,984.76 ms. No HTTP status, native prompt count, completion count or response body was returned, so the outcome is retained as uncertain. The Agent gate did not open and Agent was not called. No retry was made.

Before/after runtime, model, template and parameter identities matched. Cleanup stopped the exact isolated server and runner; the final check found no listener on port 11438 and no owned process remaining.

[Sanitized evidence](../evidence/a01-paired-igpu-validation-2026-10-28.json) records the measured facts. Raw operational records remain outside Git. This failed development validation does not establish paired A01 acceptance, production-counter adoption, experiment readiness or a study result. A01 remains blocked on a valid paired model-path result under any separately authorized future run policy.
