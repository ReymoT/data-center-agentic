# October 20: Matty's six-priority delivery

Owner: Matty Anderson (MattyAnd); technical contacts Nisha for checker/evaluation and Ved for unchanged contracts. Tracking: [F04/F05 issue #25](https://github.com/ReymoT/data-center-agentic/issues/25). Base main: `91eead14678c30e148d43b22df7e72c538bacbe9`. Task branch: matty/oct20-decisions-and-intake. Instruction deployment: 1.14; F02 remains 1.0.0.

Authority: Matty explicitly requested, "Finish all 6 priorities as you recommended." This authorizes the audit's technical answers, agreement records, E01 compatibility check, focused missing-input follow-ups and plan/shared-instruction corrections. It does not supply missing teammate agreement, authorize a live probe or move another owner's implementation task. No formal document review request is required.

## Work delivered

| Priority | Concrete work and source | Remaining gate |
|---|---|---|
| 1. Q03/A03 | [Matty answered](https://github.com/ReymoT/data-center-agentic/issues/7#issuecomment-6298589507) Q03 and confirmed the intended zero-call empty-noop path is feasible to implement. [Partial ledger](../decisions/Q01_Q04_AGREEMENT_STATUS.md) records scope; Edison tagged. | Edison Q01-Q04 reply, unsettled joint infeasibility/Q08 details and actual checker/runtime/no-op implementation acceptance. |
| 2. Q09/A01 | Recorded [Nisha/Ved/Matty setup agreement](../decisions/Q09_DEPLOYMENT_OCT20.md). Refreshed actual metadata and prepared both request shapes with the real L01 renderer/public synthetic F02 input. [Follow-up](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6298590019) reports runtime drift and asks Nisha/Ved about revalidation. | Observed 0.40.6 differs from accepted 0.40.5; validated pinned counter/context measurement missing; explicit bounded inference authorization and run environment verification missing. Zero model calls. |
| 3. E01 intake | Created [issue #24](https://github.com/ReymoT/data-center-agentic/issues/24), assigned Nisha. Reproduced exact draft-head tests and nine independent synthetic hand cases; [answered PR #23](https://github.com/ReymoT/data-center-agentic/pull/23#issuecomment-6298634637) about future capacity and reported a slack discrepancy. | PR remains draft, unmerged. Owner correction/agreement, protocol/replay/real saved-output evidence still needed. |
| 4. Q10/E04 | [Accepted baseline/A2/A4/A6 and requested A1/A3 clarifications](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6298590572); Ved tagged. [Status record](../decisions/Q10_REVIEW_STATUS.md) preserves each proposal's scope. | Nisha/Matty resolve summary assertion and queue eligibility rules; Ved confirms sampling/analysis. No freeze/code adoption. |
| 5. Q11/Q12 | [Recorded Matty coordinator/publisher, Nisha accepted backup and allocation](https://github.com/ReymoT/data-center-agentic/issues/21#issuecomment-6298590974); activated [dated summary](../COORDINATION.md). Reimo/Ved/Edison tagged with existing critical tasks and confirmation request. | Remaining owner allocation/access choices; no reassignment or new permissions/monitoring. |
| 6. Q13 | [Accepted Nisha-reported course schedule for planning](https://github.com/ReymoT/data-center-agentic/issues/16#issuecomment-6298591471); corrected plan, README, masters and context. Recorded Nisha's platform/conditional license reply, asked for missing requirements and remaining contributors' agreement. | Timezone/rubrics/demo/report/code requirements, other platform/license/access/retention agreement and source/course permissions. No LICENSE/visibility/storage/retention change or presentation production. |

All six manager-action deliverables are addressed. This is not a claim that all related Issues, scientific decisions, A01/A03/E01 or the project are complete. Open gates stay in their Issues and the decision index.

## E01 compatibility evidence

Reviewed unmodified PR #23 head `f5a2542c1816ed0f34d8f784053453ae9b26c1f6` in an isolated detached worktree. Its F02/schema and A03 checker match main's base byte-for-byte. Reproduced 55 focused tests and full 871 tests plus 19 subtests on Windows CPython 3.12.14 with the existing candidate environment. Nisha's own 3.12.10 report and hosted CI remain separate evidence.

[review_e01_capacity.py](../../scripts/review_e01_capacity.py) requires that exact clean draft and checks nine synthetic cases against independently specified hand outcomes, rather than using either implementation as truth. [Saved results](../evidence/e01-a03-compatibility-2026-10-20.json): sequential occupancy, future-only 110 kW overload, running occupancy, exact 100 kW before PUE 1.2, changed 70 kW capacity, slot-23 completion at 30, missing capacity, omission and the tolerance boundary. This is not a real policy/model run or independent episode replay.

One discrepancy: background 40 plus job 60.0000000001 exceeds capacity 100 at slot 2. A03 fails strictly; E01 permits FLOAT_SLACK=1e-9 and returns valid. Reported to Nisha/Ved; recommended strict shared physical limit or explicitly agreed numerical comparison tolerance, without importing checker truth into E01. A03's otherwise feasible overall error is not comparable to an E01 valid verdict while protocol checks remain incomplete. No production or evaluator code was changed to hide either distinction.

Reproduce from the repository root, with a clean checkout of that exact E01 commit at the supplied path (preserve other work):

```powershell
.venv\Scripts\python.exe scripts/review_e01_capacity.py --draft-root ..\data-center-agentic-e01-check --out ..\e01-capacity-recheck.json
```

Run E01 tests from its checkout with the validated Python environment. The tool imports draft code only for this explicit review; it does not copy/install E01 into main. Output files refuse overwrite.

## A01 preparation and validation limits

[inspect_ollama.py](../../scripts/inspect_ollama.py) read only version/tags/show metadata twice, without loading/generating/installing. [Fresh inventory](../evidence/ollama-qwen3-8b-2026-10-20.json) records runtime 0.40.6; full digest/license/template/parameter hashes retained. It is observational evidence, not an adopted replacement pin. The accepted 0.40.5 record is preserved.

```powershell
.venv\Scripts\python.exe scripts/prepare_q09_probe.py --inventory docs/evidence/ollama-qwen3-8b-2026-10-20.json --out ..\q09-probe-recheck.json
```

This actually renders both public request shapes and hashes/size diagnostics. [Saved preparation](../evidence/q09-probe-preparation-2026-10-20.json) is blocked, with prompt token counts null. There is no network/dispatch/provider instance or manufactured response. Character/byte lengths are not token counts. Later inference must use the real plain policy and one shared two-attempt provider ledger after validation/authorization; this preparation is not a fake runner or full agent implementation.

The production adapter accepts an injected counter but has no validated real one. The current [Ollama chat documentation](https://docs.ollama.com/api/chat) exposes post-response prompt_eval_count, which cannot itself precheck a request. The [proposed tokenizer endpoint](https://github.com/ollama/ollama/pull/12030) is not deployment validation. No tokenizer dependency, template approximation or runtime downgrade was guessed to bypass the gate. The actual context boundary and two-call probe remain blocked rather than falsely marked complete.

## Changed scope, verification and receiving handoff

Changed: README/architecture/plan/coordination/context, decision records, AGENTS/project master/all ten numbered-role headers/changelog/audit, two working offline review/preparation scripts and three dated evidence files. Preserved all 50 checklist rows, exact merge/authority policies, F02 schema/interface bytes, locks, existing prompts, production/teammate code, source attachments and unmerged work. The target architecture diagram remains accurate at its stated implementation boundary; no new production component is claimed by the draft review.

Applicable verification: full main offline pytest suite, lint/format, compileall, dependency smoke/pip consistency, instruction/link/version validation, canonical F02 hashes and diff/whitespace checks. Exact publication commit and main CI evidence are recorded in issue #25 after publication, avoiding a self-referential commit hash. No live inference, held-out, paid/cloud, simulator action, email delivery or scientific result is claimed.

Local verification detail: lint/format (51 Python files), compileall, dependency smoke, pip consistency, setup and whitespace checks passed. F02 Git blobs remain `41ab733816ac171fa283f75c5252c658025c124d` (interface) and `f139266bc9638208617e23c686ac97c442757fbf` (schemas). The initial full E01 run passed 871 tests and 19 subtests. Later main runs each had 815 passes/19 subtests and one intermittent timeout in the existing deep-JSON object HTTP regression; a focused provider run had 43 passes/two timeouts. The unchanged E01 checkout subsequently reproduced one timeout in the same test. A separate diagnostic invocation of both synthetic cases received all 24001 bytes and recorded the intended decoder failure correctly. This is unresolved timing behavior, not proof that a live request works. No test/deadline was weakened or skipped, and no provider code changed. Hosted exact-head checks must be inspected independently before merge; local timeouts remain disclosed even if CI passes.

Receiving owners: Nisha continues E01 and Q10/course facts; Ved checks sampling/contracts and runtime replacement proposal; Edison replies to Q01-Q04 and supplies existing impact/policy prerequisites; Reimo/Ved/Edison confirm Q12/Q13 items. Matty retains his blocked integration work. Check Issues for later responses; no automatic follow-up service is created.
