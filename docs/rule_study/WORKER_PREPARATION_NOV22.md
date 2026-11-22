# Actual authored-case worker preparation — November 22

Matty, #244. This completes offline backend wiring to the merged RULE02 runner.
It is not a released research dispatcher, scientific run or accepted freeze.

`scripts/prepare_rule_study_worker.py` prepares one fixed authored case/policy work
unit: A, B, B-progress or rules-v1-only B-fault, with 30 recorded decisions. There
is no arbitrary shell command, callback, module or final-seed generation operation.
The cases, policies, checker semantics and artificial score convention are unchanged.

The future trusted supervisor must authenticate the exact fresh bounded human
authorization and consume its real single-use ID before releasing this worker.
No such approval or real ledger release is supplied today. The public CLI only
inspects a pending request; it cannot launch even the prepared worker.

## Wiring and stop behavior

The fixed child first waits for the existing supervisor's `G` containment signal.
Without it, it exits before reading inputs or importing project code. After release,
it checks request bytes, the complete Python/lock/spec source map and repository
path containment before importing the backend. The backend repeats the clean
merged-code/input preflight, obtains actual bindings and calls the existing
`runner.run_case`. Only an absent output directory is created. Results or failure
evidence remain on disk; output reuse is refused, not retried or erased.

The existing Windows Job Object supervisor supplies hard timeout, descendant
cleanup and fail-closed containment. Its 900-second technical maximum is not a
new scientific allowance. Each actual operation still needs its exact approved
bound; multiple workers cannot obtain separate unapproved allowances.

The backend and CLI are not human-approval authenticators. Directly calling its internal
function or sending `G` manually does not grant authorization. The `dispatch_once` trusted-host entry point now implements exact-envelope authority
checking, actual Windows/Python/locked-version checks, durable one-use ID reservation,
post-reservation drift checks and the existing fixed process supervisor. Its authority
callback must come from trusted host code authenticating the fresh human decision
and actual receiving records; it cannot come from the request, a URL or a module name.
No such host authority or real authorization is supplied today. Actual required
receiving/freeze records must exist before research execution.
Final generation and independent verifier callback wiring remain separate.

## Pending request shape and inspection

A request has only `kind`, `plan`, `case_id`, `policy_id`. `kind` is
`rule_study_authored_worker_preparation_v1`; `plan` is the unchanged pending
preflight plan from `prepare_rule_study_dispatch.py`. Approval/command/module
fields are rejected. Missing case/accounting files or receiving references stay
explicitly blocked. Refresh all code pins after the new code is merged.

```
python scripts/prepare_rule_study_worker.py --inspect <pending-request.json> --out <new-report.json>
```

`WORKER_PREPARED_NOT_AUTHORIZED` describes hash/shape readiness only. Inspection
never releases a child, consumes an authorization or creates the study output.

## Ordinary offline tests

New tests exercise closed stdin, changed request bytes, missing gates, forbidden
approval/command fields, fault-case identity, one actual authored Case A fixture
through the existing runner, retained failure and output-reuse refusal. Fixture
binding placeholders are explicitly test-only, never scientific source bindings.
Dispatcher tests use fixture authorities and mocked supervision to check denial,
exact-envelope refusal, used-ID/drift stops and missing-result failure without
research execution. Existing supervisor tests exercise real dummy
success/failure/timeout and descendant cleanup. A separate actual environment
check observed Windows Python 3.12.14 and 74 lock-matching installed versions;
that is version evidence, not a binary attestation. No study or model run is performed by this preparation.

Next: Nisha #241 receives the current implementation and verifier mapping;
Edison #242 supplies retained development inputs/accounting and metrics. Matty
then pins the actual freeze and records a fresh exact authorization before any
real release. Original Nov 25/26–27/28 delivery checkpoints remain unchanged.
