# October 24: approved issue intake and bounded A01 evidence

Owner MattyAnd; technical contacts remain the canonical task owners. Matty explicitly
approved all audit recommendations, then A01 and F04/F05, followed by E05/P02 review
only when actual deliverables arrive. [Issue #54](https://github.com/ReymoT/data-center-agentic/issues/54) records the plan
before measurement. Base 2df8e2d1da19277089e4824c486a386d1b4fe889, instruction 1.23;
this authorized status publication advances instruction deployment to 1.24.

## Received replies and actual actions

| Issue | Received input and Matty action | Remaining gate |
|---|---|---|
| #6 | Ved official-tokenizer direction received; coordinate request-path tests with Nisha while Matty retains A01 | New runtime direction and actual validation; no accepted counter or inference |
| #7 | Ved boundaries/Q08 reply received; Matty supports feasibility certification separate from policy objective | Reimo exact simulator boundary and affected-consumer Q08 agreement/tests |
| #22 | Nisha exact sampling refinement received, synthetic selection PR October 30 | Explicit impossible-arrival eligibility decision if B adopted; implementation/rubric/originals/freeze |
| #24 | Nisha E01 PR October 27 received; current completed_work=None and optional precision deferred | Agreed-portion implementation and real-output acceptance |
| #36 | Nisha scoring alternative received; Matty conditionally supports review | Reimo/Ved agreement and tests; strict helper unchanged |
| #12 | Nisha 11-state K02/L01 receiving result on 2df8e2d received | Validated A01/runtime and actual authorized development episode |
| #21 | Ved allocation confirmation received; ask only Reimo | Reimo canonical allocation confirmation |
| #13 | Ved completed structure/window and remaining source gates received | Reimo source/freeze/regeneration artifacts and dated checkpoint; no rerun |
| #16 | Existing Nisha/Edison positions retained; targeted Reimo/Ved request only | Actual source/course permissions and remaining positions; no repeated unpublished-rubric request |
| #17/#18 | K02/S02 receiving inputs available | Usable A01/P02, agreed A03, controller/runner and real development integration |
| #42 | Matty original preserved; Nisha original due October 24 | Both originals before human adjudication; no replacement judgments |

Approved comments are linked in the corresponding Issues. The new [runtime finding](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6386512132)
requests direction on 0.40.10, not a pin change. No other owner's implementation or
assignment is claimed. The savings/scalar/sampling alternatives are not silently adopted.

## Fixed TCP-state measurement

Exactly four serial observations: original close, wait for client, wait for client,
original close. Replay the prior six-pair report's exact HTTP bytes, request and
unchanged native binary with the unchanged ten-second raw client. One read-only
netstat snapshot per observation is scheduled at 250 ms; retain errors and all outcomes.
No replacement or extra observations. [Full report](../evidence/a01-tcp-states-2026-10-24.json).

All four received the complete 24,001-byte body in 0 to 32 ms. Each client returned
before its snapshot (actual snapshot start 250 ms). Original-close snapshots show
only the helper listener; wait snapshots also show client TIME_WAIT. No stalled
connection was captured. This does not diagnose the missing tail, prove delivery
reliability or establish a fix. netstat instrumentation can perturb timing; it is
not packet or send/receive-queue evidence. Earlier five-of-six original-close
timeouts and all older provider/curl failures remain valid retained observations.

Reproduction on Windows with the optional existing isolated native helper:

```powershell
.venv\Scripts\python.exe scripts/diagnose_a01_tcp_states.py --reference docs/evidence/a01-six-close-pairs-2026-10-23.json --native-server '<explicit-local-native-reference>' --out ../new-tcp-state-report.json
```

The runner refuses an existing output, hash-checks binary/request/wire identities,
records partial results on errors, and exports only its loopback endpoints. Native
binary/compiler remain outside Git. No new application dependency; no change to
the original observer/client/provider/test/native helper or production transport.

## Runtime, service and offline readiness

[Read-only inventory](../evidence/ollama-qwen3-8b-2026-10-24.json) reports **0.40.10**,
not accepted **0.40.5** or the October 22 observation 0.40.9. Model digest and template hash match October 22; the parameter-text hash differs.
Old parameter hash: `d6b2700710ae824c6690a7b47383ea3836790cb59d52dc3018ad7b5530faf124`.
New parameter hash: `316504eda9b907ddeaf5403f02da3b12d13e998162db42cbb917a1e095cf731a`.
The original notice incorrectly said the parameter hashes matched; its correction
is retained in the linked comment. A text-hash change does not establish which
effective generation settings changed. Runtime/effective-setting equivalence
remains unvalidated. [Process/resource evidence](../evidence/a01-service-resources-2026-10-24.json)
records the 127.0.0.1 listener, executable hash, no matching SCM service, CPU/RAM
and reported Intel Arc driver. No service/update/startup configuration was changed
or inferred. Reported AdapterRAM is not validated dedicated VRAM/GPU offload.

[Offline preparation](../evidence/q09-probe-preparation-2026-10-24.json) retains both
public development request shapes/hashes and explicit blocked status. It is not a
model driver, actual agent execution, production tokenizer or context validation.
No model load/call, native token comparison, effective generation settings or
complete resource acceptance is claimed. The candidate dependency requires actual
validated integration; native probe authorization remains separate.

## Verification and handoff limits

The single serial local full suite passed **1,137 tests and 19 subtests in 10.04s**.
No rerun was needed and no earlier failure is erased. Ruff lint/format (91 Python
files), compileall, pip consistency, setup/versions/links/exact policies and
whitespace checks pass. The dependency smoke initially hit a sandbox temporary-file
PermissionError; it passed after using an explicit workspace temporary directory,
without changing project code/settings. SHACL/SPARQL, tiny MILP, both classifier
fit/save/load checks and the bounded LangGraph route pass. The four diagnostic observations are measurements, not
four new unit tests. Exactly 242 other tracked files remain byte-identical.
Exact PR/main CI and verified merged-head branch cleanup are recorded in issue #54
after execution. The final notice gives the published main SHA and actual CI runs.
All 50 task rows, exact authority/merge/cleanup rules, original E05 ratings, F02,
prompts, locks, scientific settings and production/tests stay unchanged.

No E05 original or P02 delivery exists at the initial/final pre-publication check.
Nisha checkpoint is today October 24; Edison P02 tomorrow October 25. Review only
actual deliverables; no fake adjudication or implementation. Full substantive
issues remain open. No continuous monitor, presentation work or deferred Frontier
follow-up is created. Next shared-decision and implementation gates remain explicit.
