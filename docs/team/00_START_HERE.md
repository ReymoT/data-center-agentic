# Team master instruction package

Version: 1.1 — October 10, 2026. Repository: https://github.com/ReymoT/data-center-agentic

Give each teammate the whole package and ask their assistant to start with that teammate's `MASTER_<NAME>.md`. The role file defines its work; the four numbered shared files define the common rules, interfaces, coverage and unresolved decisions. A detached role file is not the complete specification. Read the linked shared files before implementation.

## What this package establishes

The October final proposal is the research specification. The revised collaboration plan supplies the workflow. The user's latest instruction explicitly gives Matty repository setup, README, architecture documentation, master-file maintenance/fixes, and final end-to-end testing. Earlier Model D diagrams are background: do not implement their broader cooling, water, digital-twin or live-control system.

The proposal pairs Reimo/Ved on E1/E3 and Matty/Nisha on E4/E5/E6. This package makes the revised plan's lead split concrete: Reimo leads data/simulation; Ved leads ontology/references; Edison leads calculations and classical policies; Matty leads agent/runtime verification/integration; Nisha leads the plain comparison, explanations and independent evaluation.

**Allocation transparency:** the exact lead for shared schemas (Ved), CI/environment (Matty), experiment runner/report assembly (Nisha), and second-machine reproduction (Ved) is an implementation allocation supplied by this package, not a named assignment in the proposal. It gives every deliverable one accountable owner and stays within the existing work areas. Review these allocations before marking their issues Ready. Human integration coordinator, backup and merge authority remain decisions in `04_OPEN_DECISIONS.md`; Matty is not silently appointed to those human roles. Reviewers in the checklist are proposed routing assignments; a reviewer who coauthored a change needs an independent replacement.

These are instructions to implement the project, not a claim that the project is built. Checklist boxes are intentionally unchecked. The repository tree checked on October 10 contained `.gitignore`, `README.md`, `architecture/`, and `architecture/architecture.png`. All code paths in this package are proposed locations. Inspect the current repository before creating or moving anything; preserve existing work. The existing image may describe an earlier scope and must not become the final architecture by accident.

## Files and use

1. `MASTER_MATTY.md`: repository foundation, common runtime, gate, master-file fixes, final E2E.
2. `MASTER_REIMO.md`: sources, synthetic scenarios, splits, simulator and data documentation.
3. `MASTER_VED.md`: shared contracts, ontology/retrieval, offline references and reproduction.
4. `MASTER_EDISON.md`: energy/carbon functions, A/B policies, trained C/D policies and model artifacts.
5. `MASTER_NISHA.md`: plain LLM, explanations, independent evaluation, experiments and report assembly.
6. `01_SHARED_RULES.md`: scope, coordination, branch/review process and completion standard.
7. `02_INTERFACE_CONTRACTS.md`: proposed shared module boundaries, records and handoffs.
8. `03_RESPONSIBILITY_CHECKLIST.md`: one owner per required task and acceptance evidence.
9. `04_OPEN_DECISIONS.md`: unresolved rules, decision drivers and affected work.
10. `REVIEW_RECORD.md`: cross-file consistency checks and remaining limits.

`reference/` contains the previously dependency-resolved core requirements and Windows Python 3.12 lock. They are proposed environment inputs, not proof of runtime compatibility. The provider SDK is not included. Matty must validate them and update the lock after provider selection.

## Install the instructions into the repository

Matty owns the bootstrap PR when implementation is authorized. Place this package's Markdown files together under `docs/team/` so their relative links keep working. Maintain a short root `AGENTS.md` instructing assistants to read `docs/team/01_SHARED_RULES.md`, the named role file, assigned Issue, interface contract and decision register before coding. Do not assume an arbitrary role filename is automatically loaded by every AI product. Each teammate explicitly supplies the role filename to their assistant.

Use root `README.md` for the actual project's quick start, not this package guide. Use `docs/ARCHITECTURE.md`, `docs/PROJECT_PLAN.md`, `docs/INTERFACES.md`, `docs/COORDINATION.md`, `docs/handoffs/` and `docs/decisions/` for the maintained project records. `docs/INTERFACES.md` becomes the sole current interface specification after adopting `02_INTERFACE_CONTRACTS.md`; replace the package contract with a pointer to it so two specifications cannot drift. Likewise, keep `04_OPEN_DECISIONS.md` as the open-decision index pointing to accepted decision records, and link the project plan to the coverage checklist rather than copying ownership tables.

Copy dependency inputs into the chosen environment layout as part of that reviewed PR. Verify account names before creating CODEOWNERS entries. No repository setting, Issue, PR, automation or GitHub file was created by delivery of this package.

## First implementation order

- [ ] Team resolves the coordination/permission decisions and accepts the lead split.
- [ ] Matty opens repository bootstrap work; Ved drafts schemas; all owners review interfaces.
- [ ] Reimo publishes a tiny deterministic fixture; Edison supplies hand-checked math/A; Matty and Nisha develop verification against that fixture; Ved builds graph/solver in parallel.
- [ ] Prove a development vertical slice before full training or paid experiment runs.
- [ ] Merge validated data/simulator/graph/reference work; train C/D; integrate both LLM paths and explanations.
- [ ] Complete failure tests, independent evaluation and pre-evaluation claim review; freeze.
- [ ] Run held-out experiments, review results, reproduce on a second machine, finish Matty's final E2E acceptance and final deliverables.

Internal proposal targets: October 16 data/simulator and second-person check; October 23 A/B and retrieval; October 30 C/D and LLM paths; November 6 repair/fallback/gate; November 13 freeze; November 23 experiments/analysis; December 2 reproduction/rehearsal; December 4 delivery. An earlier course deadline takes precedence. November 26–27 is reserved.

## Bootstrap repository adaptation

Matty's confirmed GitHub ID is `MattyAnd`. Follow [project context](../PROJECT_CONTEXT.md): README starts with teammates and roles, discloses reviewed systems and selection method/similarities, and uses plain language with architecture. The [single interface draft](../INTERFACES.md) remains proposed pending Ved/consumer F02 review. No scientific decision or allocation was changed. See [changelog](CHANGELOG.md).
