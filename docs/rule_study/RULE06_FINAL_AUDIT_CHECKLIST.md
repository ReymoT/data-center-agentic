# RULE-06 final audit checklist (#244)

Owner Matty. Prepared November19; checklist only, no boxes are pre-passed. Due November28 18:00 Arizona, with repairs/reproduction November26-27. See [the specification](RULE01_SPECIFICATION.md) and [plan](../decisions/NOV19_RULE_STUDY_PLAN.md).

| Gate | Evidence to retain | Responsible handoff |
|---|---|---|
| Scope/version | Final rule question, two cases, instruction/decision revisions; original RQ unanswered | Matty #239 |
| Accepted boundaries | Exact adapter/result mapping and affected-owner replies; no guessed F02 SystemId | Ved/Nisha/Edison #239 |
| Rule freeze | Rule IDs/predicates, objective/ties, complete search limits and specification/code hashes | Ved #240 |
| Input authorization | Independently authored profiles/workloads, generator provenance/parameters/hash and no old private/source reuse | Edison #242 |
| Unseen isolation | Dev/test seed domains, accepted/rejected generation counts, case hashes, no overlap and no tuning on final set | Edison/Nisha |
| Research authorization | Exact approved single-use batch/proof envelope, code ancestry/hashes, resource/stop controls, new output location | Matty before run |
| Independent verification | Distinct oracle implementation; actual states/transitions,64-domain inputs or explicit deviations; no production-checker verdict reuse | Nisha #241 |
| Safety | Separate property results, invalid-proposal tests, latest-state gate, capacity terms and fail-closed evidence | Nisha/Ved |
| Progress | Joint feasibility and closed-arrival assumptions; starvation/deadlock counterexamples; termination is not successful completion | Nisha |
| Real results | Actual files/hashes, complete vs partial status, failure retention, zero placeholder/fabricated measurements | Edison |
| Comparison | Identical inputs, fair Greedy A/B, all denominators and missing-data reasons; equal-work gates before reduction | Edison/Nisha |
| Demo | Two scenarios, runnable commands, actual fired-rule arithmetic/fallback; fault injection labeled; optional saved backup | Edison + Ved #246 |
| Requested materials | Named requests answered or exact unresolved optional artifacts; report/method diagrams supplied by Reimo | Edison/Ved/Reimo |
| Clean reproduction | Independent operator, environment identity, commands, regenerated outputs, semantic comparison and discrepancy log | Ved, with Nisha verifying code she did not author |
| Direct repairs | Original failures retained, fix commit, affected tests and new independent check; untouched retest set if rules changed | Matty + affected owner |
| Report | New study vs original design clearly separated; limits, existing IRR, four feedback dispositions, contributions and citations | Reimo/Nisha #223/#231 |
| Course/release | Actual #16 official-field status; public-package rights, correct format/location and submission responsibility | Nisha/Matty |
| CI/cleanup | Exact latest PR and merged-main checks; latest-head inclusion before deleting only merged branches | Matty |
| Delivery | Audited candidate bundle/PDF/demo hash inventory, broken-link/secret/private-data review, actual submission receipt later | Matty |

For every gate record PASS, FAIL, BLOCKED or NOT_APPLICABLE with evidence and reason; blank is not PASS. Do not mark research or final delivery complete merely because code CI passes. Deadline pressure cannot supply missing permissions, independent results or course acceptance.
