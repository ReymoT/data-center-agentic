# Selective development continuation: offline implementation

November 26 accepted update: [Nisha's new-output and combined receiving](../handoffs/RULE04_COMBINED_RECEIVING_ACCEPTED_NOV26.md) is accepted within scope. Development coverage is 360/360; the 178-pair approved continuation succeeded with verified cleanup. Do not repeat receiving or seek authorization for that consumed run again. Actual clean scientific reproduction, final/unseen evaluation and final PDF/demo/release acceptance remain pending. [Offline next-scope preparation](RULE06_NEXT_SCOPE_OFFLINE_NOV26.md) is not execution approval. Earlier dated preparation statements remain historical.


Owner Matty; November 25. This implements preparation only. No additional study
run, scientific replay, model, training or final generation is authorized here.

[Matty's package-review resolution](RULE04_SUFFIX_REVIEW_RESOLUTION_NOV25.md)
adds single-read hash verification, fail-closed inspection reports, explicit stop
reasons and native suffix regressions. A further incomplete stop remains a material
risk. The read-only union reporter is now implemented and fixture-tested; actual new-output/union receiving remains pending. See [the November26 contract and reproduction handoff](RULE04_UNION_AND_REPRODUCTION_NOV26.md).

The original full-batch request and guard remain supported unchanged. A distinct
`rule04_development_suffix_preparation_v1` request adds one exact `parent` receipt
path/hash. It selects only the unexecuted suffix of the original frozen case/policy
order, never an arbitrary subset or a failed/in-flight pair. Retain every original
attempt, consumed ID, raw failure and output directory. Do not rerun the old launcher.

## Parent receipt

The external receipt uses kind `rule04_retained_prefix_v1`, original `output`,
original request `path`/raw `sha256`, `status_sha256`, ordered `pairs` containing
case ID/policy ID/raw pair-result hash, and a complete relative-path/raw-hash
`artifacts` inventory. All parent files remain outside the checkout. Use the
reviewed retained package and separate-person receiving before prospective approval;
the receipt alone is not independent acceptance or permission to execute.

Preflight authenticates the canonical consumed parent ledger/request identity,
approved bounds, verified cleanup, exact development input/scientific pins, a
resource-stopped successful prefix, pair replay PASS/counters and no extra pair
directories. Full raw inventory checks run before reservation, again after reservation
and after a successful child. Every child rechecks the receipt/status/pair commitments.
The parent/new output directories must be disjoint, with a different one-use ID.
Existing source/environment checks, serial containment, absolute wall bound,
cleanup reserve, output stop threshold and fail-fast behavior remain in force.

Minimum charged-step preparation is 60 times the authenticated suffix length for
both states and transitions. This does not increase the existing 900-second,
60-second/pair or 256 MiB technical ceilings. Eligibility enumeration also consumes
wall time; charged counters do not measure all work. A suffix can stop incomplete.
Never silently extend time or retry. Missing-forecast control signatures carry
across the attempt boundary; evaluator-only weights stay outside policy views.

## Preparation interface

After obtaining a reviewed external parent receipt, use a clean merged checkout:

```
python scripts/prepare_rule_study_rollout.py --draft --parent-receipt <receipt.json> --out <new-request.json>
python scripts/prepare_rule_study_rollout.py --inspect <request.json> --out <new-inspection.json>
```

These public commands never execute. Populate the new exact source/input/freeze,
unused ID, absent short external output and explicit prospective limits. The
host-only authority callback must authenticate the different suffix operation and
the fresh request hash. The original approval cannot authorize this operation.

## Reporting and remaining gates

A successful suffix reports `scope_complete_only`, its authenticated selected
pairs and parent binding. Its PASS means that selected suffix only, not a complete
combined study. The read-only summary validates that scope and keeps coverage
PARTIAL across the full development set. Parent evidence is never overwritten or
automatically pooled across authorities. A separately checked union/report must
retain per-attempt and cumulative counts, failures and unequal comparison coverage.

New-output receiving, clean reproduction, final isolation/generalization and final
report/audit are separate gates. Generic preparation approval does not release a
research dispatcher. The source/specification/scientific package is unchanged;
controller/summary changes require new merged pins and prospective exact approval.
