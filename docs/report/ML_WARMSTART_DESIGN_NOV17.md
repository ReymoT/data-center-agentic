# ML warm-start Agent — exact offline proposal

Owner: Matty (A02); Edison supplies existing ranker scoring; Nisha evaluation and Ved contract/label boundaries are affected. Tracking: #231. Status: design only, not adopted or implemented. Preserve the current Agent and six-system matrix. No model artifact, private corpus or source data is loaded by this preparation.

## Separately versioned experimental variant

Proposed variant ID: `agent_ml_warmstart_v1`, outside the current accepted system IDs until shared agreement. Pin exactly one existing ranker per experiment (C or D), its feature order/artifact hash and legacy-forecast provenance; do not choose the better model per episode or refit implicitly. Source/forecast compatibility gates remain necessary. Classification threshold 0.5 is not a feasibility filter.

Generate only arrived waiting-job/start pairs using current visible constraints and forecast. Score with the pinned classifier, then apply deterministic physical checks. Ranking preserves the current constructor order: nonflexible first, latest-start urgency, decreasing probability, earlier start, numeric/full job ID. Candidate-level validity does not imply joint validity when capacity is shared.

Proposed fixed caps for agreement: up to 3 feasible options per job and 16 total ranked pairs, sorted by that order; truncate deterministically and report counts/reasons. Never silently drop a mandatory waiting-job obligation: omitted jobs remain in the visible queue, with candidate-unavailable/truncated reasons; if the bounded representation cannot retain required coverage, use the existing checked fallback/abstention rather than label omission feasible. Keep these caps in the versioned proposal, not global defaults.

Present candidate IDs, job/start, scores, feasibility evidence, the complete waiting-job obligations and snapshot/plan bindings. The LLM chooses IDs or explicit deferral/abstention; it cannot invent another start or mutate constraints. Reject duplicate, unknown or stale IDs. Validate the joint selected plan through the production checker, and recheck latest state before controller execution. A repair, if agreed, chooses from the same frozen option set plus explicit deferrals/abstentions; the current one-repair limit and checked-A fallback remain. If no forecast/artifact/complete candidate evidence is available, route through the existing checked fallback with explicit logging.

## Accounting and evaluation proposal

The ranker is deterministic local computation, not a hidden model request: record feature construction, ranking and verification latency separately and include it in total decision latency. Preserve at most one proposal, one repair and one explanation call; no ranking call in addition to those. Token/context/candidate limits are fixed before any run. Record artifact identity, feature/forecast version, candidate set hash, truncation, LLM choices, checks and actual execution origins.

Compare this variant against the unchanged Agent on the same permitted development cases, initial visible information/model/settings and bounded authorization. Report completion, validity, unsafe proposals, fallback, calls/tokens, total latency and explanation support; do not select only successful cases or substitute classification F1 for scheduling quality. Flat forecast ties and unavailable candidates remain explicit. Final held-out adoption or a seventh matrix system requires a separately agreed frozen protocol, not this design.

## Required implementation verification (not completed here)

Synthetic fixtures cover stable ordering/ties, missing/invalid scores, unknown IDs, per-job/total cap boundaries, mandatory coverage, jointly infeasible candidates, stale snapshots, absent forecasts/artifacts, deterministic fallback, no private feature leakage, preserved current Agent behavior and unchanged request ceilings. Artifact loading requires authenticated trusted input and permission; no joblib is opened in this design task.

Acceptance: Edison confirms score/feature/artifact contract; Nisha confirms fair variant/comparison/caps; Ved confirms ID/plan/reference boundary. Implement the agreed independent parts only, run offline checks, then obtain fresh scoped run approval if needed. No superiority, successful hybrid schedule, trained model or experiment result is claimed now.
