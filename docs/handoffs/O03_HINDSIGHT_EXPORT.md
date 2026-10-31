# Task handoff

Task ID / Issue: O03 offline hindsight reference generation/export infrastructure
Human owner / technical contacts if needed: Ved
Active assistant session / instruction version: ved/o03-hindsight-export worktree, F02 schema 1.0.0
Objective:
  Implement offline hindsight reference generation and export for the F02
  offline-only reference track. Hindsight uses the full private episode
  (realized carbon, true job arrivals, actual durations) to compute the
  best achievable schedule with perfect foresight. The artifact is sealed,
  hashed, marked `offline_only=True`, and exported outside any Git checkout.
  Online policy consumers (O02 labels, plain LLM policy) reject hindsight
  artifacts and any result that claims future arrivals.

Base commit / branch / PR:
  Branch: ved/o03-hindsight-export
  Worktree: /home/vpatil14/src/data-center-agentic-o03
  Parent worktree: /home/vpatil14/src/data-center-agentic

Changed paths:
  dc_sustainability/reference/hindsight.py        (new)
  dc_sustainability/reference/labels.py           (modified)
  dc_sustainability/llm/plain.py                  (modified)
  tests/reference/test_hindsight.py               (new)
  docs/handoffs/O03_HINDSIGHT_EXPORT.md           (this file)

Input and output contract/config versions:
  F02 schema version: 1.0.0
  Hindsight solver version: o03-v1
  Solver backend: scipy.optimize.milp (same backend as O01 visible solver)
  Artifact envelope: HindsightReferenceArtifact with provenance hashes
    - source_snapshot_hash: SHA256 of the visible snapshot used as context
    - realized_carbon_hash: SHA256 of the realized carbon series
    - solver_config_hash: SHA256 of solver configuration
  Output files:
    - {artifact_id}.hindsight.json      (artifact envelope + SolverResult)
    - {artifact_id}.hindsight.manifest.json

Artifact locations and checksums:
  Artifacts are written to a caller-supplied directory by
  export_hindsight_reference(...). No committed artifacts are produced by
  tests; tests use a temporary directory and clean up.

Exact reproduction commands:
  # Run O03 tests
  cd /home/vpatil14/src/data-center-agentic-o03
  /home/vpatil14/src/data-center-agentic/.venv/bin/python -m pytest \
      tests/reference/test_hindsight.py tests/reference/test_labels.py \
      tests/reference/test_solver.py -q

  # Lint/format checks
  /home/vpatil14/src/data-center-agentic/.venv/bin/python -m ruff check \
      dc_sustainability/reference/hindsight.py \
      dc_sustainability/reference/labels.py \
      dc_sustainability/llm/plain.py \
      tests/reference/test_hindsight.py
  /home/vpatil14/src/data-center-agentic/.venv/bin/python -m ruff format --check \
      dc_sustainability/reference/hindsight.py \
      dc_sustainability/reference/labels.py \
      dc_sustainability/llm/plain.py \
      tests/reference/test_hindsight.py

Tests actually run and observed results:
  tests/reference/test_hindsight.py: 13 passed
  tests/reference/test_labels.py: 7 passed
  tests/reference/test_solver.py: 6 passed
  Combined reference tests: 25 passed
  Full suite: 1637 passed, 1 failed (pre-existing A02 manifest hash mismatch
    in docs/evidence/a02-episode-authorization-preparation-2026-10-30.json,
    unrelated to O03).

Limitations and open decisions:
  - Hindsight solver currently assumes a single site and single power/carbon
    dimension. Multi-site episodes will raise HindsightError.
  - The `complete` flag is true when every job that has at least one feasible
    window in the realized horizon is scheduled; jobs that are infeasible by
    deadline or capacity are excluded from completeness.
  - Export rejects any directory that contains a `.git` entry to prevent
    accidental commit of hindsight artifacts.
  - File permissions are set to 0o600; group/other read is denied.
  - No CLI or batch pipeline is included; this handoff covers the library
    primitives only.

Receiving owner and consumer check:
  - O02 label generation (dc_sustainability/reference/labels.py) now rejects
    hindsight contexts and SolverResult records with kind="hindsight" or
    uses_future_arrivals=True.
  - Plain LLM policy (dc_sustainability/llm/plain.py) now rejects hindsight
    contexts before proposing a decision.
  - Future online policies should call reject_hindsight_in_context(context)
    on any Context-like input before using it for training or inference.

Next checkpoint:
  Merge ved/o03-hindsight-export after the pre-existing A02 manifest hash
  mismatch is resolved or acknowledged as out-of-scope. Update the Issue with
  the resulting merge SHA and acceptance.

Record the resulting merge SHA and acceptance in the Issue after merge. Do not fabricate review, test or merge evidence.
