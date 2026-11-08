# CF60-v1 broker implementation for independent review

Reimo, Issue #60. Reviewed latest fetched main
`74383b7ae25391e0e9db2f3fb7fe52572efae2b3`, instruction 1.28, F02 1.0.0.
Local branch: `reimo/issue60-cf60-production-broker`. Reimo explicitly authorized
commit, push and draft PR publication in the follow-up request. Merge and comments
remain outside that authorization.
Reviewed #60 through comment 6675313998, merged PR #168, the conditional
[proposal](ISSUE60_CAUSAL_STUDY_FORECAST_PROPOSAL.md), and the
[compatibility plan](CF60_DEVELOPMENT_COMPATIBILITY_PLAN.md).
Edison's parameter acceptance 6673065635 is received; current C/D artifacts remain
legacy-forecast artifacts. This implementation is opt-in, not scientific adoption.

## Implementation boundary

- `dc_sustainability/data/cf60_acquisition.py`: privileged pinned CSV checksum and
  structural validation using the existing D01 loader. **This reads/parses the full
  CSV.** It is not restricted source access. It copies only the three candidate
  rows into a new capability and discards its full-array reference on return.
- `dc_sustainability/data/cf60_broker.py`: version `CF60-v1`, implementation
  `cf60-restricted-broker-v1`. The broker accepts exactly `RestrictedHistory`, not
  a full array, mapping, subclass or unrestricted loader. Each capability contains
  only an immutable copy of present authorized candidate rows, an immutable
  timestamp allowlist and immutable issue/source/authorization metadata. There is
  no backing-store, CSV path, enumeration or loader API. `read` logs before checking
  the allowlist, rejects every other key, and records successful versus missing
  reads separately. Out-of-year candidate attempts return missing without consulting
  any store. Extra supplied rows, duplicate rows and malformed/nonfinite/negative
  evidence fail. No wrap, interpolation or history expansion exists.
- `dc_sustainability/data/cf60_receiving.py`: separately derived interval arithmetic,
  active access probes and development-only metadata footprints. No source loader,
  solver, held-out selector or model is called. This is receiving preparation;
  Nisha's own run/review and signed findings remain outstanding.
- `tests/data/test_cf60_broker.py`: synthetic production-boundary and fault tests.

The clock is supplied by the trusted runner. For each slot 0..29 it must mint a
fresh capability and call `issue_forecast(history, anchor=anchor, slot=slot,
trusted_issue=anchor + slot*H)`, then publish atomically at that time. Capability
clock and runner clock must match. Reuse of a read capability is rejected.
The broker always attempts exactly the three completion ages 2/3/4 hours; start
labels subtract one further hour, end labels do not. With lag one hour all are
strictly pre-issue available under the conditional simulation assumption.
All present candidates are read; latest timestamp wins regardless of magnitude.
All missing means an empty forecast tuple and explicit visible missing slots.
Each hour is independent; later history cannot backfill a prior issue.

Only current `[t,min(t+24,30))` F02 persistence forecasts return. Latent lead 24+
values are never exposed or serialized. Values do not depend on valid-slot time,
so remaining-horizon persistence does not cause a future read. No realized scoring
carbon, jobs, outcomes, model or oracle enters this interface. F02 semantics stay
unresolved/provisional even when a conditional interpretation is specified.
The caller resolves the source in its existing snapshot and passes `forecasts`
and `missing_slots` to its existing VisibleState construction. Q04 freshness,
coverage of occupied slots, decision-wide checked A and P05/E02 fallback remain
unchanged. This adds no runner default and makes no C/D compatibility claim.

This is an enforceable library capability against accidental or unauthorized
API reads. Python name privacy is **not** protection against arbitrary hostile
code executing under the same principal: introspection, monkeypatching and process
memory inspection require a separate process/OS principal boundary. Do not pass
privileged acquisition credentials, full arrays or private actuals into a policy
process. Deployment OS/custody access controls still need Nisha's verification.

## Pin and receipts

`code_hash()` hashes canonical LF broker source. `bundle_hashes()` also pins
acquisition, receiving, D01 source validation and F02 schema source. Every success
returns an immutable JSON receipt with versions, these code hashes, source identity,
authorization locator, clock/slot, conditional interpretation, all attempts and
statuses, selected timestamp, footprint hash, forecast canonical hashes and missing
slots. No source values appear in receipts. `footprint()` returns copied events
also after a rejected call; retain that failure evidence rather than reusing the
capability. No successful receipt is produced for invalid evidence.

Authorization locators link evidence; nonempty strings and checksums do not
establish human permission. Authenticate authorization separately before real
acquisition. Keep real receipts and source-derived forecasts in approved private
storage. Source IDs/timestamps in real footprints may themselves be restricted.

Exact machine-readable producer evidence is in
[the validation receipt](../evidence/cf60-production-validation.json) and
[synthetic receiving output](../evidence/cf60-synthetic-receiving.json).
These bind working-file hashes to the base SHA; the exact code commit is recorded in the draft PR description after committing
(to avoid a self-referential commit hash). Neither file is Nisha's acceptance.

## Safe commands and expected evidence

Run from the repository root in the existing Python 3.12 core environment.
Use the existing core environment interpreter for `python` below. No requirements
or locks were changed, installed or certified for another platform.

```sh
python -m pytest tests/data/test_cf60_broker.py -q
python -m pytest tests/data/test_cf60_broker.py tests/data/test_issue60_causal_forecast_proof.py tests/data/test_forecast_isolation.py tests/data/test_held_out_custody.py tests/training/test_features.py tests/reference/test_labels.py tests/policies/test_learned.py tests/experiments/test_runner.py -q
python -m dc_sustainability.data.cf60_receiving > cf60-nisha-receiving.json
python -m pytest tests -q --tb=short
python -m ruff check dc_sustainability scripts tests
python -m ruff format --check dc_sustainability scripts tests
python scripts/validate_setup.py
python -m compileall -q dc_sustainability scripts tests
python -m pip check
python scripts/smoke_dependencies.py
git diff --check
git status --short
git rev-parse HEAD origin/main
```

The receiving JSON must show 60 issue/hypothesis checks: three actual accessible
rows and 8,757 denied reads per issue, probing all 8,760 year keys (525,600 probes).
A malicious accessor that returns values on denied keys must fail receiving even
if it writes a plausible log. Tests inject that fault. Distinguishable synthetic
values establish the selected row and returned values. Both interval hypotheses,
all slots, missing candidates, year boundaries, no backfill, duplicate/invalid
inputs, deterministic receipts and F02/context/Q04 boundaries are tested.
Existing proof/consumer tests retain latent lead-29 and fallback evidence.
Dependency smoke checks use only tiny synthetic solves/classifiers/mock graphs;
they are not source-dependent compatibility jobs or C/D retraining.

## Nisha's separate receiving procedure

Receiving checklist addressed to @nkolekar-nk; producer runs do not satisfy your
independent receiving requirement.

1. Authenticate the reviewed working-file bundle (eventually the exact authorized
   commit) and independently recompute LF SHA-256 hashes. Verify source identity
   metadata and the scope of any input authorization without opening real values.
2. Inspect acquisition separately from broker operation: full parsing is privileged.
   Confirm only filtered copied candidate rows cross the boundary and no full-store
   reference or callback survives in the capability. Test the production interface
   in your own process with synthetic values and the commands above.
3. Review/reimplement the eligibility equations independently. Inspect every
   accessible return value and every denial, not merely receipt row names. Change
   forbidden rows and values, inject unauthorized-read behavior, and confirm failure.
   Compare `checks_sha256` and `development_metadata_sha256` with the supplied
   producer evidence, retaining your own unmodified output and environment record.
4. The harness reads only the pinned public forty-record development allocation.
   Its metadata report includes original recorded scoring indices, legacy preceding
   row dependencies, conditional physical start/end scoring indices and exact
   32-row CF60 start/end unions across all thirty issues, plus their reserved union.
   Independently audit the legacy adapter's original recorded mapping; its full-CSV
   loader access remains separate from its preceding-row value dependencies.
   Reserve all forty episodes, not just one fold/scenario or selected candidates.
   Original allocation/fold/content receipts and binaries must compare unchanged.
5. Do not instantiate a nonce, rank held-out candidates or call custody preparation.
   The existing selector is still `sha256-rank-greedy-fixed-development-v1`, which
   does not implement the forecast-history amendment. A separately agreed, merged
   and pinned metadata-only selector amendment must precede any actual selection.
   It must cover scoring/scoring, both scoring/history directions and history/history
   related groups for recorded mapping and both conditional hypotheses, reserving
   legacy plus CF60 development footprints. Failures block acceptance, never cause
   silent fold changes or outcome-driven retries.
6. Record your own PASS/FAIL, code and evidence hashes, actual accessible rows,
   environment, scope and limitations. Receiving this implementation is distinct
   from real-source access/custody receiving and scientific compatibility acceptance.

## Remaining authorization and blockers

No implementation blocker remains for this conditional library handoff. Reimo
authorized commit, push and a draft PR; no merge or Issue/PR comments are authorized.
Nisha's independent receiving has not occurred. Real-source acquisition/comparison requires a separately
recorded bounded development-only authorization with paths, allowed privileged
reads and broker rows, private outputs, solver limits if applicable and stop rules.
No such authorization is inferred here; no real source was opened by this work.

The versioned custody eligibility amendment, actual custody/principal access tests,
source B1–B3, provisional B4, Ved O02/Q08 and Edison C/D compatibility findings,
affected-owner acceptance and scientific freeze remain open. No originals, forty
episode hashes, model artifacts, labels, contracts or shared instructions changed.
No held-out selection/access, external model/API calls or source-dependent solver
comparison was performed.

## Publication audit

Fetched main remains `74383b7ae25391e0e9db2f3fb7fe52572efae2b3`; no
reconciliation or instruction changes were required. GitHub and local Git identity
were verified as Reimo. The complete original eight-file draft was backed up
outside the repository before review edits. The audit fixed deletion/reassignment
of capability metadata and rejected arbitrary/subclass source objects that could
carry privileged handles; only the plain F02 SourceRef metadata type is accepted.
Two regression tests cover these boundary defects. The implementation identifier
is unchanged because this was an unpublished correction; the new source hash
supersedes the originally reported hash for publication. Both are retained in
the validation receipt, with historical and publication runs separated.

The public-file audit found only synthetic values and already-public development
metadata. No source-derived observations, held-out information, credentials or
confidential custody paths are included. Temporary host environment paths were
removed from the public handoff. Python/library checks, privileged full-source
ingestion, OS custody and Nisha's independent receiving remain distinct.

Publication validation: 18 broker tests passed (1.54s), 155 focused tests passed
(9.63s), and the full offline suite passed 2,102 tests plus 19 subtests (42.08s).
All 525,600 receiving probes passed. Ruff lint/format (224 files), compilation,
dependency consistency and synthetic smoke checks passed. Setup/link validation
and Git preservation/whitespace checks are part of the final pre-commit audit.
The independently calculated publication broker SHA-256 is
`832e6cfe27a41e457e0775ca825b6ec8debea3b2c6d34d5dfb5310d330b5ce56`.
