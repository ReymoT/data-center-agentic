# Architecture for the final scheduling study

Status: proposed implementation, prepared for F01/F05 review on 2026-10-10. No scheduling component is implemented by this branch. Read the [interface draft](INTERFACES.md) for records and ownership, and [open decisions](team/04_OPEN_DECISIONS.md) for rules still awaiting approval.

## What the system does

The system recommends start times for jobs at one simulated data center. It compares six scheduling systems using equivalent visible information. The main comparison asks whether the complete agent improves accuracy, evidence support and safety compared with the plain LLM. It does not establish the separate effect of any one component.

We reviewed AssetOps, LC-Opt, DeepMind cooling and Resource Advisor using the criteria documented in [the README](../README.md) and [source review](SOURCE_REVIEW.md). Connected facts, simulation, checks/fallback and evidence-linked explanations fit our research question. This is a reasoned design choice, not a measured ranking of architectures. The final proposal narrows those inspirations to workload scheduling. The existing [historical image](../architecture/architecture.png) remains unchanged; its facility twin, UI, water, weather and cooling scope is not required.

## Data flow

1. Reimo acquires and validates carbon data, shapes synthetic jobs and freezes episode manifests and splits. Units, source versions, timestamps and checksums travel with the data.
2. The simulator reveals arrived jobs and running work at each hourly slot. It keeps future arrivals, split labels and private actual carbon outside the policy view.
3. Ved builds typed RDF facts and constraints. SHACL validates structure before an episode; controlled SPARQL queries preserve evidence IDs and detect missing links. Flat context contains the same visible facts and constraints, with canonical hashes for equivalence checks.
4. The common runner asks one of six policies for a proposal. Policies cannot mutate the simulator. The agent uses graph-grounded context; the plain LLM uses equivalent flat facts. The greedy and learned policies use the same visible records.
5. Matty's production checker checks the proposal and supporting evidence. The controller gate rechecks the latest state before executing eligible current-slot starts through Reimo's simulator.
6. Matty records initial, repaired, fallback, final and actually executed stages separately. Nisha's runner owns the episode loop and experiment checkpoint/resume.
7. Nisha independently scores original outputs and execution records. Offline reference schedules, hand arithmetic and blinded claim review provide comparison evidence.

This pipeline is planned. This branch provides directories and documents; it does not simulate execution.

## Two different graphs

The RDF knowledge graph represents domain relationships: sites, jobs, slots, carbon observations, constraints, sources, decisions and checks. It supplies evidence and authoritative limits. Brick, PROV-O and practical QUDT units are planned vocabulary sources; Ved must pin their versions.

The LangGraph workflow represents steps and conditional routes. Its shared state records the visible snapshot, fact/constraint IDs, proposals, checks, repair count, call budget, state version and trace ID. A workflow edge does not establish factual correctness. Python validation and execution code enforce the rules.

## Policy behavior and execution

The agent route is read state, retrieve context, propose, verify, optionally repair once, verify again, then use a checked greedy-A fallback if needed. The gate rechecks against the latest state. Missing verification means abstention or escalation. Explanation generation uses recorded evidence and cannot change the approved action. At most three model calls include proposal, optional repair and explanation; SDK retries count too. No model calls occur in slots 24-29.

The plain LLM uses the same provider version and settings in one call. It has no tools, corrective feedback, repair or fallback. The gate can block unsafe starts, but the evaluator retains and scores the original response. Blocking does not silently improve the plain system's recommendation score.

Greedy A starts as soon as feasible; greedy B prefers lower forecast emissions. Neither guarantees a feasible or optimal outcome. Trained decision tree C and random forest D rank candidate starts from visible features. They use no exact solver during inference. All four pass the same production checker; B/C/D forecast fallback scope awaits Q04. Classical explanations use templates and make no model calls.

The controller alone invokes `execute_step`. Approval is bound to a plan hash and state version, then checked against current state. Running work is immutable. Invalid, stale, duplicate or bypassed actions must be rejected. After rejection no new jobs start, but the runner advances the clock and running work once. Future plan entries are intentions, not unchecked executable commitments. Q01-Q03 must settle completion starts, partial infeasibility, coverage and deferral behavior before runtime acceptance.

Missing capacity links block execution. Missing carbon blocks unsupported emissions or savings claims; a verified A fallback may still be feasible under the accepted evidence rule. Forecast freshness details await Q04. Simulator, graph, all policies, checker, solver and evaluator share the same authoritative constraint records. A graph change from 100 to 70 kW must change the decision for a 40 kW job with 40 kW background without code or prompt changes.

## Offline learning and evaluation

Offline visible-state integer programs provide certified development labels to Edison, with future arrivals excluded. Only certified optimal feasible states create training labels. Unresolved solver results do not establish infeasibility or optimality. Candidate features, rollout, ties and solver settings await Q07/Q08.

A separate full-episode hindsight oracle supplies a descriptive lower bound after inference. It can see future arrivals and is never a policy tool or input. Neither training labels nor reference schedules belong in visible state. Nisha's reference validator is separately implemented; importing the production checker as truth would remove evaluation independence.

The development set has 40 episodes. The held-out matrix has 30 episodes and 300 system runs. Models, prompts, source windows, seeds, budgets and scoring freeze before evaluation. All 30 slots contribute accounting. Emissions accompany completed jobs/work, deadline misses and unfinished jobs; savings require matching work and an explicit baseline, horizon and inputs.

Faithfulness review preserves independent blinded Matty/Nisha ratings before adjudication. Claims need supporting evidence, not just an existing ID. Numerical scoring tolerances differ from internal calculation-test tolerances. Sample selection and confidence interval details await Q10.

## Interfaces, modules and completion

Named interfaces include `read_state`, `get_context`, `check_schedule`, controller-only `execute_step` and `write_trace`. Simulator APIs, provider/plan records and exact CLI names await F02 review. The [interface document](INTERFACES.md) is the sole maintained draft; placeholders must not become competing schema definitions.

An actual model-driven development episode with repair or fallback is required for E4 acceptance. Mocks suffice for ordinary offline CI, not final integration evidence. Matty owns early and final end-to-end acceptance, Nisha independently verifies results, Ved reproduces on another machine, and each module owner fixes defects. The [demo plan](DEMO.md) and [project plan](PROJECT_PLAN.md) record the remaining evidence.
