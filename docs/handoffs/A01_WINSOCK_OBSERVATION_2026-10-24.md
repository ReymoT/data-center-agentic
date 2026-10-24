# A01: read-only Winsock observation of the original deep-response tests

Owner MattyAnd; issue [#6](https://github.com/ReymoT/data-center-agentic/issues/6).
Matty approved applying the current recommendations and finishing with A01
investigation. Base dea312c2b8556101c7a5e96fa0755b103086c07e, instruction 1.24
unchanged; branch matty/a01-winsock-observer. The [fixed plan](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6389041388)
was recorded before measurement, including omission of SO_ERROR to avoid consuming
socket error state. No original provider, test, fixture, payload, deadline or
assertion is changed. The observer is optional Windows-only tooling, not a new
application dependency or production transport.

## Apply each reviewed recommendation

| Issue | Actual disposition this turn |
|---|---|
| #6 A01 | Continue the independent observation below; actual runtime/counter/native/context validation and separate model-call authorization still required |
| #7 A03 | No new Reimo/affected-consumer replies; keep disputed rules blocked and existing exact requests in place, no duplicate reminder |
| #17 A04 | No new agreed approval/controller prerequisite; do not invent a gate or execution acceptance |
| #18 A02 | No new usable A01/P02/approved gate; retain actual K02/S02 handoffs without fake integration |
| #42 E05 | Matty original already submitted; no Nisha original at latest check, due today October 24; human comparison/adjudication waits |
| #36 P01/S02/P02 | Strict helper unchanged pending Reimo/Ved scoring response; no P02 delivery, checkpoint October 25 |
| #24 E01 | Await Nisha agreed-portion PR October 27; scalar precision stays deferred and completed_work=None |
| #22 Q10 | Await tested selection PR October 30; no silent primary-frame or freeze change |
| #13 source | Existing exact artifact/checkpoint request remains; no rerun of completed structural verification |
| #21 allocations | Only Reimo confirmation missing; existing request remains, no ownership change |
| #16 Q13 | Await targeted remaining positions/actual official requirements, not another request for the same unpublished answer |
| #12 L01 | Nisha receiving check is received; no new Matty action until validated A01 is available |

No new owner comments, open PRs or task branches were available at start. Check
again before final handoff; review actual E05/P02 artifacts if they arrive. No
teammate non-response is fabricated as agreement, and no continuous monitor or
premature overdue reminder is created. Instruction 1.24 is already current and
requires no new deployment for this diagnostic.

## New question and fixed method

The earlier 250 ms netstat snapshots occurred after complete transfers. This
observer instead queries the specific socket near actual read1, large sendall
and shutdown calls while four original parametrized tests run once. It reads
SIO_TCP_INFO version 0, linger, TCP_NODELAY and buffer values; it never sets
options, consumes body bytes separately, changes retries, or reads SO_ERROR.
All four original cases and all existing assertions remain intact.

[Microsoft's IOCTL contract](https://learn.microsoft.com/en-us/windows/win32/winsock/sio-tcp-info)
describes per-socket TCP statistics; [TCP_INFO_v0](https://learn.microsoft.com/en-us/windows/win32/api/mstcpip/ns-mstcpip-tcp_info_v0)
defines the fields. The [Microsoft header](https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/shared/mstcpip.h)
defines the control code. The observer verifies the 88-byte Windows layout and
BytesOut/BytesIn offsets 48/56, requests version DWORD zero, and records actual
returned size/API errors. These counters are not a packet trace or a guarantee
that the application received each byte. No privileged packet capture is used.

## Actual measurement and limits

[All results and events](../evidence/a01-winsock-2026-10-24.json) are retained.
Exactly four original cases passed in 0.22 seconds: array/object, agent/plain.
There were 60 events, 44 successful 88-byte TCP_INFO snapshots and no IOCTL errors.
Twelve subsequent snapshots retain WinError 10038 after their socket had closed;
four test-start events have no socket. These unavailable snapshots are not
silently discarded or reported as successful IOCTL calls.

All active-socket snapshots report linger disabled. The four server body-send
return snapshots show zero bytes in flight, retransmitted bytes and timeout
episodes. Both 8,001-byte array and 24,001-byte object bodies were retained in
full by the original assertions. No partial-body failure occurred, so the observer
did not capture the stalled condition and cannot establish its cause or a fix.
TCP BytesOut/In values are retained as reported and are not equated to HTTP body
lengths or used to infer the earlier missing-tail location. A successful write,
snapshot, close, or current test pass does not erase older failure evidence.

Instrumentation changes timing and may affect reproducibility. One machine,
four cases once; no replacement or extra diagnostic run. Earlier original-close
five-of-six timeouts, raw/curl failures and ordinary-suite failures stay retained.
No inference/model load, production counter, runtime pin adoption, effective
settings/context validation or experimental acceptance is established here.

## Reproduce and verify

```powershell
.venv\Scripts\python.exe scripts/diagnose_a01_winsock.py --out ../new-winsock-report.json
```

Use a new path; the tool refuses overwrite, restores wrappers in finally, records
outcomes and original source hashes, and preserves observations on exceptions.
Ordinary CI lints/compiles this optional tool but does not run it or call a model.
No Go compiler, new wheel, dependency lock or shared setting is introduced.

The single serial ordinary full suite retained **1,136 passes, 19 passing subtests
and one existing object-plain_llm timeout in 18.85s**. No repeat-until-green rerun
was performed. Its failure log remains outside Git; original assertions and the
uncertain failed attempt remain intact. Instrumented four-case success versus
ordinary-suite failure leaves observer timing/test order as limitations, not a
proven cause. Full A01 is not accepted.

Setup/versions/links/exact policies, Ruff lint/format (92 Python files), compile,
pip consistency and whitespace checks pass. Exactly 272 other tracked files,
all 50 task rows, original E05 ratings/F02/locks/prompts/pins/instruction 1.24 and
all seven worktrees are preserved. No production/test/shared-setting change.
Exact PR/main CI, merge SHA, handoff and verified branch deletion are recorded
in issue #6 after actual execution. Hosted green cannot erase local failures.
Full A01 and dependent substantive issues remain OPEN.
