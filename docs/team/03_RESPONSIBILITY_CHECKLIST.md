# Shared responsibility and coverage checklist

Audit update, instruction 1.26: [active guidance and issue audit](../handoffs/CODER_PLAN_AUDIT_2026-10-24.md) keeps the coder-owned rule unchanged, corrects received K02/readiness facts and routes P02/source/scoring work to #59/#60/#61. Reimo source ownership/blocker reply is received; October 26 is accepted for his evidence inventory only. Scientific acceptance and disputed shared behavior remain gated; ready agreed coding proceeds.

Current workflow, instruction 1.26: [Matty's coder-owned decision rule](../decisions/Q11_CODER_OWNED_DECISIONS.md) gives the implementer internal decision authority, limits shared confirmation to affected owners and escalates unresolved shared questions within 24 elapsed hours. Proceed with agreed independent work; block only the disputed behavior/acceptance. Existing scope, task ownership and scientific agreements remain unchanged.

Current manager update, October 24: [coder-owned decisions](../decisions/Q11_CODER_OWNED_DECISIONS.md), authorized by Matty in [the team announcement](https://github.com/ReymoT/data-center-agentic/issues/57). Internal implementation decisions belong to the coder; shared changes go only to affected owners and unresolved shared questions escalate to Matty within 24 elapsed hours. Work on agreed portions proceeds immediately. Existing task assignments, exact merge/main-authority rules and scientific acceptance stay intact. Earlier dated entries are historical where superseded.

Current E05 first pass: [issue #42](https://github.com/ReymoT/data-center-agentic/issues/42) and [the original-rating handoff](../handoffs/E05_MATTY_RATINGS_2026-10-22.md). Matty's 22-output submission is retained unchanged and structurally valid. E05 is Verifying pending Nisha's original, paired agreement and joint adjudication; its task checkbox remains unchanged. Earlier dated preparation notes describe the prior state.

Current follow-up: [F04/F05 #40](https://github.com/ReymoT/data-center-agentic/issues/40) and [the handoff](../handoffs/OCT22_NISHA_FOLLOWUPS.md) record received Nisha replies and merged E04 preparation. E05 personal ratings are now available to begin using [the guide](../e04/MATTY_RATING_GUIDE.md); no original human rating or final freeze is claimed. A01 diagnosis is deferred. All50 rows below are preserved.

Version: 1.26 — 2026-10-24. Maintainer: Matty. One accountable primary owner per row; technical contacts are separate people. PRs may merge once checks pass; teammate review is welcome but not required. Shared data-format or settings changes require affected teammates' agreement first. All boxes mean pending implementation, not missing ownership. Add an Issue link and merged acceptance evidence to each row when work begins. Lead allocation details that refine paired proposal duties are explicitly disclosed in `00_START_HERE.md` and Q12; no task is silently transferred.

Use the published main checklist. Teammates and their AI assistants must not change or replace this shared instruction file without Matty's explicit authorization; propose corrections in an Issue.

Current F03/F04/F05 maintenance is tracked in [issue #5](https://github.com/ReymoT/data-center-agentic/issues/5) and [its handoff](../handoffs/F03_F04_F05_MAINTENANCE.md). F03's final provider-inclusive/platform acceptance remains pending; F04/F05 continue through the project. The existing task rows are preserved rather than marking partial maintenance as final acceptance.

Current A03/F04/F05 development maintenance is documented in [the D03 consumer handoff](../handoffs/A03_D03_F04_F05.md), with A03 issue #7 and documentation issue #10. D02/D03 are merged tooling/provisional fixtures, not final scientific acceptance. Task boxes and allocations stay unchanged.

Dependencies are artifact prerequisites; development may use agreed fixtures/contracts first. The matrix has no task dependency cycles. O03/P06/E03 implement and test reference/metric pipelines on development data before freeze. I01 is pre-freeze integration; I02 produces frozen held-out run outputs; O04/P07/E06/E07 then produce final references, metrics and annotations. I04 is Matty's separate final E2E acceptance after reproduction. F04 and F05 continue throughout the project after their initial deliverables.

| Done | ID | Primary owner | Technical contact | Required responsibility | Dependencies | Acceptance evidence |
|---|---|---|---|---|---|---|
| [ ] | F01 | Matty | Reimo | Initialize repository layout, issue/PR templates, ownership routing and configuration skeleton | None | Published foundation; teammates' work preserved; setup guide works |
| [ ] | F02 | Ved | Matty | Own shared schemas and interface contracts; coordinate and validate with all consumers | F01 | Versioned schemas, examples, strict validation and contract tests |
| [ ] | F03 | Matty | Edison | Own Python environment, dependency locks, CI, coding conventions and secret exclusions | F01 | Fresh installation and offline CI pass; provider SDK added after selection |
| [ ] | F04 | Matty | Nisha | Maintain all master files, project plan, responsibility checklist and decision register; fix instruction bugs | None | Cross-file consistency checks and changelog accompany each affected change |
| [ ] | F05 | Matty | Ved | Create and maintain repository README and final-scope architecture document | F01, F02 | Executable quick start; architecture reflects implemented interfaces and scope |
| [ ] | D01 | Reimo | Ved | Acquire and validate pinned Arizona carbon data, timestamps, units and annual plausibility | F02 | Source manifest, checksum, unit/time evidence and hand-checked window |
| [ ] | D02 | Reimo | Edison | Prepare Frontier calibration distributions and fixed-power/PUE assumptions | F02 | Validated job-table adapter, exclusions, quantiles and scaling report |
| [ ] | D03 | Reimo | Ved | Generate hand fixtures, four scenarios and missing-forecast variant | F02, D01, D02 | Deterministic fixtures with expected counts, labels and quality checks |
| [ ] | D04 | Reimo | Nisha | Own development/held-out splits, blocked folds, seeds, fixture manifests and freeze | D03 | 40 development and 30 held-out episodes; no overlapping source windows |
| [ ] | D05 | Reimo | Ved | Maintain data README, dictionary, licenses, acquisition and regeneration instructions | D01, D02, D03, D04 | Second person can locate, validate and regenerate allowed artifacts |
| [ ] | S01 | Reimo | Ved | Implement simulator reset/state/step, visibility boundary and 30-slot accounting | F02, D03 | Arrival, occupancy, rejection, progression and hidden-data tests pass |
| [ ] | S02 | Reimo | Edison | Integrate simulator impact ledger with shared calculations and hand fixture | S01, P01 | 54.5/48.4 kg job checks and full-period job/background totals pass |
| [ ] | D06 | Ved | Reimo | Independently reproduce data adapter and manually check 24-hour source window | D01, D05 | Second-person reproduction record by October 16 |
| [ ] | K01 | Ved | Reimo | Implement ontology, source/constraint records, unit mappings and SHACL | F02, D03 | Valid/invalid graph fixtures; static, episode and trace separation |
| [ ] | K02 | Ved | Nisha | Implement SPARQL retrieval and equivalent flat-context projection | K01, S01 | Same fact IDs/values for all systems; hidden data unavailable |
| [ ] | K03 | Ved | Matty | Prove graph-driven constraints and runtime missing-link failures | K01, K02, A03 | 100-to-70 kW test changes decision without code/prompt edits |
| [ ] | O01 | Ved | Edison | Implement offline integer-program reference solver and deterministic tie rules | F02, D03 | Tiny brute-force comparisons; optimal/infeasible/unresolved distinguished |
| [ ] | O02 | Ved | Edison | Generate certified visible-state schedules and candidate label caches | O01, D04, P03 | No future arrivals; certified optimal labels; infeasible fixtures and exclusions |
| [ ] | O03 | Ved | Nisha | Implement hindsight-bound and offline candidate-reference export pipelines | O01, D04, E02 | Development reference manifests/statuses; never accessible to policy inference |
| [ ] | O04 | Ved | Nisha | Generate certified held-out hindsight and visible-state references after inference | O03, I02 | Final reference artifacts, matching-work metadata and unresolved exclusions |
| [ ] | P01 | Edison | Reimo | Implement shared slot/job/site energy, carbon and comparison calculations | F02 | Hand calculations, 0.01 tolerance, PUE scaling and equal-work checks |
| [ ] | P02 | Edison | Matty | Implement greedy A and B and reusable A fallback | F02, P01 | Priority, ties, occupancy and forecast fallback tests pass |
| [ ] | P03 | Edison | Ved | Implement candidates/features, state collection, schedule construction and blocked training protocol | F02, D04, S01, P02, A03 | Feature/rollout contract frozen; constructor supports temporary fold models |
| [ ] | P04 | Edison | Ved | Train/select/refit decision tree C and random forest D | P03, O02 | Required grid and blocked folds; saved models, seeds and selection results |
| [ ] | P05 | Edison | Matty | Implement learned policy inference and checked fallback integration | P02, P04, A03 | Reloaded models schedule deterministically; no inference-time solver calls |
| [ ] | P06 | Edison | Nisha | Publish model cards, development candidate metrics, training times and metric implementation | P04, P05 | Development precision/recall/F1 and support; frozen artifacts and feature versions |
| [ ] | P07 | Edison | Nisha | Score held-out candidate predictions with frozen metric rules | P06, O04 | Held-out precision/recall/F1 and support; no retraining; unavailable labels counted |
| [ ] | A01 | Matty | Nisha | Implement shared LLM provider adapter and accounting | F02, F03 | Pinned provider settings; structured response, timeout and budget tests |
| [ ] | A02 | Matty | Nisha | Implement LangGraph route, one repair and checked A fallback | A01, K02, P02, A03 | Bounded route; actual model-driven development episode with repair/fallback |
| [ ] | A03 | Matty | Nisha | Implement production schedule/evidence checker for every system | F02 | At least ten meaningful E5 tests, including invalid and missing-evidence cases |
| [ ] | A04 | Matty | Reimo | Implement controller-only execution gate, state recheck and runtime trace writer | S01, A03 | Stale/duplicate/bypass rejection; separate initial/repair/fallback/executed records |
| [ ] | L01 | Nisha | Matty | Implement plain-LLM comparison using common provider and flat facts | A01, K02 | One call; original output retained; no feedback, repair or fallback |
| [ ] | L02 | Nisha | Matty | Implement evidence-based explanation contracts, prompts and classical templates | F02, P01, A03 | Agent explanation uses approved plan; plain output unchanged; no fabricated checks |
| [ ] | E01 | Nisha | Ved | Implement independent reference validator and numerical claim scoring | F02, D03 | Separate logic from production checker; hand-truth and disagreement tests |
| [ ] | E02 | Nisha | Matty | Implement experiment registry, resumable runner and comparable six-system execution | S02, K02, P02, P05, A02, A04, L01, L02 | Stable run IDs; no silent reruns/dropped failures; 300-run matrix supported |
| [ ] | E03 | Nisha | Edison | Implement and test accuracy, safety, completion, impact, cost and statistical analysis | E01, E02, O03, P06 | Development truth tests; explicit denominators and paired episode-resampling code |
| [ ] | E04 | Nisha | Ved | Prepare faithfulness rubric, blinded sample, first annotation pass and adjudication format | L02, E02 | Frozen rubric; at least ten paired development cases; first original ratings retained |
| [ ] | E05 | Matty | Ved | Perform independent second blinded pre-evaluation annotation and joint adjudication with Nisha | E04 | Second ratings before discussion; both originals retained; disagreements resolved |
| [ ] | I01 | Matty | Nisha | Own early vertical integration and pre-freeze end-to-end acceptance | F03, S02, K03, P05, A02, A04, L01, L02, E01, E02 | All six systems traverse real development pipeline; failure paths verified |
| [ ] | I02 | Nisha | Matty | Assemble freeze manifest and execute held-out experiment runs | D04, O02, P04, A02, L01, E03, E04, E05, I01 | Frozen protocol; all planned run outputs/accounted failures; no test-set tuning |
| [ ] | E06 | Nisha | Edison | Produce final held-out scores, statistics, figures and failure analysis | I02, O04, P07, E03 | Reproducible final tables with counts, paired intervals and limitations |
| [ ] | E07 | Nisha | Ved | Execute frozen held-out faithfulness review with Matty as independent second rater | I02, E04, E05 | Approved Q10 sample; both original ratings, adjudication, coverage and claim scores |
| [ ] | I03 | Ved | Matty | Coordinate second-machine reproduction of deterministic results and saved-output scoring | E06, E07, P06 | Clean-checkout report, hashes, limitations and regenerated tables/figures |
| [ ] | I04 | Matty | Nisha | Own final project end-to-end testing and release acceptance | I01, I03, E06, E07 | Final integrated acceptance report; defects fixed/retested and independently verified |
| [ ] | R01 | Reimo | Ved | Write data/simulator report section and present its assumptions and limitations | D05, S02 | Validated section and supporting figures/tables |
| [ ] | R02 | Ved | Reimo | Write ontology/reference-solver section and reference artifact documentation | K03, O04 | Validated section, certified-status explanation and reproduction details |
| [ ] | R03 | Edison | Nisha | Write classical-policy/impact section and ML results documentation | P07, E06 | Validated section with training and episode results |
| [ ] | R04 | Matty | Nisha | Write agent/verification section and maintain demo/runbook | I04 | Final E2E report and trace-based backup demo ready for report assembly |
| [ ] | R05 | Nisha | Matty | Write evaluation/results section and assemble final report and presentation | E06, E07, R01, R02, R03, R04 | All authors review; claims match saved evidence; final deliverables indexed |
| [ ] | R06 | Matty | Nisha | Assemble final release package and verify its delivery manifest | R05, I04 | Code/environment/data/model/reference/trace/results/report/presentation/demo links verified |

## Coverage cross-check

| Required area | Owning task IDs | Receiving work |
|---|---|---|
| Repository, local environment, CI and collaboration records | F01–F05 | All members |
| Source access, validation, calibration, synthetic jobs, scenarios, splits and licenses | D01–D06 | Simulator, graph, labels, training and experiments |
| E1 simulator, visibility, time progression and accounting | S01–S02 | Every policy and evaluator |
| E2 impacts, A/B references, C/D training/inference and model documentation | P01–P07 | Runtime, shared comparisons and report |
| E3 ontology, SHACL, provenance, equivalent retrieval and changed capacity | K01–K03 | Every context/checker and report |
| Offline training labels and evaluation bounds | O01–O04 | Classical learning and independent evaluation only |
| E4 provider/agent/plain comparison | A01–A02, L01 | Six-system comparison |
| E5 production safety checks and gate | A03–A04 | Every policy; independent truth in E01 |
| E6 explanations and blinded faithfulness | L02, E04–E05, E07 | Main LLM comparison; templates separate |
| Experiment reproducibility, independent scoring/statistics and frozen runs | E01–E03, E06, I02–I03 | Tables, figures, report and demo |
| Early integration and final end-to-end acceptance | I01, I04 | Matty owns; Nisha verifies, module owners fix |
| Documentation, technical writing, report/presentation/demo and release | D05, F04–F05, P06, R01–R06 | Final submission and repeatable handoff |

## Process duties that apply to every member

- [ ] Maintain your own Issue/branch/handoff, report blockers promptly and check upstream readiness.
- [ ] Write tests and documentation for your owned module; review other members' interfaces/results.
- [ ] Fix defects in your module discovered during integration, evaluation or reproduction.
- [ ] Preserve source/artifact/model/prompt versions, seeds and meaningful test evidence.
- [ ] Contribute your report section and participate in presentation/demo rehearsal and final review.
- [ ] Do not claim another member's task or start duplicate assistant sessions without explicit reassignment.

**Accepted coordination roles:** Matty is integration coordinator and shared-summary publisher; Nisha accepted backup. Matty is the authorized publishing/merge actor under the existing manager rule; passing checks permits a merge without required teammate review. This does not grant new GitHub permissions. Explicit bounded model-run authorization and remaining resource/account choices are still gates in Q09/Q11, rather than unnamed coordinator roles. Nisha confirms course deliverables (Q13). Optional extensions have no active implementation assignment until separately approved; they are outside required coverage.

A01 is tracked in [issue #6](https://github.com/ReymoT/data-center-agentic/issues/6) and A03 in [issue #7](https://github.com/ReymoT/data-center-agentic/issues/7), assigned to Matty. [Agreed core evidence](../handoffs/A01_A03_AGREED_CORE.md) is available; full task boxes remain pending.
