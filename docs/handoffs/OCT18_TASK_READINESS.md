# October 18 task completion and remaining gates

Owner: Matty Anderson (MattyAnd). Date: 2026-10-18, America/Phoenix. Instruction
deployment: 1.10; F02: 1.0.0. Matty authorized starting at A01/Q09 and completing the
five listed work items. That instruction does not approve missing scientific rules,
shared settings, course facts or fabricated replacement modules.

Branch: `matty/q09-run-setup-handoff`. Initial base `d0a138f` incorporated the merged
L01 fix (PR #14); while working, main `21a972ca70b147c874f9ce15c879ce0095425b6f` also
merged Reimo's S01 (PR #15), and that prerequisite was integrated before testing.

| Requested work | Verified progress | Remaining acceptance gate |
|---|---|---|
| 1. A01/Q09 run setup | [Concrete proposal sent](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6257425665) to Nisha/Ved; runtime/artifact evidence rechecked and dated | Explicit affected-member agreement, validated actual token/template/context method and measured/authorized run inputs. No runnable configuration is claimed. |
| 2. Q13 course/platform confirmation | [Issue #16](https://github.com/ReymoT/data-center-agentic/issues/16) assigned to Nisha; Matty also asked directly for the official course requirements | Authoritative instructor/rubric facts and affected platform/access agreement. Internal dates are not course confirmation. |
| 3. PR #11 fix recheck | Strict context revalidation and both regression cases are present on merged main through PR #14; local tests and exact merged-head CI verified | Full L01 still needs K02, accepted projections/context/deployment inputs and a real authorized development episode. |
| 4. A03 checker approval | New actual S01/A03 consumer tests exercise all four development scenarios and 30-slot rejection progression; no synthetic approval is issued | Q01-Q04 agreement, substantive claim support and downstream/independent verification. Otherwise feasible proposals continue to return unresolved-rule errors. |
| 5. A02/A04 agent/gate | Actual S01 interface and its checker intake now verified; explicit prerequisite gaps recorded below | K02 retrieval, P02 real checked-A fallback, usable A01/Q09 configuration, agreed checker semantics and A04/runner trace integration. No placeholder implementation is supplied. |

## Runtime recheck and drift

The model remains `qwen3:8b`, GGUF Q4_K_M, full digest
`500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.
The local CLI/API now report Ollama 0.40.5, whereas the original installation record
reported 0.40.3. The rendered default-parameter text hash also differs. Model size,
quantization, license and template evidence match the original inventory. The
original comparison correctly failed on runtime and parameter-text hash differences.

[The dated inventory](../evidence/ollama-qwen3-8b-2026-10-18.json) preserves the
new observation. The old record and blob-integrity proof remain unchanged. No
automatic update/downgrade, service setting, model download or inference was performed
by this work. `ollama ps` was empty. Inventory observation does not accept a pin or
establish GPU offload/throughput. Python 3.12.14, LangGraph 1.2.14 and Pydantic 2.14.0
were observed in the existing candidate environment; locks were not changed.

The full Q09 proposal is in issue #6, following the instruction to propose unaccepted
settings in Issues. It asks about runtime/transport, matched seeds, existing F02
projections, a validated token/context policy and a bounded compatibility/warm-up
plan. No proposed number is applied to the shared configuration or presented as a
measured safe threshold. All .env/config placeholders remain unchanged.

## Actual consumer checks

[Twelve new intake cases](../../tests/verification/test_s01_checker_intake.py)
call Reimo's real SchedulingSimulator and Matty's real check_schedule. They use
D03-generated synthetic development episodes through the existing test fixture,
never held-out fixtures or a fabricated passing checker. Both explicit constructor
choices for completion starts are tested; neither is adopted as the Q01 rule.

Across four scenarios, actual visible states retain arrived-job visibility and
authoritative projected constraints. Feasible-looking proposals still receive the
actual unresolved Q02/Q03 error, cannot create ApprovedActions, and cannot bypass
S01 by passing a raw Plan. Every rejected slot advances once, all 30 slot records
remain, and unfinished jobs stay accounted for. Future private jobs are unknown to
the actual policy view. Impact totals stay unset because S02/P01 are not provided.
These tests are rejection-path compatibility evidence, not an A04 runtime gate,
successful approved execution, a scientific experiment or a complete agent episode.

At the checked main revision, K02/P02/agent/runtime implementations are still absent
beyond package initializers. S01's actual state/step/Transition/history API is now
available, but the production checker cannot yet certify a successful action. A04
must later own serialized latest-state rechecks, authentic approval capability use,
idempotency and trace persistence; A02 must use actual retrieval and checked fallback.
Neither task is marked complete by a test-only helper or a mocked route.

## Verification and owner handoff

The merged PR #14 head `d0a138f591cadfd3dc035926967645623822d9f7` passed 760 tests
and 19 subtests locally and in [exact-head main CI](https://github.com/ReymoT/data-center-agentic/actions/runs/39182764757).
That satisfies the requested recheck; the historical candidate handoff's earlier
unmerged status is superseded by this verified merge record.

Current local verification passed 801 tests and 19 subtests, including twelve new
actual S01/A03 intake cases. Lint/format (47 Python files), compilation, setup,
pip consistency and whitespace passed. The new inventory comparison matched a
fresh read. SVG/PNG were regenerated and visually inspected. The published commit
and exact-head hosted CI are linked from issues #6/#7/#12. README, architecture text/SVG/PNG,
hardware/setup guidance and the dated inventory reflect the implemented components
and runtime drift. F02 schema/interface bytes, all teammate code/manifests, shared
prompts/settings, dependency locks, instruction rules, source attachments and task
allocations remain preserved. Instruction deployment remains 1.10.

Reproduction:

```powershell
.venv\Scripts\python.exe scripts/inspect_ollama.py --compare docs/evidence/ollama-qwen3-8b-2026-10-18.json
.venv\Scripts\python.exe -m pytest tests/verification/test_s01_checker_intake.py -q
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
.venv\Scripts\python.exe -m pip check
git diff --check
```

Next evidence needed: Nisha/Ved reply to the Q09 proposal; Nisha/Matty supply official
Q13 course facts; all affected owners agree Q01-Q04 in issue #7; Ved supplies K02 and
Edison P02. [D06/source follow-up #13](https://github.com/ReymoT/data-center-agentic/issues/13)
still requests source evidence. Sending requests, publishing a proposal and passing
tests do not establish consent, receiving-member adoption or completed full tasks.
