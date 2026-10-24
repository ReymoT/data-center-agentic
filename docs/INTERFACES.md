# Shared interface and handoff blueprint

Current implementation receiving note, Matty: [actual A03/A04/A02 APIs and remaining adoption](handoffs/OCT24_IMPLEMENTATION_AND_RECEIVING.md). Existing F02 1.0.0 records/specification are unchanged. Several formerly planned modules below now exist; their handoffs define actual entry points and receiving limits. This pointer does not claim all consumers have adopted them or replace the sole F02 contract. Earlier dated planning/adoption inventories below are historical where superseded.

- **Contract version:** 1.0.0
- **Document version:** 1.1 — 2026-10-12
- **Contract owner:** Ved
- **Status:** F02 schemas are implemented and unit-tested; **consumer adoption is pending**.

This document is the sole maintained interface contract. Records in `dc_sustainability/schemas.py` are strict, versioned boundaries for implementation. Function names and paths outside the implemented F02 code remain proposals until the relevant modules exist. Shared data-format or settings changes require affected teammates' agreement, recorded in the relevant Issue or decision record. Teammate PR review is optional; agreement and consumer validation are not implied by a merge.

## 1. Ownership and proposed locations

| Location | Primary owner | Purpose |
|---|---|---|
| `dc_sustainability/schemas.py` | Ved | Versioned shared records, validation, serialization, canonical hashes |
| `dc_sustainability/config.py`, `configs/` | Matty | Settings loader and composed configuration |
| `dc_sustainability/data/`, `dc_sustainability/simulator/` | Reimo | Source adapters, episode generation, split/visibility rules, simulator state transitions |
| `dc_sustainability/knowledge/`, `ontology/` | Ved | RDF graph construction, SHACL validation, controlled queries, flat projection |
| `dc_sustainability/reference/` | Ved | Offline solver, label cache and evaluation bounds |
| `dc_sustainability/metrics/impact.py` | Edison | Physical impact calculations |
| `dc_sustainability/policies/greedy.py`, `policies/learned.py`, `dc_sustainability/training/` | Edison | Policies A/B, models C/D and training |
| `dc_sustainability/llm/provider.py`, `dc_sustainability/agent/`, `dc_sustainability/verification/`, `dc_sustainability/runtime/` | Matty | Provider, LangGraph, production checks, execution gate, trace writer |
| `dc_sustainability/llm/plain.py`, `dc_sustainability/explanations/`, `prompts/` | Nisha | Plain-LLM path, explanation contracts/templates; Matty reviews agent prompts |
| `dc_sustainability/evaluation/`, `dc_sustainability/experiments/`, `dc_sustainability/cli.py` | Nisha | Independent validator, metrics, runner, analysis and command routing |
| `tests/<module>/` | Corresponding module owner | Unit and contract tests; Matty owns `tests/e2e/`, Nisha owns `tests/evaluation/` |
| `data/` | Reimo | Permitted fixtures, manifests and acquisition instructions; private data stays separate |
| `models/` | Edison | Versioned model manifests and permitted trained artifacts |
| `results/` | Nisha | Run/evaluation manifests and permitted outputs; Matty owns runtime record format |
| `.github/`, environment files, `README.md`, `docs/ARCHITECTURE.md`, `docs/team/` | Matty | Repository foundation and shared-instruction maintenance |

Nisha integrates CLI operations by calling each owner's module; she does not duplicate their implementations. Planned CLI operations cover data validation/generation, graph validation, label generation, training, one episode, matrix runs, scoring and figures. Their exact names are agreed during implementation; they are not available commands until implemented.

## 2. Core records

- **`Job`**: stable ID, arrival slot, integer positive duration, constant IT kW, completion deadline and flexibility. Scenario, split, seed and synthetic-generator metadata stay in a private fixture manifest. An impossible deadline is structurally valid so downstream code can report infeasibility.
- **`SiteConfig` / `Constraint` / `ConstraintSnapshot`**: site identity, background load, PUE, slot length, stable constraint IDs, typed limits, applicability and source references. Site capacity is represented only by a capacity `Constraint`; `SiteConfig` deliberately has no second capacity field. `ConstraintSnapshot.capacity_kw` raises `MissingEvidenceError` when capacity evidence is absent; missing capacity never means unlimited capacity.
- **`SourceRef`**: source identity/path, optional commit and checksum, and an explicit redistribution status (`unresolved`, `permitted`, or `restricted`). Every constraint source ID must resolve within the snapshot's `sources`. Policy-visible context includes the source records referenced by visible constraints and forecasts; unresolved source references cause an error.
- **`CarbonObservation` / `CarbonForecast`**: separate types with required `fact_kind`. Observations carry `observed_at_utc` and are private. Forecasts carry a `valid_slot`, simulated `issued_at_utc`, and `forecast_kind`; observation time is never re-used as issue time. Carbon values use the dimensional unit `g/kWh`; pollutant and model meaning remain separate metadata.
- **`CarbonSemantics`**: explicit pollutant basis, interval convention, emissions-factor type and slot-mapping status. Q05 values may remain `unresolved`; a mapping cannot be marked `agreed` while its interval convention is unresolved. The schema does not select an interval convention or establish redistribution rights.
- **`VisibleState`**: episode-safe ID, current slot, state version, arrived waiting jobs, running/completed views, missed IDs, visible forecast facts, explicit missing-forecast slots, and visible constraint IDs. Private scenario/split/seed labels, realized carbon, future arrivals and solver/reference outputs are not state fields.
- **`Context`**: same information and stable evidence IDs in graph or flat presentation, plus a representation-independent `content_hash`. Source references are included so `source_id` can be resolved to provenance.
- **`Plan` / `ApprovedActions`**: proposal and checked current-slot action payloads. Plans may include future intentions; only starts for the plan's current decision slot are eligible to become `ApprovedActions`. `ApprovedActions.from_checked_plan` is a contract helper, not the production runtime gate.
- **`PolicyOutput`, `Explanation`, `Claim`**: common policy envelope and source-linked explanatory claims. A plan is required only when `output_status="ok"`.
- **`CheckResult`**: plan hash, episode/slot/state version, performed/skipped checks, violations, evidence availability and a feasibility status distinct from impact-claim support. A passing result requires the core `schema`, `ids`, `timing`, `deadline`, `nonflexible`, and `capacity` checks all to be recorded as performed and passing; capacity evidence must identify the constraint it checked. A failing result must include a violation and at least one failed performed check, and cannot label a check error as a simple failure. Impact-claim support remains separate from physical schedule feasibility.
- **`DecisionRecord`**: initial/repaired/fallback stages and their checks remain distinct. A missing check is unperformed, never an implicit pass. Each initial/repaired/fallback plan must belong to the decision record’s episode and slot. An `executed` step requires a passing execution check associated with a recorded plan and the same episode/slot/plan hash. The execution recheck's state version may be newer than the proposal's origin version; `ApprovedActions.from_checked_plan` binds the action to the checked latest version, which the runtime must compare atomically with the live state before applying. A successfully executed no-op can have zero starts only when the checked plan has no current-slot starts; `executed_starts` must exactly match the checked plan’s current starts.
- **`SolverResult`**: offline-only visible/hindsight solver output with `certified_optimal`, `certified_infeasible`, `unresolved`, or `insufficient_evidence`. Timeouts and unknown results do not prove feasibility, infeasibility or optimality.
- **`EpisodeResult`**: slot-level values, totals, completed work, deadline misses, unfinished jobs and reference/trace references. Physical totals are populated by the simulator/impact modules rather than recalculated by the schema layer.
- **`PrivateEpisode` / `PrivateJob`**: private fixture manifests used by `reset`, including scenario/split/seed, realized carbon and reference references. They are not accepted as policy-visible state records.

### 2.1 Versioning, validation and serialization

Every top-level exchanged record has `record_type` and `schema_version` (`MAJOR.MINOR.PATCH`). Direct Python construction can use the current-version default; **external deserialization requires both envelope fields**. Readers accept the same major version when the supplied minor/patch is not newer than their supported version. Unknown record types, incompatible/newer versions and unknown fields are rejected. Nested value records (for example `PlannedStart`, `Violation` and `Claim`) are versioned by their parent envelope rather than carrying separate envelopes.

Records are immutable and strict: Boolean values are not integers, fractional slots are invalid, non-finite numeric values are rejected, and timestamps must be UTC-aware (`Z` or `+00:00`). Identifiers use the patterns defined in `schemas.py`. `parse_record(data)` dispatches top-level records by type.

`to_json()` emits compact JSON with sorted object keys. `canonical_hash()` applies declared set-like collection normalization recursively (including nested `Constraint.applies_to_jobs`, solver schedules and per-slot job-ID collections) before SHA-256; genuinely ordered sequences such as the episode's slot timeline retain their order. Fields that intentionally do not identify the content, such as `Plan.status`, are excluded only where documented by the corresponding record. The JSON representation itself preserves each collection's supplied order.

Structural validity is not schedule feasibility. Start/deadline relationships, unknown job IDs and backdated plan starts remain representable so the checker can report violations. Contradictory duplicate representations of visible job facts and constraints are rejected when building context.

### 2.2 Policy visibility and constraint projection

The full `ConstraintSnapshot` is the authoritative source for the simulator, checker, policies, solver and evaluator; policy inputs receive only a visibility-safe projection of it. `visible_constraints_for(state, snapshot)` projects:

1. all site-wide constraints for the state's site; and
2. job-specific constraints only when every job named by the constraint is already visible in the state (waiting, running, completed or explicitly missed).

This conservative rule avoids leaking a not-yet-arrived job through an ID such as `CON-DL-J3` or through an `applies_to_jobs` list. Use `VisibleState.from_snapshot(snapshot, ...)` when a producer creates a policy-visible state; it derives the constraint IDs from the full snapshot and visible jobs rather than copying the full constraint list. A `VisibleState.constraint_ids` tuple must match the projected constraint IDs, and `Context.build` checks this against the authoritative snapshot. Because a standalone state stores IDs rather than the corresponding `Constraint` records, its JSON cannot independently prove that projection; the runtime must construct it with `from_snapshot` and validate the context against the authoritative snapshot before passing state/context to a policy. Visible carbon and missing-forecast slots must be current/future slots within the 24-slot view and the episode's 0–29 slot range; past observations are not policy forecasts. Running views must still occupy the current slot under half-open intervals, and completed views must have a positive interval ending no later than the current slot. The complete snapshot stays available to trusted simulator/checker components.

When a visible `Job` and a corresponding constraint both provide the same fact, the values must agree: arrival constraints match `arrival_slot`, deadline constraints match `deadline_slot`, and a nonflexible constraint refers to a nonflexible job and its arrival slot. Redundant constraints are not required where none was supplied; absence must not be interpreted as an alternative value. Completed/missed job views do not carry enough `Job` fields for this cross-check, so the runtime/checker remains responsible for validating the full state transition.

### 2.3 Carbon and source semantics

The SustainDC AZPS `avg_CI` numerical unit is dimensionally `g/kWh`, but pollutant/model scope and the precise hour-start/hour-end convention remain unresolved in D01 evidence. The schema carries those details as explicit unresolved/provisional metadata rather than relabeling the values or shifting timestamps. A forecast issue time is separately supplied simulated metadata; freshness is evaluated by the runtime using the freshness constraint and an agreed Q04 rule.

Visible forecast facts must resolve their `source_id` to a `SourceRef` in the supplied snapshot. Context contains only source records relevant to visible constraints and forecast facts. The schema does not prove dataset-specific redistribution permissions; a source can remain `redistribution_status="unresolved"`.

## 3. Main interfaces and authority

These callable interfaces are proposed boundaries, not all implemented code.

| Interface | Producer/owner | Consumer and invariant |
|---|---|---|
| `reset(private_episode)`, `state()`, `step(approved_current_actions)` | Reimo | Runtime obtains only visible state; clock advances exactly once per slot even after rejection |
| `get_context(visible_state, constraint_snapshot)` | Ved | Controlled graph/flat retrieval preserves visible records, identifiers, units and provenance |
| `propose(visible_state, context) -> PolicyOutput` | Edison / Matty / Nisha | Common runner; policies do not mutate the simulator |
| `calculate_impact(schedule, carbon, site) -> CalculationRecord` | Edison | Shared physical calculation; unsupported comparisons are refused |
| `check_schedule(plan, visible_state, constraints) -> CheckResult` | Matty | Every system uses the same checker; no policy bypass or hidden reference answers |
| `execute_step(plan, check, expected_state_version)` | Matty | Latest-state recheck; execute only eligible current starts via the simulator |
| `write_trace(decision_record)` | Matty | Durable, typed runtime evidence with stable IDs |
| `solve_visible(snapshot)` / `solve_hindsight(private_episode)` | Ved | Offline labeling/evaluation only; certification, status, gaps and limits recorded |
| `validate_reference(plan, fixture_view)` | Nisha | Independent evaluator does not treat the production checker's verdict as truth |

The runner owns the episode loop and advances the runtime exactly once per slot. The LangGraph controller orchestrates proposal/repair/fallback and asks for gated execution; explanation generation cannot alter the approved action. The plain-LLM system receives equivalent flat facts in one call, without corrective feedback or fallback. Invalid actions are blocked and missed work remains recorded.

Label generation is offline. Edison specifies candidate features/rollout policy; Ved supplies certified selections keyed by state hash, job ID and candidate start; Reimo supplies immutable development episodes/fold groups. Held-out labels may be requested by Nisha for offline evaluation, but never enter policy-time state/context.

## 4. Handoff sequence

1. **F01/F02:** Matty supplies the repository skeleton; Ved implements schema examples; consumers exercise them. Skeleton work and interface drafting can proceed in parallel.
2. **D03/S01/P01/P02/A03:** Reimo supplies a small development episode; Edison adds impact math and greedy A; Matty implements checks; Nisha begins independent validation. Do not wait for the full source download before writing contract tests.
3. **K01/K02/O01:** Ved builds the ontology and offline solver on the agreed records. Reimo and Nisha verify visibility and information equivalence. K03's graph-to-checker capacity test waits for A03, but graph development does not.
4. **D04/P03/O02/P04:** Splits and candidate contracts precede labels; labels precede model training. O02 depends on P03 (features/rollout specification), not P04 (trained model).
5. **A01/A02/L01/L02/A04:** Provider and context boundaries precede LLM integration; use mocks initially, then a real development episode.
6. **E02/E03/I01:** Nisha wires systems into one runner; Matty tests the integrated development pipeline. Offline oracle results are available only to evaluation.
7. **Freeze/I02:** Run held-out experiments; then produce held-out references, ML metrics, statistics and claim review. I03/I04 acceptance verifies clean-checkout reproduction. Training/evaluation pipeline implementation and final result production are separate tasks.

Dependencies express artifact readiness, not permission to expose held-out data early. Train/test separation is both a loader boundary and a team rule.

## 5. Open decisions remain open

F02 does not decide:

- **Q01:** whether new jobs can start during completion slots.
- **Q02/Q03:** plan coverage, partial plans, infeasibility/abstention semantics and the completed-work unit.
- **Q04:** forecast issue-time generation, staleness, partial coverage and fallback behavior.
- **Q05:** pollutant/model scope, physical interval convention and dataset-specific redistribution rights.
- **Q08:** solver backend, tolerance, tie-breaking and certification rules.

The records encode the relevant distinctions and permit honest unresolved states. Do not insert temporary defaults that become hidden experimental assumptions.

## 6. Examples and validation commands

Examples in `tests/contracts/examples/` are generated from `tests/contracts/fixtures.py`. They use the proposal's seven-slot hand-check values (500, 450, 300, 250, 400, 480, 520 g/kWh) and the J1/J2/J3 scheduling fixture. They are synthetic examples, not SustainDC data. Commit all generated JSON examples; pytest reads those files directly and does not read an external `.tgz` archive.

Regenerate examples and run the contract tests from the repository root:

```sh
python -m tests.contracts.fixtures
python -m pytest tests/contracts -q
python -m pytest tests/data -q
```

Use `.venv\Scripts\python.exe` instead of `python` on the proposed Windows environment. The repository's full setup, Ruff checks, and other suites must be run on the project's supported Python/dependency environment before PR acceptance; an isolated contract pass is not full-repository acceptance.

## 7. Adoption checklist and status

**Implemented in F02:** strict top-level records, validation, serialization/version envelopes, canonical hashes, private/visible types, constraint projection for policy context, source provenance, shared hand fixtures, regression tests and this contract documentation.

**Still planned:** simulator functions, RDF graph, SHACL shapes/SPARQL retrieval, production `check_schedule` and `execute_step`, solver, impact calculations, policies, agent, experiment runner and CLI.

**Not yet adopted:** each consumer must record validation against the examples and interfaces. Reimo should verify E1 state/action compatibility and D06 carbon-window reproduction; Edison checks policy/impact input compatibility; Matty checks checker/runtime/gate contracts; Nisha checks independent evaluation and context equivalence. The schema is not considered adopted merely because this PR merges.
