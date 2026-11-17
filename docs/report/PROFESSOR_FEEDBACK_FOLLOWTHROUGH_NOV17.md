# Professor presentation feedback: report and demo follow-through

Manager request: November 17, 2026. Tracking and owner responses: [#231](https://github.com/ReymoT/data-center-agentic/issues/231). These four items must be addressed in the final report and demo with actual implementation/results or an explicit pending/future-work disposition. Matty supplied the feedback; this is not an independently authenticated instructor transcript.

This request supersedes the November 16 assessment's optional-reporting disposition for these four items. It does not itself adopt an exact shared experimental protocol or authorize data/model/training execution. Prior three-fold metrics, selected artifacts and saved runs remain immutable historical evidence. Scalability and the accepted inter-rater-reliability requirement remain relevant.

## 1. Grouped ten-fold cross-validation — Edison (P04/P06)

Requested change: replace the current three-fold training/tuning split with ten-fold cross-validation over the existing 40 development episodes. Every episode's candidate/time-slot rows stay together. Episodes sharing dates or overlapping source/forecast windows must also remain in one group. Do not random-split candidate rows or reuse held-out observations.

Before adoption, publish the exact group map, overlap checks, deterministic seed, candidate hyperparameter grid, train-only preprocessing, selection metric and aggregation. Check that ten independent groups exist. A 36-episode/4-episode train/validation split is possible only if group sizes permit it; preserving stronger leakage isolation takes priority over an exact 90/10 episode count. Ordinary grouped CV is not necessarily chronological forward validation; state which generalization is measured. Ten correlated folds do not automatically guarantee tighter variance, and tuning-fold scores are not unbiased final test estimates.

Affected boundaries: Nisha evaluation/custody; Ved labels/source-window compatibility; Reimo allocation facts. Preserve the original allocation and three-fold artifacts while agreeing the new development split. No replacement metrics, refit binaries or new selection are claimed yet.

Report: training/tuning methods, fold membership policy, mean/spread/support and historical-versus-new artifact identity. Demo: explain the grouping and show measured results only after accepted execution.

## 2. Structured violation arithmetic and repair deltas — Matty (A03/A02)

Current route already supplies checker feedback and permits one repair. Requested enhancement: deterministic structured feedback with constraint and slot IDs, job/background terms with units, total observed load, limit, signed excess and the relevant bound/rounding convention. For repaired proposals, distinguish resolved, persistent and newly introduced violations by stable identity; retain both counts and exact records. A change from one violation to two is not alone proof that the same constraint became worse.

Illustrative arithmetic: J1 40 kW + J2 40 kW + background 40 kW = 120 kW, exceeding a 100 kW cap by 20 kW. Do not attribute those particular terms to EP-HAND1 without checking the exact saved state/plan. The saved public Slot 0 trace records initial count 1, repaired count 2 and checked Greedy A fallback. Preserve the failed repair as evidence.

No hidden future/source facts enter policy-visible feedback; use the exact visible snapshot and verifier input. The controller still rechecks before execution. Preserve the independent evaluator and the one-repair limit. If a new feedback schema/prompt is adopted, version and pin it and obtain affected Nisha/Ved agreement. An optional matched feedback-versus-no-feedback ablation requires its own fixed design and bounded approval.

Report/demo: show a real saved rejected proposal, exact arithmetic, repair outcome and checked fallback, separating implemented feedback from proposed enhancements. No new prompt, verifier output or successful repair is claimed by this document.

## 3. ML-ranked warm-start proposals — Matty (A02), Edison candidate supplier

Requested variant: use a pinned existing tree/forest to score candidate (job, start-slot) pairs, deterministically filter feasibility and present a bounded top-ranked option set to the LLM. Specify top-k, per-job coverage, duplicate/tie ordering, model/artifact identity, missing-forecast behavior, invalid-choice rejection, abstention/fallback and full timing/call accounting. Recheck the chosen plan against the latest state; candidate feasibility is not an execution permit.

Keep this a separately versioned Agent variant. The present six systems and existing Agent behavior do not silently change; current fallback is checked Greedy A. Any comparison must control episode/facts/model/settings and state the additional ranker contribution and budget. If ranker scores tie under flat persistence, report ties rather than claim strategic carbon optimization. Shared protocol changes require Nisha's evaluation agreement and relevant contract/label agreement before implementation. No hidden refit, private artifact load or model request is authorized here.

Report/demo: describe the architecture/choice boundary and show a genuine measured example if available; otherwise label the proposed hybrid and its limitations explicitly.

## 4. Delay versus environmental impact plot — Nisha (E03/E06/R05)

Proposed x-axis: mean job turnaround = completion time minus arrival time, in hours. This is different from waiting delay (start minus arrival); label either metric explicitly. Report completed-job support and all missed/unfinished counts, since dropping incomplete jobs can make a bad policy look fast. Prefer matched completed-job sets for comparable points; do not impute unfinished turnaround as zero or claim it was observed.

Proposed y-axis: equal-work modeled emissions reduction (%) relative to Greedy A, 100 * (baseline kg - system kg) / baseline kg, only when the existing equal-work/input/realized-carbon/replay gates pass and baseline emissions are positive. Blocked, missing or undefined savings remain unavailable with reasons/counts. Average only with a specified weighting/paired denominator; preserve per-episode/trial identities, all LLM trials and uncertainty. Separate 24 core from six withheld-forecast episodes. No pooling unrelated historical runs, cherry-picked trials or ratios of unmatched work.

Show all six systems where comparable measurements exist, including negative savings and overlapping/uncertain points. Identify the nondominated measured set by minimizing turnaround and maximizing valid reduction, rather than drawing an interpolated frontier that suggests unmeasured attainable outcomes. A hybrid variant is extra and separately labeled. Use carbon-proxy wording while source semantics in #60 remain unresolved; flat forecasts and no equal-work observations may leave some or all points unplottable. Do not create fake placeholder values.

Report: metric definitions, paired plot, support/exclusions, uncertainty and trade-off interpretation. Demo: the same accepted figure with its source/run identities, or a clear pending-evidence explanation.

## Acceptance and handoff

Each owner posts an exact proposal/draft or blocker on #231 within 24 elapsed hours of the issue request; unresolved shared choices escalate to Matty, not inferred agreement. Matty fixes technical defects directly and notifies owners. Nisha integrates report dispositions; Reimo integrates demo coverage. Matty receives the final checklist before I04/R06. Neither this checklist nor passing CI grants run permission.

- [ ] Ten-fold grouping/tuning change agreed, versioned and measured, or explicitly limited/deferred.
- [ ] Structured repair arithmetic/deltas implemented and tested, with exact saved demonstration, or explicitly pending.
- [ ] ML warm-start variant defined/verified and measured, or explicitly future work.
- [ ] Valid paired turnaround/reduction plot and denominators, or explicit missing-evidence disposition.
- [ ] All four dispositions appear in final report and demo; no proposed result presented as completed.

Execution HOLD, source/input/custody gates, current feasibility checkpoint and inactive contingency remain unchanged.
