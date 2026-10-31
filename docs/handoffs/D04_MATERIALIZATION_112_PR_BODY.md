## Summary

Implements deterministic materialization for all 40 development episodes in the
accepted `d04-development-20261028-v1` allocation. **PARTIAL / BLOCKED for end-to-end
P04/O02 readiness**; this is a bounded materialization deliverable for review.

## Completed

- 40 validated F02 PrivateEpisodes, with 40 canonical content hashes and 40
  serialized-file hashes bound to the original allocation hashes.
- Preserved episode IDs, dates, scenarios, seeds, source windows and 16/12/12 folds.
- Byte-identical independent regeneration and full 30-slot S01 replay for all 40.
- Separate checksum-only receipts; historical #102 manifest stays unchanged.
- Portable reproduction instructions, source provenance and restricted custody.

Private source-derived episode files and the pinned CSV stay outside Git. This
public PR contains only code, diagnostic tests, permitted checksums and documentation.
An authorized recipient must acquire the exact pinned input privately, validate
its checksum and regenerate; the materializer/verifier never silently download.
Checksums are not signatures, scientific certification or redistribution permission.

## Validation

- Focused D03/D04/F02/S01/P03/O02: **846 passed, 19 subtests passed**, including
  17 new materialization fault/integration tests.
- Full offline suite: **1,641 passed, 1 failed, 19 subtests passed**.
- Ruff lint/format, setup/documentation, compilation, dependency consistency/smoke,
  deterministic regeneration and Git whitespace checks passed locally.
- Hosted CI results remain independently visible in the Checks tab; a local pass
  is not a hosted pass. A failing required check blocks merge.

### Independently reproduced existing EP-HAND1 failure

`tests/agent/test_a02_authorization_preparation.py::test_episode_and_all_renderers_are_frozen_without_inventing_bounds`
fails at line 40 on both this branch and an **unmodified current-main worktree**,
base `8f797f18a678293b66b6916718747285157d7208`:

- Expected frozen bundle SHA-256:
  `c7f05743bbb3055f8ae15b0f18f2548bdd57bb7fbff0e05eef4ae3b1eb529db3`
- Actual committed bundle SHA-256:
  `8bef36ace7bc4a3cf2debdce81c75edd87e175b20592a520a5449ec1fb0cddd6`

Reproduce with:
`python -m pytest tests/agent/test_a02_authorization_preparation.py::test_episode_and_all_renderers_are_frozen_without_inventing_bounds -q`.
PR #129's freeze-record commit `f7d004e` records the expected hash; the bundle from
`1f3c732` already has the actual hash and is unchanged on current main. #112 changes
none of those files. A read-only experiment shows the expected hash is exactly
the **CRLF** encoding of the committed **LF** bundle. Hosted CI runs on Windows,
so its result may differ from this macOS baseline; no cross-platform frozen-byte
claim is made. No frozen input/checksum was rewritten and no test weakened.

## Remaining blocker

P03 collected **120 decisions and zero candidate feature rows**. An agreed
source-derived forecast issuance/visibility path is still required before usable
O02 labels and P04 training. O02 accepted bounded samples but produced no training
labels; its no-forecast `certified_infeasible` result is preserved as a consumer
limitation, not claimed physical infeasibility. Diagnostic synthetic-forecast tests
prove interfaces/unknown-label handling only and do not establish actual readiness.

Smallest remaining decision for Reimo/Edison/Ved, with Nisha's visibility/custody
verification: a concrete authorized D01-derived perfect-foresight release adapter
or input specifying simulated issue times, trusted decision UTC, 24-slot visibility
clipped to 0–29 and agreed Q04 freshness/required coverage. No new issuance rule is
invented here; existing Q04 rules and accepted allocation remain unchanged.

## Scientific and custody limitations

- No held-out study episode generation or evaluator-only artifact publication.
- No development reallocation, P04 training, paid/model calls or scientific run.
- Private source-derived content retained in authorized local custody; no transfer
  or redistribution is authorized by this public receipt.
- Q05 source acceptance, data rights, physical interval meaning and Q06 scientific
  freeze/held-out union isolation remain unresolved.
- Ready for bounded materialization review; **not ready to merge while required
  CI fails**, and not an end-to-end P04/O02 handoff.

Full evidence and authorized recipient steps:
[`docs/handoffs/D04_DEVELOPMENT_MATERIALIZATION_112.md`](https://github.com/ReymoT/data-center-agentic/blob/reimo/d04-materialization-112/docs/handoffs/D04_DEVELOPMENT_MATERIALIZATION_112.md).

Related: #112, #102, #60. No issue closure requested.
