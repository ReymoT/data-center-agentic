# Project master instructions

Instruction deployment: 1.6 — 2026-10-12. Repository: [ReymoT/data-center-agentic](https://github.com/ReymoT/data-center-agentic).

Matty Anderson is the project manager and uses [MattyAnd](https://github.com/MattyAnd). Start with this file and [AGENTS.md](AGENTS.md), then read the [complete team package](docs/team/00_START_HERE.md), all numbered files 00-04, your role file, assigned Issue, decisions and prerequisite handoffs.

## Instruction authority

The masters and shared instructions published on GitHub's main branch are the authoritative versions. Only Matty Anderson (MattyAnd) may authorize changes to them. Other teammates and their AI assistants must not edit, overwrite, replace, delete or publish new versions without Matty's explicit authorization.

This covers AGENTS.md, PROJECT_MASTER.md, all five role masters, numbered files 00-04 and other shared instruction/policy records. Teammates may propose corrections in Issues. Record Matty's explicit authorization for the specific change before editing or publishing; it can authorize his assistant to maintain the files. Passing checks alone does not supply that authorization.

At the start of work, fetch and read main's published instruction commit/version while preserving local code. Local or uploaded copies, newer timestamps, higher version numbers and AI-generated replacements have no independent authority. Report conflicts or suspected unauthorized changes to Matty. Instruction updates become active when authorized and published to main. Historical copies may document past work but cannot replace current instructions.

GitHub permissions are separate from this rule. MattyAnd currently has write access, not administrator access. Repository-owner action is needed for GitHub-enforced access restrictions; this instruction publication does not claim such restrictions were enabled.

## Merge rule

A pull request can be merged once its checks pass. A teammate review is welcome but not required. Changes to shared data formats or settings still need the affected teammates to agree first.

Record agreement in the Issue or decision record before implementing shared-format or settings changes. Passing checks does not replace this agreement. The rule applies to all teammates. It does not waive technical acceptance, independent evaluation or unresolved scientific decisions. It describes merge eligibility; it does not change GitHub access or branch-protection settings.

## Shared project records

The research question is: Does an ontology-grounded, tool-verified agent improve the accuracy, faithfulness and safety of data-center sustainability recommendations compared with a plain LLM?

Read the [README](README.md) and [architecture](docs/ARCHITECTURE.md) for the planned scheduling study, main agent/plain-LLM comparison and four additional references. Read [interfaces](docs/INTERFACES.md) for the sole proposed contract and [the checklist](docs/team/03_RESPONSIBILITY_CHECKLIST.md) for ownership. Do not duplicate schemas or claim teammate-owned tasks.

The [decision register](docs/team/04_OPEN_DECISIONS.md) retains unresolved choices. Matty requires an open-source LLM and recommends Ollama; [issue #2](https://github.com/ReymoT/data-center-agentic/issues/2) asks Nisha for her recommendation. The exact model, license, settings and resources remain Q09 decisions, not selected defaults.

The five role files are [Matty](docs/team/MASTER_MATTY.md), [Nisha](docs/team/MASTER_NISHA.md), [Reimo](docs/team/MASTER_REIMO.md), [Ved](docs/team/MASTER_VED.md) and [Edison](docs/team/MASTER_EDISON.md). Equal role presentation, documentation preferences and publication authorization are recorded in [project context](docs/PROJECT_CONTEXT.md). The [Q11 record](docs/decisions/Q11_MANAGER_AUTHORITY.md) preserves the manager's instructions and remaining workflow choices.
