# Offline dispatcher preflight — November 20

Matty implemented `scripts/prepare_rule_study_dispatch.py` as the next offline
step after the dummy containment rehearsal. It is preparation, not the real
final-generation dispatcher. The generator's final route remains disabled.

The tool drafts a pending plan from the actual clean merged checkout. It records
the exact commit, normalized Python-source/Windows-lock/specification file hashes
and the accepted canonical specification hash. Assessment checks those bindings,
two distinct development case/accounting input byte hashes, a new output location
outside the checkout, proposed ID/time limit and receiving-reference fields.
Unknown fields, JSON claims of approval and changed bindings fail closed.

```
python scripts/prepare_rule_study_dispatch.py --draft --out <new-plan.json>
python scripts/prepare_rule_study_dispatch.py --assess <plan.json> --out <new-report.json>
python -m pytest tests/runtime/test_rule_study_dispatch_preflight.py -q
```

Drafting and assessment do not launch a process, consume a real authorization,
generate cases, read input values as policy facts or call a model. Missing actual
paths/hashes, output, proposed ID/time and receiving records stay null in the
draft; assessment names them as BLOCKED. Fill them only from actual handoffs.
The reader caps each input at eight MiB; that is a parser limit, not a scientific
allowance. The existing supervisor's 900-second technical maximum does not adopt
or approve a study limit. The actual chosen bound still needs exact approval.

Tests also exercise an internal dummy-only dispatch path. It reserves a
`dummy-...` ID using exclusive file creation, rechecks preflight after reservation,
then invokes only the existing built-in dummy worker. A failure leaves the ID
consumed, so a repeated ID cannot silently retry. Its ledger is explicitly a
rehearsal namespace: a proposed real authorization ID cannot be consumed there.
The actual proposed study output remains absent. The public CLI cannot dispatch
even these dummy workers. Tests use synthetic bindings and one real contained
dummy worker; they fabricate no human approval or scientific result.

## Evidence limits and remaining work

`HASH_PREFLIGHT_READY_NOT_AUTHORIZATION` means the stated file/hash checks pass.
It does not authenticate receiving-reference text, validate input semantics,
verify the installed environment against its lock, establish a freeze, or grant
human approval. Real final dispatch remains absent. Its exact approval must be
authenticated outside untrusted JSON, consumed once in the real run ledger, and
rechecked against actual frozen code/inputs/output before releasing contained
work. Real failure evidence must be retained. No callback or command from a plan
can execute through this preparation tool.

Actual retained development cases/accounting, Ved's adapter, independent
accounting receiving and verifier freeze are still required. No final seed was
drawn and no policy or research batch ran. #244 remains open for the actual run
and reproduction gates; the accepted specification task #239 is separate.
