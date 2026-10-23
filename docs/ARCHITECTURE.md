# Architecture for the final scheduling study

Current E05 update, October 22: [Matty's original ratings submitted](handoffs/E05_MATTY_RATINGS_2026-10-22.md), [issue #42](https://github.com/ReymoT/data-center-agentic/issues/42). His first pass covers 11 pairs / 22 output units and passes structural validation, with the submitted bytes and judgments unchanged. E05 is Verifying: Nisha must retain her own original before viewing these labels, then lead paired comparison and separate adjudication. Remaining Q10/rubric and affected-owner agreements stay open. Prior dated intake notes remain historical. A01 diagnosis remains deferred; no shared format, setting or task owner changed.

Status: current implementation boundaries and target design, updated 2026-10-22, instruction deployment 1.20. Published under the project manager's instruction without a formal document-review gate. F02 records, D01 source inspection and A01/A03 agreed core code are implemented; the complete scheduling pipeline remains planned. Read [interfaces](INTERFACES.md) for implemented records and proposed APIs, and [open decisions](team/04_OPEN_DECISIONS.md) for unresolved rules.

## Research question

Does an ontology-grounded, tool-verified agent improve the accuracy, faithfulness and safety of data-center sustainability recommendations compared with a plain LLM?

The main comparison is `agent` versus `plain_llm`, using equivalent visible information. Workload scheduling at one simulated data center is the experimental setting for this question. Greedy A/B and trained decision tree C/random forest D are four additional scheduling references, not four additional research questions. Conclusions apply to the evaluated scenarios.

## What the system does

The system recommends start times for jobs at one simulated data center. The six systems share the same arrived jobs, visible forecasts and authoritative constraints. Accuracy measures correctness, faithfulness measures whether claims are supported by evidence, and safety measures unsafe advice, constraint violations and appropriate abstention. The study compares the complete agent with the plain LLM; it does not establish the separate effect of any one component.

We reviewed AssetOps, LC-Opt, DeepMind cooling and Resource Advisor using the criteria documented in [the README](../README.md) and [source review](SOURCE_REVIEW.md). Connected facts, simulation, checks/fallback and evidence-linked explanations fit our research question. This is a reasoned design choice, not a measured ranking of architectures. The final proposal narrows those inspirations to workload scheduling. The [updated diagram](../architecture/architecture.svg) replaces the obsolete repository image and describes this final scope. Its [PNG version](../architecture/architecture.png) is shown in the README. Facility twins, water/cooling control and enterprise telemetry remain outside the required study.

## What is implemented today

| Component | Actual behavior | Acceptance limit |
|---|---|---|
| F02, Ved | Strict contract 1.0.0 records for jobs, visible/private carbon, constraints, contexts, plans, checks, actions and traces; serialization, canonical hashes and committed examples | Records validate structure and consistency; they do not calculate a schedule verdict or execute actions. Actual consumer adoption is pending. |
| D01, Reimo | Pinned source download/checksum, CSV validation, private UTC observations and provenance/uncertainty reports | D06 now provides bounded independent structural/window evidence; pollutant scope, physical interval mapping, dataset rights, factor alignment and F02 adaptation remain pending. It does not generate episodes or visible forecasts. |
| D06, Ved; verified by Matty | Standalone pinned-byte/UTC/window checker and reproduction handoff; actual Windows rerun matches the adapter and includes the merged checker's required valid-timestamp field | Structural reproduction only. It does not authenticate Ved's earlier JSON, settle Q05 semantics/rights or adopt policy-facing carbon facts. See [the verification](handoffs/D06_F04_F05_VERIFICATION.md). |
| D02, Reimo | Checksum-pinned Frontier job-table inspection with explicit field/unit mappings, exclusion reports and calibration/scaling tooling | Real Frontier access, source field/unit/license verification (Q05), empirical statistics and accepted scaling (Q06) remain pending. |
| D03, Reimo | Seeded synthetic job generation, hand jobs and private episode assembly; withholding forecasts preserves private actuals | Distributions are provisional and not Frontier-calibrated. Q05/Q06, D04 allocation/freeze, simulator visibility and downstream acceptance remain pending. |
| P01, Edison; reviewed by Matty | Real slot/job/background/site PUE-scaled energy/emissions ledger, horizon overlap and same-work savings guards; finite fractions and one-decimal display have review regressions | Merged through PR #35, 27 focused cases and exact-head/main CI986 tests/19 subtests. S02 calling convention/adoption and shared completed_work mapping are not agreed; no source pollutant or independent evaluation truth is selected. [Handoff](handoffs/P01.md). |
| S01, Reimo | Deterministic reset/state/step, arrived-job visibility, current-slot action validation, occupancy and 30-slot history | Completion behavior requires an explicit development choice; Q01-Q04, runtime approval, S02/P01 impact accounting and downstream acceptance remain pending. |
| L01 preparation, Nisha | One shared-provider request for a required decision; empty waiting queues produce a zero-call no-op proposal. Original outputs retained, no repair/fallback, strict F02 context revalidation | Merged preparation is offline-tested, not an inference or integrated-episode result. K02, validated token/context handling, runtime match and actual probe remain pending. |
| A01, Matty | Local Ollama REST transport, strict F02 parsing, explicit runtime/artifact checks, request deadlines and shared attempt accounting | Offline HTTP tests use a synthetic local server. Development projections/pins are agreed; runtime drift, a validated context counter and authorized run evidence remain pending. |
| A03, Matty | Fixed schedule/evidence checks on actual records; authoritative capacity/running occupancy; consumer tests using actual D03-generated development jobs | Known violations are rejected. Q01-Q04 remain unresolved, so otherwise feasible plans receive an error and no execution approval. Claim arithmetic is not certified. |
| E01 preparation, Nisha | Independent decision/claim references and structural episode replay; strict capacity/episode boundaries, raw input/metadata validation and same-decision checker comparisons | Draft protocol remains explicit. Joint infeasibility, unsupported units/reference selection, the proposed one-decision visibility change and real saved-output acceptance remain pending. A supplied completed_work scalar needs an agreed mapping; replay does not certify impact totals or forecast/mutation history. See [merge review](handoffs/E01_MERGE_REVIEW.md). |
| E04 preparation, Nisha; reviewed by Matty | Draft assertion extraction rule, 11 synthetic X/Y pilot pairs, blank annotation template, structural annotation validation and per-output arithmetic | PR39 merged with eight review regressions and exact PR/main CI1016/19. No model output; Matty's original ratings are submitted while Nisha's original and joint adjudication remain pending. Raw-text extraction/deduplication and unit/reference questions remain, with Q10 design/eligibility and actual independent originals required before freeze. [Rating guide](e04/MATTY_RATING_GUIDE.md). |
| F03, Matty | Hashed Windows Python 3.12 candidate, dependency smoke checks, CI and verified local Ollama/Qwen installation inventory | Final provider/framework environment, accepted deployment pins, live inference and multi-platform certification remain pending. See [model setup](OLLAMA_SETUP.md). |

The provider helper lives only under tests and replays labeled outcomes. The simulator and plain-LLM preparation are now implemented with the limits above. Retrieval, policies, gate, agent and full episode evaluation/runner remain planned; E01 decision/claim and structural replay preparation are available. The adapter/checker core is tested without those components; see [the handoff](handoffs/A01_A03_AGREED_CORE.md). A serialized example of a passing check is a fixture, not evidence that a checker ran. No experiment result or completed integration is claimed.

## Planned data flow

1. Reimo acquires and validates carbon data, shapes synthetic jobs and freezes episode manifests and splits. Units, source versions, timestamps and checksums travel with the data.
2. The simulator reveals arrived jobs and running work at each hourly slot. It keeps future arrivals, split labels and private actual carbon outside the policy view.
3. Ved builds typed RDF facts and constraints. SHACL validates structure before an episode; controlled SPARQL queries preserve evidence IDs and detect missing links. Flat context contains the same visible facts and constraints, with canonical hashes for equivalence checks.
4. The common runner asks one of six policies for a proposal. Policies cannot mutate the simulator. The agent uses graph-grounded context; the plain LLM uses equivalent flat facts. The greedy and learned policies use the same visible records.
5. Matty's production checker checks the proposal and supporting evidence. The controller gate rechecks the latest state before executing eligible current-slot starts through Reimo's simulator.
6. Matty records initial, repaired, fallback, final and actually executed stages separately. Nisha's runner owns the episode loop and experiment checkpoint/resume.
7. Nisha independently scores original outputs and execution records. Offline reference schedules, hand arithmetic and blinded claim review provide comparison evidence.

The complete pipeline remains planned. F02 supplies shared boundaries, D01/D02 inspect source/calibration inputs, D06 independently checks the pinned carbon source/window, D03 supplies provisional private fixtures, and S01 now performs actual deterministic transitions. L01 preparation uses the real shared transport. Controlled retrieval, policies, approval gate, agent, impact accounting and independent evaluation still require their own implementations and acceptance.

## How the implemented records connect

The source loader returns private timestamp/value pairs and a source-inspection report. An agreed adapter still needs to map those observations into F02 records and separately create policy-visible forecasts. The report does not establish forecast issue times or resolve Q05; observation timestamps must not be reused as issue times by assumption.

F02 separates private observations and episodes from visible state and forecasts. A constraint snapshot holds source provenance and the authoritative capacity constraint; capacity is not duplicated in site configuration. Missing capacity raises an explicit error. Context records carry only the sources, constraints and forecast facts relevant to currently visible jobs, with hashes for graph/flat equivalence checks.

Plan records retain structurally valid but infeasible proposals. The fixed checker now calculates their rule violations and reports performed/skipped checks in CheckResult, bound to plan hash/state version. It uses unchanged F02 records. Its 100-to-70 kW test proves a constraint input changes the capacity subcheck; the RDF retrieval and execution gate still need separate integration evidence. Unresolved coverage and freshness rules prevent overall approval.

D03 jobs can now be exercised through F02 visible records and the actual fixed checker. [The consumer tests](../tests/verification/test_d03_consumer.py) explicitly build synthetic constraints and an arrived-job view only for tests. They demonstrate fixed-rule compatibility, not production S01 visibility or integrated approval. No private episode, split/seed label or future arrival is provided to the checker as a policy view. [The handoff](handoffs/A03_D03_F04_F05.md) records scope and commands.

## Two different graphs

The RDF knowledge graph represents domain relationships: sites, jobs, slots, carbon observations, constraints, sources, decisions and checks. It supplies evidence and authoritative limits. Brick, PROV-O and practical QUDT units are planned vocabulary sources; Ved must pin their versions.

The LangGraph workflow represents steps and conditional routes. Its shared state records the visible snapshot, fact/constraint IDs, proposals, checks, repair count, call budget, state version and trace ID. A workflow edge does not establish factual correctness. Python validation and execution code enforce the rules.

## Policy behavior and execution

The accepted development provider is local Ollama with Qwen3 8B Q4_K_M and temperature 0.2 for both LLM systems. [Q09](decisions/Q09_OLLAMA_QWEN3.md) lists accepted development settings and agreed October 20 development settings and remaining runtime/context/GPU/run gates. The common low-level transport is implemented with offline HTTP tests. [Hardware inventory](HARDWARE.md) now records Matty's Intel GPU and installed runtime; Qwen inference and measured offload remain untested.

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

Named interfaces include `read_state`, `get_context`, `check_schedule`, controller-only `execute_step` and `write_trace`. `check_schedule` now implements the fixed core above, and the local provider transport is available. S01 state/step and L01 preparation are now implemented; retrieval, controller execution/trace APIs and the experiment CLI remain planned. F02's Job/Plan/Context/CheckResult/ApprovedActions/DecisionRecord and other records are implemented in `dc_sustainability/schemas.py`. The [interface document](INTERFACES.md) is the single maintained contract, with consumer adoption explicitly pending.

Run the existing offline checks using the [README quick start](../README.md). The current suites cover strict records, source/calibration inspection, provisional scenario generation, helpers, real local HTTP transport and fixed checking of hand and D03-generated jobs. They do not prove live inference, integrated execution or independent scientific acceptance. [The maintenance handoff](handoffs/F03_F04_F05_MAINTENANCE.md) records the actual environment and test evidence. Do not present stubs, fabricated traces or a constant passing verdict as implementation.

The [current handoff](handoffs/OCT20_SIX_PRIORITIES.md) records Q09 agreement on 0.40.5 and a fresh observed 0.40.6 mismatch. Counter validation and live authorization remain missing. E01 preparation in PR #23 has an [authorized merge review](handoffs/E01_MERGE_REVIEW.md), including fixes for strict capacity, input consistency, comparison identity, claim scoring and the fixed episode end. It remains an explicit draft scientific protocol, not full evaluation acceptance. Earlier isolated f5a2542 evidence describes the original defect, which is now corrected. Production checker and independent evaluation remain separate; neither is the other's truth. The architecture diagram still shows the target system; this update does not add a runtime component or assert integrated execution.

An actual model-driven development episode with repair or fallback is required for E4 acceptance. Mocks suffice for ordinary offline CI, not final integration evidence. Matty owns early and final end-to-end acceptance, Nisha independently verifies results, Ved reproduces on another machine, and each module owner fixes defects. The [demo plan](DEMO.md) and [project plan](PROJECT_PLAN.md) record the remaining evidence.
