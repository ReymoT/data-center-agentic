# Offline provider mocks

Task: A01 mock preparation only. Owner: Matty Anderson (MattyAnd). Date: 2026-10-12.

[ScriptedTransport](mock_transport.py) is a provider-independent test helper. It accepts an iterable of opaque response objects or Python exceptions. Each explicit call consumes one outcome. Exceptions propagate, malformed responses remain malformed, and every invocation is recorded, including failures and calls after the script is exhausted. Returned responses and recorded arguments are copied so later mutation does not erase test evidence.

It uses no provider SDK, credential, network call, waiting, retry or repair. It defines no Job, Plan, VisibleState, provider-result schema, model setting, timeout duration or spending limit. It is not the production provider adapter. F02/Q09 still govern that adapter and its integration.

Example for a future test using an adopted provider boundary:

```python
from tests.llm.mock_transport import ScriptedTransport

transport = ScriptedTransport([TimeoutError("synthetic timeout"), "synthetic raw response"])
# Inject/wrap transport at the future adapter's outbound-call boundary.
# The first explicit call raises; a second call is possible only if the caller makes it.
# At the end of the test:
# transport.assert_consumed()
```

Run the existing helper tests offline:

```powershell
.venv\Scripts\python.exe -m pytest tests/llm/test_provider_mocks.py -q
```

The tests cover credential-free operation with network guards, raw malformed outputs, failures without automatic retries, explicit subsequent attempts, a one-response plain script, a three-outcome agent script, extra calls, unused script stages and mutation-resistant records. The three-outcome script includes a failed repair attempt; it does not execute a real agent workflow or certify its retry/call accounting. A blocked extra invocation appears in attempt_count for test evidence but incurs no real provider charge.

Mocks must not be used as evidence of an actual model-driven episode, valid scheduling, independent scoring, token/cost accuracy or A01/A02 acceptance. Keep requests/responses synthetic and replace the generic callable wrapper with the adopted SDK/F02 boundary during integration. Nisha's production modules are not changed by this task.
