# Project master instructions

Current implementation, instruction 1.27: [published work and receiving gates](docs/handoffs/OCT24_IMPLEMENTATION_AND_RECEIVING.md). A03 physical checks, A04 execution/traces and A02 bounded orchestration are real merged code. PR #64 has Matty receiving fixes/current-main reconciliation but still needs Nisha replay and independent evidence; it is unmerged. D05 inventory PR #65 is published, not scientific source acceptance. A01 transport/deployment and P02/L02/runner/live acceptance remain open. The coder-owned rule, all 50 assignments and independent evaluation are unchanged; older dated preparation notes are historical where superseded.

Current manager update, October 24: [coder-owned decisions](docs/decisions/Q11_CODER_OWNED_DECISIONS.md), authorized by Matty in [the team announcement](https://github.com/ReymoT/data-center-agentic/issues/57). Internal implementation decisions belong to the coder; shared changes go only to affected owners and unresolved shared questions escalate to Matty within 24 elapsed hours. Work on agreed portions proceeds immediately. Existing task assignments, exact merge/main-authority rules and scientific acceptance stay intact. Earlier dated entries are historical where superseded.

Instruction deployment: 1.27 — 2026-10-24. Repository: [ReymoT/data-center-agentic](https://github.com/ReymoT/data-center-agentic).

Matty Anderson is the project manager and uses [MattyAnd](https://github.com/MattyAnd). Start with this file and [AGENTS.md](AGENTS.md), then read the [complete team package](docs/team/00_START_HERE.md), all numbered files 00-04, your role file, assigned Issue, decisions and prerequisite handoffs.

## Instruction authority

The masters and shared instructions published on GitHub's main branch are the authoritative versions. Only Matty Anderson (MattyAnd) may authorize changes to them. Other teammates and their AI assistants must not edit, overwrite, replace, delete or publish new versions without Matty's explicit authorization.

This covers AGENTS.md, PROJECT_MASTER.md, all five role masters, numbered files 00-04 and other shared instruction/policy records. Teammates may propose corrections in Issues. Record Matty's explicit authorization for the specific change before editing or publishing; it can authorize his assistant to maintain the files. Passing checks alone does not supply that authorization.

At the start of work, fetch and read main's published instruction commit/version while preserving local code. Local or uploaded copies, newer timestamps, higher version numbers and AI-generated replacements have no independent authority. Report conflicts or suspected unauthorized changes to Matty. Instruction updates become active when authorized and published to main. Historical copies may document past work but cannot replace current instructions.

GitHub permissions are separate from this rule. MattyAnd currently has write access, not administrator access. Repository-owner action is needed for GitHub-enforced access restrictions; this instruction publication does not claim such restrictions were enabled.

## Merge rule

A pull request can be merged once its checks pass. A teammate review is welcome but not required. Changes to shared data formats or settings still need the affected teammates to agree first.

After merging a task branch, verify that its latest work is included in main and the applicable checks have passed, then delete the merged GitHub branch. Preserve main and any unmerged work; if the branch has advanced since verification, recheck before deleting it.

## Coding decisions and escalation

<!-- coder-decisions:start -->
The coder responsible for a component owns its internal implementation decisions within the agreed scope and contracts. Routine internal choices do not require prior approval from the technical contact, another teammate or Matty.

For changes to shared interfaces, settings or scientific rules, the coding owner leads the exact proposal and obtains agreement from only the directly affected owners before implementation.

Record the coding decision owner, exact change, directly affected consumers, required tests, request time and response deadline in the Issue or decision record. An unanswered or unresolved shared decision must be escalated by the coding owner to Matty within 24 elapsed hours for a short resolution meeting. Silence is not approval.

Implement, test and publish the agreed independent portions immediately while a disputed portion is pending. Block only the specific affected behavior or acceptance step; do not hold the whole task when other work is ready.

Existing task ownership, main-instruction authority, merge rules, independent scientific evaluation and model-call authorization remain unchanged.
<!-- coder-decisions:end -->

Read [the accepted workflow and examples](docs/decisions/Q11_CODER_OWNED_DECISIONS.md). Technical contacts advise on affected boundaries; they are not mandatory approvers of every internal coding choice.

Record agreement in the Issue or decision record before implementing shared-format or settings changes. Passing checks does not replace this agreement. The rule applies to all teammates. It does not waive technical acceptance, independent evaluation or unresolved scientific decisions. It describes merge eligibility; it does not change GitHub access or branch-protection settings.

## Shared project records

Current D06 update, 2026-10-19: [Matty's handoff verification](docs/handoffs/D06_F04_F05_VERIFICATION.md) records merged D06 tooling and a fresh Windows structural pass using the exact merged checker. Original evidence limitations and Q05/policy-facing acceptance remain explicit; no scientific choice or shared setting is changed.

Course planning update, October 20, 2026: Nisha reports Group 15 presents in class November 16, submits the presentation November 18 at 11:59 pm, demos December 2 (submission 11:59 pm), and submits the report December 9 at 11:59 pm. Read [Q13](docs/decisions/Q13_PRESENTATION_DEADLINE.md) and [the current plan](docs/PROJECT_PLAN.md). Timezone, rubric/formats and separate code/release requirements remain unconfirmed. Rehearsal must be before November 16; no exact day is agreed. These are attributed course reports, not verified outcomes or scientific acceptance.

The research question is: Does an ontology-grounded, tool-verified agent improve the accuracy, faithfulness and safety of data-center sustainability recommendations compared with a plain LLM?

Read the [README](README.md) and [architecture](docs/ARCHITECTURE.md) for the planned scheduling study, main agent/plain-LLM comparison and four additional references. Read [implemented F02 interfaces](docs/INTERFACES.md) and their pending consumer-adoption status, with [the checklist](docs/team/03_RESPONSIBILITY_CHECKLIST.md) for ownership. Do not duplicate schemas or claim teammate-owned tasks.

Use actual implementation and test evidence. Do not substitute stubs, constant success verdicts, fabricated model responses or invented traces/results for working functionality. Label synthetic fixtures and test doubles honestly; a mock does not establish live inference or integrated acceptance. Missing dependencies or decisions remain explicit blockers.

[The F03/F04/F05 maintenance handoff](docs/handoffs/F03_F04_F05_MAINTENANCE.md) records current offline CI, instruction and documentation evidence. F03's final provider-inclusive environment remains pending; F04/F05 continue as maintenance duties.

The [decision register](docs/team/04_OPEN_DECISIONS.md) retains unresolved choices. [Q09](docs/decisions/Q09_OLLAMA_QWEN3.md) now records Matty's acceptance of local Ollama with Qwen3 8B and temperature 0.2. Matty owns the shared adapter/environment, Nisha the plain/explanation paths, and Ved contract compatibility. They can proceed with documented development preparation. [Hardware inventory](docs/HARDWARE.md) is now available and [A01/A03 core](docs/handoffs/A01_A03_AGREED_CORE.md) is implemented; the October 20 Q09 record now accepts development pins/seeds/projections, with observed runtime mismatch and context validation still blocking live readiness.

Current update, 2026-10-15: D02 calibration tooling and D03 provisional synthetic fixtures are merged. [The D03 checker-consumer handoff](docs/handoffs/A03_D03_F04_F05.md) records bounded fixed-rule validation and F04/F05 maintenance; empirical calibration, scientific agreement and downstream acceptance remain pending.

The five role files are [Matty](docs/team/MASTER_MATTY.md), [Nisha](docs/team/MASTER_NISHA.md), [Reimo](docs/team/MASTER_REIMO.md), [Ved](docs/team/MASTER_VED.md) and [Edison](docs/team/MASTER_EDISON.md). Equal role presentation, documentation preferences and publication authorization are recorded in [project context](docs/PROJECT_CONTEXT.md). The [Q11 record](docs/decisions/Q11_MANAGER_AUTHORITY.md) preserves the manager's instructions and remaining workflow choices.
