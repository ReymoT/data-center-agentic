# Project plan

Current planning update, October 20, 2026. Matty accepted [Nisha's Canvas-reported Group 15 schedule](https://github.com/ReymoT/data-center-agentic/issues/16#issuecomment-6283757221). [Q13](decisions/Q13_PRESENTATION_DEADLINE.md) records attribution and missing requirements. Matty's assistant has not independently inspected Canvas or an instructor document. Timezone remains unconfirmed; do not convert the reported times.

| Course milestone reported by Nisha | Planning action and owner |
|---|---|
| November 16: Group 15 first class presentation | Be presentation-ready for this class; Nisha coordinates assembly, all authors provide actual verified contributions. Rehearsal before November 16, exact date still to agree. |
| November 18, 11:59 pm: presentation submission | Nisha coordinates submission; timezone, duration, format/rubric and destination still to confirm. |
| December 2: Group 15 second round/demo; DEMO Submission 11:59 pm | Prepare a truthful working-demo path against this reported milestone; demo expectations still to confirm. Matty's runbook/final acceptance and all module owners' dependencies remain required. |
| December 9, 11:59 pm: final report | Nisha coordinates R05 assembly, all authors provide evidence-backed sections. Length/format/rubric and separate code/repository submission details remain unknown. |

This task updates the plan only; it does not create slides or run experiments. November 23 analysis, December 2 rehearsal and December 4 delivery were earlier internal estimates and are superseded as course scheduling guidance. December 2 is now a reported demo day, not a rehearsal date. A separate code/release deadline is still unknown. Historical entries below are retained as context, not alternate active deadlines.

## Current critical path

1. Matty has answered Q03 and confirmed the runtime can be designed for zero-call empty no-ops. Edison must still reply to Q01-Q04; joint-infeasibility and Q08 certification details remain open. Implement and test shared no-call behavior only under the recorded rule; do not claim it already works.
2. Q09 setup is agreed by Nisha/Ved/Matty. Resolve the observed Ollama 0.40.6 versus accepted 0.40.5 mismatch, validate both rendered prompts with a real pinned counter, then obtain bounded run authorization. [Offline probe inputs](evidence/q09-probe-preparation-2026-10-20.json) are prepared, not dispatched.
3. E01 preparation is merged at b06cda7 with the strict-capacity/input/identity fixes. Nisha fetched it and reproduced 906 tests/19 subtests; she opened [PR #28](https://github.com/ReymoT/data-center-agentic/pull/28) for independent replay. [Full acceptance](https://github.com/ReymoT/data-center-agentic/issues/24) still needs protocol/reference decisions and actual saved policy outputs. Preserve evaluation independence.
4. Nisha/Matty accept checkable summary-assertion extraction and retaining selected pairs/shortfalls under Q10. Resolve exact eligibility and obtain Ved's sampling/analysis agreement before E04 freeze. Preserve original ratings, failures and the planned sample; no silent reduction.
5. Matty is coordinator/publisher, Nisha accepted backup. Record remaining Reimo/Ved/Edison Q12 confirmations. Keep current primary/contact rows; no reassignment by stale status.
6. Nisha confirms course timezone/rubrics/demo/report/code requirements. Remaining contributors confirm platform/license/access/retention needs. No LICENSE, visibility, storage or retention change is assumed.

Matty's [eight-priority handoff](handoffs/OCT20_EIGHT_PRIORITIES.md), [decision index](team/04_OPEN_DECISIONS.md) and [dated coordination snapshot](COORDINATION.md) link evidence and outstanding inputs. The [50-task checklist](team/03_RESPONSIBILITY_CHECKLIST.md) remains authoritative for ownership/dependencies. Q11 coordination-role acceptance does not remove scientific agreement or independent evaluation.

The study still requires its real data/fixture decisions, math/A/B, graph/retrieval and references, trained C/D, both LLM paths, gate/runner, development integration and failure tests, independent blinded review, freeze, held-out runs, scoring/reproduction and final E2E/release. There are no held-out results yet. If only development evidence exists at the presentation, label it that way; if less exists, state that honestly. Nisha's expectation of development-review results is a plan, not a result or permission to invent them. Course dates do not waive acceptance or silently narrow the protocol.

## Historical dated entries and estimates

The entries below describe earlier knowledge. Their unknown report/demo dates, pending Q09 agreements and November 18-only presentation planning are superseded by the October 20 record above. Internal milestone dates are estimates, not current promises or evidence of completion.

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
