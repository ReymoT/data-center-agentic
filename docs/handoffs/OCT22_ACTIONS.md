# October22: reviewed P01 and approved follow-ups

Matty explicitly requested review/merge of edison/p01-impact first, then all recommendations from the October22 audit. Matty uses `MattyAnd`; Edison remains P01 owner and Reimo the S02 receiving owner. [P01 issue #36](https://github.com/ReymoT/data-center-agentic/issues/36) records review defects/adoption limits before edits. [F04 issue #37](https://github.com/ReymoT/data-center-agentic/issues/37) records stale Edison-agreement status before instruction edits. This increment publishes instruction1.18; policies, contracts and task allocations remain unchanged.

## First requested task: P01 review, merge and cleanup

Original PR #35 head `d7dbb479ef62ad91931f2acc90b2679be5910487` and all Edison commits are preserved. An isolated review worktree reproduced all22 original metrics cases. Five added hand-derived cases first had three failures: finite ledger totals produced infinite normalized fractions, and positive/negative large finite display values raised InvalidOperation. Existing ImpactError now rejects non-finite produced fractions; local Decimal precision preserves half-up one-decimal display without changing caller context. The finite reverse comparison and explicit F02 value conversion remain available. All27 metrics cases pass.

The F02 hand conversion gives65.4/58.08 job kg,504 site facility kWh,168 job facility kWh versus140 job IT kWh before PUE, and7.32 kg savings at PUE1.2. This is actual component calculation on labeled synthetic hand records, not a production S02 adapter or a selected completed_work mapping. Missing/unmatched evidence keeps savings blocked. Nisha's independent evaluator does not use P01 as truth.

Reviewed head `965c9808c215b3ed08f471b4161e11285873810f` merged at main `2d78cfbfcdfa11eae48cf2f2b5167ece934ec24d`. Exact reviewed-head CI39827351140 and exact merged-main CI39827745582 both pass986 tests and19 subtests. Local full-suite985 passes/19 subtests plus the unchanged intermittent A01 object-agent timeout are retained, with no P01 failure. Setup/lint/format69 files/compile/pip/dependency smoke pass. No payload, assertion or deadline was weakened.

After current-head ancestry and exact-main CI verification, the latest remote edison/p01-impact was deleted using an exact-head lease. Matty's merged review branch was detached/deleted with its worktree files and all unrelated work preserved. [The verified receiving handoff](https://github.com/ReymoT/data-center-agentic/issues/36#issuecomment-6347716937) asks Reimo/Edison to agree the calling convention, proceed with S02 and report actual consumer adoption. P01/S02 acceptance stays open; a merge is not receiving approval.

## Second requested phase: item-by-item actions

| Recommendation | Action completed | Remaining exact input |
|---|---|---|
| P01 review/handoff | Reviewed/fixed/merged #35, opened #36 and verified CI/cleanup above. | Reimo/Edison calling convention and actual full30-slot S02 accounting/adoption. |
| New Q04 question | [Answered Edison](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6347718020) with recommendation(b), whole-decision checkedA for incomplete required fresh coverage; [published the exact pending-window proposal](../decisions/Q04_PARTIAL_COVERAGE_PROPOSAL.md). | Reimo/Ved/Nisha exact required-window agreement with Edison implementation. No silent candidate truncation or shared setting. |
| F04/F05/Q12 intake | Recorded Edison's actual Q01-Q04 and allocation replies across current masters/ledger/index/plan/coordination/README/architecture. All ten numbered/role headers/changelog are1.18. | Only Reimo/Ved allocation confirmations remain missing. Edison should not be asked to repeat his existing reply. |
| Arrival optionB/Q08 | Preserved the pending proposal and asked only for the missing positions/boundaries in [one consolidated owner request](https://github.com/ReymoT/data-center-agentic/issues/37#issuecomment-6347749860). | Reimo S01/D03 decision, Edison position, Ved reference/context/joint-certification rule and Nisha exact independent replay/scoring boundary confirmation. Current code behavior is unchanged. |
| A01/Q09/F03 | Continued controlled diagnostic work below; preserved the existing failure evidence and all production transport/settings. Named Ved/Nisha missing inputs in the owner request. | Timeout root cause; Ved runtime0.40.6 revalidation, Nisha/Ved tokenizer dependency direction, actual rendering/count/context/resource/service evidence and explicit bounded inference authorization. |
| E01 | Requested reviewed replay/guard adoption and completed_work/claim unit/meaning/reference agreement. Kept evaluation arithmetic separate from P01. | Nisha/Ved reply and real saved-output evidence when runtime records exist. |
| Q10 | Preserved accepted assertion/no-replacement/shortfall rules and asked Ved for analysis/eligibility agreement. | Exact design/eligibility reply; Nisha owns rubric/map, Matty independent second ratings. No frozen map or ratings exist. |
| K02/P02/S02 integration | Named actual owners and handoffs; P01 is available for S02 after calling-convention agreement. | Ved K02, Edison P02, Reimo S02 actual artifacts/consumer checks. Edison's October25 checkpoint is future, not missed. No fake replacement module or full integration. |
| Source/freeze/training | Retained verified D06 structure and missing Q05-Q08 facts/rules, with named owners. | Pollutant/interval/rights/factor/adoption evidence; split/distribution/training/certification agreement. Separate FrontierD02 follow-up stays deferred. |
| Q13 | Retained Nisha's attributed Nov16/18 and Dec2/9 dates and requested remaining official/platform/release facts. | Official timezone/rubric/demo/report/code requirements and contributors' remaining platform/license/access/retention replies. No slides or release settings changed. |

The owner request includes task IDs, exact missing inputs and next evidence checkpoints. GitHub mentions do not prove email delivery, teammate agreement or receiving adoption. Current Issue summaries are reconciled without deleting earlier history; unfinished tasks remain open. Final publication/main CI and refresh/resume proof are recorded in #37 after execution.

## A01 controlled protocol observations

The local full P01 review still reproduced the existing object-agent timeout. Previously published [matched-socket failure evidence](../evidence/a01-http-wire-2026-10-21.json) remains untouched. The shipping provider, test bodies, assertions and deadlines are unchanged.

The existing observer now has an explicit `--synthetic-protocol` option for a controlled local test-server experiment. Its default selects no protocol override. It only changes the initial protocol of a ThreadingHTTPServer fixture named server; existing tests can still set their own explicit protocol cases. This is neither a production/Ollama protocol choice nor a substitute acceptance run. The observer restores wrappers, hashes rather than prints body text, and refuses existing output paths.

Actual single observations on the same47 provider cases: HTTP1.0 had47 passes; HTTP1.1 had47 passes. Both object-agent and object-plain sends were matched by socket pair to complete24,001-byte bodies with identical received SHA256. [Compact evidence](../evidence/a01-protocol-observations-2026-10-22.json) records commands, artifact/observer hashes and the actual cases. Instrumentation changes timing, one pass per mode establishes neither reliability nor protocol root cause, and no timeout fix is claimed. These passes do not cancel earlier failures. Expected server resets in deliberate early-abort/timeout tests are not hidden or converted into model results.

Reproduce on the existing environment, with a new output path for each observation:

```powershell
.venv\Scripts\python.exe scripts/diagnose_provider_wire.py --synthetic-protocol HTTP/1.0 --out ../new-http10-observation.json
.venv\Scripts\python.exe scripts/diagnose_provider_wire.py --synthetic-protocol HTTP/1.1 --out ../new-http11-observation.json
```

Ordinary CI still runs the unmodified test suite without this optional experiment. No model call, runtime/pin/dependency/service change, fabricated response, production workaround or scientific result is created.

## Preservation and final publication

All50 task rows/owners/dependencies, exact seven-file merge/authority policies, canonical F02 schemas/interfaces, shared requirements/locks/prompts/settings, source attachments and newly merged P01 code/tests/handoff are preserved in this second phase. The diagram is regenerated from its maintained source and visually checked. Protected byte/task checks, actual final local tests, exact PR/main CI, verified task-branch cleanup and receiving refresh request are recorded in #37 after execution. Those workflow checks do not imply full A01/A03/A04/E01, source/freeze or end-to-end acceptance.


## Actual final local publication checks

The ordinary final suite without protocol overrides passes986 tests and19 subtests in7.81 seconds. The earlier local full review's985 passes plus known A01 timeout remain disclosed; this later pass does not establish a fix. Setup/links/versions/50-task/seven-policy checks, Ruff lint/format69 Python files, compilation, pip consistency and dependency smoke pass. F02/interfaces, requirements, shipping provider and reviewed P01 code/tests/handoff match the pre-maintenance byte baseline. The new protocol evidence's observer hash matches the actual script. Diagram assets were regenerated and visually inspected. Exact PR/main CI, publication SHA and verified merged-branch cleanup are recorded in #37 after execution.
