Teammates and roles

- Edison Perez Cash: energy and carbon calculations, greedy scheduling references, and trained decision-tree and random-forest policies (E2).
- Matty Anderson and Nisha Mahadev Kolekar: the LangGraph agent and plain-LLM comparison, verification and safety, evidence-based explanations, integration, evaluation and reporting (E4-E6).
- Reimo Tamme: source data, synthetic jobs, scenario splits and the simulator, working with Ved on E1 and E3.
- Ved Patil: shared contracts, ontology and retrieval, offline reference schedules and reproduction, working with Reimo on E1 and E3.

All teammates contribute their technical sections, interface coordination and results. Matty and Nisha share the research responsibilities listed above; their detailed implementation duties are divided in the [responsibility checklist](docs/team/03_RESPONSIBILITY_CHECKLIST.md). The package's detailed lead allocations remain recorded under Q12.

# Data Center Sustainability Agent

FSE 598, Arizona State University.

Our research question: Does an ontology-grounded, tool-verified agent improve the accuracy, faithfulness and safety of data-center sustainability recommendations compared with a plain LLM?

We test this question through workload scheduling at one simulated data center. The main comparison is `agent` versus `plain_llm`, using equivalent visible information. The four additional scheduling policies provide reference results. Scheduling is the experimental setting; conclusions will be limited to the evaluated scenarios.

This repository contains project documentation, F02 shared schemas/examples, D01 carbon ingestion, and Matty's A01 transport/accounting and A03 fixed schedule checks. The scheduling pipeline, training, experiment CLI and demonstration are not implemented yet. The executable checks validate the existing components and candidate dependencies; they do not run experiments or establish research results.

## Systems we reviewed and why we chose this architecture

We reviewed AssetOps Knowledge Graph and AssetOpsBench, LC-Opt, Google DeepMind's data-center cooling system, and Schneider Electric's Resource Advisor Copilot. Our supplied system review compared their data, asset relationships, division of work between an LLM and deterministic software, testing, uncertainty, safety and approval controls.

AssetOps is similar to our project because it connects facts and dependencies through a typed knowledge graph. We use that idea for jobs, slots, constraints and evidence IDs. LC-Opt is similar because it tests decisions in simulation; our final scope uses a small Python scheduling simulator rather than its cooling digital twin. DeepMind is similar because checks and fallback protect execution; we use deterministic schedule checks, a latest-state recheck, checked fallback and abstention. Resource Advisor is similar because it explains sustainability information; we require source-linked claims, units, assumptions and limitations.

We chose a combination of these ideas because our question requires connected evidence, exact calculations, bounded model decisions and comparable saved outputs. RDF represents domain facts. LangGraph manages the agent's sequence of steps. Python checks decide whether a simulated action can execute. This is our best-fit design rationale, not proof that it is the best architecture or will outperform the alternatives. The experiments will test the complete agent; they cannot isolate the ontology's contribution. We have not reproduced these external systems or compared their accuracy directly.

The [source review record](docs/SOURCE_REVIEW.md) identifies the supplied documents and their public references. The [updated architecture diagram](architecture/architecture.svg) and [plain-language architecture document](docs/ARCHITECTURE.md) describe the final scheduling study. The diagram shows the planned design, not implemented components.

![Planned architecture for the final scheduling study](architecture/architecture.png)

## Main comparison and scheduling references

The main research comparison uses two systems with the same arrived jobs, visible forecasts and authoritative constraints:

- `agent`: the ontology-grounded LangGraph agent, with one repair and checked greedy-A fallback.
- `plain_llm`: one model call with equivalent flat facts; no tools, repair or fallback.

Four additional policies use the same visible inputs to put scheduling performance in context:

- `greedy_a`: start jobs as soon as feasible.
- `greedy_b`: choose feasible starts with the lowest forecast emissions.
- `decision_tree_c`: a trained scheduling classifier.
- `random_forest_d`: a trained scheduling classifier.

These six systems do not represent six separate research questions. The study evaluates the complete agent against the plain LLM; it does not separately prove the benefit of ontology grounding or tool verification alone.

The earlier name "Model D" means the agent. Policy `random_forest_d` is a different system. Both learned policies are required; greedy policies and offline optimization are not substitutes for classical ML.

The site has 100 kW IT capacity including 40 kW background, constant job power of 10-40 kW and durations of 1-4 hourly slots. Jobs cannot pause once started. PUE 1.2 is a design assumption, with 1.0 used in hand checks. Episodes have 24 decision slots and six completion slots. No model calls occur in completion slots. Whether new jobs may start then is unresolved Q01.

Energy equals PUE times IT kW times hours. Emissions equal kWh times carbon g/kWh divided by 1,000, with the source's CO2 versus CO2e meaning still to be verified. Timing changes emissions, not the energy required for the same completed fixed-power work. Results must also show completed work, deadline misses and unfinished jobs.

Live equipment control, cooling or water savings, reinforcement learning, Modelica/FMU and enterprise integrations are outside the required project. No LLM fine-tuning is planned.

## Start with the instructions

Read [PROJECT_MASTER.md](PROJECT_MASTER.md), [shared rules](docs/team/01_SHARED_RULES.md), your `MASTER_<NAME>.md` in [the complete package](docs/team/00_START_HERE.md), [interfaces](docs/INTERFACES.md), [open decisions](docs/team/04_OPEN_DECISIONS.md), your assigned Issue and upstream handoffs. Ved's contract 1.0.0 schemas and examples are implemented. The interface document distinguishes those records from planned callable APIs; each consumer must still validate adoption. Experiment CLI names are not runnable commands yet.

See [the current maintenance handoff](docs/handoffs/F03_F04_F05_MAINTENANCE.md) for checks and remaining inputs, and [the publication audit](docs/team/REVIEW_RECORD.md) for current documentation status. The [original setup handoff](docs/handoffs/F01.md) is historical. These documents are published under the project manager's instruction; formal document review is not required.

## Quick start for the repository foundation

The package proposes Python 3.12. Windows is the only supplied dependency-lock target; additional supported operating systems await Q13.

```powershell
git clone https://github.com/ReymoT/data-center-agentic.git
cd data-center-agentic
git switch main
py -3.12 -m venv .venv
.venv\Scripts\python.exe scripts/validate_setup.py
```

The checker needs only the Python standard library and makes no network or model calls. It validates documentation links, task ownership/dependencies, role consistency, configuration placeholders and dependency input locations.

To validate the proposed full Windows environment:

```powershell
.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/requirements-windows-py312.lock.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts/smoke_dependencies.py
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
```

Installation needs package-index access. Smoke checks run imports, SHACL/SPARQL, a tiny MILP, classifier fit/save/load and a LangGraph route without an LLM. See [environment instructions](requirements/README.md) for status and troubleshooting. The supplied lock is a candidate, not a final provider-inclusive environment. Do not use its Windows wheel hashes on other platforms.

The offline test command runs F02 contracts, D01 inspection, provider helpers, actual Ollama transport against a local synthetic HTTP test server, and actual fixed schedule checks. Synthetic fixtures and server responses are test-only; they do not establish model inference, source acceptance or end-to-end integration. CI runs the same whole test directory on PRs and main. [The A01/A03 handoff](docs/handoffs/A01_A03_AGREED_CORE.md) links implementation and verification evidence.

All provider/account/settings placeholders in `.env.example` are blank. Keep them blank until the complete Q09 deployment configuration is recorded; the accepted development direction below does not fill missing pins. [The configuration template](configs/project.example.json) records known proposal constants and keeps decision entries null. It is not a production loader or an execution permission.

Matty accepted local Ollama with Qwen3 8B and temperature 0.2. [The Q09 decision](docs/decisions/Q09_OLLAMA_QWEN3.md) records the accepted development settings and owners: Matty prepares the shared adapter/environment, Nisha prepares plain/explanations, and Ved supports F02 compatibility. Matty supplied his [Intel Arc 140V / 32 GB hardware details](docs/HARDWARE.md); Ollama 0.40.3 is installed, but Qwen3 8B is absent. Final runtime/SDK/model-digest/seed/context/resource pins remain pending. No inference or held-out/cloud/paid run was performed.

## Available adapter and checker core

[The shared Ollama transport](dc_sustainability/llm/provider.py) performs real HTTP, strict F02 parsing, pin checks, deadlines and attempt accounting. It uses the Python standard library without choosing an SDK. Both LLM callers must share one run ledger. Prompts/output projections, a validated model-specific token counter, explicit deployment pins and run limits are still required; there is no runnable experiment configuration or automatic model installation.

[The fixed checker](dc_sustainability/verification/checker.py) checks visible job/evidence IDs, timing, deadlines, nonflexible starts and proposed/running occupancy against authoritative capacity. Changing the constraint from 100 to 70 kW changes the check. Known violations are rejected; an otherwise feasible proposal receives an explicit unresolved-rule error. Q01-Q04 still block overall approval, and no execution gate or numerical-claim certification is supplied.

Run these components' offline tests with:

```powershell
.venv\Scripts\python.exe -m pytest tests/llm/test_ollama_provider.py tests/verification/test_checker.py -q
```

## Data, experiments and outputs

Reimo implemented pinned SustainDC Arizona source acquisition, checksum/CSV inspection and private UTC observations. Pollutant meaning, physical hour-start/hour-end mapping, derived-data redistribution rights, F02 adaptation and independent source reproduction still block accepted experimental use. [Data instructions](data/README.md) record acquisition and evidence. Frontier-calibrated job generation and episodes remain planned; EPA eGRID is an annual plausibility check. Perfect-foresight forecast replay must be labeled and must not be confused with a live forecast.

The implemented source-inspection command is:

```powershell
.venv\Scripts\python.exe -m dc_sustainability.data.carbon_source --help
```

Its help describes local inspection and the optional pinned download. A download uses the network and requires new destination/report files. Validation success is not scientific acceptance; returned records are not adopted F02 forecasts. Offline CI does not download the source.

The proposal requires 40 development episodes and 30 held-out episodes: six dates across four scenarios plus six missing-forecast episodes. Three trials for each LLM and one for each A/B/C/D policy produce 300 runs. Held-out data cannot tune models, prompts or thresholds. The agent has at most three model calls per decision including explanation; the plain LLM has one. Paid runs await Q09.

Nisha will define the CLI during F02/E02 implementation with the module owners. Data validation, graph validation, labels, training, single-episode runs, matrix runs, scoring and figures are planned commands, not runnable commands in this scaffold. The [demo runbook](docs/DEMO.md) records the future evidence requirements without inventing a transcript.

`data/` will hold permitted fixtures and manifests, `ontology/` graph definitions, `models/` trained-artifact manifests, and `results/` trace/evaluation manifests. Raw/private data, generated runs, secrets and large artifacts are excluded from Git by default. License and retention decisions await Q05/Q13. No license is selected here.

## Workflow and remaining work

The masters and shared instructions on GitHub's `main` branch are authoritative. Only Matty Anderson (`MattyAnd`) may authorize changing them. Teammates and their AI assistants must not overwrite, replace or publish new versions without his explicit authorization. Propose corrections in an Issue. Local copies and higher version numbers do not supersede main; preserve unpublished code when synchronizing instructions. This project rule is documented in [PROJECT_MASTER.md](PROJECT_MASTER.md); GitHub-enforced access restrictions require repository-owner action.

A pull request can be merged once its checks pass. A teammate review is welcome but not required. Changes to shared data formats or settings still need the affected teammates to agree first.

Record affected teammates' agreement in the Issue or decision record before changing shared formats or settings. Matty is the project manager and has also authorized direct publication of these documents to `main`. Development can use short task branches, with applicable checks before publication. [Module ownership](docs/OWNERSHIP.md) supports technical coordination, and [repository settings](docs/REPOSITORY_SETTINGS.md) record the current workflow. Matty's GitHub account for this project is [MattyAnd](https://github.com/MattyAnd).

The [project plan](docs/PROJECT_PLAN.md) links the authoritative checklist and timeline. The [decision register](docs/team/04_OPEN_DECISIONS.md) retains unresolved choices and records partial Q09/Q11 decisions. Shared-record consumer adoption, source evidence, final provider/budget pins, remaining team permissions, detailed allocations and target platforms still need evidence. Stubs, constant success verdicts and fabricated model responses/traces/results are not completion evidence. Final end-to-end acceptance belongs to Matty, independent verification to Nisha, and second-machine reproduction to Ved.
