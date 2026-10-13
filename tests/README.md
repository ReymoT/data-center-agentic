# Test areas

Directories reserve module-owner test locations. Ved's F02 contract tests and Reimo's D01 carbon-loader tests are now executable alongside the provider-mock helper tests. Matty owns `e2e/`, Ved owns `contracts/`, Nisha owns independent `evaluation/`, and other directories follow module ownership. Scheduling/checker/runtime tests still require those implementations.

Matty's [production checker case catalogue](verification/CASES.md) prepares 19 cases with established rule expectations and four scenarios waiting for Q01-Q04. It is a test specification, not an executable suite or passing checker evidence.

The [offline provider mocks](llm/README.md) now have executable helper tests under `tests/llm/`. They verify scripted responses, failures and call evidence. They do not test a production provider adapter or complete A01.

`scripts/validate_setup.py` checks repository/package consistency, including deployment versions and the canonical interface location. `scripts/smoke_dependencies.py` checks installed candidate dependencies offline. Neither proves simulator, checker, policies, integration or final E2E acceptance.

Run all current offline suites with `python -m pytest tests -q` (or `.venv\Scripts\python.exe -m pytest tests -q` on Windows). PR/main CI uses that command. Current cases include 168 F02 contract tests, 12 D01 data tests and 13 provider-helper tests, plus 19 unittest subtests. D01 tests use generated synthetic CSVs; download boundaries are mocked in tests, not production. F02 fixtures are synthetic contract examples, not actual checker/solver results.

Add meaningful offline tests as implementation arrives; empty discovery and constant passing verdicts are not completion evidence. Live-model/paid tests need a separately authorized run and must not enter ordinary CI. Keep independent evaluation tests separate from production-checker tests.
