# L01 empty-queue guard

Task ID / Issue: L01, [issue #12](https://github.com/ReymoT/data-center-agentic/issues/12). Rule from Q03.4 in [issue #7](https://github.com/ReymoT/data-center-agentic/issues/7), recorded in [Q01-Q04 status](../decisions/Q01_Q04_AGREEMENT_STATUS.md): with an empty waiting queue, neither LLM system makes a model call and a deterministic no-op is recorded.
Human owner / technical contacts if needed: Nisha Mahadev Kolekar (nkolekar-nk); technical contact Matty (A01 adapter and runtime boundary).
Active assistant session / instruction version: one Claude Code session for Nisha; instruction deployment 1.15.
Objective: Close the L01 gap Matty noted in #7: the plain path had no empty-queue guard.
Base commit / branch / PR: base `894f39f` on main; branch `nisha/l01-empty-queue-guard`; PR to be opened.

Changed paths:
- `dc_sustainability/llm/plain.py`: `PlainLLMPolicy.propose` returns a no-op without calling the provider when the visible state has no waiting jobs. `PlainDecision` gains `empty_queue_noop` (a local L01 field, not an F02 change).
- `tests/llm/test_plain.py`: 5 new tests.
- `docs/handoffs/L01_EMPTY_QUEUE.md` (this file).

Behavior:
- The completion-slot refusal, the one-request-per-decision rule, state/context revalidation and the flat-context check all still run first. A mismatched context is still refused even when the queue is empty.
- With no waiting jobs, the output is `PolicyOutput(output_status="ok")` with an empty plan bound to the state's episode, slot and state version, status `proposed`, no explanation and no `raw_response`. `attempt` and `blocked_reason` are None and `empty_queue_noop` is True. The provider is never consulted, so a runtime that would block dispatch does not turn the no-op into an error.
- The decision is still used: a second `propose` for that slot raises, as for any other decision.
- No explanation means the Q10 claim review marks that component not applicable; nothing is fabricated.

Input and output contract/config versions: F02 1.0.0 unchanged. No schema, provider, prompt or setting changed; the prompt hash is unchanged.
Artifact locations and checksums: none.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/llm/test_plain.py -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m pip check
```

Tests actually run and observed results: Windows, Python 3.12.10, hashed lock. 923 tests and 19 subtests passed (918 on main before, 5 new). Ruff check/format, compileall, setup validation and pip check passed. The new tests check zero HTTP requests and zero provider attempts, the exact no-op record, that E01's independent validator scores it valid, that a blocking runtime is not consulted, and that the decision is still used up. With the guard removed, the four empty-queue tests fail. Tests use the loopback test server; no model ran.

Limitations and open decisions:
- This covers the plain path only. The agent path and the shared runtime/runner (Matty's A01/A04 boundary, E02) must make the same no-op with zero dispatch before the "both systems" requirement is met.
- L01 full acceptance is still blocked on K02's flat projection (Ved), Q09 runtime revalidation (#6) and an authorized development probe.

Receiving owner and consumer check: Matty, to confirm this matches the runtime boundary's no-op record and to mirror it on the agent path; Nisha (E02), to count these slots in the empty-queue total and exclude them from the primary accuracy denominator.
Next checkpoint: verify zero dispatch for both systems once the runtime/runner exists.
