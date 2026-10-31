# A01 bounded paired validation — October 30, 2026

Matty recorded the fresh single-use authorization in
[issue #6](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6536340075).
The run used exact merged commit `e7775b75ce9666a05abcf134a26400ddc7092c6d`,
accepted Ollama 0.40.5 and Qwen3 8B, temperature 0.2, `top_p` 1, seed 101,
context 16,384 and generation ceiling 1,536.

The sequence made exactly two serial local requests. Plain ran first and passed its
HTTP, strict-parse, normal-stop, native/offline prompt-count and Arc/Vulkan offload
gates. The Agent then returned one strictly parsed Plan and passed the same gates.
Plain used 2,291 prompt and 153 completion tokens in 25.414 seconds. Agent used
2,146 prompt and 78 completion tokens in 11.929 seconds. Both used full 37/37 layer
offload, and runtime/model/template/parameter identity was unchanged before and after.

There was no retry, warm-up, repair, explanation, tool, checker, simulator action,
cloud request or study run. The exact owned runtime exited and the isolated listener
was absent after cleanup. Five earlier metadata-only launch failures made zero model
calls and remain preserved outside Git; they are not substituted for this result.

The sanitized record is
[`docs/evidence/a01-bounded-paired-validation-2026-10-30.json`](../evidence/a01-bounded-paired-validation-2026-10-30.json).
Raw requests, responses and runtime logs remain outside Git with hashes in that
record. This validates A01's shared local provider path. It is not a complete A02
episode, does not exercise repair or fallback, and is not experiment readiness or a
scientific finding.
