# RULE-02 implementation handoff (#240, PR #257)

Date: November 21, 2026, Arizona. Implementation: Ved. Receiving fixes: MattyAnd.

The branch publishes executable study-local rules and offline unit tests. It does not
establish independent verification, an accepted scientific freeze, new evaluation results
or permission to dispatch a study. No model request is part of this handoff.

## Implementation

`dc_sustainability/rule_study/` contains the R01–R09 scheduler, strict proposal-1 records,
authored case adapters, common checked runner and an offline demonstration entry point.
`tests/rule_study/` tests their behavior with synthetic authored fixtures.

The scheduler exhaustively enumerates at most 7^4 assignments for at most four waiting
jobs and absolute candidate start slots 0–5. The R06 objective maximizes scheduled count,
then the priority inclusion vector, then minimizes artificial score, completion sum and
start vector. Future starts remain advisory. Only current-slot starts can execute.

All three policies use the existing production checker, latest-state recheck and actual
simulator. An invalid rules proposal routes to unchanged Greedy A, which must itself pass
the checker. The simulator advances refusal/drain without new starts when approval fails.
Changed live state or out-of-scope rules input stops without another simulator step.
The F02 schema, six-system registry, checker, simulator and existing Greedy A/B are unchanged.

The authored case driver enforces PUE 1, because the accepted case envelope omits PUE as
a varying input. Hourly artificial score-kWh is not measured carbon or emissions.
Perfect artificial forecasts are disclosed assumptions, not predictive accuracy evidence.

## Receiving corrections

- Case IDs must be safe path components; traversal and Windows drive syntax are rejected
  before creating output directories.
- A supplied case body must match its case binding before any file is written.
- Replay checks an exclusive completion commitment, decision identity, state/snapshot,
  transition and available case bytes. Missing completion stops as indeterminate; changed
  evidence is refused without another simulator step. Result aggregation also checks
  committed decision identity/sequence and exact transition hashes.
- The replay fingerprint includes the declared score convention. These local commitments
  detect accidental changes; they are not signatures or independent source authentication.
- The previous local-only publication statement and unreceived frozen-commit claim have
  been replaced by this current handoff. The full original report is preserved in
  `RULE02_IMPLEMENTER_REPORT_NOV21.md`, clearly attributed as historical and unreceived.

## Scenario and scientific limits

The authored Scenario B contains jointly conflicting rigid jobs. Each fits individually;
the unchanged production gate refuses the partial-plan abstention and the fallback.
That blocked/no-start outcome must remain visible. It is not progress success. B-progress
is a separate jointly feasible example; B-fault is explicitly injected, not a natural
policy failure. No new joint-exclusion semantics are adopted in this PR.

The historical implementer report names local `/tmp` traces and a `c42376...` code binding.
The later submission now supplies archived replacement traces bound to `176361a`; see
[the November 22 receiving record](RULE02_EVIDENCE_RECEIVING_NOV22.md). They do not validate
the corrected implementation on main. The published original code commit is
`176361ad23ba57940b1576828893ce3a7b1a1666`, followed by documentation commit
`ee1de66aec897d481308e3ce35a583c026c1b3ee`. Neither historical trace claims nor their hashes
authenticate the corrected implementation. A later approved run must bind the actual
clean, merged code and exact current artifacts. Unit-test placeholder commits are never
scientific bindings.

## Binding and file conventions

The study serializes sorted compact UTF-8 JSON plus one LF, with NaN forbidden. Spec and
case hashes use that convention. Adapter hash is the canonical JSON hash of a map from
each `rule_study/*.py` basename to its LF-normalized SHA-256. Generator and Windows Python
3.12 lock hashes use LF-normalized bytes. Non-test binding reads the actual clean Git HEAD.

Each case/policy directory contains case/result JSON, immutable decision records,
hash-addressed raw states/snapshots, transitions, `.intents` and `.completed` commitments.
State and snapshot hashes in the records reference their hash-addressed raw files.
Unexpected failure after reservation must be reconciled, never automatically retried.

## Checks and next handoff

Run `python -m pytest tests/rule_study -q`, repository validators, complete offline tests,
Ruff lint/format and compile checks. Exact PR checks and merged-main checks are the
publication evidence; synthetic unit-test success does not establish generalization.

Nisha (#241): independently review the merged implementation and reconstruct bindings
from supplied artifacts before accepting a frozen-system verification result. Edison
(#242): receive the actual case and accounting artifacts and compare against the separate
accounting implementation. Matty (#244): prepare the exact freeze and bounded authorization
only after the required receiving evidence exists. No final-seed generation, new scientific
batch, private/source access, model call or automatic dispatch is authorized by merging.
