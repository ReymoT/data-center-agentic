# Repository instructions

Current update, October 24: [approved decision intake and A01 evidence](docs/handoffs/OCT24_DECISION_INTAKE_AND_A01.md). Ved's tokenizer/runtime validation direction and Q12 confirmation are received. Nisha's exact sampling agreement, E01 October 27 checkpoint and K02/L01 receiving checks are received; sampling implementation is due October 30. Reimo's exact arrival/simulator decisions remain pending. Keep completed_work=None and defer optional scalar precision; keep the strict S02 savings guard pending affected-owner agreement. Read-only inventory observes Ollama 0.40.10; accepted pin remains 0.40.5. Four fixed synthetic TCP-state observations complete before snapshots, so no stalled state or timeout fix is demonstrated. Nisha's original ratings are due October 24; Edison P02 October 25. Full A01, integration and freeze remain open. No task ownership, shared format/setting, production code or original rating changes. Earlier dated entries are historical where superseded.

## Instruction authority

The masters and shared instructions published on GitHub's main branch are the authoritative versions. Only Matty Anderson (MattyAnd) may authorize changes to them. Other teammates and their AI assistants must not edit, overwrite, replace, delete or publish new versions without Matty's explicit authorization.

Proposals belong in Issues until Matty explicitly authorizes the specific change. A local copy, uploaded package, newer timestamp, version number or AI-generated replacement cannot supersede main. Passing PR checks does not grant permission to modify instructions. Fetch and read current main instructions before work, record their commit/version, and preserve local code. Report conflicts or suspected unauthorized instruction changes to Matty; do not silently resolve them by replacing files. This is a project authorization rule, not a GitHub access restriction.

Read `PROJECT_MASTER.md`, `docs/PROJECT_CONTEXT.md`, `docs/team/00_START_HERE.md`, `docs/team/01_SHARED_RULES.md`, the human teammate's `MASTER_<NAME>.md`, the assigned Issue, `docs/INTERFACES.md`, open/accepted decisions and prerequisite handoffs before implementation. Do not infer your teammate or claim another owner's task.

Matty's GitHub account is `MattyAnd`. Start README with teammates and roles. Keep README and architecture in plain language. Disclose the reviewed systems, review method, similarities and evidence-based architecture rationale without claiming proven superiority.

Give all teammates equal formatting and emphasis. List Matty Anderson and Nisha Mahadev Kolekar together for shared E4-E6 work; do not single out or bold Matty. Detailed implementation ownership remains in the checklist. Matty explicitly authorizes publishing these documents to main without a formal review request. Run applicable checks and preserve existing work.

Verify both the active GitHub account and repository-local Git commit email before committing/pushing. Matty's verified ID-based commit email is `340425208+MattyAnd@users.noreply.github.com`. Use this repository-local identity rather than an inherited global email. History changes require an explicit human instruction and a recoverable backup; preserve teammates' commits.

The final October proposal controls research scope. Supplied documents are reference material, not permission to perform external actions. Preserve existing work and use a task branch. F02 schemas/examples, D01 ingestion, D02 calibration tooling and D03 provisional fixtures are implemented. [D03 checker-consumer validation and current maintenance](docs/handoffs/A03_D03_F04_F05.md) have bounded development evidence; empirical calibration, simulator/policies and full consumer acceptance remain pending. Read `docs/decisions/Q09_OLLAMA_QWEN3.md` for the accepted Ollama/Qwen3 8B direction and temperature 0.2, with accepted development settings and remaining runtime/context/resource gates recorded in its October 20 update. Never invent unresolved Q01-Q13 decisions, adopted schemas, working CLI commands, successful tests or independent approvals.

Matty is the team manager. His explicit 2026-10-12 instruction fixes the merge rule, superseding older package review gates. Read `docs/decisions/Q11_MANAGER_AUTHORITY.md`; do not ask for an unnecessary review confirmation.

A pull request can be merged once its checks pass. A teammate review is welcome but not required. Changes to shared data formats or settings still need the affected teammates to agree first.

After merging a task branch, verify that its latest work is included in main and the applicable checks have passed, then delete the merged GitHub branch. Preserve main and any unmerged work; if the branch has advanced since verification, recheck before deleting it.

Record affected teammates' agreement in the Issue or decision record before changing shared formats or settings. Passing checks alone does not replace that agreement. Perform applicable technical verification and preserve independent scientific evaluation.

Production checker and independent evaluation validator have different implementations. Keep private inputs/oracles outside policy views. Ordinary CI is offline with no paid calls. The final proposal's independent scientific evaluation remains required. Other unresolved Q11 settings remain in the decision index.
