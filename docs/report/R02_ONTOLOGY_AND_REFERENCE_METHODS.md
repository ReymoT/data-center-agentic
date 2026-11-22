# R02 Technical Evidence Report: Ontology, Retrieval, Validation, Simulator and Reference Solver

Repository: https://github.com/ReymoT/data-center-agentic, branch `main`
Commit inspected: `cd272e93a58af8e373bfa8ed96d1191687b919fc`
Prepared for: Ved Patil, ASU FSE 598 Data Center Sustainability Agent project
Date of investigation: 18 November 2026
Purpose: source material for a separate writer who will draft the final R02 section. This document is deliberately not that section. It records what the repository contains, how the pieces connect at runtime, what evidence supports each statement, and what cannot be claimed.

## 0. Method, access and conventions

### 0.1 How the investigation was done

The repository was cloned at the tip of `main` (533 commits visible; the clone is shallow with a 200-commit fetch, which is enough to date recent work but not to audit early history). Source files named in the brief were read directly. Where a call chain left the named files, the additional files that were needed to follow it were read too; they are listed with reasons in section 2.7. Tests were read and, for the suites that bear on R02, executed locally. The proposal and the handoff documents were read last and used only to cross-check what the source says.

Evidence is ranked as the brief requires: source first, then tests, then execution and CI records, then documentation. When a document and the source disagree, this report follows the source and says so.

### 0.2 Access limits and what they imply

Access to the GitHub API and the `gh` client for this repository was refused during the investigation (HTTP 403, "GitHub access to this repository is not enabled for this session"). Consequences:

1. Pull request pages, issue threads and the list of Actions runs could not be queried. Merge status is therefore inferred from the local clone of `main`: a commit reachable from `origin/main` is treated as merged to `main`. Whether a given pull request was reviewed, or whether a branch was later deleted, is not established here.
2. One Actions run page (run #259, commit `6c288c0`, 1 November 2026) could be fetched as a rendered summary. Step logs require a login and were not available. No run for the inspected commit `cd272e93` could be found.
3. Everything described as "execution-verified" below is a local run performed during this investigation. It is real execution of the real code, but it is not a CI record and was not performed on the project's Windows target. Each such statement carries the interpreter and platform.

The language model that the agent harness calls (Ollama with Qwen3 8B) was not available, and no paid or model-backed call was made. The agent's live behaviour is therefore known only from source, from tests that use a synthetic HTTP server, and from the project's own recorded validation handoffs, which are described but not re-verified.

### 0.3 Local execution environment

The project's lock file targets Windows with Python 3.12. The first local run used Python 3.13 and produced 15 failures, all in `tests/data` and all caused by interpreter-version behaviour (section 7.5). A second, complete run under CPython 3.12.3 on Linux, in a fresh virtual environment installed with the pinned versions from `requirements/requirements-core.in` (pydantic 2.14.0, pyshacl 0.40.1, rdflib 7.6.0, scipy 1.18.1, pytest 9.1.1), passed in full: 2348 passed, 0 failed, 23 skipped. The hash-pinned Windows lock file itself was not used.

### 0.4 Status labels

The seven labels from the brief are used with their stated meanings. Two additions keep the evidence honest. "Tested" is used whenever an identifiable test asserts the behaviour; it does not imply that the test passed. "Execution-verified" is used only where I saw the test or code run, and the platform is named. I use "static analysis" for conclusions reached by reading source without running it, and "probe" for small read-only scripts I ran against the commit to observe behaviour that the tests do not assert. The probe scripts are not part of the repository.

### 0.5 Link convention

A reference of the form `path:Lnn` or `path:Lnn-Lmm` points to
`https://github.com/ReymoT/data-center-agentic/blob/cd272e93a58af8e373bfa8ed96d1191687b919fc/<path>#L<nn>`.
Section 10 gives full URLs for the principal items. Line numbers are those at the inspected commit.

---

## 1. Executive summary

### 1.1 What the repository contains for R02

The project is a bounded data-center job-scheduling study. A site has a fixed power capacity, a background load and a power usage effectiveness (PUE) factor. Jobs arrive during the first 18 hourly slots, each with a power draw, a duration and a deadline, and some jobs are flexible about their start. Carbon intensity varies by hour. Six systems (an LLM agent, a plain LLM, two hand-written greedy policies and two trained classical models) propose which waiting jobs to start now and which to defer, and a deterministic checker and simulator decide what is allowed to happen. R02 is the part of the report that describes the knowledge layer (ontology, graph, retrieval, validation) and the reference optimisation (the offline solver, labels, cache and hindsight bound).

Five technical contributions are present in source and are supported by tests that pass in my local runs.

First, there is a small, versioned ontology in the `sched:` namespace, expressed as OWL-style Turtle (`ontology/dc-sustainability.ttl`) and accompanied by twelve SHACL shapes (`ontology/shapes.ttl`). It reuses Brick for the site, PROV-O for provenance and QUDT for units, to the extent shown in section 3.7. A graph builder (`dc_sustainability/knowledge/graph.py`) turns the policy-visible state and the constraint snapshot into an RDFLib graph, and a validation function (`knowledge/ontology.py`) runs pySHACL against it with inference turned off.

Second, there is a SPARQL retrieval layer (`knowledge/retrieval.py`) with six queries over that graph, and a `retrieve()` function that returns both the flat query results and a hashed `Context` record.

Third, there is a layered validation scheme. SHACL checks the shape of the graph. Pydantic validates every shared record (the "F02" contract in `schemas.py`) and refuses to treat absent capacity as unlimited. A hand-written runtime checker (`verification/checker.py`) checks a proposed plan against the visible state and the constraint snapshot, and the simulator repeats the essential checks before any start takes effect.

Fourth, there is a deterministic simulator with 24 decision slots and 6 completion slots, and shared energy and carbon formulas.

Fifth, there is a reference optimisation stack: a mixed-integer program solved with `scipy.optimize.milp` (HiGHS) for the visible state, with four explicit result statuses; a label generator that turns certified results into training labels; an immutable label cache keyed by content hashes; and a separate offline hindsight solver that uses future arrivals and realised carbon and exports sealed artifacts.

### 1.2 How the pieces fit together at runtime, and where they do not

The most important finding for R02 is about integration, not about any single component. The ontology, the graph and SHACL are real, tested and documented, but they are not the channel through which scheduling facts reach the decision-making components. Retrieval builds the RDF graph and runs SPARQL on every call, but the `Context` that the agent, the plain model, the greedy policies, the trained models and the reference solver all consume is assembled directly from the Pydantic state and constraint snapshot (`Context.build`, `schemas.py:L966`). A probe that replaced every SPARQL result with garbage left the `Context` content hash unchanged. The checker reads the constraint snapshot directly and never sees the graph. SHACL is not called anywhere on the production path; it is called by tests and by a dependency smoke script. The project's own architecture document says as much for the Context ("K02 Context is still built from authoritative F02 inputs rather than reconstructed from arbitrary RDF", `docs/ARCHITECTURE.md:L165`), and this report confirms it from source.

The "graph" and "flat" context presentations carry identical content. They differ only in a `representation` label, and each consumer insists on one label: the agent's prompt renderer refuses anything but "graph", and the plain model refuses anything but "flat". Whatever advantage the agent has from the knowledge layer therefore cannot come from different information in its prompt. It can only come from what the surrounding agent harness adds (routing, a single repair, a checked fallback, execution gating).

The knowledge layer does matter in three ways that can be stated safely. It gives the project a controlled vocabulary and a machine-checkable specification of what a valid visible state looks like. It provides a demonstration, in tests, that a capacity value retrieved from the graph is the value a checker would use, and that changing 100 kW to 70 kW changes the outcome without code changes. And it is a failure dependency of the agent's retrieval step, since a failure in graph construction stops retrieval.

### 1.3 Quality of the evidence

On the project's target interpreter the complete test suite passed in my local run. The knowledge, reference, verification and simulator suites, which carry the weight of R02, passed with 75, 82, 85 and 51 tests respectively. No CI result for the inspected commit was accessible, and the one CI page I could read predates the reference cache, labels and hindsight code, so it is not evidence about them.

### 1.4 What cannot be claimed

The report should not say that agent decisions are grounded in the ontology at runtime, that SHACL validates plans or gates execution, that the graph presentation changes the model's input, or that the reference schedule is the unique optimum. A "certified optimal" status means HiGHS reported success on the visible-horizon model. The code sets no explicit gap tolerance, stores a `tolerance` value it does not pass to the solver, leaves the tie-break unfrozen (open decision Q08), and the project's own label audit says that alternative global optima are not counted. The carbon data come from a pinned public CSV whose pollutant basis, interval convention and redistribution rights are unresolved (Q05; Issue 60 blockers B1 to B3). Development labels are not held-out labels, and the held-out reference artifacts (task O04) depend on later work that has not happened.

---

## 2. Architecture and end-to-end data flow

### 2.1 Which parts of the architecture belong to R02

The responsibility checklist (`docs/team/03_RESPONSIBILITY_CHECKLIST.md:L50-L56, L82`) assigns the relevant work to Ved as tasks K01 (ontology, source and constraint records, unit mappings, SHACL), K02 (SPARQL retrieval and the flat-context projection), K03 (proof that graph-driven constraints change behaviour and that missing links fail at runtime), O01 (offline integer-program reference solver), O02 (certified visible-state schedules and label caches), O03 (hindsight and offline reference export) and O04 (held-out hindsight and visible references after inference). R02 itself is listed as "Write ontology/reference-solver section and reference artifact documentation", depending on K03 and O04. The checklist boxes are all unticked in the file, so the checklist is not a status record. Sections 7.6 and 8 give the status that the source supports: K01 to K03 and O01 to O03 are implemented and merged; O04 has not happened because it waits for the held-out run, which the handoffs describe as not authorised.

### 2.2 The runtime path, step by step

The path below follows the source from the simulator to the point where a start takes effect. File and line references are given so each step can be checked.

1. The experiment runner (`dc_sustainability/experiments/runner.py:L214-L266`, `_drive_episode`) creates a `SchedulingSimulator` and calls `reset(episode, forecasts_by_slot=...)`. `reset` (`simulator/core.py:L45-L109`) validates the private episode, requires 24 decision and 6 completion slots, hourly slots, arrivals before slot 18 and deadlines no later than 30, checks each job-scoped constraint against the job record, and for each supplied forecast slot builds a `VisibleState` and calls `Context.build(view, snapshot, "flat")` as a consistency check.

2. At each decision slot the runner reads `view = simulator.state()` (`core.py:L132`). This is a `VisibleState`: the waiting and running jobs, completed job intervals, missed job ids, the visible carbon forecasts issued for that slot, the explicit list of slots with no forecast, and the id of the constraint snapshot. Future arrivals and realised carbon are not in it; they live in the private episode.

3. For the four non-model systems, `_policy_output` (`runner.py:L269-L284`) calls `retrieve(view, episode.snapshot).context` and passes that `Context` to the policy. For the plain LLM, `plain()` (`runner.py:L309-L340`) does the same and records a blocked decision if retrieval raises. For the agent, `_model_step` builds a harness with `new_harness` (`experiments/models.py:L245`) and calls `agent_step` (`models.py:L263`) at each slot; the harness's retrieve node calls `retrieve(st["view"], st["snapshot"], representation="graph").context` (`agent/harness.py:L121-L128`).

4. Inside `retrieve()` (`knowledge/retrieval.py:L267-L295`) two things happen independently. `build_graph(state, snapshot)` builds the RDF graph, projecting constraints through `visible_constraints_for` so constraints of not-yet-arrived jobs cannot appear (`graph.py:L126-L204`), and the six `query_*` helpers run SPARQL against it. Separately, `get_context` (`retrieval.py:L213-L246`) calls `Context.build`, which projects the same visible constraints and sources from the Pydantic records and hashes the result. The flat query results and the `Context` are returned together in a `RetrievalResult`, but only the `Context` is used downstream.

5. The agent harness renders the proposal prompt with `render_proposal(context)` (`agent/renderers.py`), which requires `representation == "graph"` and inserts `context.content.to_json()` into the prompt template `prompts/agent/proposal.md`. The plain model does the equivalent with `render_messages` in `llm/plain.py`, requiring "flat". The same JSON content is used by both. The greedy policies read capacity from `context.content.constraints` (`policies/greedy.py:L154-L162`).

6. The model's response is parsed into a `Plan`. The harness calls `check_schedule(candidate.plan, st["view"], st["snapshot"])` (`harness.py:L218`; `verification/checker.py:L37-L350`). The checker takes the state and the snapshot, not the context or the graph. If the check fails, the agent gets one repair attempt with the failure messages; if that fails it falls back to a deterministic greedy policy (A), and a call cap of three model calls per decision applies. The plain model gets a single call with no repair or fallback (`docs/INTERFACES.md`, `checklist L68`).

7. The controller (`runtime/controller.py:L41`, `execute_step`) rechecks the plan against the latest state with `recheck_schedule` (`controller.py:L100`; `checker.py:L15-L35`), which rebinds the state version without relabeling an old check as a pass, and only then builds `ApprovedActions` from the checked plan (`controller.py:L105`, `ApprovedActions.from_checked_plan`). The controller accepts only a `DecisionRecord`, never a ready-made `ApprovedActions` (`controller.py:L49`).

8. The simulator's `step` (`core.py:L163-L231`) accepts only a runtime-issued `ApprovedActions` object and re-checks, for the whole batch, the episode/slot/version binding, Q01 (no starts after slot 23), the existence of each waiting job, the deadline and episode end, nonflexible timing and capacity in every affected slot. Any failure rejects the whole batch and the slot still advances.

9. After 30 slots, `result()` returns an `EpisodeResult`; impact accounting is done afterwards by `simulator/impact.py:L55` (`account_realized`) using the private realised carbon and the shared formulas in `metrics/impact.py`.

The reference stack sits beside this path, not inside it. During development, `training/pipeline.py:L40-L80` (`build_labeled_corpus`) collects candidate decisions from private development episodes, using persistence forecasts, and calls `label_episode`, which calls `solve_visible` (optionally through the label cache) and attaches labels. The hindsight code in `reference/hindsight.py` consumes a `PrivateEpisode` directly and writes sealed export files. Searching the package for callers shows that `solve_visible` and the label functions are called only from `training/pipeline.py` and from tests; no runtime scheduling component calls the solver, and no code outside `reference/` and `schemas.py` mentions hindsight.

### 2.3 Text diagram

```
              PRIVATE (never shown to policies)                     POLICY-VISIBLE
   +--------------------------------------------+      +------------------------------------+
   | PrivateEpisode: all jobs, future arrivals, |      | ConstraintSnapshot (F02): site,    |
   | realised carbon, split and seed labels     |      | constraints, sources, ids          |
   +----------------------+---------------------+      +----------------+-------------------+
                          |                                              |
                 SchedulingSimulator.reset/state()                       |
                          |                                              |
                          v                                              |
                 VisibleState (F02, strict, hashed) <--------------------+
                          |
          +---------------+--------------------------------------------+
          |                                                            |
          v                                                            v
  knowledge.retrieve(state, snapshot)                          verification.check_schedule
   |                    |                                       (reads state + snapshot directly)
   |  build_graph()     |  get_context() -> Context.build()                ^
   v                    v  (from F02 records, NOT from the graph)          |
 RDF graph       Context(representation="graph"|"flat", content_hash)     |
   |                    |                                                  |
   v                    +--> agent prompt (graph label)  --> LLM --> Plan -+--> repair x1 --> greedy_a fallback
 SPARQL query_*         +--> plain prompt (flat label)   --> LLM --> Plan -+
   |                    +--> greedy / trained policies (capacity from context.content)
   v                    +--> solve_visible (reference, development only)
 RetrievalResult.{jobs,forecasts,constraints,...}
   (flat lists: inspected by tests, consumed by nobody downstream)

 Plan --> ExecutionController.execute_step --> recheck_schedule (latest state) --> ApprovedActions
      --> SchedulingSimulator.step (re-checks Q01, deadline, nonflexible, capacity; rejects whole batch on error)

 Offline, beside the runtime path:
   training/pipeline.build_labeled_corpus --> collect_decisions --> label_episode --> solve_visible
        (certified_optimal only becomes a definite label)  --> LabelCache (immutable, hash-keyed)
   reference/hindsight.generate_hindsight_reference(PrivateEpisode) --> sealed export outside a Git checkout
   SHACL validate_graph(graph): called by tests and scripts/smoke_dependencies.py only
```

### 2.4 Which steps are connected

| Step | State in the current implementation | Evidence |
|---|---|---|
| Visible state to RDF graph | Connected; the graph is rebuilt on every `retrieve()` call | `retrieval.py:L267-L295` |
| Graph to SPARQL results | Connected | `retrieval.py:L27-L101`, `L213-L246` |
| SPARQL results to `Context`, agent, plain model, policies, solver, checker | Not connected; each reads F02 records. Probe: replacing all SPARQL output left the context hash unchanged | probe P1 |
| Graph construction as a failure dependency | Connected; if `build_graph` raises, `retrieve()` raises, the agent harness marks the step fatal and the plain runner records a blocked decision | probe P2; `harness.py:L121-L128`; `runner.py:L309-L323` |
| SHACL on the production path | Not connected; no non-test caller of `validate_graph` | grep; probe P2b (0 pySHACL calls inside `retrieve()`) |
| Graph-retrieved capacity driving the checker | Demonstrated only inside a test helper (`_snapshot_from_graph`) | `tests/knowledge/test_graph_driven_constraints.py:L56-L68`, `L121` |
| Context to LLM prompt | Connected; the whole `ContextContent` JSON is placed in the prompt | `agent/renderers.py`, `llm/plain.py` |
| Plan to checker, repair, fallback, controller, simulator | Connected | `harness.py:L82-L111`, `L218`; `controller.py:L100`; `core.py:L163-L231` |
| Reference solver to labels to training | Connected for development | `training/pipeline.py:L40-L80` |
| Reference solver to runtime scheduling | Not connected, by design | caller search |
| Hindsight to any consumer in the package | Not connected in code; artifacts are exported for offline use | caller search; `hindsight.py:L518` |
| `reject_hindsight_in_context` | Defined and tested, but with no caller on any production path | grep; `tests/reference/test_hindsight.py:L192` |

### 2.5 Can the agent bypass the ontology, and is the ontology a runtime dependency?

The agent cannot bypass the retrieval call, because the harness's first node is `_retrieve` and the model prompt is built only from the context it returns. In that narrow sense retrieval is mandatory. But what the agent receives is the Pydantic-derived content, so there is nothing in the graph that the agent could miss by bypassing it, and no way for the agent to query the graph directly (it has no tools that do so). The agent's system prompt calls it "the ontology-grounded data-center scheduling agent" (`prompts/agent/system.md`); that is a name, not a mechanism.

Using the brief's four categories, the ontology and graph are best described as follows. They are a verification and specification mechanism at test time (SHACL shapes and the tests that apply them). They are a preparation mechanism only in the sense that the vocabulary was designed to describe the same records the pipeline uses. They are a runtime dependency only as a failure point. They are not a runtime source of facts.

### 2.6 Cross-check against the documentation

The architecture document's planned data flow states that "SHACL validates structure before an episode" (`docs/ARCHITECTURE.md:L145`). No code on any path I traced does that; the sentence is documented intent. The "Two different graphs" paragraph (`ARCHITECTURE.md:L165`) is accurate: Context comes from F02 inputs, and the K03 tests do not yet establish that graph-query results drive the checker. The module docstring of `tests/knowledge/test_graph_driven_constraints.py` claims that its tests "prove that the RDF graph projection (K01/K02) is the source of truth for the production schedule checker (A03)". That is stronger than what the tests do, which is to rebuild a snapshot from SPARQL output inside the test and give it to the checker. The existing in-repository R02 draft (`docs/report/R02_ONTOLOGY_AND_REFERENCE_METHODS.md`) is cautious on these points and agrees with this report that the Agent receives "graph-grounded context" and the plain model "equivalent flat facts", which it calls "matched-information design"; it also says this "does not prove equivalence of model attention". It is worth comparing any new text against it.

### 2.7 Additional files read and why

| File | Why it was needed |
|---|---|
| `dc_sustainability/agent/renderers.py`, `prompts/agent/*.md` | To establish what the LLM actually receives from the context |
| `dc_sustainability/llm/plain.py` | To see which context representation the plain model accepts, and whether it contains a hindsight guard |
| `dc_sustainability/experiments/runner.py` | To trace how simulator state reaches `retrieve()` for every system |
| `dc_sustainability/runtime/controller.py` | To see the recheck and approval step between plan and simulator |
| `dc_sustainability/policies/greedy.py` | To see whether a policy reads graph-derived or record-derived constraints |
| `dc_sustainability/training/pipeline.py` | To find the only production caller of the label functions and solver |
| `dc_sustainability/metrics/impact.py` | To read the shared energy and carbon formula and its refusal rules |
| `dc_sustainability/data/materialize_development.py` | To read the persistence forecast adapter and, later, to explain a version-guard test failure |
| `docs/handoffs/O03_HINDSIGHT_EXPORT.md`, `LEGACY_LABEL_AUDIT_2026-11-04.md`, `VED_REFERENCE_MANAGER_REVIEW.md`, `O01_EXHAUSTIVE_ORACLE_REVIEW.md` | Because the brief asks about tie-breaking, label ambiguity and hindsight; these record decisions the source alone does not explain |
| `scripts/smoke_dependencies.py` | To determine whether SHACL is exercised outside tests |
| `.github/workflows/bootstrap.yml`, `requirements/*` | Required by the brief for CI and dependency versions |

---

## 3. Ontology and knowledge graph

### 3.1 How the ontology is defined and represented

The ontology is a Turtle file, `ontology/dc-sustainability.ttl` (349 lines), whose default prefix `:` is the project namespace `https://data-center-agentic.example.org/sched#` (conventionally written `sched:`). It declares an `owl:Ontology` with version IRI `.../sched/1.0.0` and `owl:versionInfo "1.0.0"` (ontology revision 2026-10-24, header lines 1 to 22). Its classes are `owl:Class` declarations with a small number of `rdfs:subClassOf` axioms, and its properties are `owl:DatatypeProperty` or `owl:ObjectProperty` declarations with domains and ranges. It is an annotation-level vocabulary: it contains no OWL restrictions, cardinality axioms or property characteristics. Structural requirements are expressed separately as SHACL shapes in `ontology/shapes.ttl` (431 lines).

RDFLib is used throughout. `dc_sustainability/knowledge/ontology.py` loads both Turtle files offline with `load_ontology_graph` and `load_shapes_graph`, and `graph.py` builds data graphs with `rdflib.Graph`, `Namespace`, `Literal` and `URIRef`. The pinned version is rdflib 7.6.0. The ontology revision is checked by `test_ontology_declares_version`.

A header comment in the ontology states its design intent: the file declares "the static schema/ontology layer", "kept separate from per-episode facts and runtime traces". That intent is realised in the sense that the ontology file contains no instances, the data graph contains no schema, and runtime traces are stored elsewhere (section 3.6).

### 3.2 Namespaces

| Prefix | IRI | Use in source |
|---|---|---|
| `sched:` (default `:`) | `https://data-center-agentic.example.org/sched#` | All project classes and properties; also the IRIs of instances, formed by appending the F02 identifier (`graph.py:L18-L20`, `_iri`) |
| `brick:` | `https://brickschema.org/schema/Brick#` | `Site` subclass axiom; explicit type on site nodes; required by `SiteShape` |
| `prov:` | `http://www.w3.org/ns/prov#` | Subclass and subproperty axioms in the ontology |
| `qudt:` | `http://qudt.org/schema/qudt/` | `GramPerKiloWattHour` is declared a subclass of `qudt:Unit` |
| `unit:` | `http://qudt.org/vocab/unit/` | Bound in the ontology and in `ontology.py:L29` (`QUDT_UNIT`), and used in the ontology's own unit declarations |
| `sh:` | `http://www.w3.org/ns/shacl#` | The shapes file |

The `sched` namespace uses the reserved example domain `data-center-agentic.example.org`, so the IRIs are identifiers, not dereferenceable resources. Instance IRIs are the bare F02 identifiers appended to the namespace, so a job `J1`, a constraint `CON-CAP-01` and a fact `FACT-CI-0` live in the same flat identifier space. The code relies on identifiers being unique across record types.

### 3.3 Classes

The ontology declares the classes below. The last column reports what `build_graph` emits, determined by reading `graph.py` and by a probe that counted `rdf:type` triples in the graph for the hand-built example (171 triples in total).

| Class | Line in ttl | Parent | Meaning | Emitted by `build_graph` |
|---|---|---|---|---|
| `Episode` | 31 | none | One scheduling episode at a given slot and state version | Yes (one node) |
| `Site` | 35 | `brick:Building` | The data-center site and its fixed parameters | Yes; also typed `brick:Building` explicitly |
| `Job` | 40 | none | A schedulable job | Yes, as a second type on every job node |
| `WaitingJob` | 44 | `Job` | Arrived and not started | Yes |
| `RunningJob` | 49 | `Job` | Started and not finished | Yes (`graph.py:L161-L163`); none in the example graph |
| `CompletedJob` | 54 | `Job` | Finished; only its interval is visible | Yes (`graph.py:L169-L177`); none in the example graph |
| `Slot` | 59 | none | An hourly decision slot | No |
| `CarbonFact` | 63 | none | Parent of carbon values | Not directly |
| `CarbonObservation` | 67 | `CarbonFact` | A realised value | No (realised carbon is private by design) |
| `CarbonForecast` | 72 | `CarbonFact` | A forecast visible at a decision slot | Yes (7 in the example) |
| `Constraint` | 77 | none | A capacity, arrival, deadline, nonflexible or freshness limit | Yes (3 in the example) |
| `Source` | 81 | `prov:Entity` | A provenance record for a constraint or fact | Yes; typed `sched:Source` and `sched:Entity`, not `prov:Entity` |
| `Decision` | 86 | `prov:Activity` | A scheduling decision | No |
| `Check` | 91 | `prov:Activity` | A verification outcome | No |
| `GramPerKiloWattHour` | 345 | `qudt:Unit` | Project unit for carbon intensity | Referenced as a unit IRI |

Searches of all Python files for `sched:Decision`, `sched:Check`, `Slot` and `wasGeneratedBy` found no producer. The classes `Slot`, `CarbonObservation`, `Decision` and `Check`, and the property `wasGeneratedBy`, are therefore declared in the ontology but never instantiated by any code in this commit. Status for these: documented in the ontology only. The brief asks how time slots, carbon observations, decisions and verification results are represented. The accurate answer is that slots are plain integer literals (`arrivalSlot`, `validSlot` and so on), realised carbon is excluded from the policy-visible graph, and decisions and verification results are not represented in RDF at all; they are F02 records (`DecisionRecord`, `CheckResult`) persisted by the runtime's `TraceStore` (`runtime/controller.py`), outside the graph.

### 3.4 Properties and relationships

| Property | Kind | Domain to range | Purpose | Emitted |
|---|---|---|---|---|
| `currentSlot`, `stateVersion`, `snapshotId` | Datatype | Episode | Position of the visible state and the constraint snapshot it was built against | Yes |
| `missingCarbonSlot` | Datatype | Episode | Explicit record that no forecast is available for a slot | Only when slots are missing |
| `missedJob` | Object | Episode to Job | Jobs that have already missed their deadline | Only when present |
| `backgroundKw`, `pue`, `slotHours` | Datatype | Site | Fixed site parameters | Yes |
| `arrivalSlot`, `durationSlots`, `powerKw`, `deadlineSlot`, `flexible` | Datatype | Job | Job attributes | Yes |
| `startSlot`, `endSlot` | Datatype | Running or Completed job | Execution interval | When such jobs exist |
| `carbonValue`, `validSlot`, `issuedAtUtc`, `forecastKind` | Datatype | CarbonForecast | The value, the slot it applies to, when it was issued and its method (for example `persistence`) | Yes |
| `qualityStatus`, `pollutantBasis`, `intervalConvention`, `emissionsFactorType`, `slotMappingStatus` | Datatype | CarbonForecast | The semantic fields that record the unresolved Q05 questions | Yes |
| `validFromUtc`, `validToUtc`, `sourceSha256` | Datatype | CarbonForecast | Optional validity interval and source hash | When present |
| `constraintType`, `limitValue` | Datatype | Constraint | Which limit, and its numeric value | Yes |
| `appliesToSite`, `appliesToJob` | Object | Constraint to Site or Job | Scope of a constraint | Yes |
| `sourceVersion` | Datatype | Constraint | Optional version of the constraint source | When present |
| `source` | Object, subproperty of `prov:wasDerivedFrom` | Constraint to Source | Provenance of a constraint | Yes |
| `carbonSource` | Object, subproperty of `prov:wasDerivedFrom` | CarbonFact to Source | Provenance of a carbon value | Yes |
| `path`, `redistributionStatus`, `commit`, `sha256` | Datatype | Source | Where a source lives, its redistribution status, commit and hash | Yes (`commit`, `sha256` when present) |
| `unit` | Datatype | (none declared) | The original F02 unit string | Yes, but not declared in the ontology |
| `qudtUnit` | Object | (none declared) | A link to a QUDT or project unit | Yes |
| `unitCode` | Datatype | (none) | Declared as the way to carry the original unit literal | Never emitted; the code uses `unit` instead |

Entities are connected in a small number of ways. Constraints point to the site or to jobs they restrict (`appliesToSite`, `appliesToJob`) and to the source that justifies them (`source`). Forecasts point to the source of their values (`carbonSource`) and carry their slot as an integer. Jobs are not linked to the episode, and the site is not linked to the episode, in the emitted graph: they are found by type, not by relationship. The retrieval queries do not traverse more than one relationship at a time, so the graph is closer to a typed record store than to a rich knowledge graph. This is a description, not a criticism, since the scheduling problem is small. It does limit how much "reasoning over relationships" R02 can credibly claim.

The two source-link properties are separate on purpose. A test (`test_forecast_uses_carbon_source_not_source`) records the reason: because `source` has `Constraint` as its domain, using it on a forecast node would let RDFS inference classify the forecast as a Constraint. Keeping `carbonSource` distinct avoids that, which matters because the SHACL setup originally ran into inference problems (section 5.2).

### 3.5 Identifiers, units, timestamps and provenance

Identifiers. F02 identifiers become the local part of instance IRIs (`_iri`, `graph.py:L18`), and `_id` (`L23`) reverses the mapping. Each query result returns the identifier string, so the evidence identifiers that the agent is told to cite (`evidence_ids` in the context) are the same strings that appear in the graph.

Units. Every F02 value carries a unit string, and `add_unit_metadata` (`ontology.py:L214-L227`) writes `sched:unit` with that string and, when a mapping exists, `sched:qudtUnit` with an IRI, plus an `rdfs:comment`. Unknown or miscased codes raise `UnitMappingError`, so they cannot enter the graph. `map_unit` maps `kW`, `kWh`, `h`, `kg` and `1` to QUDT IRIs, `slot` to no IRI, and `g/kWh` to the project-defined `sched:GramPerKiloWattHour`. The project class carries a comment explaining that no official QUDT unit exists for grams of CO2e per kWh and that the pollutant basis is recorded separately. Values are never converted.

Two properties of the unit encoding limit what can be said about it. First, unit metadata is attached to the node, not to the property. A probe of the example graph found two unit literals on job `J1` (`kW` and `slot`), three on the site (`1`, `h`, `kW`), and one each on the constraint and forecast nodes. A reader of the graph cannot tell from the triples which unit belongs to `powerKw` and which to `arrivalSlot`. Only constraints and forecasts, which carry a single unit, are unambiguous. Second, the QUDT IRIs emitted by the code (`http://qudt.org/vocab/unit#Hour`, `#Kilowatt`, `#Unitless`) are not the IRIs the ontology file declares (`http://qudt.org/vocab/unit/HR`, `/KiloW`, `/UNITLESS`). Only the project-defined `GramPerKiloWattHour` IRI appears in both. A comment in `ontology.py` (lines 50 to 55) says the `#` form follows the pinned pyqudt 1.1.1 vocabulary, and a test hard-codes it (`test_map_unit_uses_canonical_qudt_iris`). I did not inspect pyqudt, so I cannot say which form is correct; what is verified is that the code and the ontology disagree. The documented unit prefix in `docs/ontology/README.md` follows the ontology (`/` form).

Timestamps. Forecast issue times are emitted as `xsd:dateTime` literals in UTC with a trailing `Z` (`graph.py:L84-L92`; `test_datetime_literals_carry_xsd_datatype`). Time within an episode is otherwise an integer slot index. The mapping from a slot to a UTC instant is not in the graph; it is supplied by the caller as a trusted decision time (for the checker and the solver) and, for development data, by the materialisation code (section 6.7).

Provenance. A `Source` node carries a path, a redistribution status, and optionally a commit and a SHA-256. Constraints and forecasts link to it, and SHACL checks that the link resolves to a `Source` (`ConstraintSourceReferenceShape`, `ForecastSourceReferenceShape`). The PROV-O alignment is by axiom only: `Source` is declared a subclass of `prov:Entity` and the two link properties are declared subproperties of `prov:wasDerivedFrom`, but the data graph asserts `sched:Source` and `sched:Entity` rather than `prov:Entity`, and SHACL runs without inference, so no PROV-O triple ever appears in the data. The `Decision` and `Check` classes that were meant to be `prov:Activity` subclasses, and the `wasGeneratedBy` property that was meant to link facts to them, are unused.

### 3.6 Static facts, episode facts and execution traces

The brief asks how these three are separated. The checklist's acceptance criterion for K01 is "static, episode and trace separation". In the implementation:

Static schema. The ontology file holds classes and properties only. It is loaded separately and passed to pySHACL as the ontology graph. It holds no site or job instances.

Episode facts. `build_graph` creates a fresh graph from one `VisibleState` and one `ConstraintSnapshot`. The site node and its parameters come from the snapshot, which is static for an episode, while jobs, forecasts, missing-slot markers, and execution intervals come from the state, which changes each slot. Both are in the same graph and nothing in the graph distinguishes "static site data" from "episode-specific data" other than the node type and the `Episode` node's `snapshotId` link by value.

Execution traces. They are not in the graph. `DecisionRecord` and `CheckResult` records, the attempt ledger and the controller's durable traces are stored by `runtime/` (`TraceStore`). `ARCHITECTURE.md:L165` states the intention: "Domain graphs, runtime traces and private labels stay separate." The separation therefore holds, but only because traces were never put into RDF. Status: separation implemented; trace representation in the ontology documented only.

### 3.7 External vocabularies: exact uses

Brick. `sched:Site` is a subclass of `brick:Building` in the ontology, `build_graph` adds `brick:Building` explicitly as a second type on the site node (`graph.py:L147`), and `SiteShape` requires `rdf:type` to have the value `brick:Building`. Because SHACL runs without inference, the explicit triple is necessary; a test removes it and expects validation to fail (`test_validate_graph_without_inference_fails_without_building_type`). No other Brick class or relationship is used. Brick adds a type label to the site; it does not contribute any scheduling semantics.

PROV-O. Used as described above: subclass and subproperty axioms in the ontology only. The ontology header also states that it is derived from Brick, PROV-O and QUDT via `prov:wasDerivedFrom` annotations.

QUDT. Used through `sched:qudtUnit` links to unit IRIs and a project unit class, with the namespace inconsistency noted above. No QUDT quantity kinds or dimension vectors are used.

No other external vocabulary is used. RDFS (`rdfs:label`, `rdfs:comment`, `rdfs:subClassOf`, domains and ranges) and OWL (`owl:Class`, property types, ontology versioning) are used in a minimal way. The accurate summary is that the ontology is a project vocabulary that cites three external ones, not a reuse of their modelling.

### 3.8 How graph facts are created, updated and retrieved

Created: all at once by `build_graph(state, snapshot)` (`graph.py:L126-L204`). The function adds the episode node, the site node, one node per waiting, running and completed job, one per visible forecast, one per visible constraint, and one per visible source. Constraints and sources are filtered through `visible_constraints_for` so the constraints of jobs that have not arrived cannot leak (`test_graph.py::test_infeasible_job_j3_not_in_graph`, `test_constraints_projected`).

Updated: never. There is no function that modifies a graph in place. A new graph is built at every call, and no graph survives between slots. The only code that mutates a graph is test code, which removes or adds triples to produce invalid or tampered graphs.

Retrieved: by the six SPARQL queries in section 4.

### 3.9 The role of the ontology in making constraints explicit

The ontology and graph make constraints explicit in three ways that are real and testable. Constraints are first-class nodes with an identifier, a type from a closed set (`capacity`, `arrival`, `deadline`, `nonflexible`, `freshness`), a numeric limit, a unit, a scope and a source. The capacity requirement is stated declaratively as a SHACL-SPARQL shape: exactly one capacity constraint per site, with the message "absence is not unlimited capacity" (`shapes.ttl:L342-L376`). And the graph-to-checker test shows that a capacity value read back out of the graph by SPARQL is the value the checker uses.

The same constraints are, however, equally explicit in the Pydantic `ConstraintSnapshot` that existed before the graph. The graph restates them in a second form. That is a legitimate contribution (a second, independent, standards-based description that can be validated by a different mechanism), but the report should present it as a specification and validation layer, and it should not suggest that the constraints would be invisible or unenforceable without it.

### 3.10 Discrepancies and gaps in the ontology layer

These were found by probe and by reading, and are all small. The unit IRIs differ between code and ontology. Unit metadata is node-level. `sched:unit` is used but not declared, and `sched:unitCode` is declared but never used. Fourteen declared properties are never emitted for the example graph; some (`startSlot`, `endSlot`, `missingCarbonSlot`) are conditional on the state and are emitted when applicable, while `commit`, `sha256` and others appear when source records have those fields. Four classes and one property have no producer. `Source` carries `sched:Entity` but not `prov:Entity`. None of these makes a test fail, and none changes a scheduling decision. They matter because they limit statements such as "the graph uses PROV-O for provenance" to "the ontology declares PROV-O alignment".

### 3.11 Test evidence for the ontology and graph

The four knowledge test files below were read in full. The counts are the numbers collected by pytest and the pass status is from my local run on CPython 3.12.3 (all 75 knowledge tests passed; the same suite passed on 3.13). "Establishes" and "does not establish" are my interpretation of the assertions, not claims made by the tests.

`tests/knowledge/test_ontology.py` (27 tests)

| Test (line) | What it does | Establishes / does not establish |
|---|---|---|
| `test_ontology_loads_offline` (23) | Loads the ontology graph; asserts it is non-empty and has an `owl:Ontology` node | Files parse offline. Not that the ontology is semantically consistent |
| `test_ontology_declares_version` (31) | Reads `owl:versionInfo` and compares with `ONTOLOGY_VERSION` | Version literal matches the code constant |
| `test_shapes_load_offline` (38) | Loads the shapes graph; asserts non-empty | Shapes parse. Not that each shape is correct |
| `test_map_unit_known_codes` (45) | Checks `map_unit` for kW, kWh, slot, h, kg, 1 | Code-side mapping table; the expected IRIs use the `#` form |
| `test_map_unit_uses_canonical_qudt_iris` (65) | Hard-codes expected `#`-form IRIs "against the pinned pyqudt 1.1.1 vocabulary" | That code matches the test's expectation; does not compare with the ontology file's `/` IRIs |
| `test_map_unit_g_per_kwh_uses_project_unit` (76) | `g/kWh` maps to `sched:GramPerKiloWattHour` | Project unit is used for carbon intensity |
| `test_map_unit_rejects_unknown_and_miscased_codes` (83) | Ten wrong spellings (`kw`, `KWH`, `g/kwh`, `MW`, `ft` and so on) raise `UnitMappingError` | Strict unit vocabulary; no silent unit coercion |
| `test_add_unit_metadata_adds_qudt_link` (90) | Writes `unit`, `qudtUnit`, `comment` triples for kW | Metadata shape on an isolated node |
| `test_add_unit_metadata_dimensionless_slot` (101) | `slot` gets a comment and no `qudtUnit` | Slot is treated as dimensionless |
| `test_add_unit_metadata_unknown_unit_raises` (115) | `MW` raises | Unknown units fail closed |
| `test_standard_fixture_graph_conforms` (122) | Hand-example graph validated with SHACL | The example conforms. Only one fixture |
| `test_validation_report_to_dict` (131) | `ValidationReport.to_dict` fields | Report serialisation |
| `test_graph_without_capacity_fails_validation` (143) | Snapshot without capacity; SHACL fails and text mentions capacity | SHACL detects missing capacity |
| `test_graph_with_bad_forecast_source_fails` (153) | Forecast pointed at a non-existent source IRI | Dangling forecast source is a violation |
| `test_graph_with_missing_unit_fails` (167) | Remove the unit literal from the capacity constraint | A constraint without a unit is a violation |
| `test_datetime_literals_carry_xsd_datatype` (178) | `issuedAtUtc` literal has datatype `xsd:dateTime` | Typed timestamps for forecasts only |
| `test_forecast_uses_carbon_source_not_source` (189) | Forecast has `carbonSource`, not `source` | Property discipline that avoids inference problems |
| `test_constraint_uses_source_not_carbon_source` (200) | The converse for constraints | Same |
| `test_site_is_typed_as_building` (210) | Site has `Site` and `brick:Building` types | The Brick usage is an explicit type |
| `test_job_is_typed_as_job` (220) | Waiting job has `WaitingJob` and `Job` | Explicit parent type |
| `test_validate_graph_accepts_external_shapes_and_ontology` (230) | Caller-supplied shape and ontology graphs | API flexibility |
| `test_validate_graph_without_inference_checks_explicit_types` (241) | Validation passes because Brick type is explicit | Why explicit types are emitted |
| `test_validate_graph_without_inference_fails_without_building_type` (251) | Remove the Brick type; validation fails | SHACL depends on the explicit triple |
| `test_validate_graph_rejects_rdfs_inference` (263) | `inference="rdfs"` raises `ValueError` | Inference is deliberately disabled |
| `test_completed_job_graph_conforms` (272) | State with a completed job validates | Completed-job shape works for one case |
| `test_duplicate_capacity_constraint_fails_validation` (291) | Add a second capacity constraint for the site | Duplicate capacity is a violation |
| `test_capacity_unit_must_be_kw` (309) | Capacity constraint given unit `slot` | Unit-consistency shape fires |

`tests/knowledge/test_graph.py` (13 tests; behaviour from the test docstrings, which are one-line statements of what each asserts)

| Test (line) | Behaviour | Note |
|---|---|---|
| `test_graph_is_rdflib_graph` (17) | `build_graph` returns an RDFLib graph with `sched` bound | Basic construction |
| `test_episode_triples_present` (25) | Episode has current slot, state version, snapshot id | Episode node content |
| `test_site_triples_present` (35) | Site has background, PUE, slot hours | Site node content |
| `test_waiting_jobs_present` (46) | J1 and J2 present with correct properties | Job content |
| `test_infeasible_job_j3_not_in_graph` (62) | J3 (arrives slot 4) absent at slot 0 | Future arrival not visible |
| `test_forecasts_present` (72) | Forecast nodes and values | Forecast content |
| `test_constraints_projected` (82) | Only site-wide and visible-job constraints appear | Visibility projection |
| `test_missing_capacity_not_in_graph` (97) | No capacity triple when the snapshot has none | Absence is not filled in |
| `test_no_private_keys_in_graph` (105) | No scenario, split or seed values in the graph | Privacy of fixture metadata |
| `test_running_job_triples` (115) | Running jobs carry start slot and job fields | Running jobs |
| `test_completed_job_triples` (136) | Completed jobs carry start and end slots | Completed jobs |
| `test_missing_carbon_slots_in_graph` (157) | Missing forecast slots recorded on the episode | Explicit missing-forecast marker |
| `test_source_triples_present` (176) | Source provenance records present | Source content |

These tests establish that the builder produces the intended triples for the hand-calculated fixture. They do not establish behaviour on generated development episodes; I found no test that builds and validates a graph from a real simulator-produced state across many slots. Running and completed job cases are each exercised once.

### 3.12 What the ontology section of R02 can safely say

The ontology is a documented, versioned project vocabulary with twelve SHACL shapes; it is instantiated, for every decision, as a per-slot graph of the visible facts; it partially reuses Brick, PROV-O and QUDT; and it is validated by SHACL in tests. It is not a runtime knowledge base, it is not updated, it holds no decisions or checks, and its PROV-O and QUDT alignment has the specific gaps listed above.

---

## 4. Retrieval and SPARQL

### 4.1 The queries that are implemented

`dc_sustainability/knowledge/retrieval.py:L27-L101` defines six SPARQL strings, each used by a `query_*` helper that converts rows into plain Python dictionaries (`L101-L212`). All queries use the `sched:` prefix and select on the explicit class.

Eligible jobs (`SPARQL_ELIGIBLE_JOBS`) selects every `sched:WaitingJob` together with its arrival slot, duration, power, deadline and flexibility, ordered by job. The `query_eligible_jobs` helper casts them to int, float and bool. Despite the name "eligible", the query does not test eligibility (for example whether the job is arrived or can still meet its deadline); a job is present in the graph only because the visible state listed it as waiting.

Running jobs (`SPARQL_RUNNING_JOBS`) selects `sched:RunningJob` with start slot, power and duration. Forecasts (`SPARQL_FORECASTS`) selects `sched:CarbonForecast` with value, valid slot, source, issue time and kind. Constraints (`SPARQL_CONSTRAINTS`) selects `sched:Constraint` with type, limit, unit, source, and optional site and job. Missing links (`SPARQL_MISSING_LINKS`) selects the `sched:missingCarbonSlot` values of the episode node. Site (`SPARQL_SITE`) selects the site's background load, PUE and slot hours.

### 4.2 A representative query, explained

```sparql
PREFIX sched: <https://data-center-agentic.example.org/sched#>
SELECT ?con ?type ?limit ?unit ?src ?site ?job
WHERE {
    ?con a sched:Constraint ;
         sched:constraintType ?type ;
         sched:limitValue ?limit ;
         sched:unit ?unit ;
         sched:source ?src .
    OPTIONAL { ?con sched:appliesToSite ?site }
    OPTIONAL { ?con sched:appliesToJob ?job }
}
ORDER BY ?con ?job
```

This is the query that carries the capacity limit. Every node typed `sched:Constraint` that has a type, a limit, a unit and a source is returned; the site and job scopes are optional because a constraint has one or the other. `query_constraints` turns each row into a dictionary with `constraint_id`, `constraint_type`, `limit_value` (float), `unit`, `source_id`, `applies_to_site` and `applies_to_jobs`. Two points follow from the query's form. A constraint without a source or a unit would be silently omitted from the result, rather than reported, because the pattern is a plain conjunction; SHACL is what would flag the omission. And a constraint that applies to several jobs yields several rows, one per job, with a scalar `applies_to_jobs`, whereas the F02 `Constraint` record holds a tuple. The graph-driven test has to wrap that scalar into a tuple (`_snapshot_from_graph`, `test_graph_driven_constraints.py:L56-L68`) before it can rebuild a snapshot.

### 4.3 What the flat results preserve

The brief asks how fact identifiers, source references, timestamps and units are preserved. The answer differs by query.

| Result | Identifier | Source | Timestamp | Unit | Not returned |
|---|---|---|---|---|---|
| Eligible jobs | `job_id` | none | none | none | no units, no source |
| Running jobs | `job_id` | none | none | none | |
| Forecasts | `fact_id` | `source_id` | `issued_at_utc` (string, `Z`-suffixed) | not selected | unit, quality status, pollutant basis, interval convention, factor type, slot-mapping status, validity interval, source hash |
| Constraints | `constraint_id` | `source_id` | none | `unit` | source version |
| Site | `site_id` | none | none | none | |

The forecast query is the most limited. The semantic fields that the project cares most about for Q05 (pollutant basis, interval convention, quality status) are in the graph but are not retrieved by the query. They reach the agent only through the `Context`, which carries the full F02 `CarbonForecast` records. The test `test_k02_exposed_query_values_match_canonical_facts` compares the retrieved forecast fields (value, slot, source, kind, issue time) with the canonical facts and passes in my run; it checks the columns that are exposed, and its own comment says it does not reconstruct a `Context` from RDF.

### 4.4 Data flow from graph construction to downstream use

The trace was given in section 2.2. In the terms of the brief's question 5, retrieved information flows into the downstream scheduling components in exactly one form: the `Context`, built from the F02 records, which is then used by the agent prompt, the plain prompt, the greedy and trained policies and the reference solver. The flat SPARQL lists in `RetrievalResult` are inspected by tests and by no production component. Question 6 (does the agent consume graph-derived information at runtime) therefore has a precise answer: it consumes a `Context` labelled "graph" whose content is derived from the Pydantic records, not from the RDF graph.

Probe results that support this are:

| Probe | Observation |
|---|---|
| Replace `query_constraints`, `query_eligible_jobs` and `query_forecasts` with fabricated or empty results, then call `retrieve()` | `Context.content_hash` unchanged; the flat `constraints` field in `RetrievalResult` followed the fabricated data |
| Make `build_graph` raise | `retrieve()` raises; in the harness this becomes a fatal step with the message "retrieval failed", and in the plain runner a recorded blocked decision |
| Spy on `pyshacl.validate` while calling `retrieve()` | Zero calls |
| Snapshot without capacity | `retrieve()` completes; SPARQL returns zero capacity rows; calling `validate_graph` on the same graph returns non-conformance with the messages "Site is missing a capacity constraint; absence is not unlimited capacity." and "A site must have exactly one capacity constraint in the visible graph." |

The docstring of `get_context` says directly that the content is identical across the two representations and that only the presentation label differs, and the docstring of `retrieve` calls the SPARQL results "a development convenience for inspection and testing" while the `Context` is "the authoritative policy input". Both agree with the probes. A reader of the docstring "content_hash proves graph/flat equivalence" should take it to mean equivalence of the two context presentations, not equivalence of the RDF graph and the flat records.

### 4.5 Alternative paths that bypass the graph

Every consumer reaches facts through the `Context` or the state and snapshot, so in practice the graph is bypassed by all of them. The checker takes the snapshot directly. The solver takes the `VisibleState` and a `Context`, and obtains capacity and the freshness limit from the context's constraints (`solver.py:L138-L142`). The simulator holds the private episode. The legitimate reason for these paths is that the F02 records are the single source of truth and the graph is derived from them; the consequence is that the graph cannot cause a scheduling difference.

### 4.6 Missing information versus a valid empty result

The brief asks how the system distinguishes the two. Retrieval itself does not. An empty list from `query_running_jobs` means no running job; an empty list from `query_constraints` could mean no visible constraint, or a graph that lost its constraints. The distinction is made elsewhere, by mechanisms that require presence:

For capacity, the checker returns an `error` outcome and an evidence record with status `missing` (tested by `test_missing_capacity_is_error_not_infinite_capacity`), the solver returns `insufficient_evidence` (`solver.py:L177-L179`), SHACL reports non-conformance, and reading `snapshot.capacity_kw` raises `MissingEvidenceError` (`schemas.py:L483`; `test_missing_capacity_raises_in_snapshot`). The distinction is made by the Pydantic property, not by retrieval.

For carbon forecasts, the F02 state carries an explicit `missing_carbon_slots` field, which the graph represents as `sched:missingCarbonSlot` and the missing-link query returns. The checker treats missing carbon as a reason to withhold impact claims, not as a physical violation, and the solver treats a job whose only feasible starts lack fresh carbon as `insufficient_evidence`, not `certified_infeasible`.

For future jobs, absence is by design: they are not visible, and the checker reports an unknown job without looking one up.

### 4.7 Test evidence for retrieval and consumers

`tests/knowledge/test_retrieval.py` (17 tests) and `tests/knowledge/test_consumers.py` (6 tests). All 23 passed in my local run on CPython 3.12.3.

| Test (line) | What it does | Establishes / does not establish |
|---|---|---|
| `test_query_eligible_jobs` (29) | Two waiting jobs returned; J1 power 40, duration 2; J2 power 30 | The query returns the fixture's jobs. Not eligibility logic |
| `test_query_running_jobs_empty` (41) | No running jobs at slot 0 | Empty case only |
| `test_query_forecasts` (48) | Seven forecasts; values 500 at slot 0 and 520 at slot 6 | Forecast rows for the fixture |
| `test_query_constraints` (59) | Capacity and J1 deadline present; J3's deadline absent | Visibility projection reaches SPARQL |
| `test_query_missing_carbon_slots` (70) | State with slots 0, 1, 2 missing returns `[0, 1, 2]` | Missing marker round trip |
| `test_query_site` (86) | Site id, background 40, PUE 1.0 | Site row |
| `test_context_hash_matches_flat_build` (99) | `get_context` hash equals `Context.build` hash | A wrapper test; both call `Context.build` |
| `test_graph_and_flat_context_same_hash` (107) | Graph and flat contexts share a hash and differ in label | Representation is a label only |
| `test_context_evidence_ids_match` (117) | Context evidence ids equal `evidence_ids_for` | Evidence-id derivation |
| `test_context_no_private_keys` (125) | No private keys in the context JSON | Privacy check |
| `test_retrieve_returns_full_result` (136) | Context hash equals flat build; 2 jobs, 7 forecasts, site id | Bundle contents |
| `test_retrieve_constraints_match_context` (149) | SPARQL constraint ids equal context constraint ids | Cross-check of graph vs records, on identifiers only |
| `test_retrieve_eligible_jobs_match_context` (158) | Same for jobs | Same |
| `test_retrieve_forecasts_match_context` (167) | Same for forecast fact ids | Same |
| `test_future_job_not_leaked` (179) | J3 and its deadline constraint absent at slot 0 | Visibility at one slot |
| `test_capacity_change_changes_context` (190) | 100 kW versus 70 kW changes the hash and the limit in the context | Constraint change reaches the context |
| `test_missing_capacity_raises_in_snapshot` (203) | `snapshot.capacity_kw` raises `MissingEvidenceError` | The failure is in the snapshot property, not in `retrieve()` |
| `test_k02_flat_context_enters_actual_plain_policy` (consumers, 20) | Real retrieval, real `PlainLLMPolicy`, synthetic HTTP server | The prompt equals `render_messages(context)`; J3's constraint is not in the prompt. A synthetic response, not a model |
| `test_k02_graph_presentation_is_not_accepted_as_plain_input` (37) | Graph-labelled context passed to the plain policy | `ValueError`, no request sent |
| `test_k02_capacity_value_reaches_real_fixed_checker` (50, two cases) | Capacity 100 and 70 go through `retrieve` and the real checker | Outcome pass at 100, fail at 70; also asserts `result.status != "pass"` because other rules remain unresolved |
| `test_k02_missing_capacity_stays_missing_at_checker_boundary` (76) | No capacity rows in the query result; checker status `error`; `ApprovedActions` cannot be built | Fail-closed at the checker |
| `test_k02_exposed_query_values_match_canonical_facts` (89) | Retrieved jobs, site and forecasts equal the canonical F02 values | Field-level equality for exposed columns; not a reconstruction from RDF |

What these tests do not establish: they use one hand-calculated state; they show consistency of graph and records at slot 0 of the fixture; and they do not show that any consumer reads the graph.

---

## 5. Validation and constraint enforcement

### 5.1 Three mechanisms, kept separate

The brief insists that SHACL not be confused with Pydantic or ordinary Python checks. The following classification is from the source.

| Mechanism | Technology | What it checks | When it runs |
|---|---|---|---|
| Graph validation | pySHACL 0.40.1 against `ontology/shapes.ttl`, `inference=None`, `meta_shacl=False` (`ontology.py:L164-L211`) | Structure of the RDF graph: required fields and datatypes on site, jobs, forecasts, constraints, sources and episode; exactly one capacity constraint per site; constraint units match their type; source references resolve | Tests, and a dependency smoke script on a toy fixture; not on the production path |
| Record validation | Pydantic 2.14.0 strict models in `schemas.py` | Types, ranges, id formats, constraint/job consistency, matching snapshot and state ids, resolution of source ids, duplicate capacity, `MissingEvidenceError` on absent capacity, canonical hashing | Whenever a record is constructed or `Context.build` is called, which is on every path |
| Runtime verification | Python in `verification/checker.py`, `rules.py` | Plan against state and snapshot: ids, binding, arrival and current slot, deadline, nonflexible, Q01, capacity, evidence citations, freshness | Before execution (`harness.py:L218`), again at the controller (`controller.py:L100`) |
| Simulator guard | Python in `simulator/core.py` | The same essential rules, applied to approved starts | Every step |

### 5.2 The SHACL shapes

`ontology/shapes.ttl` defines twelve node shapes: `SiteShape` (L17), `JobShape` (L46, targeting waiting and running jobs), `RunningJobShape` (L83), `CompletedJobShape` (L93), `CarbonForecastShape` (L110), `ConstraintShape` (L203), `SourceShape` (L293), `EpisodeShape` (L319), `CapacityEvidenceShape` (L342), `UnitConsistencyShape` (L378), `ConstraintSourceReferenceShape` (L401) and `ForecastSourceReferenceShape` (L417).

Property shapes require single occurrences with datatype and range restrictions. For the site, background load must be a non-negative double, PUE at least 1.0, slot hours positive, and the type must include `brick:Building`. Job shapes require integer arrival and duration with minimum values and the other job fields. The constraint shape (L203 onward) requires a constraint to apply to exactly one of a site or a non-empty job list, requires capacity constraints to apply to a site with a positive limit, and requires slot-valued constraints (arrival, deadline, nonflexible, freshness) to have a non-negative integer limit. The capacity shape uses SHACL-SPARQL: it fires when a site has no capacity constraint ("Site is missing a capacity constraint; absence is not unlimited capacity.") or has two ("Site has more than one capacity constraint; scheduling requires a single unambiguous limit."). The unit shape fires when a capacity constraint's unit is not `kW` or a slot-valued constraint's unit is not `slot`. The two source-reference shapes require that the linked node is a `sched:Source`.

SHACL is run with inference disabled. The documentation (`docs/ontology/README.md`) and a code comment give the reason: pySHACL's RDFS expansion applies the waiting-job and running-job requirements to completed-job views, which do not contain those fields, so the function raises if any other inference mode is requested. Explicit types are therefore required in the data, which is why the builder asserts both `sched:Job` and `sched:WaitingJob` and `brick:Building`.

What SHACL does not check. A changed numeric limit is not a violation: the test `test_tampered_graph_capacity_fails_closed` states in its docstring that "SHACL does not catch a changed numeric limit". It does not check that a plan is feasible, that a start fits, or that a forecast is fresh. It does not check that the graph is consistent with the Pydantic records; there is no code that compares the two (the nearest thing is a test that compares identifiers).

### 5.3 Is SHACL executed, and when

`validate_graph` is exported from `knowledge/__init__.py` and is called in tests (`test_ontology.py`, `test_graph_driven_constraints.py`) and in `scripts/smoke_dependencies.py:L37-L58`, where a toy two-triple fixture checks that pySHACL works. No function in `dc_sustainability/` other than its definition and re-export refers to it. The project's `ARCHITECTURE.md:L145` says "SHACL validates structure before an episode"; `README.md:L233` says smoke checks run "SHACL/SPARQL". The README sentence is accurate for the smoke script; the architecture sentence describes planned behaviour that is not wired to any runner. The architecture document also lists "graph validation" among planned CLI operations. Status: implemented as a library function; tested; not integrated into the production path.

### 5.4 Pydantic and schema-level enforcement

`Context.build` (`schemas.py:L966-L1014`) refuses to build a context unless the state and snapshot agree: it raises `ContractError` if the constraint snapshot ids differ, if the site differs, if the state's constraint ids are not exactly the policy-visible constraints, if visible facts or constraints reference source ids missing from the snapshot, and if job-scoped constraints conflict with the job records (`_validate_job_constraint_consistency`). The `capacity_kw` property of the snapshot raises `MissingEvidenceError` rather than returning a default when no capacity constraint exists (documented at `schemas.py:L447`, raised at `L483`), and duplicate capacity constraints are rejected at the schema level (`test_schema_rejects_duplicate_capacity_constraints`). `visible_constraints_for` (`L756`) filters constraints to the jobs and slots visible in the state.

### 5.5 Runtime verification

`check_schedule(plan, visible_state, constraints)` (`checker.py:L37-L350`) revalidates its inputs strictly, then builds a list of named checks: `schema`, `freshness`, `ids`, `evidence`, `timing`, `deadline`, `nonflexible` and `capacity`, each with an outcome of pass, fail, error or skipped, plus violation records with the offending slots and constraint ids. The capacity check (`L291-L349`) computes background plus running plus newly started load in every slot of each half-open job interval and compares it with the single capacity constraint, before PUE. If capacity is absent it appends an error outcome and a `missing` evidence record (`L296`, `L317`). `rules.py` supplies `legal_starts` (`L14`), which enumerates starts that respect arrival, deadline, nonflexibility, Q01 (last start 23) and capacity under known reservations, and `assess_forecasts` (`L66`), which computes the union of slots required by all legal candidates and flags missing, stale, future-issued and beyond-horizon slots. Freshness uses the authoritative freshness constraint, capped at two slots (`min(2, ...)` at `rules.py:L81`); with no freshness constraint it raises `MissingEvidenceError`.

`recheck_schedule` (`checker.py:L15-L35`) is used by the controller. For a plan from the same episode and slot, it rebinds the state version to the latest state, reruns `check_schedule`, and returns the result under the original plan hash, so an old check is never relabelled as a pass for new state.

### 5.6 Do policies and the independent checker use the same constraint records?

Yes, with the qualification that they use them in record form, not graph form. The checker reads the `ConstraintSnapshot`. The greedy policies read `context.content.constraints`, which `Context.build` obtained from the same snapshot through `visible_constraints_for` (`greedy.py:L154-L162`, which returns no capacity if there is not exactly one). The solver reads capacity and the freshness limit from the same context. The simulator reads `episode.snapshot.capacity_kw`. So a single edit to the snapshot changes all of them, and the tests show this for the checker and the context (100 kW to 70 kW). That is the intended meaning of "shared constraint records" in the project documents.

The independent evaluation validator (`evaluation/validator.py`) is a separate implementation, as `AGENTS.md` requires. A search of the package found no import of `check_schedule` or `verification.checker` under `evaluation/`; that is consistent with independence, but I did not compare the two implementations line by line.

### 5.7 How missing capacity is prevented from becoming unlimited capacity

The same principle is implemented four times, at four different layers, and each layer has at least one test.

| Layer | Behaviour | Test |
|---|---|---|
| Snapshot property | `capacity_kw` raises `MissingEvidenceError` | `test_retrieval.py::test_missing_capacity_raises_in_snapshot` |
| SHACL | Missing or duplicate capacity is a violation | `test_ontology.py::test_graph_without_capacity_fails_validation`, `test_duplicate_capacity_constraint_fails_validation` |
| Checker | Outcome `error`, evidence `missing`, no `ApprovedActions` can be built | `test_checker.py::test_missing_capacity_is_error_not_infinite_capacity`; `test_consumers.py::test_k02_missing_capacity_stays_missing_at_checker_boundary`; `test_d03_consumer.py::test_missing_capacity_never_becomes_unlimited_for_generated_jobs` |
| Solver | `insufficient_evidence`; no schedule, no labels | `test_solver.py::test_missing_capacity_is_insufficient_evidence`; `test_labels.py::test_missing_capacity_labels_are_none` |
| Greedy policy | `_capacity_kw` returns `None` unless exactly one capacity limit exists | (source only) |

The retrieval layer is the one place that does not stop: with capacity missing, `retrieve()` completes and the SPARQL result simply has no capacity row.

### 5.8 Evidence that changing a graph-defined constraint changes behaviour without code or prompt changes

Three independent pieces of evidence exist, with different strengths.

1. `test_checker.py::test_constraint_change_100_to_70_changes_actual_check_without_code_change` (line 83) builds two snapshots differing only in the capacity limit and shows that the checker's capacity outcome flips from pass to fail. This establishes that the checker is driven by the snapshot record. No graph is involved.

2. `test_retrieval.py::test_capacity_change_changes_context` (190) shows the context hash and the limit in the context change with the capacity limit. This establishes that the context is driven by the snapshot, and `test_consumers.py::test_k02_capacity_value_reaches_real_fixed_checker` shows retrieved capacity of 100 and 70 and the checker outcomes pass and fail.

3. `test_graph_driven_constraints.py::test_retrieved_capacity_drives_checker_result` (121) is the graph-driven version. For capacities 100 and 70 it builds the graph, reads the capacity back with `query_constraints`, rebuilds a `ConstraintSnapshot` from the SPARQL rows with the test-local helper `_snapshot_from_graph`, and gives that snapshot to `check_schedule`. The result is pass at 100 kW and fail at 70 kW. `test_tampered_graph_capacity_fails_closed` (229) goes further: it edits the graph's capacity to 200 kW, rebuilds the snapshot, and shows the checker passes a plan that the authoritative 100 kW snapshot would pass anyway (a 40 kW job on a 40 kW background) while the retrieved context hash differs from the flat hash. The test's docstring says the regression "proves the checker is driven by the retrieved graph value", but the pass outcome is the same as it would be with the untampered 100 kW snapshot, so the assertions that actually discriminate are that the rebuilt snapshot reports 200 kW instead of 100 kW and that the context hash differs.

These show that if a component were wired to take capacity from the graph, a change in the graph would change its outcome. They do not show that the production components are so wired, because they are not. The prompt is unchanged between the 100 kW and 70 kW cases in the checker tests simply because no model is involved. The brief asks for evidence that the behaviour changes "without changing the code or prompt": for the checker and the context, that is demonstrated; for an actual agent decision it is not, since no test or recorded run varies capacity and observes a model's decision.

The project's own `docs/team/03_RESPONSIBILITY_CHECKLIST.md:L52` sets the K03 bar as "100-to-70 kW test changes decision without code/prompt edits". The checker-level tests meet the letter of that for the checker's decision. Whether it meets the intent depends on whether "decision" means the checker's verdict or the agent's choice.

### 5.9 Graph-driven constraint tests, listed

`tests/knowledge/test_graph_driven_constraints.py` (12 tests; all passed in my local run on 3.12.3).

| Test (line) | Behaviour | Establishes / does not establish |
|---|---|---|
| `test_graph_conforms_for_single_job_state` (73) | Single-job fixture graph validates | One fixture conforms |
| `test_sparql_retrieves_capacity_constraint` (81) | SPARQL returns the capacity constraint with its limit | Query finds capacity |
| `test_capacity_100_kw_allows_single_job` (94) | Checker passes a 40 kW job at 100 kW | Boundary case with a 40 kW background |
| `test_capacity_70_kw_blocks_single_job` (106) | Checker fails the same plan at 70 kW | Same |
| `test_retrieved_capacity_drives_checker_result` (121) | Snapshot rebuilt from SPARQL feeds the checker; 100 passes, 70 fails | Graph-to-checker edge exists only in the test helper |
| `test_missing_capacity_fails_closed` (133) | No capacity: SHACL non-conformant, SPARQL has no capacity row, checker `error` | Layers agree on missing capacity |
| `test_wrong_capacity_unit_fails_shacl` (152) | Capacity with the wrong unit fails SHACL | Unit shape |
| `test_dangling_capacity_source_fails_shacl` (166) | Capacity source that does not resolve fails SHACL | Source-reference shape |
| `test_retrieve_bundles_capacity_context_and_constraints` (178) | `retrieve` returns the capacity in both the context and the flat constraints | Consistency of the bundle |
| `test_capacity_change_changes_retrieved_context_hash` (191) | Different capacity gives a different context hash | Hash sensitivity |
| `test_schema_rejects_duplicate_capacity_constraints` (200) | Pydantic rejects two capacity constraints | Schema-level, not SHACL |
| `test_tampered_graph_capacity_fails_closed` (229) | Edited graph capacity reaches the checker; SHACL does not catch the numeric change | Same limitation as above |

### 5.10 How the mechanisms complement each other

SHACL gives a declarative statement of what a valid visible graph looks like and a way to check graphs without running the scheduler; its checks are structural and cannot reason about plans. Pydantic and `Context.build` guarantee that every record entering any component is well formed and mutually consistent, and are the layer that actually refuses missing capacity in production. The runtime checker applies the scheduling rules to a concrete proposal, and the simulator applies them a second time to what is approved. The tests are written so that for capacity the four layers agree with one another. The division of labour that R02 can describe is therefore: the ontology and SHACL specify and validate the shape of facts, Pydantic enforces it in the running system, and the checker enforces the physical rules on plans. R02 should avoid saying that the ontology "guarantees" scheduling correctness. The ontology constrains the representation, not the schedule.

---

## 6. Simulator and reference optimisation

### 6.1 The physical scheduling model

A site is described by an F02 `Site` record: an identifier, a constant background load in kW, a PUE factor (at least 1) and a slot length in hours (required to be 1 by the simulator). A job is an F02 `Job`: an identifier, an arrival slot, a duration in whole slots, a constant power draw in kW, a deadline slot and a flexibility flag. The site capacity is not part of the site record; it is a constraint of type `capacity` in the `ConstraintSnapshot`, so that capacity has a source and a unit like every other constraint (`docs/ARCHITECTURE.md`, "capacity is not duplicated in site configuration"). Time is discretised into 30 hourly slots, of which slots 0 to 23 are decision slots (new starts are allowed) and slots 24 to 29 are completion slots (running work finishes, no new starts). The rule that no job may start after slot 23 is the agreed decision Q01, enforced in the simulator (`core.py:L180-L181`), the checker (`rules.py:L19`, `min(23, ...)`) and both solvers.

Feasibility is defined by four rules. A job starts once, at or after its arrival and at or after the current slot. It completes by its deadline, meaning `start + duration <= deadline` (a half-open interval, so a job that starts at slot 5 with duration 2 occupies slots 5 and 6 and meets a deadline of 7); a job whose slack is negative is deliberately representable (the "impossible" job J3 in the hand fixture and the `infeasible` scenario). A nonflexible job must start at its arrival slot. In every slot the sum of background load, running jobs and newly started jobs must not exceed capacity. Capacity is an IT-power limit, so it is compared before PUE is applied (tested by `test_exact_it_capacity_before_pue_is_allowed`, where 40 + 40 + 20 = 100 passes with PUE 1.2).

Execution is non-preemptive. `SchedulingSimulator.step` takes a runtime-issued `ApprovedActions`, applies all validated starts at the current slot, advances running jobs, retires those that finish, marks jobs that can no longer meet their deadline as missed, and increments the slot (`core.py:L163-L231`). A batch is atomic: if any start is invalid, none is applied, the rejection reason is recorded in the transition, and the slot still advances. `state()` (`core.py:L132-L157`) returns only waiting jobs that have arrived and are not running, completed or missed, the forecasts issued for the current slot, and an explicit list of slots in the next 24 (bounded by 30) for which no forecast was supplied. Missing forecasts are therefore visible to policies as an explicit fact. A `reset` call with no forecasts means "unavailable evidence", never a conversion of private actual values (`core.py:L50-L54`, docstring).

### 6.2 Energy and carbon calculations

The shared formulas are in `metrics/impact.py` and are used by the simulator's accounting adapter (`simulator/impact.py:L55`, `account_realized`) and by the solver's candidate construction. For one slot the facility energy is PUE times the sum of job load and background load times the slot length in hours (`impact.py:L251-L252`), and emissions in kilograms are energy in kWh times carbon intensity in g/kWh divided by 1000. PUE therefore multiplies energy and emissions, and does not enter the capacity check. Missing carbon leaves emissions as `None`, never zero, and the module refuses to report savings when carbon is missing, the baseline is zero, the completed-job sets differ, work is unfinished, horizons differ or inputs differ (the `Blocked` reasons include `missing_carbon`, raised at `impact.py:L335`; `compare` at `L310`). The docstring records that the pollutant basis (CO2 versus CO2e) is unresolved under Q05 and that no label is implied.

`account_realized` uses the realised carbon of the private episode and the executed starts, so it is evaluation-side code. The reference solver uses a narrower quantity, job emissions only, because background energy is the same for every schedule: for a candidate start it multiplies the job's power, duration, slot length and PUE by the mean carbon of the slots it would occupy (`solver.py:L124-L132`, `L170-L173`). A consequence worth stating: the solver's objective is a sum over starts of energy times the mean of the carbon values in the covered slots, which equals the slot-by-slot sum because energy is constant across the covered slots of one job.

### 6.3 How simulator state connects to the ontology and the graph

It does so only through F02 records. The simulator emits `VisibleState` objects, and `retrieve()` builds the graph from them. The simulator never reads the graph, and the graph never reads the simulator. At `reset`, the simulator calls `Context.build` for each supplied forecast slot, which checks that the visible state and snapshot are mutually consistent, but it does not build or validate an RDF graph. The only time the graph is validated against a simulator-produced state is in tests that build states by hand. I found no test that runs SHACL over graphs built from many slots of a real simulated episode.

### 6.4 Which constraints are shared by the checker, the solver and the simulator

The same constraint records, in the sense of section 5.6, are read by all three. Capacity comes from the snapshot's single capacity constraint, and the same slot rules are implemented independently in each place: `legal_starts` and `check_schedule` in the verification package, `_window` and `_fits` in the solver, and the guard in `step`. They are three implementations of one rule set, not one shared function. The project handles this with tests: the solver tests include an exhaustive-search oracle that does not call the production solver (section 6.8), and the simulator and checker tests are written to agree on capacity, deadline, nonflexible and Q01 behaviour. I did not find a test that feeds one set of random states to all three and compares their feasibility verdicts.

### 6.5 The reference optimisation problem

The visible-state reference solver is `dc_sustainability/reference/solver.py` (424 lines), with `solve_visible` as its entry point (`L396`) and `_MILPModel` doing the work (`L76`). It takes the `VisibleState`, the `Context`, a trusted UTC decision time, a time limit and a tolerance.

Decision variables. One binary variable for each pair of an arrived, waiting job and a start slot that survives four filters (`_build_vars`, `L105-L136`): the start lies in the job's legal window; the job would finish within the visible horizon, that is before `min(current_slot + 24, 30)`; the job fits under capacity given background and already running work (`_fits`, `L144-L150`, using an occupancy map); and every slot the job would cover has a carbon forecast that is within the context's maximum age (`_fresh_carbon`, `L152-L168`, where age is decision time minus issue time, and a forecast issued in the future or too long ago is rejected).

Objective. Minimise the sum, over chosen starts, of emissions in kilograms (`c = [var.emissions_kg ...]`, `L211`). There is no secondary term and no numerical perturbation (comment at `L208-L210`).

Constraints. Each arrived waiting job starts exactly once (equality row per job, `L213-L219`); each nonflexible job's only allowed start is its arrival slot (`L221-L242`); and for every slot the load from newly started jobs may not exceed capacity minus existing occupancy (`L246-L258`). The problem is solved with `scipy.optimize.milp`, with all variables integral and bounded to 0 or 1, and only `time_limit` passed as an option (`L267-L274`).

What the formulation leaves out is a choice of the model, not an error: it does not allow a job to be left unstarted, because the "start exactly once" row forces every arrived job to be scheduled within the visible horizon; it does not model the value of waiting for future arrivals; and it covers only jobs that have arrived. That makes it a reference for the schedule that minimises emissions for the jobs currently visible under the forecasts currently available, which is what a label for "start this job now" needs, and not a reference for the best full-episode outcome. The latter is the hindsight solver.

### 6.6 Statuses, certification and the treatment of timeouts

`SolverResult` (`schemas.py:L1454`) carries a status of `certified_optimal`, `certified_infeasible`, `unresolved` or `insufficient_evidence`, along with the kind (`visible` or `hindsight`), a flag for use of future arrivals, backend and version, time limit, elapsed time, termination message, tolerance, objective, bound, gap, tie-break description, certification basis, the schedule and the matching-work job ids. The mapping from solver outcome to status is:

| Condition | Status | Source |
|---|---|---|
| Capacity missing from the context | `insufficient_evidence` | `solver.py:L177-L179` |
| An arrived job has no start that passes capacity, deadline and nonflexible rules | `certified_infeasible` | `L189-L194` |
| Feasible starts exist but carbon is missing, stale or the freshness limit is missing | `insufficient_evidence` | `L195-L200`, `_max_age_seconds` at `L138-L142` |
| A nonflexible job has no start at its arrival slot | `certified_infeasible` | `L229-L236` |
| No waiting job and no candidate | `certified_optimal`, empty schedule | `L202-L205` |
| HiGHS returns success with status 0 | `certified_optimal`, with recorded `gap` and `bound_kg` | `L283-L291` |
| HiGHS returns status 2 | `certified_infeasible` | `L292-L293` |
| Any other outcome: time limit (status 1), unbounded, a solver exception | `unresolved` | `L275-L277`, `L294` |

Four points need care when writing about certification. First, a timeout is never reported as infeasible or optimal. `test_solver_timeout_is_unresolved` (`test_solver.py:L460`) passes a 1 microsecond limit on a non-trivial problem and asserts the status is `unresolved`, with a reason and a non-negative elapsed time. Second, `certified_infeasible` is established partly by pre-checks and partly by HiGHS, and in both cases it is relative to the model: it says that no start in the visible horizon satisfies the rules, not that the whole episode is infeasible. Third, "certified optimal" is the label for HiGHS success. The call passes no `mip_rel_gap` or `mip_abs_gap`, so the HiGHS default tolerance applies; I did not run a check of what that default is, so this is static analysis. The result does record `gap` and `bound_kg` taken from the solver response, so an auditor can read the achieved gap for any individual result, and `test_solver_populates_gap_and_bound` (L448) asserts the gap is non-negative. Fourth, the `tolerance` argument (default `1e-6` at the label layer) is stored in the result (`L327`) but is not passed to the solver; I checked this by reading the `milp` call, which only receives `time_limit`.

### 6.7 Deterministic tie-breaking

The implementation of tie-breaking is candidate ordering, nothing more. Variables are created in sorted job order and increasing start slot, the schedule is returned sorted by job and start, and the recorded `tie_break` string reads "stable candidate order (job_id, start_slot) with pinned scipy/HiGHS; formal Q08 scientific tie-break not frozen" (`L331-L334`). Determinism then rests on the pinned solver version and its repeatable behaviour for identical input. `test_solver_is_deterministic` (L319) and `test_tie_break_is_deterministic` (L471) run the solver repeatedly and compare schedules, and the latter uses uniform carbon so that several schedules tie.

The handoffs agree. The header of `docs/handoffs/O03_HINDSIGHT_EXPORT.md` says "The backend uses stable candidate ordering, not a proved lexicographic secondary optimization", and `docs/report/R02_ONTOLOGY_AND_REFERENCE_METHODS.md` says that a manager review rejected a proposed secondary optimisation that could tolerate a more expensive schedule. The test `test_oracle_equal_cost_optima_without_imposing_tie_break` (L682) constructs two identical twin jobs under uniform carbon, shows by exhaustive enumeration that several schedules achieve the same objective, and checks only that the solver returns one of them. So there is explicit evidence that ties exist and that the solver's choice among them is an implementation artefact. R02 should say "deterministic for a pinned backend and input", not "canonical" or "unique".

### 6.8 Independent verification of the solver

`tests/reference/test_solver.py` contains an exhaustive-search oracle (`exhaustive_oracle`, defined in the test file, approximately lines 500 to 530) that enumerates all combinations of starts under the same rules and returns the minimum objective and every optimal schedule. The comparison helper `_assert_oracle_matches_production` (L520) asserts, for each state, that when the oracle reports insufficient evidence the solver does too, when the oracle finds no feasible schedule the solver reports `certified_infeasible` with no schedule, and otherwise that the solver is `certified_optimal`, that its schedule is among the oracle's optima and that the objectives agree to 1e-6 kg. Six scenarios are covered (small optimum, overlap and capacity, running and background occupancy, arrival/deadline/nonflexible, physical infeasibility, equal-cost optima), plus a test that makes the production solver raise if called from the oracle (L714), to prove the oracle is independent, and two evidence cases (L729, L743). The hand example's optimum is 48.4 kg, achieved by J1 at slot 2 and J2 at slot 4 (`test_hand_example_is_certified_optimal`, L257, and the oracle test at L530). The checklist's acceptance wording for O01, "tiny brute-force comparisons", is met by this, in the sense that small cases are compared with a brute-force enumerator. The comparison covers hand-built small states. It does not show agreement on the 20-job, 30-slot scale the solver is meant for. The brief's own question (how does the solver establish feasibility and optimality) is answered in two parts: by the MILP and HiGHS statuses on the encoded model, and, for small cases, by independent enumeration in tests.

### 6.9 Visible-state optimisation versus full-episode hindsight

The two solvers share a formulation and differ in what they are allowed to know.

| Aspect | Visible solver | Hindsight solver |
|---|---|---|
| Entry point | `solve_visible` (`solver.py:L396`) | `solve_hindsight` (`hindsight.py:L394`), `generate_hindsight_reference` (`L481`) |
| Input | `VisibleState`, `Context`, UTC decision time | A whole `PrivateEpisode` |
| Jobs considered | Arrived waiting jobs only | All jobs in the episode, including those that arrive later |
| Carbon used | Forecasts visible at the decision slot, subject to freshness | Realised carbon for all 30 slots (`_realized_carbon_map`, `L102-L112`), with no freshness test |
| Occupancy | Background plus running work at the decision slot | Background only, over the whole horizon |
| Horizon | `min(current + 24, 30)` | 30 slots, with Q01 start limit |
| Result kind and flags | `kind="visible"`, `uses_future_arrivals=False` | `kind="hindsight"`, `uses_future_arrivals=True`, `offline_only=True` |
| Gap and bound recorded | Yes | No (objective is `res.fun`; `_certified_optimal` receives no gap) |
| Output | A `SolverResult` | A sealed `HindsightReferenceArtifact` exported to files |

The hindsight model drops, rather than fails, a job whose window is empty (for example a job with negative slack): `solve` compares the jobs represented by variables with the jobs that have a non-empty window, so an intrinsically infeasible job does not make the episode infeasible. This matches the handoff's statement that "matching work excludes intrinsic timing infeasibility; capacity-blocked eligible jobs must not disappear" and the test `test_capacity_blocked_job_cannot_silently_disappear` (`test_hindsight.py:L59`), which raises a job to 80 kW on a 40 kW background and expects `certified_infeasible`. The artifact's `complete` flag is true only if the status is `certified_optimal` and the scheduled job ids equal the set of jobs with a feasible window and an arrival no later than 23 (`hindsight.py:L499`). The hindsight solver also passes only `time_limit` to HiGHS and stores a `tolerance` it does not pass.

The hindsight artifact records `source_snapshot_hash`, `realized_carbon_hash` and `solver_config_hash` and carries a solver version `o03-v1`. `export_hindsight_reference` (`L518-L568`) requires an existing directory that is not inside a Git checkout (it checks every ancestor for `.git`), refuses to overwrite, writes a temporary file with mode 0600 and links it into place, and writes a manifest next to the artifact. `load_hindsight_reference` (`L571`) reads it back. The tests `test_export_and_load_roundtrip`, `test_export_rejects_git_directory` and `test_export_rejects_overwrite` cover these behaviours. The handoff notes that file-mode privacy is POSIX behaviour and that Windows ACL privacy is the caller's responsibility.

### 6.10 Label generation, eligibility and exclusions

Labels are produced by `label_decision` (`labels.py:L165`) and `label_episode` (`L230`). `label_decision` requires an explicit trusted UTC decision time, recomputes the candidate feature rows from the visible inputs and checks they equal the collected rows, builds a cache key, looks the result up in the optional `LabelCache`, and otherwise calls `solve_visible` and stores a certified optimal result. `_attach_labels` (`L109-L162`) then labels the candidate rows. It refuses a result that is not `kind == "visible"` or that uses future arrivals ("hindsight results cannot supply visible training labels"), and refuses a result whose input hash does not match the visible state. If the result is `certified_optimal`, each candidate gets `label = True` if its (job, start) pair is in the one returned schedule and `False` otherwise. For every other status, including certified infeasible, unresolved and insufficient evidence, every candidate gets `label = None`, and downstream training excludes the whole decision.

A positive label therefore means membership in the single schedule HiGHS returned, not membership in every optimal schedule. The legacy label audit (`docs/handoffs/LEGACY_LABEL_AUDIT_2026-11-04.md`) records the practical consequence for the saved development corpus: 6,046 labels across 40 development episodes (1,411 positive, 4,635 negative), all matched to 570 cached certified results, with 1,075 of the 1,411 job decisions having several candidate starts whose saved carbon features are identical, and with the number of alternative global optima unknown. The audit also says that the historical pipeline used flat persistence forecasts. These figures come from the handoff and the repository's evidence file; I did not recompute them.

Eligible states are decisions for which candidate rows exist. `build_labeled_corpus` skips decisions without rows (the completion-slot drain) and raises if no definite rows result (`training/pipeline.py:L66-L80`). Tests cover the labelling rules: `test_optimal_labels_match_solver_schedule`, `test_infeasible_state_labels_are_none`, `test_missing_capacity_labels_are_none`, `test_label_episode_excludes_unresolved_states`, `test_only_optimal_results_produce_training_labels`, `test_negative_labels_are_feasible_candidates_only`, `test_labels_cannot_use_future_arrivals` (a decision before J3 arrives must not label J3's candidates), `test_labels_cannot_use_realized_future_carbon`, and `test_visible_labels_reject_hindsight_and_wrong_context` (section 7.2).

### 6.11 Caching and input hashes

`reference/cache.py` implements `LabelCache`. A `CacheKey` (`L45-L75`) holds the state hash, the context hash, the UTC decision time, a hash of the candidate set, backend and version, tolerance, time limit, the reference solver version and the label schema version, and exposes a canonical dictionary and a digest. `make_cache_key` (`L90-L118`) requires an explicit UTC decision time. `get` (`L165-L189`) returns a result only if the entry's versions match, the stored key equals the requested key, the result file exists and parses, the status is `certified_optimal`, the kind is `visible` with no future arrivals, the stored SHA-256 of the result matches, and the result's `input_hash` equals the key's context hash. Any failure is a miss. `put` (`L192`) publishes immutably and rejects a collision with a different payload. `unresolved`, infeasible and insufficient-evidence results are never returned from cache. The solver's own `input_hash` is the context's `content_hash` (`solver.py:L296-L297`), which ties every stored result to the exact visible inputs. Twenty-six tests in `test_cache.py` cover key sensitivity to state, solver config, candidate set, decision time, forecast values and metadata and solver version; miss-then-hit; ignoring non-optimal results; invalidation on corruption, schema or solver version change and key mismatch; idempotent put; collision rejection; and an end-to-end collect, label, cache and hit test.

### 6.12 Where each part is used: development, training, evaluation and runtime

Development and training. The visible solver and label cache are used by `training/pipeline.py:build_labeled_corpus`, which builds the labelled corpus used to train the decision tree and random forest policies (`training/select.py` and `training/train.py`). `select.py` also calls `check_schedule`, so the checker is used to gate the training rows.

Evaluation. The hindsight code produces offline bounds and exports. No code in the package consumes a hindsight artifact. Per the checklist, held-out hindsight and visible references are generated by task O04 after inference and the freeze (I02), and neither has been done: the handoffs I read state that held-out opening is not approved and that no held-out work has occurred. The development hindsight infrastructure has been exercised only through its tests.

Runtime scheduling. Neither solver is called by any runtime scheduling component. `solve_visible` is called by `label_decision`, which is called by `label_episode`, which is called by the training pipeline and tests. The agent, plain, greedy and trained policies do not call the solver, and the reference result is never shown to them. The reference solver is therefore a source of training labels and an offline comparator, and cannot be described as part of the agent's decision procedure.

### 6.13 Role of the reference solver, in one paragraph

The reference solver answers the question "what would a cost-minimising scheduler do with exactly the information the policy has", which is what a supervised label needs, and, in its hindsight form, "what was the best that could have been achieved with perfect knowledge", which is what an evaluation bound needs. The agent's decision-making is separate. It is a language model constrained by a checker, one repair, a fallback and an execution gate, and its output is compared with the reference after the fact. A feasible agent schedule is not thereby optimal, and an agent schedule that differs from the reference is not thereby wrong, since the reference may be one of several equal-cost optima.

---

### 6.14 Carbon data and forecast handling

The brief lists carbon and forecast handling as a scope area of its own, so it is set out here in one place, with the points where it connects to the sections above.

Source and ingestion. Carbon intensity comes from a single public CSV, `data/CarbonIntensity/AZPS_NG_&_avgCI.csv`, in the Hewlett Packard `dc-rl` repository, pinned by commit `a92b4755aca560e34a98d14028dda629eb968482` and by SHA-256 `e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4` (`data/carbon_source.py:L16-L22`). The adapter (`inspect_csv`, `load_source`, `episode_indices`, `provenance`) requires 8,760 hourly records in UTC, and reports errors for missing or extra rows, bad columns, non-finite, negative or outlying values, and duplicate, gapped, disordered or non-UTC timestamps (`L43-L98`). It maps an episode to physical source rows only when an explicit interval convention (timestamp as interval start or as interval end) is supplied, and it never wraps past the ends of the year. The tests listed in section 7.4 cover each of these behaviours, and the whole data suite passed on Python 3.12.

What is not resolved. The provenance record that the adapter emits sets `pollutant_basis` to `None` and `dataset_redistribution_verified` to `False`, and lists as open items that dataset-specific redistribution rights are unverified ("repository has mixed licensing", `L29`) and that the annual eGRID magnitude comparison is regional only, with the AZNM region differing from AZPS and the AZPS factor alignment unverified (`L30`, `L189-L190`). The project tracks these as decision Q05 and as the source blockers of Issue 60 (B1 to B3 unresolved, B4 provisional, B5 incomplete in `docs/handoffs/ISSUE60_SOURCE_EVIDENCE.md`, which I read in summary). A working adapter that loads the file correctly establishes that the file is read faithfully. It does not establish that the numbers are CO2 or CO2e, that they refer to the stated interval, that they are valid for the Phoenix site, or that the project may redistribute them.

Forecasts versus realised values. Policies see only forecasts. `persistence_forecasts` (`materialize_development.py:L192-L235`) builds a development-only schedule in which, at decision slot t, the forecast value for every slot in the visible horizon is the source row immediately before the row associated with slot t, and the issue time is that current row's timestamp label, so the input row is strictly earlier than the issue time (the function raises otherwise). The records are marked `forecast_kind="persistence"`, `quality_status="unvalidated"`, unit `g/kWh`, source `SRC-D01` with the pinned hash, and carry a semantics object describing the open interval convention. The docstring states that this is "a provisional development adapter, not evidence about the source's interval semantics and not authorization for held-out or final study use." Realised values live in the private episode (`PrivateEpisode.realized_carbon`) and are read only by the simulator's accounting adapter and by the hindsight solver. A persistence forecast is flat across the horizon, so for any single decision it gives every start slot of a job the same carbon intensity, which is the reason the legacy label audit finds many candidate starts with identical carbon features and, therefore, many ties.

Visible versus future information. The `VisibleState` carries only the forecasts issued for the current slot and an explicit list of slots with no forecast. Where evidence is missing, the downstream behaviour is fail-closed in three places: the checker skips freshness with a Q04 reason and declares the impact claim unsupported; the solver returns `insufficient_evidence` for a decision whose feasible starts lack fresh forecasts; and the impact module leaves emissions as `None`. Freshness is bounded by the authoritative freshness constraint but never by more than two slots (`rules.py:L81`).

`forecast_isolation.py` is not part of this visibility mechanism. It is a 55-line offline utility that computes, for a 30-hour Phoenix-day window (starting at 07:00 UTC, the Phoenix midnight) and an explicit lookback, the set of source rows that would be scored and the set that a forecaster would read, under either interval convention, and refuses to wrap around the year. It supports the conflict check between development and held-out source footprints; its docstring says it performs "no selection, source reads or defaults" and that the lookback is "not an adopted forecast method". Calling it a leakage barrier between visible and future information in the running system would be wrong.

Status of the scenario inputs. The jobs themselves come from `data/scenarios.py`, whose catalog is described by the repository as provisional (D03); the catalog is byte-reproducible (tested) but the distributions are not empirically calibrated (D02 and the calibration decisions are open). The F02 example fixtures and the hand-calculated fixture used by the knowledge and reference tests are synthetic and labelled as such.

## 7. Implementation and test evidence

### 7.1 Component and implementation table

| Component | Source files | Principal symbols (line) | Status |
|---|---|---|---|
| Ontology | `ontology/dc-sustainability.ttl` | 15 classes, 43 properties | Implemented; Tested; Execution-verified (local) |
| SHACL shapes | `ontology/shapes.ttl` | 12 node shapes (L17 to L417) | Implemented; Tested; Execution-verified (local); not on the production path |
| Ontology API | `knowledge/ontology.py` | `load_ontology_graph`, `load_shapes_graph`, `UNIT_MAP` (L55-L68), `map_unit`, `validate_graph` (L164-L211), `add_unit_metadata` (L214-L227) | Implemented; Tested; Execution-verified (local) |
| Graph builder | `knowledge/graph.py` | `build_graph` (L126-L204), `_add_*_triples` | Implemented; Tested; Execution-verified (local) |
| Retrieval | `knowledge/retrieval.py` | SPARQL constants (L27-L101), `query_*`, `get_context` (L213), `RetrievalResult` (L249), `retrieve` (L267) | Implemented; Tested; Execution-verified (local) |
| Records and contexts | `schemas.py` | `MissingEvidenceError` (L64), `visible_constraints_for` (L756), `Context.build` (L966), `SolverResult` (L1454) | Implemented; Tested; Execution-verified (local) |
| Checker | `verification/checker.py`, `rules.py` | `check_schedule` (L37-L350), `recheck_schedule` (L15), `legal_starts` (rules L14), `assess_forecasts` (rules L66) | Implemented; Tested; Execution-verified (local) |
| Agent harness | `agent/harness.py`, `agent/renderers.py` | `_retrieve` (L121), wiring (L82-L111), `run_decision` (L300), `render_proposal` | Implemented; tested with synthetic HTTP; live model not run by me |
| Controller | `runtime/controller.py` | `execute_step` (L41) | Implemented; Tested; Execution-verified (local) |
| Simulator | `simulator/core.py`, `simulator/impact.py` | `SchedulingSimulator` (L30), `step` (L163), `account_realized` (L55) | Implemented; Tested; Execution-verified (local) |
| Impact formulas | `metrics/impact.py` | `calculate_impact` (L153), `compare` (L310) | Implemented; Tested; Execution-verified (local) |
| Visible solver | `reference/solver.py` | `_MILPModel` (L76), `solve_visible` (L396) | Implemented; Tested; Execution-verified (local) |
| Labels | `reference/labels.py` | `label_decision` (L165), `_attach_labels` (L109), `label_episode` (L230) | Implemented; Tested; Execution-verified (local) |
| Cache | `reference/cache.py` | `CacheKey` (L45), `make_cache_key` (L90), `LabelCache` (L133) | Implemented; Tested; Execution-verified (local) |
| Hindsight | `reference/hindsight.py` | `_HindsightMILP` (L72), `solve_hindsight` (L394), `generate_hindsight_reference` (L481), `export_hindsight_reference` (L518), `reject_hindsight_in_context` (L587) | Implemented; Tested; Execution-verified (local); guard has no production caller |
| Carbon source adapter | `data/carbon_source.py` | `inspect_csv`, `load_source`, `episode_indices`, `provenance` | Implemented; Tested; Execution-verified (local); source acceptance incomplete |
| Forecast footprint check | `data/forecast_isolation.py` | `footprint`, `conflicts` | Implemented; Tested; Execution-verified (local); not the visibility mechanism |
| Persistence forecasts | `data/materialize_development.py` | `persistence_forecasts` (L192-L235) | Implemented; development only |
| Scenario generator | `data/scenarios.py` | `generate_jobs`, `SCENARIOS` | Implemented; synthetic and provisional |
| Provenance classes in RDF | ontology | `Decision`, `Check`, `Slot`, `CarbonObservation`, `wasGeneratedBy` | Documented in the ontology only |
| SHACL before each episode | `docs/ARCHITECTURE.md:L145` | — | Documented only |
| Held-out references (O04) | checklist | — | Planned/unresolved |

### 7.2 Test evidence: reference suite

The names, lines and one-line behaviours below come from reading the test code or its docstrings; I read the bodies of the solver, hindsight and labels tests quoted in section 6 and the names and docstrings of the rest. All 82 reference tests passed in my local run (CPython 3.12.3).

`tests/reference/test_solver.py` (26 tests)

| Test (line) | Behaviour | Establishes / does not establish |
|---|---|---|
| `test_hand_example_is_certified_optimal` (257) | Hand fixture gives J1 at 2 and J2 at 4, objective 48.4 kg, backend `scipy.optimize.milp`, a gap and a bound | Correct answer on the hand example, and the result record is fully populated |
| `test_infeasible_job_is_certified_infeasible` (280) | Only J3 waiting at slot 4 | Infeasible status and message names J3 |
| `test_missing_capacity_is_insufficient_evidence` (298) | Snapshot with no capacity | `insufficient_evidence`, not infeasible |
| `test_solver_result_schema_validates` (309) | Round trips through the schema | Schema compatibility |
| `test_solver_is_deterministic` (319) | Same input, same schedule | Repeatability on one input and platform |
| `test_solver_requires_decision_time_utc` (330), `test_solver_rejects_naive_decision_time` (338) | Missing or naive time | Time must be explicit UTC |
| `test_stale_forecast_is_insufficient_evidence` (348) | Feasible start but stale forecast | `insufficient_evidence` |
| `test_missing_forecast_is_insufficient_evidence` (370) | Only feasible start lacks a forecast | `insufficient_evidence` |
| `test_missing_freshness_constraint_is_insufficient_evidence` (392) | No freshness limit | Forecast is not treated as fresh without a limit |
| `test_physical_capacity_infeasibility_is_certified` (406) | Job cannot fit under capacity | `certified_infeasible`, not insufficient evidence |
| `test_empty_waiting_jobs_is_optimal` (416) | No waiting jobs | Trivial certified optimal |
| `test_nonflexible_job_requires_arrival_start` (427) | Nonflexible job cannot start at arrival | Infeasible |
| `test_solver_populates_gap_and_bound` (448) | Gap and bound present, gap non-negative | Gap is recorded, not that it is zero |
| `test_solver_timeout_is_unresolved` (460) | 1e-6 s limit on a non-trivial problem | `unresolved` with a reason; a timeout is never certified |
| `test_tie_break_is_deterministic` (471) | Uniform carbon, repeated solves | Same schedule on repeat; does not show a canonical choice |
| `test_solver_input_hash_matches_context` (487) | `input_hash` equals `context.content_hash` | Result is bound to the context |
| `test_oracle_finds_hand_example_optimum` (530) and the oracle tests at 580, 612, 636, 668, 682, 714, 729, 743 | Independent exhaustive oracle versus production solver on small states | Agreement on small hand-built states; oracle independence; equal-cost optima exist. Not agreement at full scale |

`tests/reference/test_labels.py` (12 tests)

| Test (line) | Behaviour |
|---|---|
| `test_optimal_labels_match_solver_schedule` (43) | Positives are exactly the solver's schedule |
| `test_infeasible_state_labels_are_none` (55), `test_missing_capacity_labels_are_none` (71) | Non-optimal statuses give `None` labels |
| `test_label_decision_attaches_to_collected_rows` (81), `test_labels_preserve_feature_row_order` (218) | Labels attach to the collected feature rows in order |
| `test_label_episode_excludes_unresolved_states` (107), `test_only_optimal_results_produce_training_labels` (131) | Only certified optimal states give training rows |
| `test_negative_labels_are_feasible_candidates_only` (151) | Negatives come from feasible candidates |
| `test_labels_cannot_use_future_arrivals` (167) | A decision before J3 arrives does not label J3's candidates |
| `test_labels_cannot_use_realized_future_carbon` (180) | Labels are built from forecasts, not realised observations |
| `test_candidate_label_hash_is_stable` (205) | Candidate hash is deterministic |
| `test_visible_labels_reject_hindsight_and_wrong_context` (230) | A hindsight result or a mismatched context is refused as a label source |

`tests/reference/test_hindsight.py` (18 collected, 16 functions)

| Test (line) | Behaviour | Establishes / does not establish |
|---|---|---|
| `test_hindsight_solver_is_certified_optimal` (44) | Hand episode padded to 30 carbon slots gives J1 at 2, J2 at 4, 48.4 kg, flags set | Hindsight agrees with the visible optimum on a fixture where both coincide |
| `test_capacity_blocked_job_cannot_silently_disappear` (59) | J1 at 80 kW on a 40 kW background | `certified_infeasible`, not a dropped job |
| `test_hindsight_rejects_invalid_time_budget` (73, four cases) | 0, negative, NaN, infinity | Input validation |
| `test_hindsight_artifact_has_correct_markers` (78) | Record type, offline-only, complete, solver version `o03-v1`, snapshot hash, timestamp with zone | Artifact envelope |
| `test_hindsight_is_deterministic` (93) | Two runs agree on schedule, objective, input hash | Repeatability |
| `test_realized_carbon_alignment` (103) | Objective equals hand-calculated realised emissions | Objective uses realised carbon correctly for one fixture |
| `test_rejects_non_private_episode` (118), `test_rejects_missing_realized_carbon` (123), `test_rejects_misaligned_realized_carbon` (129) | Input validation | Fails closed on bad episodes |
| `test_infeasible_episode_is_certified_infeasible` (137) | Capacity below background plus job | `certified_infeasible` |
| `test_export_and_load_roundtrip` (155), `test_export_rejects_git_directory` (176), `test_export_rejects_overwrite` (185) | Export behaviour | Offline export and no overwrite; Windows ACLs not tested |
| `test_reject_hindsight_in_context` (192) | A poisoned context dictionary with `solver_result_kind="hindsight"` | The guard function raises when called; the guard has no production caller |
| `test_hindsight_result_does_not_mix_with_visible_labels` (205) | Kind and future-arrival flag differ from a visible result | Distinct record markers |

`tests/reference/test_cache.py` (26 tests). Key sensitivity: `test_cache_key_is_deterministic` (62), and sensitivity to state (68), solver config (88), candidate set (116), decision time (146), forecast values (175), forecast metadata (210) and solver version (251). Lookup behaviour: miss-then-hit (270), non-optimal results ignored (312), corruption invalidates (335), idempotent put (362), collision rejected (385). Integration: `test_label_decision_uses_cache` (410), `test_label_episode_excludes_unresolved_states` (428), only certified optimal gives rows (451), infeasible and missing-capacity states give no rows (463, 479), explicit decision time required (490, 504), invalidation on schema version, solver version and key mismatch (522, 550, 578), stale and future-issued forecasts rejected (606, 619), and `test_end_to_end_collect_label_cache_hit` (634). These show the cache cannot return a stale or mismatched result in the tested cases. They are written against synthetic fixtures; I found no test that fills a cache from real development episodes. The legacy audit reports such a cache (570 results) but as a handoff statement.

### 7.3 Test evidence: simulator, impact and verification

`tests/simulator/test_core.py` (43 collected) and `test_s02_impact.py` (8 collected). Behaviour listed from names, with the parameter sets noted. Hidden information and an impossible arrival (68); non-preemption and rejection progression (89); atomic rejection for capacity, unknown job, future job and a further kind (106); capacity counts running work before PUE (132); exact deadline and latest-start miss (139); explicit nonflexible violation (150); completion slots reject starts and account for all slots (159); a retired completion-start option is rejected for `True`, `1`, `None` and `'false'` (181); replay of D03 scenarios (`normal`, `spike`, `limited`, `infeasible`) with no lost jobs (187, 298); forecasts explicit and actuals withheld (207); reset validation (220); exact capacity limit and replay with starts (236); job spanning the decision/completion boundary (257); deadline and constraint conflicts (271); arrival at the boundary (287); impossible arrival visible once and rejected atomically for arrivals 0, 4 and 17 (349, 455); a slot-23 start finishing at 30 despite a slot-24 rejection (424); and forecast projection keeping issue times (476). The impact tests check hand values over all 30 slots for PUE 1 and 1.2 (42), that incomplete work is never counted as savings even when both schedules omit the same job (66), that missing actuals keep energy and refuse comparison for slots 0, 29 and all (78), replay serialisation without forecast substitution (88) and executed starts with the completion tail (108). All 51 passed in my local run.

`tests/verification/` (85 collected). `test_checker.py` (26, hand-calculated expectations, read in full): the hand plan passes (39), the committed F02 example files can be read unchanged (55), exact IT capacity before PUE (65), overlap overload reports the actual slots and constraint (73), 100 versus 70 kW (83), running work counts (90), half-open intervals (101), deadline boundary at 4 and 5 (109), start before arrival and before current slot (119), nonflexible delay (131), invalid start types bypassing validation (139), duplicate starts (149), unknown job without looking up future jobs (157), missing capacity is an error (165), fabricated citations cannot override real capacity (174), missing carbon does not fail capacity or support savings (181), impossible deadline stays a real violation (189), binding mismatch (197), authoritative job-constraint conflict (206), Q01 start prohibition (222). `test_agreed_rules.py` (21) covers dispositions, omission, deferral legality, last opportunity, joint contention, forecast union and the two-slot freshness edge. `test_d03_consumer.py` (8) and `test_s01_checker_intake.py` (3, scenario-parameterised) check the checker against generated and simulator-produced states. All 85 passed in my local run.

What these suites do not establish. They exercise the checker on hand-built and generated states, but the checker's agreement with the simulator and the solver on random states is not tested. `tests/README.md` describes `tests/verification/CASES.md` as holding established case expectations plus four scenarios that were waiting on decisions Q01 to Q04; Q01 has since been implemented in the checker and simulator, and I did not trace the other three.

### 7.4 Test evidence: carbon and data

`tests/data/test_carbon_source.py` (12 tests, passed locally): a complete year with a repeatable checksum (41); the pinned check rejecting synthetic data and the local loader (51); UTC and values preserved (62); the command line reporting failed validation and preserving an existing report (75); missing and extra records (87); column and CSV errors (94); non-finite, negative and outlier numbers (100); timestamp duplicates, gaps, disorder and time zone (109); row width (125); episode mapping requiring an explicit convention and never wrapping (131); provenance not claiming acceptance (140); and the pinned, validated, non-overwriting download (148). `tests/data/test_forecast_isolation.py` (11 collected with parameters): an empty window set cannot pass isolation (10); a history leak is detected even when scoring windows are disjoint, for both interval conventions (17); month edge and separated windows (26); and year boundaries fail rather than wrap (37). `tests/data/test_scenarios.py` (416 collected through parameterisation) covers scenario constraints, determinism, input validation, episode round trips, withheld actuals and the published catalog's byte reproduction (159). The catalog reproduction test failed under Python 3.13 and passed under Python 3.12 (section 7.5).

### 7.5 Execution evidence

All local runs used the commit recorded in section 0.

| Run | Interpreter and platform | Scope | Result |
|---|---|---|---|
| Focused knowledge, reference, verification, simulator suites | CPython 3.13, Linux | 75 + 82 + 85 + 51 tests | All passed |
| Full suite, first run | CPython 3.13, Linux | `pytest tests` | 2333 passed, 15 failed, 23 skipped, 19 subtests passed |
| Full suite, second run | CPython 3.12.3, Linux, pinned versions from `requirements-core.in` | `pytest tests` | 2348 passed, 0 failed, 23 skipped, 19 subtests passed |

The 15 failures under 3.13 are explained by interpreter behaviour. Ten are `tests/data/test_materialize_development.py` cases that raise `ValueError: approved generator requires CPython 3.12` from an explicit version guard (`materialize_development.py:L314-L315`). Five are cases in `test_scenarios.py` and `test_development_folds.py` that compare regenerated manifests with committed bytes: the regenerated `distribution_specification` text differs from the committed text only in leading whitespace, because Python 3.13 strips common indentation from docstrings at compile time (I confirmed this by running the generator and using `diff`). The repository declares `requires-python = ">=3.12,<3.13"` (`pyproject.toml:L5`), so running 3.13 was outside the supported range, and the 3.12 result is the one that corresponds to the project's configuration. The 23 skipped tests are the Windows-only launcher tests in `tests/data/test_cf60_launcher.py` and `test_development_bundles.py:L238`.

These runs are not CI. They were on Linux, not Windows, used a virtual environment built from the unhashed `requirements-core.in` rather than the hash-pinned Windows lock, and did not run `ruff` or the other CI steps. No live model was called.

The project's own recorded evidence includes a Ollama-backed development validation (`docs/R04_DEVELOPMENT_EVIDENCE.md`, run `RUN-cb85f5a3425c`, 9 November 2026): six systems, 180 decision records, 17 model requests (5 plain, 12 agent) in 532 seconds, with zero replay findings, and the agent completing one job through the checked fallback and one from an initial model plan while both repairs failed their checks, and the plain model completing none. The handoff is explicit that this is one public episode with one seed and is not a held-out study. I did not re-run it or verify its trace files; it is reported here as documented execution evidence at handoff level.

### 7.6 CI evidence

The workflow `.github/workflows/bootstrap.yml` runs on pull requests and pushes to `main` on `windows-latest` with Python 3.12 and performs, in order: `scripts/validate_setup.py`; installation from the hash-pinned lock `requirements/requirements-windows-py312.lock.txt` with `--require-hashes`; `pip check`; `scripts/smoke_dependencies.py` (the README, line 233, lists imports, SHACL and SPARQL, a small solver check, a classifier fit and save, and a LangGraph route; I read only its SHACL part at lines 37 to 58); `python -m pytest tests -q`; `ruff check`; `ruff format --check`; and `compileall`. The relevant test suites are therefore in scope for CI: they sit under `tests/` and are run by `pytest tests`. The pinned versions include rdflib 7.6.0, pyshacl 0.40.1, pydantic 2.14.0, scipy 1.18.1 and pytest 9.1.1.

The only run I could inspect is Actions run #259, commit `6c288c0`, dated 1 November 2026, from the rendered summary page. It predates the final reference-module commits recorded in the git history (`753907c` on 1 November, `fcae588`, `07bee32` and `707f995` on 31 October and 1 November) and later commits on `main`, so it is not execution evidence for the cache, hindsight or label code as they stand, and it is not evidence for the inspected commit. Its step logs were not accessible. Whether CI passed for `cd272e93` is therefore unverified.

### 7.7 Implementation status and git history

For the tasks relevant to R02, the relevant commits visible on `main` at the inspected commit are below. All are reachable from `origin/main`, so they are implemented and merged to `main` in the sense available to me. Pull request and review status was not accessible, and the clone contains only `main`, so I cannot identify implemented-but-unmerged work; that status is unverified.

| Task | Commit and date | Message | Notes |
|---|---|---|---|
| K02 | `c762833`, 2026-10-22 | "k02 knowledge graoh implemented and tests passing" | Graph and retrieval |
| K02 consumers | `62873c8`, 2026-10-23 | "Validate K02 consumers and record October 23 agreements and gates" | `test_consumers.py` |
| K01 | `f5e2b57`, 2026-10-24 | "K01: ontology, unit mappings, source/constraint records, and SHACL validation" | Ontology and shapes |
| K03 | `ba497ef`, 2026-10-24; `96b33fc`, 2026-10-27 | "K03: add graph-driven capacity check tests"; "fix(k03): close graph-to-checker edge for capacity constraints" | The test helper that closes the edge |
| K01 fixes | `b68e6f6`, `83aff05` (2026-10-28); merge `26bb990` (PR #111, 2026-10-29); `0131fc2` (2026-10-29) | Completed-job SHACL, capacity cardinality, unit IRIs; inference option | Issue #71 |
| O01 and F02 downstream | `27e4567`, `1853f52` (2026-10-27); `1ce1591` (2026-10-30); `90796ff` (2026-10-31) | Solver and label surface acceptance | |
| O02 | `14a3514`, `a6f0125`, `07bee32` (2026-10-31); `b1dc7b2` (2026-11-01) | Label cache, authoritative decision time, leakage-safe labels | |
| O03 | `707f995` (2026-10-31); `fcae588`, `753907c` (2026-11-01) | Hindsight generation, export, offline-only isolation, cache integration | |
| Simulator | `a1d848f` (2026-10-18); `162022a` (2026-10-23); `e48a343` (2026-10-24) | Simulator, S02 adapter, Q01 boundaries | |
| Checker and controller | `883a809` (2026-10-12); `9b059de`, `5e774dc` (2026-10-24) | Fixed checker core, coverage and forecast rules, controller and traces | |
| Agent | `bc73a55` (2026-10-24) to `40dcd80` (2026-11-04) | Bounded routing, fail-closed handling, proposal renderer | |
| Docs | `4b4f979`, 2026-11-15 | "Assemble evidence-first working report and draft delivery manifest" | Latest commit touching the ontology, knowledge and test folders |

Status summary for the report. K01, K02, K03, O01, O02 and O03 are implemented and merged. They are tested, and execution-verified in my local runs on Python 3.12. O04, the held-out hindsight and visible references, is planned and blocked on the held-out run, which the handoffs say has not been authorised or started. The development hindsight infrastructure is implemented but exercised only through tests. The responsibility checklist still shows these tasks as unticked, so the checklist should not be cited as status evidence.

---

## 8. Limitations

The limitations are grouped as the brief asks. Each paragraph says what the limitation is, why it matters to a claim in R02, and what the evidence is.

### 8.1 Technical limitations

The knowledge graph is rebuilt from scratch at every retrieval call and discarded. For the agent and for all other systems this costs a graph build and six SPARQL queries per decision slot for results that nothing consumes, and it adds a failure mode (a graph-construction error aborts retrieval) without adding any information. This is a design cost, not a correctness problem, but it means "the ontology is on the critical path" is true only in the narrow failure sense.

The graph is thinner than its ontology. Four classes (`Slot`, `CarbonObservation`, `Decision`, `Check`) and one property (`wasGeneratedBy`) are declared and never instantiated, and the PROV-O alignment appears only as ontology axioms; the data graph contains no `prov:` triples. Unit metadata is attached per node and not per property, so for jobs and the site the graph cannot say which unit applies to which value. The QUDT unit IRIs emitted by the code differ from those declared in the ontology file. The forecast SPARQL query omits the unit, the quality status and the Q05 semantic fields, so the flat retrieval result is a strict subset of what the graph holds. A constraint that applies to several jobs comes back as several rows with a scalar job id, unlike the F02 record, which holds a tuple.

The physical model is deliberately simple. Power is constant for a job and for the background load, slots are hourly, execution is non-preemptive, capacity is an IT-power limit compared before PUE, PUE is constant, and there are no thermal, cooling, battery or network effects. The study is about scheduling under a capacity and carbon signal, so these simplifications are defensible, but R02 should describe the model as it is and avoid any suggestion of a physical simulation of data-center operation.

The reference solver certifies a model, not the world. Its status vocabulary is explicit and timeouts are handled correctly, but: the call sets no explicit MIP gap, so the default HiGHS tolerance applies (not verified by me); `tolerance` is recorded and not enforced; the hindsight result records no gap or bound at all; the visible solver considers only arrived jobs, inside a 24-slot visible horizon, and forces every arrived job to start; and the tie-break is candidate order with a pinned backend, with the scientific tie-break (Q08) not frozen. The result is a deterministic, well-labelled reference, not a proof of a unique global optimum.

### 8.2 Integration limitations

SHACL is not part of any runtime path. It runs in tests and in a dependency smoke script, and the architecture document's statement that SHACL validates structure before an episode describes intent that no runner implements. The same is true of the "graph validation" command line operation, which `docs/INTERFACES.md` and `README.md` list as planned and not yet runnable; I found no such command in the code.

The graph-to-checker edge exists only in a test helper. The tests demonstrate that a capacity value retrieved from the graph, put into a snapshot and handed to the checker produces the expected verdicts. They do not make the production checker read from the graph. The module docstring of that test file says the graph "is the source of truth" for the checker; the project's own architecture document says the K03 tests "do not yet establish" that graph query results drive the checker. The latter is the accurate description.

The agent's "graph" presentation is a label. The prompt for the agent embeds the same JSON as the plain model's prompt, and the schema, the renderer and the consumer tests make that a deliberate "matched information" design. Any observed difference between the agent and the plain model therefore reflects the harness (routing, repair, fallback, call budget) and the prompt wording, and not different facts. R02 should not credit the ontology for differences in agent behaviour unless a separate ablation, which does not exist in the repository, shows it.

There are three independent implementations of the scheduling rules (the checker, the solver and the simulator). They are cross-checked by tests of specific behaviours but not by a randomised differential test. `reject_hindsight_in_context` is tested and has no production caller. The hindsight handoff says `llm/plain.py` was changed to reject hindsight input; the current file contains no reference to hindsight, so that statement is not supported by the commit I inspected (it may refer to a different mechanism, such as the typed schema, which has no hindsight field, but I did not establish that).

### 8.3 Testing limitations

Graph, retrieval and SHACL tests run on a single hand-calculated fixture and a few variations of it; there is no test that builds and validates graphs from many slots of generated episodes. The solver's independent oracle covers small hand-built states and not full-scale problems. The agent and the plain model are tested with synthetic servers and recorded fixtures, not with a live model, and I did not run a live model. The hindsight export's Windows ACL behaviour is untested. CI evidence for the inspected commit is unavailable to me, and the one run I could see predates the reference code. Local execution was on Linux. A full Windows CI log is the missing piece.

### 8.4 Source-data limitations

The carbon source's pollutant basis, interval semantics, regional alignment and redistribution rights are unresolved. The adapter's own provenance record says so. The forecasts that policies see in development are flat persistence forecasts labelled `unvalidated`. Job scenarios are provisional and not empirically calibrated. Any figure derived from this data is a development figure.

### 8.5 Evaluation limitations

Development labels, development hindsight bounds and the recorded validation run are not held-out evidence. The held-out references (O04) have not been generated, and R02, per the checklist, depends on them. The legacy label audit reports that most multi-candidate decisions have identical saved carbon features and that alternative optima are not counted, so label noise from ties is plausible and unmeasured. The recorded agent run in `docs/R04_DEVELOPMENT_EVIDENCE.md` is one public episode, one seed, with a small number of model calls, and says so. The human-faithfulness reliability numbers in `AGENTS.md` (32 matched claims, 75% raw agreement, Cohen's kappa 0.00 under a documented prevalence limitation, 77 items awaiting adjudication) are quoted from the repository and were not verified.

### 8.6 Documented but not implemented

SHACL validation "before an episode"; decisions and checks as PROV-O activities with `wasGeneratedBy` links; time slots as ontology individuals; carbon observations in the graph; a graph-validation command; held-out hindsight and visible references; the tie-break rule Q08; the source-acceptance decisions Q05 and Issue 60. Each appears in documents or in the ontology, and none has an implementation in the source at this commit.

---

## 9. Recommended R02 narrative and technical explanation

This section gives guidance for the writer. It does not draft the R02 section.

### 9.1 Overall framing

The most defensible account of the work is a verification-first one. The system separates what a decision-maker may know (policy-visible records) from what only the evaluator knows (private episodes), represents the visible facts in typed, hashed records and in a small ontology-backed graph, checks every proposed schedule with a deterministic checker before execution, and computes offline reference schedules whose status vocabulary distinguishes proven results from unresolved ones. Within that account, the ontology is a specification and validation layer for the facts, and the checker, simulator and solver are the enforcement and reference layers. R02 should not present the ontology as the engine of the agent's reasoning.

### 9.2 Suggested subsections and what each may claim

R02.1 Scope and design principle: information boundary and fail-closed evidence.
- Contribution: the separation of visible and private information, and the rule that missing evidence is never converted into a permissive default.
- Essential details: `VisibleState`, `ConstraintSnapshot`, `Context`, `PrivateEpisode`; `MissingEvidenceError`; the four-layer treatment of missing capacity (section 5.7).
- Evidence: `schemas.py`, `knowledge/retrieval.py`, `verification/checker.py`; tests in `test_checker.py`, `test_consumers.py`, `test_solver.py`, `test_labels.py`.
- Safe claims: missing capacity is an error in the checker, `insufficient_evidence` in the solver, a SHACL violation in the graph, and an exception in the snapshot property, with tests at each layer.
- Qualified claims: retrieval itself does not stop on missing capacity; the failure comes from the layers around it.

R02.2 Ontology and graph representation.
- Contribution: a versioned project ontology with Brick, PROV-O and QUDT alignment, twelve SHACL shapes and a builder that projects visible records into RDF.
- Essential details: the class and property tables in sections 3.3 and 3.4; the explicit-type requirement under `inference=None`; the separation of schema, episode facts and traces.
- Evidence: `ontology/*.ttl`, `knowledge/ontology.py`, `knowledge/graph.py`, `test_ontology.py`, `test_graph.py`.
- Safe claims: the ontology is implemented, versioned, loaded offline and validated by SHACL in tests; the graph is built from policy-visible records only.
- Qualified claims: PROV-O and QUDT alignment is partial (section 3.10); four classes and one property are declared but unused; SHACL is not run at runtime.

R02.3 Retrieval and context.
- Contribution: SPARQL retrieval over the graph, and a hashed `Context` that is identical across presentations.
- Essential details: the six queries, the flat results and their fields (section 4.3), the `Context.build` projection, and the label-only difference between "graph" and "flat".
- Evidence: `knowledge/retrieval.py`, `schemas.py:L966`, `test_retrieval.py`, `test_consumers.py`.
- Safe claims: retrieval exposes the visible facts through SPARQL and a context record, with evidence ids and source references preserved, and future jobs excluded.
- Qualified claims: the agent's context is derived from the records, not from the RDF query results; SPARQL results are for inspection and tests; the "graph" presentation does not change content.

R02.4 Validation and constraint enforcement.
- Contribution: three distinct mechanisms (SHACL, Pydantic, runtime checker) and an independent simulator guard, all driven by shared constraint records.
- Essential details: section 5.1 table; capacity semantics (IT power, before PUE, half-open intervals); the 100 to 70 kW tests.
- Evidence: `shapes.ttl:L342-L376`, `checker.py:L291-L349`, `test_checker.py`, `test_graph_driven_constraints.py`.
- Safe claims: a change to the capacity constraint changes the checker verdict and the context hash with no code change; the checker is independent of the evaluation validator by construction.
- Qualified claims: the graph-to-checker demonstration is test-only; SHACL does not detect a changed numeric limit and does not check plans.

R02.5 Simulator and impact model.
- Contribution: a deterministic 30-slot simulator and shared energy and carbon formulas.
- Essential details: section 6.1 and 6.2; atomic rejection; Q01; the refusal rules for savings claims.
- Evidence: `simulator/core.py`, `metrics/impact.py`, `tests/simulator/`.
- Safe claims: the simulator re-enforces the physical rules and exposes only visible state; emissions are not reported when carbon is missing.
- Qualified claims: the physical model is a deliberate simplification; the pollutant basis is unresolved.

R02.6 Reference optimisation.
- Contribution: a MILP reference with explicit status semantics, independently cross-checked by an exhaustive oracle on small cases.
- Essential details: section 6.5 and 6.6; the solver's inclusions and exclusions; the tie-break statement.
- Evidence: `reference/solver.py`, `test_solver.py` (including the oracle tests).
- Safe claims: a timeout is `unresolved`; missing or stale carbon is `insufficient_evidence`, not infeasible; results are bound to the context hash; the solver agrees with an independent oracle on the hand-built cases.
- Qualified claims: "certified optimal" means HiGHS success on the visible-horizon model, with the default gap; the tie-break is candidate order and not a frozen scientific rule.

R02.7 Labels, cache, hindsight and the evaluation boundary.
- Contribution: leakage-safe labels, an immutable hash-keyed cache, and offline hindsight bounds exported outside the repository.
- Essential details: sections 6.9 to 6.12.
- Evidence: `labels.py`, `cache.py`, `hindsight.py`, `test_labels.py`, `test_cache.py`, `test_hindsight.py`, the label audit and manager review handoffs.
- Safe claims: only certified optimal visible results become labels; labels cannot use future arrivals or realised carbon in the tested cases; the cache refuses non-optimal, mismatched or corrupted entries.
- Qualified claims: labels are single-schedule membership with unmeasured ties; development labels are not held-out labels; no production caller of `reject_hindsight_in_context` exists; O04 is pending.

R02.8 Evidence, limitations and status.
- Contribution: an honest account of what has been verified and how.
- Safe claims: the full suite passes on Python 3.12 locally; the focused suites pass; the status table in section 7.1.
- Qualified claims: CI for the inspected commit is unverified; the live-model run is documented, not re-run.

### 9.3 Report-ready technical explanation

The following paragraphs state the technical content in a form that can be adapted. They are written to be accurate against the commit inspected and are not a draft of the report section.

The system represents a scheduling problem with a small number of typed, versioned records. A constraint snapshot carries the site parameters, the capacity limit and the job constraints, each with an identifier, a unit and a source. A visible state carries the jobs that have arrived, the running and completed work, the carbon forecasts issued for the current slot and an explicit list of slots without a forecast. Realised carbon and jobs that have not yet arrived are held in a private episode that policies never receive. Each record has a canonical SHA-256 hash, and a context record, built from a visible state and a snapshot, adds evidence identifiers and a content hash that is independent of how the context is presented.

A project ontology in the `sched:` namespace describes these records, and reuses Brick for the building type, PROV-O for provenance relations and QUDT for units. A builder turns a visible state and its constraint snapshot into an RDF graph, projecting out the constraints of jobs that have not arrived, and a set of twelve SHACL shapes states what a valid graph contains. Among them is a rule that a site must have exactly one capacity constraint, so that absence of capacity cannot be read as unlimited capacity. Validation is run with RDFS inference disabled, so the graph asserts every type that a shape requires. Six SPARQL queries expose the jobs, forecasts, constraints, missing-forecast slots and site parameters from the graph. The context that the scheduling agent, the plain model, the heuristic and trained policies and the reference solver consume is assembled from the records and carries the same content under either presentation; the SPARQL results serve inspection and testing.

A proposed schedule is checked by a deterministic Python checker before anything is executed. The checker verifies identifier and state binding, arrival and current-slot timing, deadlines (the completion boundary), nonflexible jobs, the rule that no job starts after slot 23, forecast freshness, evidence citations and capacity. Capacity is compared in every slot of each job's half-open interval against the single capacity constraint, using IT power before PUE is applied, and a missing capacity constraint produces an error and never an unlimited limit. The agent receives at most one repair attempt and then a deterministic fallback, a controller rechecks the approved plan against the latest state, and the simulator applies its own batch-atomic checks. Tests show that changing the capacity constraint from 100 kW to 70 kW changes the checker's verdict and the context hash without any change to code, and that a capacity value read back from the graph by SPARQL and placed in a snapshot produces the same verdicts.

The reference solver minimises emissions over the jobs that are visible at a decision slot. Each candidate is a start slot that respects the job's window, capacity given current occupancy, the visible horizon and the freshness of the forecasts for its slots, and a mixed-integer program chooses one start for every arrived job. Results carry one of four statuses. A timeout is `unresolved`, missing or stale carbon is `insufficient_evidence`, a model with no feasible start is `certified_infeasible`, and HiGHS success is `certified_optimal` with its gap and bound recorded. Ties are broken by a stable candidate order under a pinned solver version, and the scientific tie-break remains an open decision. Certified optimal results become training labels, and a cache keyed by the state, context, decision time, candidate set, solver and label-schema versions returns only certified, visible, hash-verified entries. A separate hindsight solver uses future arrivals and realised carbon to produce sealed offline reference artifacts, which are exported outside the repository and are never part of a policy's context.

### 9.4 Claims to avoid

The report should not say that agent decisions are ontology-grounded at runtime, that SHACL validates plans or gates execution, that the graph presentation changes the model's input, that the reference is the unique or zero-gap optimum, that development labels are evaluation labels, that the carbon source is validated or licensed for redistribution, that a timeout shows infeasibility, or that passing tests on one fixture show behaviour on real episodes. It should also not cite the responsibility checklist as evidence of completion.

---

## 10. Evidence index

All URLs below are at commit `cd272e93a58af8e373bfa8ed96d1191687b919fc`. For brevity the common prefix is written `B =` and each row gives the suffix to append: `B = https://github.com/ReymoT/data-center-agentic/blob/cd272e93a58af8e373bfa8ed96d1191687b919fc/`.

| Item | URL (B + suffix) | Why it matters |
|---|---|---|
| Ontology | `B` + `ontology/dc-sustainability.ttl` | Classes, properties and the Brick, PROV-O and QUDT alignment |
| SHACL shapes | `B` + `ontology/shapes.ttl` | The twelve shapes; capacity evidence at L342-L376 |
| Ontology API and SHACL call | `B` + `dc_sustainability/knowledge/ontology.py#L164-L211` | `validate_graph` with inference disabled |
| Unit mapping | `B` + `dc_sustainability/knowledge/ontology.py#L55-L68` | `UNIT_MAP`, the IRI form that differs from the ontology file |
| Graph builder | `B` + `dc_sustainability/knowledge/graph.py#L126-L204` | How visible records become triples |
| Retrieval queries and `retrieve` | `B` + `dc_sustainability/knowledge/retrieval.py#L27-L101`, `#L267-L295` | The SPARQL and the point where graph and context are built separately |
| Context assembly | `B` + `dc_sustainability/schemas.py#L966-L1014` | `Context.build`, the source of agent and solver input |
| Missing evidence | `B` + `dc_sustainability/schemas.py#L64`, `#L483` | `MissingEvidenceError` and the capacity property |
| Checker | `B` + `dc_sustainability/verification/checker.py#L37-L350` | The runtime verification, capacity at L291-L349 |
| Rules | `B` + `dc_sustainability/verification/rules.py` | Legal starts and forecast assessment |
| Agent harness | `B` + `dc_sustainability/agent/harness.py#L82-L128`, `#L218` | Retrieval, check, repair, fallback wiring |
| Prompt renderer | `B` + `dc_sustainability/agent/renderers.py` | What the model receives |
| Plain policy | `B` + `dc_sustainability/llm/plain.py` | Flat-only context and the absence of a hindsight guard |
| Controller | `B` + `dc_sustainability/runtime/controller.py#L41-L110` | Recheck and approval |
| Simulator | `B` + `dc_sustainability/simulator/core.py#L45-L231` | Reset, state, step |
| Impact formulas | `B` + `dc_sustainability/metrics/impact.py#L153` | Energy and emissions |
| Visible solver | `B` + `dc_sustainability/reference/solver.py#L175-L343` | Model, statuses, tie-break text |
| Labels | `B` + `dc_sustainability/reference/labels.py#L109-L230` | Label attachment and exclusions |
| Cache | `B` + `dc_sustainability/reference/cache.py#L45-L230` | Key and hit rules |
| Hindsight | `B` + `dc_sustainability/reference/hindsight.py#L72-L605` | Solver, artifact, export, guard |
| Training pipeline | `B` + `dc_sustainability/training/pipeline.py#L40-L80` | The only production consumer of the solver |
| Carbon adapter | `B` + `dc_sustainability/data/carbon_source.py#L16-L98` | Pinned source and validation |
| Persistence forecasts | `B` + `dc_sustainability/data/materialize_development.py#L192-L235` | Causal development forecasts |
| Forecast footprint check | `B` + `dc_sustainability/data/forecast_isolation.py` | Source-footprint conflict utility |
| Ontology tests | `B` + `tests/knowledge/test_ontology.py` | SHACL, units, typing |
| Graph tests | `B` + `tests/knowledge/test_graph.py` | Builder content |
| Graph-driven tests | `B` + `tests/knowledge/test_graph_driven_constraints.py#L56-L68`, `#L121`, `#L229` | The test helper and the K03 demonstrations |
| Retrieval tests | `B` + `tests/knowledge/test_retrieval.py` | Queries, context, visibility |
| Consumer tests | `B` + `tests/knowledge/test_consumers.py` | Plain policy, checker, and missing-capacity boundary |
| Checker tests | `B` + `tests/verification/test_checker.py` | Hand-calculated expectations |
| Solver tests | `B` + `tests/reference/test_solver.py` | Statuses, timeout, oracle |
| Label, cache, hindsight tests | `B` + `tests/reference/test_labels.py`, `test_cache.py`, `test_hindsight.py` | Labels, cache, offline export |
| Simulator tests | `B` + `tests/simulator/test_core.py`, `tests/simulator/test_s02_impact.py` | Step, atomicity, impact |
| CI workflow | `B` + `.github/workflows/bootstrap.yml` | The CI steps |
| Dependency lock | `B` + `requirements/requirements-windows-py312.lock.txt` | Pinned versions |
| Python range | `B` + `pyproject.toml#L5` | `requires-python >=3.12,<3.13` |
| 3.12 guard | `B` + `dc_sustainability/data/materialize_development.py#L314-L315` | Explains the 3.13 failures |
| Architecture | `B` + `docs/ARCHITECTURE.md#L145`, `#L165` | The planned SHACL step and the "two graphs" statement |
| Interfaces | `B` + `docs/INTERFACES.md` | Contract definitions |
| Ontology notes | `B` + `docs/ontology/README.md` | Documented semantics and the inference constraint |
| Responsibility checklist | `B` + `docs/team/03_RESPONSIBILITY_CHECKLIST.md` | Task definitions and acceptance wording |
| Existing R02 draft | `B` + `docs/report/R02_ONTOLOGY_AND_REFERENCE_METHODS.md` | Prior text to compare against this report |
| Handoffs | `B` + `docs/handoffs/O01_EXHAUSTIVE_ORACLE_REVIEW.md`, `O03_HINDSIGHT_EXPORT.md`, `VED_REFERENCE_MANAGER_REVIEW.md`, `LEGACY_LABEL_AUDIT_2026-11-04.md`, `ISSUE60_SOURCE_EVIDENCE.md`, `D06_F04_F05_VERIFICATION.md`, `F02_DOWNSTREAM_ACCEPTANCE.md`, `D04_DEVELOPMENT_MATERIALIZATION_112.md` | Decisions and audits behind the code |
| Development evidence | `B` + `docs/R04_DEVELOPMENT_EVIDENCE.md` | Recorded validation run summary |
| Repository instructions | `B` + `AGENTS.md` | Authority, checker-versus-validator independence, current status notes |
| CI run (rendered summary only) | `https://github.com/ReymoT/data-center-agentic/actions` run #259, commit `6c288c0` | The only CI page I could read; predates the reference code |

---

## 11. Remaining uncertainty and what would settle it

| Uncertainty | What would settle it |
|---|---|
| Whether CI passed for `cd272e93` on the Windows target | The Actions run and step logs for that commit |
| Whether any implemented work exists outside `main` (open branches or pull requests) | The repository's branch and pull request list, which was not accessible |
| Whether the default HiGHS gap makes some `certified_optimal` results non-exact | The recorded `gap` and `bound_kg` values over the cached certified results, or the `milp` default documented for the pinned scipy |
| How many label ties exist, and whether the labels are materially ambiguous | Enumeration of alternative optima on a sample, under the Q08 decision |
| Whether the unit IRI form in `ontology.py` or in the ontology file is the correct QUDT form | The pinned pyqudt vocabulary and a decision, with a test that compares emitted IRIs to the ontology |
| Whether `llm/plain.py` or another layer rejects hindsight data, as the O03 handoff states | The commit that the handoff refers to, or a code search on the branch it came from |
| Whether the production checker and the evaluation validator disagree anywhere | A differential run of the two over generated and simulator-produced states |
| Whether the three rule implementations (checker, solver, simulator) always agree | A randomised differential test over generated states |
| Whether any real simulated episode, validated slot by slot, passes SHACL | A run of `validate_graph` over graphs built from every slot of a generated development episode |
| Behaviour of the agent against a live model on varied capacities | An authorised Ollama run with capacity varied, recorded with trace files |
| Windows behaviour (ACLs on hindsight exports, line endings, the skipped Windows-only tests) | A Windows run on Python 3.12, which CI would provide |
| Source rights, pollutant basis and interval semantics of the carbon data | Decision records for Q05 and Issue 60 blockers B1 to B3, which I did not find on `main` |
| Held-out reference quality (O04) | The held-out run and its freeze, which have not happened |
| Whether any consumer reads the flat `RetrievalResult` lists | A repository-wide search; I searched `agent/`, `policies/`, `runtime/`, `experiments/`, `llm/` and `training/` and found none |