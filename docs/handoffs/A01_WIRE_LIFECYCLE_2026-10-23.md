# A01: exact-wire and connection-lifecycle investigation

Owner MattyAnd; [A01 issue #6](https://github.com/ReymoT/data-center-agentic/issues/6).
Matty approved the latest recommendations and continued independent transport diagnosis.
Base main e7bb7fc316164ef8742c9a54a746a2d725c72dc7, instruction 1.23 unchanged.
[Start record](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6375708333).

## What the fixed experiment found

The missing-tail failure now reproduces outside both OllamaProvider and Python's
HTTP server. A raw socket received only 23,360 of 24,001 body bytes from a native
Go server replaying the exact captured Python HTTP response. The matching Python
raw-socket original-close condition failed with the same body prefix and timeout.
The native wait-for-client-close condition received all 24,001 bytes using the
identical response bytes. Both native writes reported the complete header and body.

| Server/client | Close control | Body received | Result |
|---|---|---:|---|
| Original Python fixture / actual shared provider | Original close | 24,001 | Complete bytes; expected invalid nested-JSON response, one retained synthetic attempt |
| Original Python fixture / raw socket | Original close | 23,360 | Timeout; original 641-byte missing tail retained |
| Original Python fixture / actual shared provider | Wait for client close | 24,001 | Complete bytes; expected invalid nested-JSON response |
| Original Python fixture / raw socket | Wait for client close | 24,001 | Complete |
| Original Python fixture / actual shared provider | Half-close write then wait | 24,001 | Complete bytes; expected invalid nested-JSON response |
| Original Python fixture / raw socket | Half-close write then wait | 24,001 | Complete |
| Native Go / raw socket | Original close | 23,360 | Same timeout and prefix hash |
| Native Go / raw socket | Wait for client close | 24,001 | Complete; server observed client EOF |

Each condition ran once, serially, before other timing-sensitive checks. Complete
raw response length/hash is the transport outcome; the expected decoder error is
not a successful model response. All actual shared-provider observations retain one
synthetic transport attempt; none contacts Ollama. Existing test-only synthetic
counter and artifact identities are used only by the transport fixture, never
adopted as a real counter, runtime or model result.

[All measured observations](../evidence/a01-lifecycle-controls-2026-10-23.json) retain
write/close timestamps, chunks, request/body/wire/source/binary hashes and errors.
Source-text identities normalize CRLF to LF; wire/body/binary identities use raw bytes.
The report's first shared-provider, first Python raw-socket and both native responses
share the same 24,117-byte wire: 116 header bytes plus the 24,001-byte body.
Native replay therefore removes the differing-header confound in earlier controls.
The request body is the same 3,399-byte existing provider shape, SHA256
04ebdb9574c77c0b30678005bb99083b82769a245090da35423bcd7036f43e3d.
The failed body prefix remains
 d7adfc98bfb8099b9c6fd63d51e7220c9cf633bffcbac3a603c61e34e86697b6.

## What this does and does not establish

A cause confined to Python's HTTP server cannot explain the native failure. The
observed difference makes connection-close timing a concrete next diagnostic lead.
It does not prove an exact operating-system, driver, filter, buffering or protocol
cause. The original-close provider sample also completed, so this is not a
deterministic all-clients failure. Python Date headers differ in later observations;
only the stated four observations share the exact wire. Instrumentation changes
timing, native controls also change process/server implementation, and a single
observation per condition does not establish reliability or a fix.

No wait, half-close, linger, TCP_NODELAY, retry, deadline, payload, read-size or
protocol change is adopted in production or the original test fixture. The entire
provider and every original test file/helper remain byte-identical to base main.
Current shared dependencies, pins, prompts, schemas, budgets and original ratings
are unchanged. Go 1.27.3 was already isolated locally; this compile used offline
GOTOOLCHAIN=local/GOPROXY=off/GOSUMDB=off. The binary/cache stay outside Git and no
compiler dependency is introduced to the application or ordinary CI.

## Reproduction

Use fresh output paths. The CLI refuses overwriting any earlier observation.
The default is six Python/provider/raw-socket conditions. The optional native
reference adds two exactly captured-wire conditions:

```powershell
.venv\Scripts\python.exe scripts/diagnose_a01_lifecycle.py --out ../new-lifecycle-python.json
# Optional: build using an explicitly selected, already available local compiler.
& '<local-go>\go.exe' build -o ../a01-exact-wire-control.exe scripts/a01_exact_wire_control.go
.venv\Scripts\python.exe scripts/diagnose_a01_lifecycle.py --native-server ../a01-exact-wire-control.exe --out ../new-lifecycle-native.json
```

The eight-condition execution is measured evidence, not eight new unit tests.
After the matrix finished, the single serial ordinary full local suite passed
**1,137 tests and 19 subtests in 7.62 seconds**. Lint/format (89 Python files),
compile, pip consistency, setup/versions/links/policies and whitespace checks pass.
Exact PR/main CI is recorded in #6 after execution. No new unit-test count is claimed.
Successes do not erase the two new raw-socket failures or previous provider/curl
failures. No repeated-until-green matrix or model run is performed.

## Other approved issue actions and remaining gates

The fresh GitHub audit found no new teammate replies or open PRs. Existing targeted
requests remain in place; no duplicate pings, premature Nisha October 24 original-rating
reminder or Edison October 25 P02 reminder is sent. Matty's E05 original remains
submitted; adjudication waits for Nisha's original. S02 verification and instruction
1.23 publication are already complete; no repeat is claimed as new work.

Exact remaining Reimo/Ved Q01-Q04/Q08, Ved counter/current-runtime direction,
Nisha sampling/E01/receiving work, source/freeze and remaining allocation/platform
agreements still gate dependent acceptance. The strict unfinished-work guard stays
unchanged. The accepted runtime remains 0.40.5; no installed runtime is adopted from
a dated observation. Actual tokenizer/native/template/effective-setting/context/
service/resource evidence and separately authorized bounded inference remain gates.
Full A01, A03/A04/A02, integration and scientific evaluation are not complete.
Issue #6 must remain open. No unfinished issue is closed from diagnostic progress.
