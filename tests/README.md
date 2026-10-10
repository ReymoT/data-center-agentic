# Test areas

Directories reserve module-owner test locations. They currently contain no production tests. Matty owns `e2e/`, Ved owns `contracts/`, Nisha owns independent `evaluation/`, and other directories follow module ownership.

Matty's [production checker case catalogue](verification/CASES.md) prepares 19 cases with established rule expectations and four scenarios waiting for Q01-Q04. It is a test specification, not an executable suite or passing checker evidence.

`scripts/validate_setup.py` checks repository/package consistency. `scripts/smoke_dependencies.py` checks installed candidate dependencies offline. Neither proves simulator, checker, policies, integration or final E2E acceptance. Add meaningful tests as implementation arrives; empty discovery is not completion evidence. Paid live calls require a separate approved budget/run.
