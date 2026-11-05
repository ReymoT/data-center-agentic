# Action-field validation outcome and model/fallback behavior

Matty instructed his assistant to carry out the reviewed recommendations, including
the linked exact `RUN-15e69e6129b7` validation proposal. That fresh approval was
recorded in a separate manager-local receipt; the original pending template is
unchanged. The single-use authorization was consumed once. A prelaunch no-startup
check passed before dispatch. No retry or warmup occurred.

## Actual outcome: failed and retained

The strict launcher stopped at Agent slot 1 after F02 rejected J2 in both `starts`
and `abstentions`. It retained the invalid response in its emergency attempt record.
This is a model semantic/contract failure, not another omitted-key response. The
existing conflict rule and stop behavior worked; they were not weakened or bypassed.

- Duration: 240.625 seconds. Requests: 5 Plain, 5 Agent, 10 total.
- One invalid-response attempt, zero uncertain outcomes; highest request 41.267 seconds.
- Five complete results (A/B/C/D and Plain), each with 30 traces and zero independent
  E01 replay findings/result mismatches. Agent has one slot-0 trace and no final result.
- Total saved traces: 151, not 180. Two slot-1 Agent requests are retained outside
  completed decision-trace accounting, including the invalid emergency response.
- Cleanup passed: owned process exited, port released and overall deadline respected.
  There is no passing summary. The abort prevented the final post-run identity
  comparison; its absence is not treated as a successful comparison.

[Sanitized failure/accounting record](../evidence/i01-action-fields-validation-2026-11-04.json)
pins the original private failure/cleanup/log hashes. Raw requests, responses,
traces, authorization and logs stay outside Git. No model call is authorized by
publishing this outcome. Source base, candidate and fixed bounds are retained in
the [preparation](I01_ACTION_FIELDS_VALIDATION_PREPARATION.md).

## Offline audit: separate model plans from executed fallback

The [aggregate behavior audit](../evidence/i01-model-fallback-behavior-2026-11-04.json)
reads both saved public runs, including the failed emergency response. It decodes
the original response content before F02 defaults and counts plan action fields.
It matches executed job starts to the execution gate's selected stage plan hash;
ambiguous matches are labeled rather than guessed. Completion comes only from a
final result; partial Agent completion is unknown. Complete units are replayed
with E01/Q03 Option B. The manager-local audit script's hash is recorded; no second
person's receipt or new validator implementation is claimed.

| Observation | Earlier received run e670485639c9 | Revised run 15e69e6129b7 |
|---|---|---|
| Outcome | Complete public validation PASS | Failed at Agent slot 1 |
| Raw plan responses | 13 | 9 before stop, including invalid response |
| Explicit action fields / plans with actions | 0 / 0 | 9 / 9 |
| Plain result | No completed jobs, no executed job starts | J1 completed; J2/J3 missed; one model-initial job start executed |
| Agent execution | J1/J2 starts from checked fallback; schedule equals Greedy A | One fallback job start saved at slot 0; no completed episode result |
| Requests / traces | 17 / 180 | 10 / 151 |
| Separate receiving | Nisha's scoped evidence PASS accepted | Not yet recorded for this failed run |

Raw proposal/repair entries can repeat a job; their counts are not executed-job
counts. An executed-status no-op is not a job start. Explanation prose is not a
schedule. Nine explicit nonempty plans demonstrate that omission no longer occurred
in this attempt, but do not prove correctness, faithfulness, improved safety or a
general causal effect of the grammar change. The two public exercises are not a
paired study or a substitute for the planned held-out experiment.

## What remains

Keep prompt/schema freeze and complete I01 acceptance blocked. Review the conflicting
action response offline against existing instructions and semantic checks before
proposing any further change. Do not silently repair the original response, resume
the interrupted Agent episode, weaken F02 or automatically rerun. Any changed
candidate requires new pins, a bounded proposal and fresh authorization. No new
ratings are requested, and Nisha's accepted earlier receiving report is unchanged.

E06 table integration is implemented through PR #179. Final analysis confirmation,
reference gaps, faithfulness scoring and held-out study reporting remain unfinished.
Source/forecast/compatibility/custody, I02, O04/P07, held-out reliability and I03/I04
retain their separate prerequisites. This outcome closes none of those gates.
