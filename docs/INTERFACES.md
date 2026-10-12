# Shared interface and handoff blueprint

Version 1.0 — 2026-10-10. Contract owner: Ved. Producers and consumers coordinate and validate interfaces during implementation. Shared data-format or settings changes require the affected teammates' agreement first, recorded in the Issue or decision record; teammate PR review is optional. These are proposed API names and paths, not existing code. This is the sole maintained draft contract. Adoption and schema versioning await F02 implementation and validation by Ved and consumers. Open decisions remain explicit configuration/validation barriers, not undocumented defaults.

## Proposed repository locations and owners

| Location | Primary owner | Purpose |
|---|---|---|
| `dc_sustainability/schemas.py` | Ved | Versioned strict shared records |
| `dc_sustainability/config.py`, `configs/` | Matty | Loader and composed settings; domain owner reviews their fields |
| `dc_sustainability/data/`, `dc_sustainability/simulator/` | Reimo | Adapters, generation, split/visibility rules, state transitions |
| `dc_sustainability/knowledge/`, `ontology/` | Ved | RDF construction, SHACL, controlled queries, flat projection |
| `dc_sustainability/reference/` | Ved | Offline solver, label cache and evaluation bounds |
| `dc_sustainability/metrics/impact.py` | Edison | Shared physical calculations |
| `dc_sustainability/policies/greedy.py`, `policies/learned.py`, `dc_sustainability/training/` | Edison | A/B, C/D and training |
| `dc_sustainability/llm/provider.py`, `dc_sustainability/agent/`, `dc_sustainability/verification/`, `dc_sustainability/runtime/` | Matty | Common model client, LangGraph, production checks, gate, trace writer |
| `dc_sustainability/llm/plain.py`, `dc_sustainability/explanations/`, `prompts/` | Nisha | Plain path and explanation contracts/templates; Matty reviews agent prompts |
| `dc_sustainability/evaluation/`, `dc_sustainability/experiments/`, `dc_sustainability/cli.py` | Nisha | Independent validator, metrics, runner, analysis and command routing |
| `tests/<module>/` | Corresponding module owner | Unit/contract tests; Matty owns `tests/e2e/`, Nisha `tests/evaluation/` |
| `data/` | Reimo | Permitted fixtures, manifests and acquisition instructions; private stores kept separate |
| `models/` | Edison | Versioned model manifests and permitted trained artifacts |
| `results/` | Nisha | Run/evaluation manifests and permitted outputs; Matty owns runtime record format |
| `.github/`, environment files, `README.md`, `docs/ARCHITECTURE.md`, `docs/team/` | Matty | Repository foundation and shared instruction maintenance |

Each CLI operation calls its owner's module; Nisha integrates commands, not duplicate implementations. Required commands cover data validation/generation, graph validation, label generation, training, one episode, matrix runs, scoring and figures. Exact spellings are agreed during F02; masters must not invent commands as already available.

## Core records

- `Job`: stable ID, arrival, integer duration, constant IT kW, completion deadline, flexible flag. Scenario/split/seed/synthetic metadata remain in a **private fixture manifest**, not in a policy's Job view.
- `SiteConfig` / `Constraint`: ID, IT capacity, background IT load, PUE, slot length, scheduling restrictions, source/version, applicability. One authoritative constraint snapshot feeds graph, policies, production checker, evaluator and solver.
- `CarbonFact`: fact ID, valid slot/UTC interval, value, explicit verified unit, simulated issue time, source/checksum. Private realized carbon and visible forecasts are separate records/stores. A timestamp field is not proof of freshness.
- `VisibleState`: episode-safe ID, current slot, state version, arrived waiting/running/completed job views, occupancy needed for planning and visible fact/constraint IDs. Never attach the complete private fixture or offline references to it.
- `Context`: same visible records and evidence IDs in graph-retrieved or flat serialized form; record a canonical content hash for information-equivalence checks. Presentation differs, available facts do not.
- `Plan`: schema version, originating state version, proposed starts, explicit deferrals/abstentions with reasons, evidence IDs and status. A future intention is not an executable commitment. Completeness and partial-infeasibility semantics await Q02/Q03.
- `CheckResult`: plan hash, state version, pass/fail/error, violation type, job/constraint IDs, performed checks and evidence availability. Distinguish schedule feasibility from unsupported impact claims; missing carbon does not automatically make A infeasible.
- `DecisionRecord`: system/run/episode/trial/slot IDs; input/config hashes; original raw response; initial/repaired/fallback plan and each check; final status; actual executed current starts; explanation/evidence; call/repair counts; timings/tokens/cost; errors. Missing stages are null/not applicable, not passing stages.
- `EpisodeResult`: all 30 slots, job/site/background totals, completed jobs/work, missed/unfinished jobs, references/statuses and trace locations. Units and denominators are explicit.

Strict schemas reject nonfinite quantities, Boolean/fractional slot values, duplicate IDs and unexpected action fields. Data validation must retain a structurally valid deliberately impossible deadline so the system can evaluate abstention.

## Functions and authority

| Interface | Producer | Consumer and invariant |
|---|---|---|
| `reset(private_episode)`, `state()`, `step(approved_current_actions)` | Reimo | Runtime obtains only visible state; clock advances once per slot even after rejection |
| `get_context(visible_state, constraint_snapshot)` | Ved | All systems; controlled retrieval preserves IDs/units/provenance and visibility |
| `propose(visible_state, context) -> PolicyOutput` | Edison / Matty / Nisha for their systems | Common runner; PolicyOutput wraps Plan, explanation/claims and raw response where applicable |
| `calculate_impact(schedule, carbon, site) -> CalculationRecord` | Edison | Simulator, tools, explanations; refuse unjustified comparisons |
| `check_schedule(plan, visible_state, constraints) -> CheckResult` | Matty | Every system; no policy bypass and no hidden reference answers |
| `execute_step(plan, check, expected_state_version)` | Matty | Controller only; recheck against latest state, execute only eligible current starts via simulator |
| `write_trace(decision_record)` | Matty | Runtime used by Nisha's runner; typed, durable records and stable IDs |
| `solve_visible(snapshot)` / `solve_hindsight(private_episode)` | Ved | Offline labeling/evaluation only; include certification/status/gap/limits |
| `validate_reference(plan, fixture_view)` | Nisha | Offline evaluator; independent implementation, no production-checker verdict as truth |

The runner owns the episode loop and asks the runtime to advance exactly once per slot. Policies propose; they do not mutate the simulator. LangGraph controls agent proposal/repair/fallback and requests gated execution through that common loop. Explanation generation cannot alter the approved action. Runtime recheck failures must produce a current-state decision record and checked fallback/abstention under the selected system's rules. The plain system never gets corrective feedback or fallback, even though unsafe actions are blocked.

Label generation is offline and separate from inference. Edison specifies candidates/features and rollout policy; Ved returns certified selections keyed by state hash, job ID and candidate start. Reimo supplies immutable development episodes and fold groups. Nisha may request held-out offline labels to score candidate predictions; these never reach the policy during execution.

## Handoff order without circular waiting

1. F01/F02: Matty supplies skeleton; Ved supplies small record examples; each consumer tests against these fixtures. Skeleton and interface drafting can proceed together.
2. D03/S01/P01/P02/A03: Reimo supplies a tiny development episode, Edison adds math/A, Matty adds checks, Nisha starts independent validation. Avoid waiting for the full data download to write tests.
3. K01/K02/O01: Ved uses those contracts for graph and offline solver. Reimo and Nisha verify visible information. K03's final graph-to-checker test waits for A03, but graph development does not.
4. D04/P03/O02/P04: splits and candidate contract precede labels; labels precede model training. O02 depends on P03 (feature/rollout specification), not P04 (trained model).
5. A01/A02/L01/L02/A04: common provider and contexts precede LLM integration; use mocks initially and a real development episode before acceptance.
6. E02/E03/I01: Nisha wires all policies into one runner, Matty tests the integrated development pipeline. Offline oracle results are added only to evaluation.
7. Freeze and I02: run held-out experiments. O04/P07/E06/E07 then produce held-out references, ML metrics, statistical results and claim review. I03 and final I04 acceptance verify the release from a clean checkout. Pipeline implementation and final result production are separate tasks; final scores are not prerequisites for running the experiments that generate them.

These dependencies describe artifact readiness, not permission to expose held-out data early. Training/test separation is both a loader boundary and a team rule.
