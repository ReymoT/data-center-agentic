# RULE-01 concrete study-local adapter proposal

Matty, November19, issue #239. Version proposal-1. Prepared against main ed2df758f906fd28e7e8e979ef5081a5dd1a2e00 and instructions1.30. This is an exact interface proposal for Ved/Nisha/Edison acceptance, not an implemented adapter, adopted schema, scientific freeze or execution authorization. Ved's agreement on identity/objective/domain/unchanged abstention is recorded in [his reply](https://github.com/ReymoT/data-center-agentic/issues/239#issuecomment-7029069906); it does not automatically accept this new serialization.

## Identity and compatible components

Use a new study-local envelope named rule_study_decision_v1. Its policy_id is exactly one of rules-v1, greedy_a, greedy_b; study_id is rule-study-20261119-v1. All three policies use this same envelope and the same production physical gate. Existing F02 SystemId, DecisionRecord, PolicyOutput, schemas and six-system registry remain unchanged. Never label rules-v1 as Agent or Greedy to pass a legacy enum.

Reuse F02 Plan, VisibleState, ConstraintSnapshot, CheckResult and ApprovedActions only for their existing meanings. Greedy A/B continue producing their normal PolicyOutput; the adapter extracts the actual .plan and preserves original policy/forecast fallback metadata. Rules-v1 supplies a Plan with the same physical meaning and a separate list of fired rule/arithmetic evidence. Do not construct a legacy DecisionRecord with a false system ID. This new envelope is not consumable by old E01 automatically; Nisha must accept/implement the independent reader or explicitly verified mapping.

## Exact decision record fields

| Field | Required meaning/type |
|---|---|
| record_kind | Literal rule_study_decision_v1; illustrative files with another kind are refused for execution |
| adapter_version | Literal proposal-1 until adopted, then an explicitly accepted version; never treat this proposal as a runtime default |
| study_id, policy_id | Exact IDs above; each policy keeps separate results |
| case_id, decision_index | Nonempty study case ID, integer0-29; case identity is not a source/old held-out ID |
| bindings | spec_sha256, adapter_source_sha256, generator_source_sha256, case_sha256, environment_lock_sha256 and full code_commit; real runs require all actual non-null values |
| state_before | slot, state_version, visible_state_sha256, constraint_snapshot_sha256; retain actual serialized VisibleState/snapshot in referenced immutable files |
| proposal_stages | Ordered list; each entry has stage_id, origin rules-v1/greedy_a/greedy_b/greedy_a_fallback/fault_injection, actual F02 Plan, rule_ids, arithmetic[], check_result and diagnostic errors; null check only before checking |
| selected_stage_id | Null if no candidate passed, otherwise a stage_id referencing an actual passing check |
| execution | status executed/abstained/blocked/indeterminate, actual current starts, actual transition reference/hash, simulator rejection or null, and state_after slot/version/hash |
| errors | Structured stage/code/message array; preserve failures, never erase them with a fallback success |
| model_call_count | Actual integer0; any nonzero count fails the no-model boundary |

A terminal/result file rule_study_result_v1 references the exact decision hashes for one case/policy, actual finished/missed/unfinished job IDs, accounting inputs/totals with units, and complete/partial/failed status. No trial pooling or zero replacement for missing totals. It is not an EpisodeResult with a fabricated F02 SystemId. Record actual failure/partial output before stopping; never fill remaining decisions with invented no-ops.

Arithmetic[] entries use rule_id, constraint_id if available, slot, terms[{label,job_id_or_null,value,unit}], total, limit, signed_excess=total-limit, and predicate outcome. These are deterministic evidence linked to the exact state/plan; a rule's explanation is not an independent verdict. No ungrounded free-text safety claim can replace the numerical check.

## Common checked transition for all policies (implementation target)

1. One trusted study-local runner serializes mutations and reads actual current state/snapshot. Bind identity/hashes, persist an intention marker, and compute the candidate plan without private future arrivals or scoring facts.
2. Check each candidate using unchanged recheck_schedule(plan,state,snapshot). If the selected candidate actually passes, reread state/snapshot and refuse any mismatch before minting ApprovedActions.from_checked_plan. Only current starts execute; future placements stay advisory.
3. Follow the existing ExecutionController refusal-and-drain pattern: approved=None calls SchedulingSimulator.step(None), which records an actual refusal, starts no new work and advances running work/time. Do not forge a passing empty-plan approval to advance time. This existing behavior is code evidence, not permission to bypass the gate; the new runner must reproduce its checks and be independently tested.
4. Derive execution/current starts and state_after from the actual simulator transition. Failed/absent approval must yield no starts; mismatch or indeterminate persistence/effect is a stop condition with no retry. Preserve candidate, check, fallback and actual execution separately.
5. Feed all three policies through identical gate/clock/accounting semantics. Preserve Greedy B's forecast-to-A routing as a policy fallback reason, not a change of policy identity. Rules-v1 fallback candidate origin is greedy_a_fallback while its outer policy_id remains rules-v1.

The existing per-job abstention rule remains unchanged. Joint infeasibility does not justify inventing an individual physical certificate. If caseB partial scheduling and Greedy A fallback fail this gate, retain that blocked/no-start result. A different joint-exclusion gate would be a new explicit proposal requiring affected acceptance; it is not adopted here.

## Independent verification output

Nisha owns a separate rule_study_verification_v1 artifact referencing input/spec/code/decision hashes, implementation identity, exact bounds and property results. Use PASS/FAIL/INCOMPLETE/NOT_RUN per property, actual states/transitions/input counts, counterexamples and reasons. No production-checker invocation supplies the independent verdict. Replay and bounded reachable-state exploration are distinct methods and must be named. Any old E01 use requires an accepted mapping and cannot pretend the new envelope was an old six-system record. Unknown fields, mismatched identities/hashes and unknown versions fail closed.

## Hash and no-fake-example convention

For study-local JSON hashes, propose UTF-8 json.dumps with sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False and one final LF, using pinned Python3.12/serialization dependencies. This is a pinned Python convention, not a claim of cross-language RFC8785 compliance. Files and referenced raw records are immutable; actual code/lock hashes bind the serializer. Do not reuse documentation's CRLF-normalized file commitments as if they were canonical runtime state hashes.

[adapter_record.example.json](adapter_record.example.json) is deliberately marked illustrative_example_not_executable, status not_run, with null bindings/state/check/transition fields. It demonstrates field placement and expected caseA behavior only; a real runner must reject it. No pass verdict, actual measured result or invented digest appears in the example.

## Exact acceptance request

Ved: accept or amend the study-local envelope, unchanged reusable F02 components and common runner path; publish actual module/functions only when implemented. Nisha: accept or amend the independent reader/output and unchanged physical-gate/failure mapping. Edison: accept or amend the result/accounting identity mapping used by the three-policy comparison. Only these exact consumers are requested, not a new general approval from the whole team. Current #239 deadline remains November20 18:00Arizona. Implementation/harness preparation continues; new shared wiring waits for actual acceptance and research execution waits for its separate frozen bounded authorization.

## November19 actual review response

Nisha [accepted proposal-1](https://github.com/ReymoT/data-center-agentic/issues/239#issuecomment-7030302299), with an independent parser/predicates and a new reader, not old E01 remapping. Record oracle-graph versus policy-induced exploration separately, domain labels/counters, scope reasons and counterexamples. P1-eligible gate refusal preventing completion is a progress FAIL; infeasible/dynamic inputs outside the P1 assumptions are not progress successes. Use the existing NOT_RUN status with a scope reason for ineligible properties rather than inventing a new status enum. All safety properties still need actual checks. The [review-2 decision](../decisions/NOV19_RULE01_REVIEW_REVISION.md) adds an optional secondary domain and workload-diversity correction without changing old F02 or gate semantics. Remaining exact Ved/Edison acceptance is tracked in #239; this is not implementation or execution authorization.

## November20 implementation handoff received

Ved [explicitly accepted the concrete proposal-1 mapping](https://github.com/ReymoT/data-center-agentic/issues/239#issuecomment-7031694901) in #239; this is implementation-boundary acceptance, not implemented code or run approval. Nisha's new independent [RULE03 harness](RULE03_VERIFIER.md) implements bounded callback checking and a draft strict trace reader. Serialization must still be checked against Ved's actual produced records; external state/code artifact authentication remains incomplete. Edison's result/accounting acceptance is separate and outstanding.
