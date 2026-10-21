# October 21: approved actions, evidence and remaining inputs

Matty approved the October 21 audit recommendations: “I have review your recommendation. you can get them done.” Owner: Matty Anderson (`MattyAnd`); F04 technical contact: Nisha. Base main is `aa90fb0ae7f3bba6b9b625d58429b6b26c22b03d`, instruction deployment 1.16. [Issue #33](https://github.com/ReymoT/data-center-agentic/issues/33) records the instruction defect and authorization before edits. This increment publishes deployment 1.17; it does not finish blocked scientific or integration tasks.

The fresh audit found 10 open task Issues, no open PRs and only main remotely. PRs #28/#30/#32 are already merged and cleaned up; exact-main CI39538267661 succeeded. No new K02, P01/P02, S02, gate or agent implementation had arrived. The [50-task checklist](../team/03_RESPONSIBILITY_CHECKLIST.md) remains the ownership/dependency authority.

## Item-by-item result

| Approved item | Action completed | Exact remaining input |
|---|---|---|
| 1. Nisha's new Q03 question | [Answered as Matty](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6322088311), supporting option B with explicit unchanged physical limits, independent certification and cross-system tests. [Recorded the proposal](../decisions/Q03_INFEASIBLE_ARRIVAL_PROPOSAL.md). | Reimo/Edison/Ved agreement and Nisha's exact boundary confirmation, then real coordinated implementation/consumer checks. Current S01/E01 behavior is unchanged. |
| 2. A01 timeout | Added a reproducible actual-socket observer and [compact failing evidence](../evidence/a01-http-wire-2026-10-21.json), with same-connection send/receive/shutdown correlation. Preserved payloads, deadlines, assertions and production code. | Root cause and a verified fix remain open. Passing observations do not clear the failure. |
| 3. Q09 runtime/tokenizer | Sent the specific missing-input request in the [consolidated owner message](https://github.com/ReymoT/data-center-agentic/issues/33#issuecomment-6322132165). Existing accepted settings/research evidence stay unchanged. | Ved runtime 0.40.6 revalidation agreement; Nisha/Ved tokenizer dependency direction; actual rendering/token/context/resource validation and explicit bounded inference authorization. |
| 4. Q01–Q04/A03/A04 | Requested Edison's outstanding response and affected owners' joint-infeasibility/Q08 confirmations; corrected contradictory L01 guard guidance in the ledger. | Shared protocol/certification agreement and usable production checks/gate. No overall passing verdict is invented. |
| 5. E01 | Asked Nisha/Ved for receiving adoption and completed-work unit/meaning/reference mapping. Recommended retaining existing separate job-ID and before-PUE IT-energy quantities with an unsupported scalar left explicit. | Their agreement, protocol/reference resolution and real saved-run validation. No independent evaluator duplication. |
| 6. Q10 | Requested Ved's sampling/analysis/fallback and exact eligibility answer. Preserved accepted Nisha/Matty summary-assertion and no-replacement/shortfall rules. | Exact eligibility/design agreement and Nisha's development rubric/map implementation. Matty still recommends the slots 0–23 frame until an alternative is agreed. |
| 7. Integration prerequisites | Named Ved K02, Edison P01/P02 and Reimo S02, requesting real commits/tests or blockers/checkpoints. | Actual handoffs before A02/A04/L01/I01 acceptance. No fake replacement module or trace. |
| 8. Sources/freeze/training | Asked Ved/Reimo for remaining D06/Q05 source evidence, Reimo Q06, Edison Q07 and Ved Q08 proposals/agreements. | Verified pollutant/interval/rights/factor/adoption evidence, accepted split/distribution/training/certification rules. Structural D06 verification is already done. The separate Frontier D02 follow-up stays deferred. |
| 9. Q12 | Asked Reimo/Ved/Edison for existing allocation/contact confirmations and evidence checkpoints. | Their replies. Matty/Nisha coordinator/backup roles and all 50 allocations are unchanged. |
| 10. Q13 | Requested Nisha's official timezone/rubric/submission/demo/report/code facts and remaining contributors' platform/license/access/retention replies. | Actual source/owner responses. No slides, LICENSE, visibility or retention change is made. Attributed Nov 16/18, Dec 2/9 planning dates are retained. |
| F04/F05 intake | Corrected current masters, ledger/index, audit, coordination, README, architecture, plan and date on the diagram; synchronized ten package headers/changelog to 1.17. | Publication/CI and receiving adoption are recorded in #33 after execution. F04/F05 remain ongoing duties. |

There is one consolidated owner request rather than repeated reminders for each unchanged blocker. A posted mention is a GitHub notification request, not proof of email delivery, agreement or receiving adoption. New replies must be read before changing a shared rule.

## Actual A01 observation

The real loopback test uses a deliberately excessive-nesting synthetic JSON body of 24,001 bytes. The new observer matches both ends of the same TCP connection. In the reproduced object-agent failure, server `sendall` returned successfully for all 24,001 bytes and server `shutdown(SHUT_WR)` completed; client `recv_into` observed the 116-byte header and 23,360 body bytes, then timed out. The missing 641 body bytes are already absent at the observed socket reads, before JSON parsing. The paired plain case received the complete body with the same SHA-256 as the server's send buffer.

This narrows the observed symptom to socket delivery/read completion on that connection. A successful send means the server's send operation returned; it does not prove the peer received every byte or identify an operating-system, driver, security product or adapter root cause. We make no such attribution. No retry/read-size/deadline workaround is adopted. The separate owned-response stream cleanup fix in PR #32 remains valid and is not called a timeout fix.

Observed runs before final publication checks:

- Temporary socket observer, provider-only: 47 passed.
- Temporary socket observer, full offline suite: 959 passed and 19 subtests passed.
- Repository diagnostic, full offline suite: 958 passed, 19 subtests passed and one unchanged object-agent timeout. [Compact evidence](../evidence/a01-http-wire-2026-10-21.json) retains the failed result, source baseline, full local artifact hash and actual matching-connection events. It was captured before the post-test snapshot lock hardening; operational socket wrappers are unchanged.

- Final repository observer after snapshot hardening/formatting, provider-only: 46 passed and one unchanged object-plain timeout. The same compact evidence retains this second matched-connection failure and the observer/artifact hashes. Both systems have now exhibited the symptom in separate observed runs.

Instrumentation changes timing. None of the passing runs proves the intermittent failure fixed. The observer only wraps the existing synthetic test sockets, restores its wrappers in `finally`, avoids body-text output and exclusively creates its output file, preserving previous evidence. It creates no production transport, fallback response or model call.

Reproduce on the existing environment, choosing a new local output filename each time:

```powershell
.venv\Scripts\python.exe scripts/diagnose_provider_wire.py --full-suite --out ../a01-wire-new-observation.json
```

Omit `--full-suite` for the provider-only tests. `scripts/diagnose_provider_http.py` remains the earlier high-level observation tool. Both preserve test expectations; neither authorizes inference or changes provider settings. Large diagnostic logs stay outside Git; compact evidence contains loopback endpoints, byte counts and hashes, with no model output, private source data or device identifiers.

## Preserved scope and completion boundary

All task rows/owners/dependencies, exact seven-file merge/authority policies, canonical F02 schemas/interfaces, shared environment locks, generation settings/prompts, prior evidence, source attachments and teammate work remain intact. This publication does not activate option B, adopt a tokenizer/runtime pin, perform model inference or fabricate scientific results. A02/A04/I01/E05/I04 and final release still need their actual prerequisites.

Final local checks, publication SHAs, exact PR/main CI, verified branch cleanup and refresh/resume evidence are recorded in #33 after execution. Do not treat those workflow checks as full A01/E01 or scientific acceptance.


## Final local publication checks

The ordinary final offline suite, without diagnostic instrumentation, passed all 959 tests and 19 subtests in 6.81 seconds. Earlier traced failures above remain valid evidence; this pass does not establish a root-cause fix. Ruff lint/format (66 Python files), compilation, pip consistency, dependency smoke and setup/links/versions/50-task/seven-policy checks pass. The smoke check initially hit the sandbox's default temporary-directory permissions; setting TEMP/TMP to the writable project tmp directory allowed the unchanged smoke command to pass. No dependency or test was altered for that environment issue.

Exact F02/interface/requirements bytes and all 50 task rows match the pre-edit baseline. The architecture PNG/SVG were regenerated from their maintained source and visually inspected. The diagnostic CLI also refused an existing output file before running tests and left its hash unchanged. No raw body, source data, model output or device identifier is published. Exact PR/main CI and branch-cleanup results are recorded in issue #33 after publication.
