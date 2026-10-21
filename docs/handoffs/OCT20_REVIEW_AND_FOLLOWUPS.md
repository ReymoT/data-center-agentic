# October 20: reviewed merges and remaining follow-ups

Matty explicitly requested review of nisha/l01-empty-queue-guard and nisha/e01-episode-replay, merge if sound, then completion of the audit recommendations. Both are reviewed/merged with original commits preserved. Instruction deployment 1.16 and [F04 issue #31](https://github.com/ReymoT/data-center-agentic/issues/31) correct current status; ongoing task/scientific acceptance is separate.

## Reviewed branches

| Work | Verified behavior and corrections | Publication evidence |
|---|---|---|
| L01 [PR #30](https://github.com/ReymoT/data-center-agentic/pull/30) | Empty waiting queue produces a decision-bound empty proposed Plan, zero requests/attempts and no explanation. Added three review cases for invalid context, completion refusal and existing running work; 24 focused tests pass. Execution/clock advancement remain the future runtime's responsibility. | Original 0104d3c preserved; reviewed head df1e703; merged main 1e561a3890383dc4958ee30a19a993160a8e73be. PR CI39535430125 and exact main CI39535687194 succeed, 926 tests +19 subtests. |
| E01 [PR #28](https://github.com/ReymoT/data-center-agentic/pull/28) | Independent structural episode replay. Nine review regressions first failed, then passed after raw constraint/hourly validation and site/snapshot/visible-constraint comparison fixes. Unsupported completed_work scalar mapping is an explicit error. 121 evaluation tests pass; combined full suite 957 tests +19 subtests passes. | Original b677ac5 preserved; final reviewed head 133f172; merged main c7e67169119fa7886b7ed8d31e62de1c24b8177d including L01. PR CI39535716893 and exact main CI39535962143 succeed. |

Both latest branch heads were verified as ancestors of main after exact-main CI, then their GitHub branches were deleted with exact-head leases. Own merged review branches were detached/deleted; all worktree files and unrelated work were preserved. [L01 handoff](L01_EMPTY_QUEUE.md), [replay handoff](E01_REPLAY.md) and [review regressions](../../tests/evaluation/test_replay_review.py) preserve actual evidence. Issues #12/#24 remain open for full acceptance. Latest receiving adoption is unconfirmed until Nisha reports it.

The accepted no-op is a proposal, never a fabricated execution record. Agent/runner zero-call handling and A04/E02 persistence are not implemented. E01's existing draft reconstruction reports and omits unknown/nonwaiting/slot-mismatched executions; it is not physical reconstruction of arbitrary corrupt runs. Forecast issuance, mutation-version history and impact totals are outside the structural comparison. Completed-work unit/definition/reference mapping needs agreement before a supplied scalar can be validated. Reimo's missed-on-arrival clarification and actual saved-run validation remain open.

## Recommendation-by-recommendation follow-up

| Item | Work completed | Exact remaining owner/input |
|---|---|---|
| 1. L01 no-op | Answered Nisha's proposal/trace question, tested and merged #30; cleanup complete. | Matty agent/runtime boundary and Nisha E02 integration when dependencies exist. Full L01 needs K02/A01 and an actual development episode. |
| 2. E01 replay | Reviewed, corrected and merged #28; cleanup complete. Existing executed_starts question answered from F02. | Reimo timing clarification; Nisha/Ved protocol/reference mapping and real saved-output acceptance. No duplicate replay implementation. |
| 3. A01/F03 | Continued diagnostics; fixed a separately reproduced response-stream ownership bug with real HTTP/1.0 and HTTP/1.1 regressions. Smaller 8192-byte reads still timed out, so that workaround is rejected. The bundled runner help has no documented vocabulary-only switch; no unverified model-loading route was used. | Matty runtime tokenizer/rendering equivalence and intermittent timeout root cause; Ved runtime revalidation; Nisha/Ved new tokenizer dependency agreement. Service/context checks and explicit bounded inference authorization remain required. |
| 4. Q01-Q04/A03 | Reconciled implemented plain guard and draft replay with the existing partial ledger; new missed-on-arrival question stays explicit. | Edison agreement and affected owners' joint-infeasibility/Q08 rule. An overall passing production checker is not created here. |
| 5. Q10 | Corrected stale index wording: summary-assertion extraction and keeping selected pairs/shortfalls are already accepted by Nisha/Matty. | Ved sampling/analysis agreement and exact eligibility. Matty recommends original slots 0–23 until an exact input-only alternative is agreed. No frozen map/ratings invented. |
| 6. Q11/Q12 | Preserved accepted Matty/Nisha roles, all allocations and existing requests. | Reimo/Ved/Edison allocation/contact confirmations, blockers and next evidence checkpoint. No reassignment. |
| 7. Q13 | Preserved attributed course dates and existing conditional Nisha response. November 16 class readiness remains the target. | Nisha authoritative timezone/rubrics/delivery/code facts; other contributors' platform/license/access/retention agreement. No slides/LICENSE/visibility/storage change. |
| 8. D06 | Structural evidence remains verified. Read the pinned upstream tree/license; it supplies no new accepted pollutant/interval/adoption decision. No raw data redistribution or transformation. | Ved/Reimo source pollutant basis, interval convention, dataset rights, factor alignment and consumer acceptance. The separate deferred Frontier D02 follow-up remains deferred. |
| 9. F04/F05 | Corrected current index/ledger/plan/coordination/README/architecture, regenerated current diagram assets and aligned all ten headers/changelog to 1.16. Earlier evidence remains historical. | Final publication checks and refresh/resume handoff; receiving adoption requires actual replies. |

A02/A04/I01 remain blocked by real provider/checker/context/policy/impact/runtime dependencies. Passing unit tests never substitutes for a real integrated episode or independent scientific approval.

## A01 resource fix and continuing diagnostic limit

A new real-loopback regression retains the actual HTTPResponse so garbage collection cannot conceal the leak. Before the fix it fails after the expected size-limit error because the response stream is still open. HTTPConnection can detach a will-close response; its own close is insufficient for that response. The fix explicitly closes the owned response in finally and still closes the connection. Both HTTP/1.0 and HTTP/1.1 regression cases pass. See [provider](../../dc_sustainability/llm/provider.py) and [test](../../tests/llm/test_ollama_provider.py); Python's [HTTP client documentation](https://docs.python.org/3.12/library/http.client.html) and its linked source describe the response/connection objects.

This is not a root-cause claim for the intermittent body timeout. The full isolated smaller-read experiment still had 956 passes/19 subtests plus one deep-object timeout. After the cleanup fix, the focused provider run had 44 passes and both deep-object variants timed out; cleanup regression itself passes. Payloads, deadlines, assertions and budget rules are unchanged. Existing [diagnostic evidence](../evidence/a01-http-diagnostic-2026-10-20.json) remains historical. A successful later full run/hosted CI does not establish a timeout fix.

The [real restricted tokenizer candidate](../evidence/q09-counter-candidate-2026-10-20.json) remains research-only. No tokenizer dependency is adopted, no installed/global runtime/service setting changed, no runner/model load or inference request was sent, and prepared production token counts remain unknown. No fake response, passing checker, trace or research result was generated.

## Preserved scope and publication

All 50 task rows/owners/dependencies, exact seven-file merge/authority rules, canonical F02 schemas/interfaces, shared locks/prompts/generation settings and source attachments are preserved. Current Issue statuses preserve history and name missing agreements. Final publication commands/counts/CI and the consolidated owner/refresh handoff are recorded in #31 after execution. No task becomes Done from silence or a documentation update.

## Local publication checks

After the two-protocol cleanup regression was added, the complete local run had 958 passes and 19 subtests plus the unchanged intermittent deep-object timeout (959 total). The new cleanup cases both pass; the earlier combined reviewed-merge suite passed all 957 before that separate fix. Ruff lint/format (65 files), setup/links/versions/50-task/seven-policy checks, compilation, pip consistency, F02/lock byte comparison and whitespace pass. Architecture SVG/PNG were regenerated and visually checked, including corrected UTF-8 punctuation and explicit zero-call empty queues. No tests/deadlines/assertions were skipped or weakened. Hosted results are recorded separately after execution.

[The new missed-on-arrival question and explicit recommendation](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6307129156) is sent to Reimo/Nisha/Edison/Ved for agreement; it is not a selected shared rule. Existing Q10/runtime/dependency/allocation/course/source requests remain open.
