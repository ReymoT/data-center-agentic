# Team master instruction package

Current decision intake, October 20, 2026: [Q01-Q04 status](../decisions/Q01_Q04_AGREEMENT_STATUS.md) records Matty's reply and missing Edison input; [Q09 setup](../decisions/Q09_DEPLOYMENT_OCT20.md) is agreed but blocked by runtime drift/context validation; [Q10](../decisions/Q10_REVIEW_STATUS.md) remains partial. Matty is coordinator/publisher and Nisha backup; Nisha confirmed her Q12 allocation, the other owners are pending. [The handoff](../handoffs/OCT20_SIX_PRIORITIES.md) records actual E01 checks and remaining gates. No teammate task, scientific default or shared schema changed.

Version: 1.14 - 2026-10-20. Repository: https://github.com/ReymoT/data-center-agentic

Give each teammate the whole package. Read the teammate's MASTER file, all numbered files 00-04, [project context](../PROJECT_CONTEXT.md), the assigned Issue and prerequisite handoffs. A detached role file is not the complete specification.

The masters and shared instructions published on GitHub's main branch are the authoritative versions. Only Matty Anderson (MattyAnd) may authorize changes to them. Other teammates and their AI assistants must not edit, overwrite, replace, delete or publish new versions without Matty's explicit authorization.

Fetch and read current main instructions, preserving local work. Local packages, timestamps, version numbers and AI-generated files do not supersede the published instructions. Propose corrections in an Issue; record Matty's authorization before changing instruction files.

The October final proposal defines research scope. Earlier Model D diagrams provide background; they do not expand the study to cooling, water, digital twins or live control. [Architecture](../ARCHITECTURE.md) and the [updated diagram](../../architecture/architecture.svg) describe the final scheduling design. F02 records, D01 carbon inspection, D02 calibration tooling and D03 provisional synthetic generation are implemented. [Current checker-consumer and documentation evidence](../handoffs/A03_D03_F04_F05.md) does not certify empirical calibration, frozen fixtures, simulator visibility or the full system.

Matty is the project manager. Start with [PROJECT_MASTER.md](../../PROJECT_MASTER.md). [Q11](../decisions/Q11_MANAGER_AUTHORITY.md) records the fixed merge rule.

A pull request can be merged once its checks pass. A teammate review is welcome but not required. Changes to shared data formats or settings still need the affected teammates to agree first.

Technical checks and independent scientific evaluation remain required. Formal review is optional; agreement on shared formats and settings is required before those changes.

The proposal pairs Matty/Nisha on E4-E6 and Reimo/Ved on E1/E3; Edison owns E2. The masters describe detailed module leads. Those allocations refine the proposal and remain subject to Q12. Matty's manager role is confirmed; backup, summary publisher and remaining permission choices stay in Q11.

D06 update, 2026-10-19: read [the current verification](../handoffs/D06_F04_F05_VERIFICATION.md) for the merged checker, actual-source Windows rerun and remaining acceptance limits. Merged tooling and a structural pass do not resolve Q05 or freeze policy data.

## Files and authority

- MASTER_MATTY.md: repository foundation, provider/agent, production checker, execution gate, instruction maintenance and final end-to-end acceptance.
- MASTER_NISHA.md: plain LLM, explanations, independent scoring, runner, analysis and report assembly.
- MASTER_REIMO.md: data, synthetic jobs, episodes, splits and simulator.
- MASTER_VED.md: contracts, ontology/retrieval, offline reference schedules and reproduction.
- MASTER_EDISON.md: impacts, greedy policies, trained decision tree/random forest and model artifacts.
- 01_SHARED_RULES.md: scope, coordination, publication and acceptance rules.
- 02_INTERFACE_CONTRACTS.md: pointer to [implemented F02 records](../INTERFACES.md) and their adoption status.
- 03_RESPONSIBILITY_CHECKLIST.md: 50 tasks, owners, technical contacts, dependencies and acceptance evidence.
- 04_OPEN_DECISIONS.md: unresolved scientific and project decisions. Do not infer defaults.
- [REVIEW_RECORD.md](REVIEW_RECORD.md): current audit and verification limits.
- [CHANGELOG.md](CHANGELOG.md): instruction adaptations from the preserved source archive.

Dependency inputs are maintained only under [requirements](../../requirements/README.md). The original package archive remains unchanged outside Git. [Q09](../decisions/Q09_OLLAMA_QWEN3.md) accepts local Ollama, Qwen3 8B Q4_K_M and temperature 0.2. Matty prepares the shared adapter; Nisha prepares the plain/explanation paths; Ved supports contract compatibility. [Hardware inventory](../HARDWARE.md) is now available and [A01/A03 core](../handoffs/A01_A03_AGREED_CORE.md) is implemented; deployment pins and full integration remain pending. See [the owner handoff](../handoffs/Q09_ACCEPTANCE.md). Platform adoption remains Q13.

## Implementation order

1. Resolve required allocations/coordination choices. Ved's F02 schemas/examples are implemented; producers and consumers validate adoption against them.
2. Reimo supplies immutable development fixtures; Edison supplies hand-checked impacts and A; Matty/Nisha develop their separate verification paths; Ved builds graph and offline references.
3. Establish a development vertical slice before full training or paid runs.
4. Validate data and labels, train C/D, integrate both LLM systems and explanations.
5. Complete failure tests, independent scoring and blinded pre-evaluation annotation; freeze the protocol.
6. Run held-out experiments, analyze results, reproduce on a second machine and finish Matty's final E2E acceptance.

Course planning update, October 20, 2026: Nisha reports Group 15 presents in class November 16, submits the presentation November 18 at 11:59 pm, demos December 2 (submission 11:59 pm), and submits the report December 9 at 11:59 pm. Read [Q13](../decisions/Q13_PRESENTATION_DEADLINE.md) and [the current plan](../PROJECT_PLAN.md). Timezone, rubric/formats and separate code/release requirements remain unconfirmed. Rehearsal must be before November 16; no exact day is agreed. These are attributed course reports, not verified outcomes or scientific acceptance.

Maintain README, architecture, plan, interfaces, coordination, handoffs and decisions in their linked repository locations. Avoid detached latest copies and duplicate contracts. README starts with equally formatted teammate roles, groups Matty/Nisha, and discloses reviewed systems, comparison method and architecture rationale. Use MattyAnd for authentication and commit attribution.
