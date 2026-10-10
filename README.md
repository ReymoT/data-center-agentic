Teammates and roles

Matty Anderson (GitHub: [MattyAnd](https://github.com/MattyAnd)) owns repository setup, environment and CI, README and architecture, shared instructions, the LLM adapter, LangGraph agent, production checks, execution gate, runtime traces, integration and final end-to-end acceptance.

Reimo Tamme leads source data, synthetic jobs, splits and the simulator.
Ved Patil leads shared contracts, ontology and retrieval, offline reference schedules and second-machine reproduction.
Edison Perez Cash leads energy and carbon calculations, greedy references and trained decision-tree and random-forest policies.
Nisha Mahadev Kolekar leads the plain LLM, explanations, independent evaluation, experiment runner, statistics and report assembly.
All teammates write their technical sections and review interfaces and results. These lead allocations clarify the proposal's paired duties; Q12 still requires team acceptance. Reviewers and task dependencies are in the [responsibility checklist](docs/team/03_RESPONSIBILITY_CHECKLIST.md).

# Data Center Sustainability Agent

FSE 598, Arizona State University. We are building a research prototype that recommends when computing jobs should run at one simulated data center. Our question is whether an ontology-grounded agent with executable checks improves accuracy, faithfulness and safety compared with a plain LLM given equivalent information.

This branch prepares the repository for review. The scheduling pipeline, training, experiment CLI and demonstration are not implemented yet. The executable commands below check the repository foundation and candidate dependencies. They do not run experiments or establish research results.

## Systems we reviewed and why we chose this architecture

We reviewed AssetOps Knowledge Graph and AssetOpsBench, LC-Opt, Google DeepMind's data-center cooling system, and Schneider Electric's Resource Advisor Copilot. Our supplied system review compared their data, asset relationships, division of work between an LLM and deterministic software, testing, uncertainty, safety and approval controls.

AssetOps is similar to our project because it connects facts and dependencies through a typed knowledge graph. We use that idea for jobs, slots, constraints and evidence IDs. LC-Opt is similar because it tests decisions in simulation; our final scope uses a small Python scheduling simulator rather than its cooling digital twin. DeepMind is similar because checks and fallback protect execution; we use deterministic schedule checks, a latest-state recheck, checked fallback and abstention. Resource Advisor is similar because it explains sustainability information; we require source-linked claims, units, assumptions and limitations.

We chose a combination of these ideas because our question requires connected evidence, exact calculations, bounded model decisions and comparable saved outputs. RDF represents domain facts. LangGraph manages the agent's sequence of steps. Python checks decide whether a simulated action can execute. This is our best-fit design rationale, not proof that it is the best architecture or will outperform the alternatives. The experiments will test the complete agent; they cannot isolate the ontology's contribution. We have not reproduced these external systems or compared their accuracy directly.

The [source review record](docs/SOURCE_REVIEW.md) identifies the supplied documents and their public references. The old [architecture image](architecture/architecture.png) is preserved as historical context. It includes a broader engineering system and is not the implementation specification. The [architecture document](docs/ARCHITECTURE.md) explains the final scope in plain language.

## Scope and six systems

Every system will use the same arrived jobs, visible forecasts and authoritative constraints:

- `agent`: the ontology-grounded LangGraph agent, with one repair and checked greedy-A fallback.
- `plain_llm`: one model call with equivalent flat facts; no tools, repair or fallback.
- `greedy_a`: start jobs as soon as feasible.
- `greedy_b`: choose feasible starts with the lowest forecast emissions.
- `decision_tree_c`: a trained scheduling classifier.
- `random_forest_d`: a trained scheduling classifier.

The earlier name "Model D" means the agent. Policy `random_forest_d` is a different system. Both learned policies are required; greedy policies and offline optimization are not substitutes for classical ML.

The site has 100 kW IT capacity including 40 kW background, constant job power of 10-40 kW and durations of 1-4 hourly slots. Jobs cannot pause once started. PUE 1.2 is a design assumption, with 1.0 used in hand checks. Episodes have 24 decision slots and six completion slots. No model calls occur in completion slots. Whether new jobs may start then is unresolved Q01.

Energy equals PUE times IT kW times hours. Emissions equal kWh times carbon g/kWh divided by 1,000, with the source's CO2 versus CO2e meaning still to be verified. Timing changes emissions, not the energy required for the same completed fixed-power work. Results must also show completed work, deadline misses and unfinished jobs.

Live equipment control, cooling or water savings, reinforcement learning, Modelica/FMU and enterprise integrations are outside the required project. No LLM fine-tuning is planned.

## Start with the instructions

Read [shared rules](docs/team/01_SHARED_RULES.md), your `MASTER_<NAME>.md` in [the complete package](docs/team/00_START_HERE.md), [interfaces](docs/INTERFACES.md), [open decisions](docs/team/04_OPEN_DECISIONS.md), your assigned Issue and upstream handoffs. The current interface document is a draft for Ved and consumers to review. No shared schema or CLI spelling is approved by this bootstrap.

See [Matty's setup handoff](docs/handoffs/F01.md) for this branch, review routing and blockers. GitHub task updates are prepared as drafts in [the review request](docs/BOOTSTRAP_REVIEW.md). No Issue number or independent approval is assumed.

## Quick start for the repository foundation

The package proposes Python 3.12. Windows is the only supplied dependency-lock target; additional supported operating systems await Q13.

```powershell
git clone https://github.com/ReymoT/data-center-agentic.git
cd data-center-agentic
# Check out the reviewed bootstrap branch or commit when it is available remotely.
py -3.12 -m venv .venv
.venv\Scripts\python.exe scripts/validate_setup.py
```

The checker needs only the Python standard library and makes no network or model calls. It validates documentation links, task ownership/dependencies, role consistency, configuration placeholders and dependency-copy consistency.

To validate the proposed full Windows environment:

```powershell
.venv\Scripts\python.exe -m pip install --require-hashes -r requirements/requirements-windows-py312.lock.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts/smoke_dependencies.py
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts
```

Installation needs package-index access. Smoke checks run imports, SHACL/SPARQL, a tiny MILP, classifier fit/save/load and a LangGraph route without an LLM. See [environment instructions](requirements/README.md) for status and troubleshooting. The supplied lock is a candidate, not a final provider-inclusive environment. Do not use its Windows wheel hashes on other platforms.

Copy `.env.example` to a local `.env` only when Q09 is approved. All provider/account/settings placeholders are blank; no paid call is enabled. [The configuration template](configs/project.example.json) records known proposal constants and keeps open decisions null. It is not a production loader or an execution permission.

## Data, experiments and outputs

Reimo will acquire the pinned SustainDC Arizona carbon file, verify units and UTC alignment, and calibrate synthetic job distributions from Frontier job records. EPA eGRID supplies an annual plausibility check. Forecast replay is perfect foresight and must be labeled. [Data instructions](data/README.md) record the required acquisition evidence; source access and redistribution are not certified here.

The proposal requires 40 development episodes and 30 held-out episodes: six dates across four scenarios plus six missing-forecast episodes. Three trials for each LLM and one for each A/B/C/D policy produce 300 runs. Held-out data cannot tune models, prompts or thresholds. The agent has at most three model calls per decision including explanation; the plain LLM has one. Paid runs await Q09.

Nisha will define the CLI during F02/E02 review. Data validation, graph validation, labels, training, single-episode runs, matrix runs, scoring and figures are planned commands, not runnable commands in this branch. The [demo runbook](docs/DEMO.md) records the future evidence requirements without inventing a transcript.

`data/` will hold permitted fixtures and manifests, `ontology/` graph definitions, `models/` trained-artifact manifests, and `results/` trace/evaluation manifests. Raw/private data, generated runs, secrets and large artifacts are excluded from Git by default. License and retention decisions await Q05/Q13. No license is selected here.

## Review and remaining work

Use short task branches and independently reviewed PRs. A human merges until Q11 establishes authority. [Review routing](docs/OWNERSHIP.md) proposes human reviewers and deliberately leaves CODEOWNERS activation pending. [Administrator instructions](docs/REPOSITORY_SETTINGS.md) propose protections without claiming to enable them.

The [project plan](docs/PROJECT_PLAN.md) links the authoritative checklist and timeline. The [decision register](docs/team/04_OPEN_DECISIONS.md) retains Q01-Q13. Setup review, shared contracts, source evidence, model/budget, team permissions, accepted lead allocations and target platforms are still required. Tests of a skeleton are not integrated acceptance. Final end-to-end acceptance belongs to Matty, independent verification to Nisha, and second-machine reproduction to Ved.
