# Project plan

D06 verification update, October 19, 2026: [the current handoff](handoffs/D06_F04_F05_VERIFICATION.md) records merged source/window tooling and an actual version-matched Windows structural pass, separate from Ved's original reports. F04/F05 documentation is aligned; this does not close D06/Q05 scientific acceptance, change any timeline, resume A01 or perform the deferred D02/Q13 follow-ups.

Current update, October 18, 2026: Matty reports the project presentation is due November 18, 2026. [The partial Q13 record](decisions/Q13_PRESENTATION_DEADLINE.md) preserves his statement and the remaining course requirements. No exact time, timezone, duration, format/rubric or separate report/code deadline has been confirmed.

Nisha coordinates presentation assembly; all teammates supply their verified technical contributions. Assemble the research question, reviewed systems and design rationale, current architecture, methods, actual available results and limitations. Arrange slides and rehearsal before November 18; preparation dates still need coordination. Keep implemented/tested work distinct from proposed or blocked work. If experiments are incomplete, state that plainly. A scheduled presentation does not prove completion or justify fabricated findings, a reduced protocol or bypassed scientific acceptance.

The previous plan placed analysis on November 23, reproduction/rehearsal on December 2 and delivery including presentation on December 4. Those targets cannot support this presentation deadline and are superseded as its schedule. Separate final report/code/release dates remain unconfirmed. Nisha and the team need to reconcile experiment and submission planning with the instructor's requirements; no remaining study deadline is inferred here.

[The October 18 readiness handoff](handoffs/OCT18_TASK_READINESS.md) records merged S01 and L01 preparation, actual S01/A03 consumer checks and the remaining Q01-Q04/Q09 and module dependencies. Calendar targets do not remove those acceptance gates.

Historical implementation update, 2026-10-15: D02 calibration tooling and D03 provisional synthetic fixtures are merged at main `d081cf5`. [The A03/F04/F05 handoff](handoffs/A03_D03_F04_F05.md) records real fixed-checker consumer tests and updated documentation. Empirical Frontier calibration, Q01-Q06 and full acceptance remain pending where documented. The older dated entries below are historical.

Current update, 2026-10-12: [A01/A03 agreed core](handoffs/A01_A03_AGREED_CORE.md) is implemented and offline tested; [hardware inventory](HARDWARE.md) is supplied. Full adapter/checker acceptance and downstream integration remain blocked by the documented decisions/inputs. This update supersedes older preparation-only status below.

The [responsibility checklist](team/03_RESPONSIBILITY_CHECKLIST.md) is the single task/owner/dependency index. Its boxes are not a live acceptance ledger; use linked Issues and published evidence. Proposed lead/technical-contact allocations await Q12. Q13 partially confirms the presentation date; remaining submission requirements are open.

The repository includes the F03 candidate environment/offline CI, current F04/F05 documentation, Ved's implemented F02 schemas/examples and Reimo's D01 source inspection. [The current maintenance handoff](handoffs/F03_F04_F05_MAINTENANCE.md) records evidence and limits. Matty authorizes publication to main without formal review; actual consumer checks remain required for dependent implementation acceptance. F03's provider-inclusive lock and final supported platforms remain pending Q09/Q13.

The intended order is repository/contracts, tiny development fixtures and math/A/checks, graph and certified labels, C/D training and LLM paths, development integration/failure tests, freeze, held-out runs, independent scoring/reproduction, final E2E and release.

The table below preserves the original internal estimates for context. It is not a confirmed course submission schedule or evidence that any milestone passed. The November 18 presentation takes precedence over its conflicting presentation/rehearsal entries; final-study dates require replanning once the remaining requirements are known.

| Historical internal target | Intended evidence |
|---|---|
| 2026-10-16 | Source/fixture/simulator checks and independent source reproduction |
| 2026-10-23 | A/B policies, retrieval and changed-capacity tests |
| 2026-10-30 | Trained C/D and both LLM paths |
| 2026-11-06 | Real development repair/fallback and gated execution |
| 2026-11-13 | Failure tests, blinded pre-evaluation review and freeze manifest |
| 2026-11-23 | Held-out runs, independent metrics, annotations and failure analysis; too late to assume available for November 18 |
| 2026-12-02 | Second-machine reproduction and final E2E; superseded as a presentation rehearsal target |
| 2026-12-04 | Release/report/demo estimate; superseded as a presentation delivery target and not a confirmed submission deadline |

November 26-27 is reserved in the proposal. Optional extensions follow required results under separately approved work. No scheduler or automatic assistant wakeup is created.

Update 2026-10-12: Matty completed the independent [A01/F03 local model installation and identity checks](OLLAMA_SETUP.md). Qwen3 8B Q4_K_M is installed with full digest/license evidence. No SDK/lock/shared-setting change, inference or full task acceptance is claimed; remaining deployment/integration prerequisites still apply.
