# Architecture for the final scheduling study

Latest: [the authorized action-choice validation passed](handoffs/I01_ACTION_CHOICE_VALIDATION_RESULT.md)
for RUN-fd87c6c8a9cb: six systems, 180 traces, 17 requests, 445.156 seconds,
zero replay findings/result mismatches and successful cleanup. Agent completed
J1/J2 using one model-initial start and one fallback start; Plain completed no
jobs. Both Agent repairs failed their checks. Nisha recorded a scoped receiving PASS;
this is public development evidence, not a study result or scientific freeze.

Current November 4 update: [one authorized unified public validation passed](handoffs/I01_UNIFIED_VALIDATION_2026-11-04.md)
for all six EP-HAND1 systems: 180 traces, 17 requests, 326.125 seconds, zero replay
findings/result mismatches and successful cleanup. Nisha's [scoped new-run receiving PASS is accepted](handoffs/I01_NISHA_UNIFIED_RECEIVING_2026-11-04.md).
The later authorized [action-field validation stopped on a semantic conflict](handoffs/I01_ACTION_FIELDS_VALIDATION_OUTCOME.md)
in Agent slot 1: 10 requests, five complete results and one partial Agent trace.
All nine raw plans had explicit nonempty actions; one put J2 in conflicting
action categories. Cleanup passed, with no retry. Complete I01 and prompt/schema
freeze remain blocked; the offline audit separates model actions from fallback. This supersedes older preparation-only status below without
changing historical records, scientific gates or task ownership. The
[offline CF60 compatibility plan](handoffs/CF60_DEVELOPMENT_COMPATIBILITY_PLAN.md)
is preparation only; no source read, relabeling, training or held-out work occurred.


[November 4 receiving acceptance](handoffs/I01_NISHA_RECEIVING_ACCEPTANCE_2026-11-04.md)
records a separate person's E01 replay review of all six existing public-development
units. This resolves their content-receiving dependency, with no change to the
architecture, original records or pending full I01/scientific acceptance.

The [November 4 latency refresh](handoffs/NOV04_LATENCY_LABELS_AND_READINESS.md) rechecks the
exact public receiving candidate without runtime startup. The independent
forecast-tie helper uses E01 replay and visible forecasts, outside the production
policy/checker path; it does not choose a forecast method or prove causal savings.
Agent request-latency totals are now saved before immutable trace persistence;
wall-clock decision duration remains separate, and old records are not rewritten.

The [P06 fold-scoring follow-up](../models/DEVELOPMENT_FOLD_METRICS.md) measures
candidate classification on the fixed development partitions. It does not change
the runtime architecture or rollout-based C/D selection, and does not replace
the research comparison of Agent versus Plain on accuracy, faithfulness and safety.

Current development status, November 2: all 40 development episodes are
materialized. Real C/D models are trained and reloaded; A/B/C/D completed public
EP-HAND1 receiving. Plain and Agent completed the same public bundle in an earlier
authorized run. Independent replay has zero findings/result mismatches in those
receiving records. These separate runs are not one frozen six-system experiment.
I01 is partial; source acceptance, actual held-out custody/freeze, full experiments
and final I04 acceptance remain open. Calibration #22 is closed; originals and
the approved prospective clarifications are retained. Held-out reliability #95
and official course requirements #16 remain open.

The [I01 audit](handoffs/I01_ACCEPTANCE_AUDIT_2026-11-02.md) records system-level
evidence and remaining acceptance. [Interfaces](INTERFACES.md) remain unchanged.
The architecture below describes implemented boundaries and the intended study;
it does not claim final scientific acceptance.

## Research question

Does an ontology-grounded, tool-verified agent improve the accuracy, faithfulness and safety of data-center sustainability recommendations compared with a plain LLM?

The main comparison is `agent` versus `plain_llm`, using equivalent visible information. Workload scheduling at one simulated data center is the experimental setting for this question. Greedy A/B and trained decision tree C/random forest D are four additional scheduling references, not four additional research questions. Conclusions apply to the evaluated scenarios.

## What the system does

The system recommends start times for jobs at one simulated data center. The six systems share the same arrived jobs, visible forecasts and authoritative constraints. Accuracy measures correctness, faithfulness measures whether claims are supported by evidence, and safety measures unsafe advice, constraint violations and appropriate abstention. The study compares the complete agent with the plain LLM; it does not establish the separate effect of any one component.

We reviewed AssetOps, LC-Opt, DeepMind cooling and Resource Advisor using the criteria documented in [the README](../README.md) and [source review](SOURCE_REVIEW.md). Connected facts, simulation, checks/fallback and evidence-linked explanations fit our research question. This is a reasoned design choice, not a measured ranking of architectures. The final proposal narrows those inspirations to workload scheduling. The [updated diagram](../architecture/architecture.svg) replaces the obsolete repository image and describes this final scope. Its [PNG version](../architecture/architecture.png) is shown in the README. Facility twins, water/cooling control and enterprise telemetry remain outside the required study.

## What is implemented today

| Component | Actual behavior | Acceptance limit |
|---|---|---|
| Shared F02 contracts | Typed records and canonical identities connect context, proposals, checks, actions and traces | Structural validation alone is not a schedule verdict |
| D01-D04/D06 data tooling | Pinned source inspection, provisional synthetic workloads and 40 verified development episodes | Historical source semantics/rights, empirical calibration and actual held-out freeze remain separate |
| S01/S02 and P01 | Deterministic execution, capacity/occupancy checks and energy/carbon-proxy accounting | Tested arithmetic does not authenticate source physical meaning or real-world emissions |
| K01-K03 | Typed domain facts, validation, controlled retrieval and constraint access | Only policy-visible facts may enter context; no private oracle access |
| Greedy A/B | Earliest-feasible and forecast-ranked proposals, with recorded checked fallback | Actual EP-HAND1 receiving exists; no optimality or final study claim |
| C/D training and policies | Certified development labels, blocked-fold selection, refit/reload and deterministic probability-to-schedule proposals | Actual models exist locally; scientific seed/freeze and final independent acceptance remain open |
| Plain LLM | Shared provider, equivalent flat facts, one combined request per required decision; no repair/fallback | Actual authorized EP-HAND1 receiving exists; one fixture/seed is insufficient for inference |
| Bounded Agent | Grounded context, proposal/check, at most one repair, checked fallback and explanation within a three-call decision bound | Actual receiving includes repair/fallback stages; stage presence does not establish successful repair or faithfulness |
| A03/A04 gate and traces | Physical validation, latest-state execution checks and immutable stage/attempt records | Physical feasibility and explanation support are distinct; regression cases do not prove exhaustive safety |
| E01/E02 evaluation and runner | Common policy execution, durable outputs and independent replay | Unified public validation passed; scoped receiving passed and full I01 remains pending |
| E04/E05/E07 human review | Both development originals, pre-adjudication reliability and separate joint adjudication retained; prospective calibration clarifications approved | #22 is closed; frozen held-out independent ratings/reliability #95 remain future work |
| F03 runtime | Hashed Windows environment and offline CI; actual accepted Ollama/Qwen Arc/Vulkan receiving | No untested cross-platform or field-deployment claim; fresh requests require authorization |

The [I01 audit](handoffs/I01_ACCEPTANCE_AUDIT_2026-11-02.md) and linked dated
handoffs retain exact code/run identities, counts and limitations. Test-only HTTP
responders and synthetic classifiers are not model results. Real C/D binaries
and source-derived inputs remain local and private. Full experiments and final
independent scientific acceptance remain pending.

## Planned data flow

1. Reimo acquires and validates carbon data, shapes synthetic jobs and freezes episode manifests and splits. Units, source versions, timestamps and checksums travel with the data.
2. The simulator reveals arrived jobs and running work at each hourly slot. It keeps future arrivals, split labels and private actual carbon outside the policy view.
3. Ved builds typed RDF facts and constraints. SHACL validates structure before an episode; controlled SPARQL queries preserve evidence IDs and detect missing links. Flat context contains the same visible facts and constraints, with canonical hashes for equivalence checks.
4. The common runner asks one of six policies for a proposal. Policies cannot mutate the simulator. The agent uses graph-grounded context; the plain LLM uses equivalent flat facts. The greedy and learned policies use the same visible records.
5. Matty's production checker checks the proposal and supporting evidence. The controller gate rechecks the latest state before executing eligible current-slot starts through Reimo's simulator.
6. Matty records initial, repaired, fallback, final and actually executed stages separately. Nisha's runner owns the episode loop and experiment checkpoint/resume.
7. Nisha independently scores original outputs and execution records. Offline reference schedules, hand arithmetic and blinded claim review provide comparison evidence.

The complete scientific study remains pending. F02 supplies shared boundaries, D01/D02 inspect source/calibration inputs, D06 independently checks the pinned carbon source/window, D03 supplies provisional private fixtures, and S01 performs actual deterministic transitions. L01 preparation uses the real shared transport. Controlled retrieval, A/B, the probability constructor, the approval gate, bounded agent and S02 accounting have bounded receiving evidence. C/D and the runner have actual receiving evidence; full independent I01/scientific acceptance remains pending.

## How the implemented records connect

The source loader returns private timestamp/value pairs and a source-inspection report. An agreed adapter still needs to map those observations into F02 records and separately create policy-visible forecasts. The report does not establish forecast issue times or resolve Q05; observation timestamps must not be reused as issue times by assumption.

F02 separates private observations and episodes from visible state and forecasts. A constraint snapshot holds source provenance and the authoritative capacity constraint; capacity is not duplicated in site configuration. Missing capacity raises an explicit error. Context records carry only the sources, constraints and forecast facts relevant to currently visible jobs, with hashes for graph/flat equivalence checks.

Plan records retain structurally valid but infeasible proposals. The production checker derives real violations and complete-plan physical passes, bound to plan hash/state version. F02 remains unchanged. The controller performs a fresh same-slot content check against actual constraints, retains the original plan hash and binds the latest version. Actual tests cover the 100-to-70 kW constraint change and controlled execution. Full graph-driven K03, source claims and independent scientific receiving remain separate.

D03 jobs can now be exercised through F02 visible records and the actual fixed checker. [The consumer tests](../tests/verification/test_d03_consumer.py) explicitly build synthetic constraints and an arrived-job view only for tests. They demonstrate fixed-rule compatibility, not production S01 visibility or integrated approval. No private episode, split/seed label or future arrival is provided to the checker as a policy view. [The handoff](handoffs/A03_D03_F04_F05.md) records scope and commands.

## Two different graphs

The target RDF knowledge graph represents domain relationships. The implemented K02 development graph includes only policy-visible site/job/forecast/constraint/source data in a local sched namespace; private realized observations and offline answers are excluded. K01 now adds local ontology, Brick/PROV-O/QUDT mappings and SHACL validation, with the validation/unit gaps in #71 still open. Domain graphs, runtime traces and private labels stay separate. K02 Context is still built from authoritative F02 inputs rather than reconstructed from arbitrary RDF; merged K03 tests do not yet establish that graph-query results drive the checker. #72 tracks that receiving proof. Ontology and SHACL validation do not by themselves authorize execution.

The LangGraph workflow represents steps and conditional routes. Its shared state records the visible snapshot, fact/constraint IDs, proposals, checks, repair count, call budget, state version and trace ID. A workflow edge does not establish factual correctness. Python validation and execution code enforce the rules.

## Policy behavior and execution

The accepted development provider is local Ollama with Qwen3 8B Q4_K_M and temperature 0.2 for both LLM systems. [Q09](decisions/Q09_OLLAMA_QWEN3.md) lists accepted development settings and remaining runtime/context/run gates. The common low-level transport is implemented with offline HTTP tests. [Hardware inventory](HARDWARE.md) records that the accepted runtime can retain Matty's Arc 140V through Vulkan when integrated-GPU use is enabled. The metadata-only check loaded no model, so Qwen offload and performance remain untested.

The agent route is read state, retrieve context, propose, verify, optionally repair once, verify again, then use a checked greedy-A fallback if needed. The gate rechecks against the latest state. Missing verification means abstention or escalation. Explanation generation uses recorded evidence and cannot change the approved action. At most three model calls include proposal, optional repair and explanation; SDK retries count too. No model calls occur in slots 24-29.

The plain LLM uses the same provider version and settings in one call. It has no tools, corrective feedback, repair or fallback. The gate can block unsafe starts, but the evaluator retains and scores the original response. Blocking does not silently improve the plain system's recommendation score.

Greedy A starts as soon as feasible; greedy B prefers lower forecast emissions and uses whole-decision checked A when its required forecast union is not fresh and complete. Neither guarantees a feasible or optimal outcome. The implemented probability constructor can receive future decision-tree C and random-forest D scores, and real development models are now trained and reloaded; final scientific selection remains unfrozen. All four use the same production checker. Trusted forecast UTC and requested-versus-effective fallback recording remain runner acceptance work. Classical explanations use templates and make no model calls.

The controller alone invokes `execute_step`. Approval is bound to a plan hash and state version, then checked against current state. Running work is immutable. Invalid, stale, duplicate or bypassed actions must be rejected. After rejection no new jobs start, but the runner advances the clock and running work once. Future plan entries are intentions, not unchecked executable commitments. Q01/Q03 physical rules are implemented by A03. S01 Option B receiving and Q08/reference certification remain explicit integration gates, not a blanket ban on physical passes.

Missing capacity links block execution. Missing carbon blocks unsupported emissions or savings claims; a verified A fallback may still be feasible under the accepted evidence rule. Q04 assessment requires complete occupied-union coverage, age at most two slots and no future issue times; its actual policy/runner adoption needs trusted UTC. Simulator, graph, all policies, checker, solver and evaluator share the same authoritative constraint records. A graph change from 100 to 70 kW must change the decision for a 40 kW job with 40 kW background without code or prompt changes.

## Offline learning and evaluation

Offline visible-state integer programs are intended to provide certified development labels to Edison, with future arrivals excluded. [Q07](decisions/Q07_TRAINING_OCT27.md) fixes the eight visible-input features, full candidate order, development-only blocked folds, training-only preprocessing/class weights, threshold and not-applicable metric rules. PRs #86/#90 provide feature rows and unlabeled collection; PR #97 adds injected blocked folds, training-only scaling and class-weight helpers. Q08 certification, fitted models and actual training/selection remain open; unresolved solver results do not establish infeasibility or optimality.

A separate full-episode hindsight oracle supplies a descriptive lower bound after inference. It can see future arrivals and is never a policy tool or input. Neither training labels nor reference schedules belong in visible state. Nisha's reference validator is separately implemented; importing the production checker as truth would remove evaluation independence.

The development set has 40 episodes. The held-out matrix has 30 episodes and 300 system runs. Models, prompts, source windows, seeds, budgets and scoring freeze before evaluation. All 30 slots contribute accounting. Emissions accompany completed jobs/work, deadline misses and unfinished jobs; savings require matching work and an explicit baseline, horizon and inputs.

Faithfulness review preserves independent blinded Matty/Nisha ratings before adjudication. Claims need supporting evidence, not just an existing ID. Numerical scoring tolerances differ from internal calculation-test tolerances. Sample selection and confidence interval details await Q10.

## Interfaces, modules and completion

Actual entry points now include K02 get_context/retrieve, policy propose for A/B, the probability-driven schedule constructor, A03 check_schedule, ExecutionController.execute_step, TraceStore.write/read and AgentHarness.run_decision. The controller accepts existing F02 decision/stage records, not an unrestricted model execution tool. Production renderers and trained C/D artifacts have receiving evidence. The model CLI remains restricted; no fresh inference is authorized by this document. F02 Job/Plan/Context/CheckResult/ApprovedActions/DecisionRecord stay unchanged in dc_sustainability/schemas.py. [The sole interface specification](INTERFACES.md) and current module handoffs distinguish implementation from consumer adoption.

Run existing offline checks using the [README quick start](../README.md). Suites cover real local HTTP, RDF retrieval, agreed checker rules, actual controller execution/refusal, durable traces and bounded graph routing on synthetic inputs. They do not prove real inference or a complete six-system study. Counter/prompts/fallback used only in tests are explicitly labeled fixtures; no production constant-passing checker or invented model result is supplied.

The [October 20 handoff](handoffs/OCT20_SIX_PRIORITIES.md) records Q09 agreement on 0.40.5 and the then-observed 0.40.6 mismatch. The active desktop metadata later records 0.40.11, while the isolated accepted 0.40.5 runtime produced the retained CPU timeout. The [metadata-only host check](handoffs/A01_IGPU_HOST_CANDIDATE_2026-10-25.md) identifies an Arc/Vulkan candidate without loading a model or authorizing another request. Counter validation remains missing. E01 preparation in PR #23 has an [authorized merge review](handoffs/E01_MERGE_REVIEW.md), including fixes for strict capacity, input consistency, comparison identity, claim scoring and the fixed episode end. It remains an explicit draft scientific protocol, not full evaluation acceptance. Production checker and independent evaluation remain separate; neither is the other's truth. The architecture diagram shows the target study; existing component code does not establish full pipeline or scientific acceptance.

An actual model-driven development episode with repair or fallback is required for E4 acceptance. Mocks suffice for ordinary offline CI, not final integration evidence. Matty owns early and final end-to-end acceptance, Nisha independently verifies results, Ved reproduces on another machine, and each module owner fixes defects. The [demo plan](DEMO.md) and [project plan](PROJECT_PLAN.md) record the remaining evidence.
