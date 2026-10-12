# Team master instruction package

Version: 1.5 - October 12, 2026. Repository: https://github.com/ReymoT/data-center-agentic

Give each teammate the whole package. Read the teammate's MASTER file, all numbered files 00-04, [project context](../PROJECT_CONTEXT.md), the assigned Issue and prerequisite handoffs. A detached role file is not the complete specification.

The October final proposal defines research scope. Earlier Model D diagrams provide background; they do not expand the study to cooling, water, digital twins or live control. [Architecture](../ARCHITECTURE.md) and the [updated diagram](../../architecture/architecture.svg) describe the final scheduling design. The repository is a scaffold, not an implemented research system.

Matty is the project manager. Start with [PROJECT_MASTER.md](../../PROJECT_MASTER.md). [Q11](../decisions/Q11_MANAGER_AUTHORITY.md) records the fixed merge rule.

A pull request can be merged once its checks pass. A teammate review is welcome but not required. Changes to shared data formats or settings still need the affected teammates to agree first.

Technical checks and independent scientific evaluation remain required. Formal review is optional; agreement on shared formats and settings is required before those changes.

The proposal pairs Matty/Nisha on E4-E6 and Reimo/Ved on E1/E3; Edison owns E2. The masters describe detailed module leads. Those allocations refine the proposal and remain subject to Q12. Matty's manager role is confirmed; backup, summary publisher and remaining permission choices stay in Q11.

## Files and authority

- MASTER_MATTY.md: repository foundation, provider/agent, production checker, execution gate, instruction maintenance and final end-to-end acceptance.
- MASTER_NISHA.md: plain LLM, explanations, independent scoring, runner, analysis and report assembly.
- MASTER_REIMO.md: data, synthetic jobs, episodes, splits and simulator.
- MASTER_VED.md: contracts, ontology/retrieval, offline reference schedules and reproduction.
- MASTER_EDISON.md: impacts, greedy policies, trained decision tree/random forest and model artifacts.
- 01_SHARED_RULES.md: scope, coordination, publication and acceptance rules.
- 02_INTERFACE_CONTRACTS.md: pointer to the sole proposed [interface blueprint](../INTERFACES.md).
- 03_RESPONSIBILITY_CHECKLIST.md: 50 tasks, owners, technical contacts, dependencies and acceptance evidence.
- 04_OPEN_DECISIONS.md: unresolved scientific and project decisions. Do not infer defaults.
- [REVIEW_RECORD.md](REVIEW_RECORD.md): current audit and verification limits.
- [CHANGELOG.md](CHANGELOG.md): instruction adaptations from the preserved source archive.

Dependency inputs are maintained only under [requirements](../../requirements/README.md). The original package archive remains unchanged outside Git. Matty validates the candidate environment; provider selection and platform adoption remain Q09/Q13.

## Implementation order

1. Resolve required allocations/coordination choices. Ved develops schemas and examples with producer/consumer validation.
2. Reimo supplies immutable development fixtures; Edison supplies hand-checked impacts and A; Matty/Nisha develop their separate verification paths; Ved builds graph and offline references.
3. Establish a development vertical slice before full training or paid runs.
4. Validate data and labels, train C/D, integrate both LLM systems and explanations.
5. Complete failure tests, independent scoring and blinded pre-evaluation annotation; freeze the protocol.
6. Run held-out experiments, analyze results, reproduce on a second machine and finish Matty's final E2E acceptance.

Internal targets: October 16 data/simulator and second-person check; October 23 A/B and retrieval; October 30 C/D and LLM paths; November 6 repair/fallback/gate; November 13 freeze; November 23 experiments/analysis; December 2 reproduction/rehearsal; December 4 delivery. An earlier course deadline takes precedence. November 26-27 is reserved.

Maintain README, architecture, plan, interfaces, coordination, handoffs and decisions in their linked repository locations. Avoid detached latest copies and duplicate contracts. README starts with equally formatted teammate roles, groups Matty/Nisha, and discloses reviewed systems, comparison method and architecture rationale. Use MattyAnd for authentication and commit attribution.
