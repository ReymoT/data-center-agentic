# Project plan

Current update, 2026-10-15: D02 calibration tooling and D03 provisional synthetic fixtures are merged at main `d081cf5`. [The A03/F04/F05 handoff](handoffs/A03_D03_F04_F05.md) records real fixed-checker consumer tests and updated documentation. Empirical Frontier calibration, Q01-Q06, simulator/policies and full acceptance remain pending where documented. The older dated entries below are historical.

Current update, 2026-10-12: [A01/A03 agreed core](handoffs/A01_A03_AGREED_CORE.md) is implemented and offline tested; [hardware inventory](HARDWARE.md) is supplied. Full adapter/checker acceptance and downstream integration remain blocked by the documented decisions/inputs. This update supersedes older preparation-only status below.

The [responsibility checklist](team/03_RESPONSIBILITY_CHECKLIST.md) is the single task/owner/dependency index. All implementation boxes remain pending. Proposed lead/technical-contact allocations await Q12; internal dates remain subject to the actual course deadline in Q13.

The repository includes the F03 candidate environment/offline CI, current F04/F05 documentation, Ved's implemented F02 schemas/examples and Reimo's D01 source inspection. [The current maintenance handoff](handoffs/F03_F04_F05_MAINTENANCE.md) records evidence and limits. Matty authorizes publication to main without formal review; actual consumer checks remain required for dependent implementation acceptance. F03's provider-inclusive lock and final supported platforms remain pending Q09/Q13.

The intended order is repository/contracts, tiny development fixtures and math/A/checks, graph and certified labels, C/D training and LLM paths, development integration/failure tests, freeze, held-out runs, independent scoring/reproduction, final E2E and release.

| Internal target | Evidence required |
|---|---|
| 2026-10-16 | Source/fixture/simulator checks and independent source reproduction |
| 2026-10-23 | A/B policies, retrieval and changed-capacity tests |
| 2026-10-30 | Trained C/D and both LLM paths |
| 2026-11-06 | Real development repair/fallback and gated execution |
| 2026-11-13 | Failure tests, blinded pre-evaluation review and freeze manifest |
| 2026-11-23 | Held-out runs, independent metrics, annotations and failure analysis |
| 2026-12-02 | Second-machine reproduction, final E2E and rehearsal |
| 2026-12-04 | Verified release, report, presentation and demo |

November 26-27 is reserved in the proposal. Optional extensions follow required results under separately approved work. No scheduler or automatic assistant wakeup is created.

Update 2026-10-12: Matty completed the independent [A01/F03 local model installation and identity checks](OLLAMA_SETUP.md). Qwen3 8B Q4_K_M is installed with full digest/license evidence. No SDK/lock/shared-setting change, inference or full task acceptance is claimed; remaining deployment/integration prerequisites still apply.
