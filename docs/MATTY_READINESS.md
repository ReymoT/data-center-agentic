# Matty duties and readiness

Current update, 2026-10-15: D02 calibration tooling and D03 provisional synthetic fixtures are merged at main `d081cf5`. [The A03/F04/F05 handoff](handoffs/A03_D03_F04_F05.md) records real fixed-checker consumer tests and updated documentation. Empirical Frontier calibration, Q01-Q06, simulator/policies and full acceptance remain pending where documented. The older dated entries below are historical.

Current update, 2026-10-12: [A01/A03 agreed core](handoffs/A01_A03_AGREED_CORE.md) is implemented and offline tested; [hardware inventory](HARDWARE.md) is supplied. Full adapter/checker acceptance and downstream integration remain blocked by the documented decisions/inputs. This update supersedes older preparation-only status below.

Read the complete [Matty master](team/MASTER_MATTY.md) and [checklist](team/03_RESPONSIBILITY_CHECKLIST.md) for authoritative task rows and technical contacts. The final proposal groups Matty/Nisha on E4-E6; the package clarifies leads but Q12 still awaits team acceptance.

## Duties

Matty owns repository layout, environment/CI/secrets, documentation and every shared master instruction correction (F01/F03/F04/F05). Matty implements the common LLM adapter, bounded LangGraph agent, common production checker, controller execution gate and runtime trace writer (A01-A04). Matty also provides independent blinded second ratings with Nisha (E05 and E07 contribution), owns early and final integration acceptance (I01/I04), writes the agent/verification section and demo runbook (R04), and verifies the final release manifest (R06).

Matty is the project manager and explicitly authorizes document publication to main without formal review. Budget, backup and summary-publisher choices remain in Q09/Q11. Each module owner fixes defects in their own module. Nisha's evaluator stays independent of Matty's production checker.

## Required inputs

- Ved: F02 schema implementation and examples are merged at `a61a7f2`, contract 1.0.0. The existing contract suite passes locally; each consumer still needs adoption/compatibility evidence. Actual graph/flat retrieval, graph failure fixtures and offline reference implementations remain required.
- Reimo: immutable development fixtures, private/public visibility boundaries, simulator reset/state/step, source/unit/license manifests, split/fold/seed rules and stale/missing-evidence examples.
- Edison: verified impacts, reusable A fallback, A/B adapters, candidate features and trained C/D artifacts with hashes, reload and consumer tests.
- Nisha: plain/explanation records and prompts, independent scoring/rubric, common runner/CLI/resume contract, blinded samples, original ratings and later evaluation/report artifacts.
- Team/humans: task ownership, adopted allocations/permissions, accepted decisions and actual course/submission requirements. Formal reviewer approval is not required. A task needs merged prerequisite evidence and receiving consumer checks before integrated acceptance.

## Ready setup work and limits

Matty explicitly requested the ready F03/F04/F05 maintenance. [The current handoff](handoffs/F03_F04_F05_MAINTENANCE.md) records all-existing-test CI, a clean hashed Windows candidate installation, corrected instructions, and README/architecture alignment with implemented F02 and D01. Consumer adoption, live inference and integration still need evidence. F03's final provider-inclusive lock/platform acceptance remains pending; F04/F05 remain ongoing maintenance duties.

Matty accepted local Ollama/Qwen3 8B and temperature 0.2 in [Q09](decisions/Q09_OLLAMA_QWEN3.md). A01/F03 adapter, accounting, environment and consumer-check preparation can proceed. Nisha owns L01/L02 preparation using that common adapter; Ved supports F02 compatibility. Actual adapter/plain/retrieval integration and acceptance still require implemented dependencies. Target hardware is supplied; accepted deployment/artifact/context/seed/resource pins remain pending. Q01-Q04 continue to block dependent scheduling/checker semantics. The [full decision index](team/04_OPEN_DECISIONS.md) records remaining choices and the partial Q11 resolution for manager authority and publication:

Q01 completion starts; Q02 partial infeasibility; Q03 coverage/deferrals/work/scoring denominators; Q04 issue times/freshness/partial coverage/fallback scope; Q05 verified source meaning/units/times/rights; Q06 distributions/seeds/splits; Q07 ML features/rollout/metrics/ties; Q08 solver certification/objective/limits; Q09 provider/settings/budget/account; Q10 blinded review/sample/statistics; Q11 coordinator/permissions/accounts/publisher/merge; Q12 lead/technical-contact allocations; Q13 course deadline/delivery/license/retention/platforms.

Do not fill any of these from a recommendation alone. Missing evidence prevents a claim or execution according to the accepted rule; it does not justify an assumed default. Continue unaffected setup while humans resolve the required points.

Update 2026-10-12: Matty completed the independent [A01/F03 local model installation and identity checks](OLLAMA_SETUP.md). Qwen3 8B Q4_K_M is installed with full digest/license evidence. No SDK/lock/shared-setting change, inference or full task acceptance is claimed; remaining deployment/integration prerequisites still apply.
