# RULE-04 development handoff: files received, partial review

Edison's [actual handoff](https://github.com/ReymoT/data-center-agentic/issues/242#issuecomment-7117430854)
and original PR #271 commit `4e25e31b5838ba5c9ba50bc61924c80ed8c2f5a4` supply
120 development cases, their evaluator-only accounting sidecar, producer-generated
checker reports and first metrics over the already retained 10 authored traces.
His five original evidence files and checksum list are retained byte-for-byte.
See [the evidence directory](../evidence/rule04-dev-nov23/README.md).

## What Matty fixed directly

The added metrics module changed the frozen scientific package's file set, and
the existing source-guard CI correctly failed. Reporting now lives in
`scripts/rule_study_metrics_core.py`; the scheduler, independent verifier and
whole `dc_sustainability` package remain unchanged. No guard or test was weakened.

Four new unit regressions reproduced false available comparisons for mismatched
or unverified impact, recorded execution violations, duplicate baselines and
different producers/incomplete runs. The corrected tool rejects these. It also
checks complete job/accounting coverage, intervals/power, strict bounded JSON,
selected current starts, retained artifact commitments and trace bindings before
high-level reporting. A complete saved two-policy example reads successfully; a
corrupted decision commitment is refused. The focused metric/source-guard suite
passes 56 tests, including the original ten metric tests.

The CLI and tool only read retained records; no policy, generator, independent
oracle or scientific replay was run in manager review. Metrics count recorded
gate/selection conflicts, not a new independent physical-safety verdict. Local
artifact consistency is not external source authentication or independent metric
acceptance. Supplied baseline and comparison must share inputs/outcome sets and
source bindings, have no recorded gate conflicts and have verified impact; the
baseline must be positive. Unavailable comparisons retain reasons, never zero.

## Preserved evidence and reviewed projection

[Original first metrics](../evidence/rule04-dev-nov23/authored-first-metrics.json)
remain the producer's submitted output. The separate
[reviewed metrics](../evidence/rule04-dev-nov23/authored-metrics-reviewed.json)
are a read-only projection of the exact saved authored archive bound to `dbb8e6f`.
All 10 supplied runs have matching recomputed totals. Scenario A is 8,000 versus
12,000 artificial score-kWh for rules-v1/Greedy B versus Greedy A; B-progress is
equal, and B's zero-baseline comparison is unavailable. These authored examples
are not an unseen-case experiment, emissions result or generalization advantage.
The [review receipt](../evidence/rule04-dev-nov23/manager-review-receipt.json)
records original/reviewed hashes and remaining gates.

Edison reports regenerating the development files using the merged generator,
and reports matching cases/weights to an earlier unpublished pre-review set.
The earlier files were not supplied; that historical equality is attributed,
not independently established here. The current files are a development handoff,
not final data. Producer checker reports do not stand in for Nisha's independent
accounting receiving; a single development set does not establish unseen
isolation. The manager does not grant retrospective execution authority.

## Next actions and unchanged gates

Nisha receives the actual pair and corrected metric tool/output in #242. Check
original hashes, case-set/sidecar identity/coverage and hidden-weight handling,
current source metadata, independent arithmetic and exact comparison reasons.
The sidecar remains evaluator-only and must never be a policy input. Missing
visible weights remain unavailable to this visible-weight reporting tool; use
the separately agreed evaluator-side accounting path for hidden-weight analysis.

No policy has run on these 120 development cases. Their rollout needs its own
exact bounded preparation/authorization; no final seed or unseen evaluation was
created by review. Input/metric/isolation freeze and final execution remain
unpassed. RULE-04 stays open, due November 25; Reimo methods and Edison/Ved demo
continue in parallel. Existing verification baseline/results are preserved.
