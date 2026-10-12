# Offline provider mock preparation handoff

Owner: Matty Anderson (MattyAnd). Technical contact: Nisha. Date: 2026-10-12. Instruction deployment: 1.4. Proposed interface blueprint: 1.0, not adopted schemas. Base commit: e926273. Task branch: matty/offline-provider-mocks. No assigned GitHub Issue is claimed.

Completed exactly one deliverable: A01 offline provider mock preparation. [Mock utility and guide](../../tests/llm/README.md) supply a generic callable with scripted responses/exceptions, copied call records, explicit attempt counts and failures for exhausted or unused scripts. No production record schema or provider SDK/API is adopted by this helper.

Added 13 executable helper tests. They cover operation without credentials/network, malformed responses, explicit failures and retries, plain/agent-sized scripts, unexpected extra attempts and preservation of request/response evidence when objects are mutated. Their synthetic scripts are not production plans, agent routing or research observations.

Updated the test guide, README commands and offline CI to run the helper tests and include tests in lint/format/compilation. Dependencies and locks are unchanged. No source attachments, teammate modules, decisions, scheduling implementation, execution gate or production provider adapter changed.

## Verification

Observed locally on the existing isolated Windows Python 3.12 candidate environment:

```powershell
.venv\Scripts\python.exe -m pytest tests/llm/test_provider_mocks.py -q
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
git diff --check
```

Results: 13 helper tests passed; setup/link/task validation, lint, format, compilation and whitespace checks passed. Applicable GitHub offline CI is checked after publication. These are helper checks, not a production provider or integrated system test. No paid call was made.

## Dependencies and deferred work

Full A01 still requires adopted F02 records, Q09 provider/model/account/settings/budget decisions and provider-specific failure/accounting behavior. Token usage, pricing, request deadlines, SDK retries, rate limiting and uncertain billable requests remain unimplemented. The mock neither estimates charges nor enforces a production spending budget; a blocked extra mock invocation is recorded but incurs no real charge.

No teammate handoff was needed to finish this test-only helper. Attach it to the adopted outbound-call boundary when A01 resumes. Nisha's plain implementation and Matty's real agent must use the common eventual adapter; this helper is not a substitute. Checker/runtime implementation, decisions, agent integration and all other tasks remain deferred until Matty requests further work. A01 is not marked Done.
