# Test areas

P01 now has27 metrics cases, including five Matty review cases in `tests/metrics/test_p01_review.py`. The F02 hand conversion is a labeled component check, not production S02 adoption. A01's optional `--synthetic-protocol HTTP/1.0` or `HTTP/1.1` observer mode is a controlled test-server experiment only; original tests/deadlines/assertions remain intact, and passing runs never establish a timeout fix.

For A01's intermittent partial-body timeout, `python scripts/diagnose_provider_wire.py --full-suite --out <new-local-json-path>` observes the existing synthetic tests with matched socket endpoints and byte/hash evidence. It never contacts Ollama. Use a new path each time. Observation changes timing; passing runs are not a timeout fix. See [the dated handoff](../docs/handoffs/OCT21_ACTIONS.md) for the reproduced failure and passing observations. No payload, deadline or assertion is weakened.

Directories reserve module-owner test locations. Ved's F02 contract tests and Reimo's D01 carbon-loader tests are now executable alongside the provider-mock helper tests. Matty owns `e2e/`, Ved owns `contracts/`, Nisha owns independent `evaluation/`, and other directories follow module ownership. Matty's fixed checker and Ollama transport now have executable tests; full scheduling/runtime integration remains pending.

Matty's [production checker case catalogue](verification/CASES.md) prepares 19 cases with established rule expectations and four scenarios waiting for Q01-Q04. [Executable fixed-core tests](verification/test_checker.py) now exercise its decided rules; overall checker approval still waits for Q01-Q04.

The [offline provider mocks](llm/README.md) now have executable helper tests under `tests/llm/`. They verify scripted responses, failures and call evidence. The helper tests remain test-only. [Additional real HTTP transport tests](llm/test_ollama_provider.py) now exercise the production adapter against a synthetic local server; no inference or full A01 acceptance is claimed.

`scripts/validate_setup.py` checks repository/package consistency, including deployment versions and the canonical interface location. `scripts/smoke_dependencies.py` checks installed candidate dependencies offline. Neither replaces component tests or proves policies, integration or final E2E acceptance.

Run all current offline suites with `python -m pytest tests -q` (or `.venv\Scripts\python.exe -m pytest tests -q` on Windows). PR/main CI uses that command. The original 168 F02, 12 D01 and 13 helper tests remain, plus 19 unittest subtests. New transport/checker cases are reported in [the implementation handoff](../docs/handoffs/A01_A03_AGREED_CORE.md) and task Issues. D01 tests use generated synthetic CSVs; download boundaries are mocked in tests, not production. F02 fixtures are synthetic contract examples, not actual checker/solver results.

Add meaningful offline tests as implementation arrives; empty discovery and constant passing verdicts are not completion evidence. Live-model/paid tests need a separately authorized run and must not enter ordinary CI. Keep independent evaluation tests separate from production-checker tests.
