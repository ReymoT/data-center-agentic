# Development-only dispatcher preparation — November 24

Owner: Matty. Implementation lives in `scripts/prepare_rule_study_rollout.py` and
`scripts/rule_rollout_supervisor.py`, outside the accepted scientific package.
The scheduler, common runner, verifier, generator, metrics core and shared contracts
are unchanged. This completes implementation/offline preparation, not a study run.

## Exact supported scope

Only the existing received 120-case development pair is allowed, by fixed raw hashes.
The order is the recorded case order, then rules-v1 / Greedy A / Greedy B: 360 runs.
There is no generator/final-seed operation, arbitrary module/command, model, training,
retry or warmup. A shared budget charges execution and replay states/transitions.
Full execution plus replay can charge 21,600 of each. The existing independent
kernel checks the same wall deadline during eligibility enumeration but does not
charge those assignments as states/transitions: counters are not total CPU work.
Old 10,000-step authorization and consumed IDs cannot be reused.

Each fixed contained pair worker uses the real common runner and independent
artifact/replay checker. It stops on FAIL or INCOMPLETE, source/input drift, malformed
accounting, missing-forecast control mismatch, or resource/cleanup failure. Actual
metrics are separated by stratum; no pooled ranking. Missing-forecast case JSON and
policy-visible forecasts stay empty. The sidecar's real artificial weights are used
only for private simulator accounting and evaluator recomputation, never forecasts.
Job-only, background and total-site artificial impact are reported separately;
equal-work reduction retains the accepted job-only basis and explicit unavailable reasons.

## Containment and resource semantics

A whole-batch Job Object contains serial nested pair Job Objects. Combined/per-pair
wall deadlines start before process creation; each cleanup has a separate three-second
allowance, with the outer supervisor bounding nested cleanup as well. Descendants are
terminated and cleanup must be verified. Output is monitored as a stop threshold,
not an operating-system disk quota: writes may overshoot between observations. Unsafe
linked output or overlarge inventories stop the worker. Do not describe it as a
guarantee that zero bytes can be written above the threshold.

Implementation validation ceilings are 900 seconds combined, 60 seconds/pair,
256 MiB observed output and 5,000,000 charged states/transitions each. These are
technical supported maxima, not an accepted experiment budget. The older proposed
3,600-second batch is not supported by this dispatcher. No concrete limits are
silently adopted: all exact values remain null in a draft until separately reviewed.
The actual native-host context must be used; the Codex sandbox cannot publish the
required hard-link fixtures. No security/control bypass is introduced.

Killed/failed pairs preserve partial output. Reported counters distinguish completed
pairs from unknown partial work; partial work is bounded by that pair's reserved
remaining budget. Do not interpret a failure's known counters as complete totals.
An ID is durably consumed once before release; request/code/input/environment are
checked again after reservation. Failure never makes the ID reusable.

## Safe public preparation commands

```
python scripts/prepare_rule_study_rollout.py --draft --out <new-external-request.json>
python scripts/prepare_rule_study_rollout.py --inspect <request.json> --out <new-inspection.json>
```

Use a clean merged checkout; output files are created exclusively. Public CLI does
not execute. The host-only `dispatch_once` hook accepts an in-memory trusted authority
adapter, never authority from JSON, a URL or an import path. That adapter must
authenticate Matty's fresh exact request hash, unused ID, source, output, all limits
and complete protocol freeze. A component baseline or a populated URL is insufficient.
The canonical external ledger is `RuleStudy_Run_Ledger` beside the checkout.

## Checks and remaining gates

Later November 24: [AI review corrections](RULE04_AI_REVIEW_FIXES_NOV24.md) add fixed
authorized-hash handoff, shared absolute deadline, cooperative stop reserve, durable
checkpoints, host/pair failure summaries and one-second outer/active-pair output scans.
The proposed 900-second/256 MiB envelope is unchanged and full-batch feasibility is
not proven. Refresh source pins/request under the revised freeze before approval.

Offline tests cover request/closed-gate/source guards, resource bounds, one-use ID,
drift after reservation, failed cleanup, actual dummy timeout/output/descendant stops,
nested containment and fail-fast/no-retry behavior. Eighteen small authored fixture runs across the three policies
exercise the real runner/replay and hidden-weight accounting path; they are unit
fixtures, not scientific evidence or the 120-case batch.

Nisha's original scoped accounting acceptance is preserved separately. Before actual
dispatch: refresh clean merged-source pins and environment, record exact prospective
resource values and output, complete the whole-protocol freeze, review the exact
request and obtain fresh single-use authorization. Final generation/no-overlap and
generalization remain outside this development dispatcher. Deadlines stay Nov25 core,
Nov26–27 repair/reproduction, Nov28 at 18:00 Arizona candidate.
