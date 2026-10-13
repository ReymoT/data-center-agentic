# Test areas

Directories reserve module-owner test locations. Ved's F02 contract tests and Reimo's D01 carbon-loader tests are now executable alongside the provider-mock helper tests. Matty owns `e2e/`, Ved owns `contracts/`, Nisha owns independent `evaluation/`, and other directories follow module ownership. Scheduling/checker/runtime tests still require those implementations.

Matty's [production checker case catalogue](verification/CASES.md) prepares 19 cases with established rule expectations and four scenarios waiting for Q01-Q04. It is a test specification, not an executable suite or passing checker evidence.

The [offline provider mocks](llm/README.md) now have executable helper tests under `tests/llm/`. They verify scripted responses, failures and call evidence. They do not test a production provider adapter or complete A01.

`scripts/validate_setup.py` checks repository/package consistency. `scripts/smoke_dependencies.py` checks installed candidate dependencies offline. Neither proves simulator, checker, policies, integration or final E2E acceptance. Add meaningful tests as implementation arrives; empty discovery is not completion evidence. Paid live calls require a separate approved budget/run.
