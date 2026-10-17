# L01 plain-LLM preparation

Task ID / Issue: L01 development preparation, authorized in [issue #2](https://github.com/ReymoT/data-center-agentic/issues/2#issuecomment-6136759988) and the [Q09 decision](../decisions/Q09_OLLAMA_QWEN3.md). L01 itself has no Issue yet.
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk); technical contact Matty (A01 adapter, prompt review); Ved for F02/K02 context.
Active assistant session / instruction version: one Claude Code session for Nisha; instruction deployment 1.10.
Objective: Prepare the plain-LLM comparator so it makes exactly one shared-adapter request per decision, keeps the original output, and never repairs, retries or falls back.
Base commit / branch / PR: base `0cc1f5e` on main; branch `nisha/l01-plain-llm-preparation`; PR not yet opened.

Changed paths:
- `dc_sustainability/llm/plain.py` (new): `PlainLLMPolicy.propose(state, context, seed=, decision_deadline=)` returns a `PlainDecision` holding an F02 `PolicyOutput`, the adapter `Attempt`, any pre-dispatch block reason, and hashes of the messages, prompt files and context.
- `prompts/shared/task_rules.md`, `prompts/shared/explanation_rules.md`, `prompts/plain_llm/system.md`, `prompts/plain_llm/user.md` (new), and `prompts/README.md`.
- `tests/llm/test_plain.py` (new, 16 tests).

Behavior:
- Uses Matty's `OllamaProvider` unchanged, so model, digest check, temperature 0.2 and all other Q09 settings are identical to the agent's. No second adapter.
- Requires a `flat` F02 `Context` whose content matches the requesting `VisibleState`; otherwise refuses before any request.
- One request per episode/slot. A second call raises, even when the first was blocked before dispatch. No call in completion slots.
- Output mapping, with the original text kept in `raw_response`: schema-valid output stays exactly as the model returned it (`ok`, even when the plan is unsafe); unparseable or self-approved output is `malformed`; empty content is `no_output`; transport failure is `error` with `uncertain_outcome`; an adapter block before dispatch is `error` with no attempt.
- Does not call the checker or the gate. The runtime must check, block invalid starts and still advance time.

Input and output contract/config versions: F02 1.0.0 (`VisibleState`, `Context`, `PolicyOutput`); Q09 development settings as implemented in `provider.py` at `0cc1f5e`. No schema, provider or setting changed.
Artifact locations and checksums: none. Prompt hash is computed at run time by `prompt_template_sha256()`.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m pip check
```

Tests actually run and observed results: on Windows, Python 3.12.10, in a fresh venv from the hashed lock: 758 tests and 19 subtests passed (742 before this change, 16 new). Ruff check, format check, compileall, setup validation and pip check passed. Tests use a loopback test server with scripted synthetic responses; no Ollama server or model inference ran.

Limitations and open decisions:
- Not L01 acceptance. It still needs a real development episode through the actual adapter with K02's flat context, and Matty's review.
- The flat presentation is the F02 `ContextContent` JSON until K02 publishes the agreed projection.
- Prompts do not settle Q01 (starts in completion slots), Q02/Q03 (coverage, abstention) or Q04 (forecast freshness); update them after those decisions.
- Prompt token size is not measured. The deployment's validated token counter decides whether the prompt fits.
- The 101/102/103 seeds are still only a proposal; the caller supplies the seed.
- Mapping `PlainDecision` into `DecisionRecord` belongs to A04/E02 and is not done here.

Receiving owner and consumer check: Matty, to review the prompts (the shared files are offered for the agent so both systems see the same rules) and confirm the adapter use; Ved, to confirm the flat-context assumption for K02.
Next checkpoint: open a draft PR, create an L01 Issue, then run one real development decision once a deployment config and K02 context exist.
