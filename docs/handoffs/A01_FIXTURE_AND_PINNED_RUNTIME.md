# A01: fixture lifecycle correction and accepted-runtime preparation

Later October 25 result: Matty separately approved the bounded validation. Its
preflight stopped before either request on a displayed parameter-text hash mismatch;
the owned child is stopped and zero model calls occurred. [Actual result and strict
guard proposal](A01_APPROVED_PREFLIGHT_2026-10-25.md). Preparation statements below
are the earlier observation, not proof of stable parameter display ordering.

Matty explicitly requested A01 completion and tagging the next owners. [The team
priority notice](https://github.com/ReymoT/data-center-agentic/issues/18#issuecomment-6401393637)
tags Nisha, Ved, Reimo and Edison with their next tasks and parallel dependencies.
Work starts at main 95c4db4, instruction 1.27/F02 unchanged. This handoff distinguishes
verified fixture/runtime preparation from native inference validation still pending.

## Corrected synthetic server, unchanged production failure handling

The retained original-close failures occur outside the provider/parser too: the
native/curl controls sometimes receive only 23,360 of 24,001 bytes. They are preserved
in the earlier lifecycle/six-pair evidence. They do not establish an exact OS or
driver cause. A new write-shutdown-then-drain candidate also failed one unchanged
object-plain test; its 1-failed/105-passed log is retained, not published as a fix.

The adopted test fixture is Content-Length framed. It now waits for client EOF
before write shutdown and handle disposal, with a ten-second total drain bound.
This makes the test client's completion/closure initiate teardown; it does not
assume a completed send proves delivery. No sleep, retry, protocol switch,
response/request mutation, xfail/skip or weaker expected error is introduced.

[Microsoft's shutdown guidance](https://learn.microsoft.com/en-us/windows/win32/winsock/graceful-shutdown-linger-options-and-socket-closure-2)
distinguishes graceful teardown from handle closure and describes a client-first
shutdown exchange. The [drain discussion](https://learn.microsoft.com/en-us/windows/win32/winsock/using-so-reuseaddr-and-so-exclusiveaddruse)
explains why waiting for peer EOF matters. This informs the bounded synthetic
fixture; it is not a claim to have repaired Windows, a driver or every early-FIN peer.

All 25 original provider test function sources, decorators, malformed bodies,
deadlines and assertions are unchanged. Only the fixture server class/import
changes. Production provider/schema/counter/pins remain unchanged. New real-socket
tests verify client-first ordering, an actual bounded undrained peer, and deliberate
HTTP/1.0/1.1 truncation. Truncation still retains the exact partial bytes, status,
request ID, unknown usage, one spent uncertain attempt and no second plain dispatch.

Actual validation:

- 106 focused provider/plain/agent/lifecycle/receiving cases pass in 10.16s.
- One ordinary complete suite passes 1,244 tests and 19 subtests in 15.24s.
- Six fixed trials of all four original deep cases pass: 24 case executions, with
  every trial retained. These are repeated original cases, not 24 new unit tests
  and not retry-until-green observations. Per-trial times 0.21-0.25s.

Earlier failures remain in the record. The first rejected candidate and original
early-close peers are not relabeled successful. New tests add four unique cases.

## Isolated already-accepted runtime, zero inference

The official [Ollama v0.40.5 release](https://github.com/ollama/ollama/releases/tag/v0.40.5)
was downloaded outside Git, with its 1,471,226,485-byte archive verified against
release SHA256 5134ce7e3bc8e94d0494721c799ec293b429450d0c52461b0ee3647dd3bb4bb7.
The isolated executable hashes to ec9f3325f134597c7188b735dcc4e79a9eca4bf53f6b958ddf22aa04bf5ce57a.
All six actual model/config/template/license/parameter/original-manifest blobs
were copied and size/SHA256-verified into an isolated store; nothing was linked to
or modified in the active model store. Binary/model copies stay outside Git.

The first attempt copied the current storage wrapper as the model tag and correctly
failed the accepted digest/parameter comparison. That result is retained. The
isolated tag was then restored from the real 859-byte original manifest blob whose
SHA256 is the already-accepted 500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41.
No digest was overridden or expected value changed. The wrapper backup remains
outside the isolated model registry, and the active global manifest is unchanged.

Metadata-only launch on isolated loopback 11435 verified that the listener belonged
to the owned hidden child. Runtime 0.40.5, model digest, template and parameter-text
hash all exactly match the accepted October 18 inventory. Child-only serial/max
loaded-model settings were 1/1; no model was loaded. The owned process was stopped.
The active 0.40.11 desktop service and its manifest were independently rechecked
unchanged. No upgrade/downgrade, persistent environment setting or inference occurred.

Startup discovery selected CPU and reported no usable offloaded GPU in this
configuration. This is not measured inference throughput, context memory usage
or GPU acceptance. Requested generation settings remain unverified by inference.
Actual metadata/identity evidence is in [the readiness record](../evidence/a01-pinned-runtime-readiness-2026-10-25.json).

## Concrete next validation, separately authorized

The real plain-policy request and shared-provider Plan compatibility request have
been prepared offline again. Both request hashes match the current actual captured
paths. Seventeen actual Go-template vectors and four provider request shapes still
match the pinned Python renderer; isolated tokenizers 0.23.3 produces candidate
counts 2,291 plain and 2,003 Plan. They are not Ollama native counts or an adopted
production counter. No Go compiler or tokenizer dependency is added to the app.

Local preparation retains the exact request bodies, hashes, candidate IDs/counts,
official-runtime assets and a conditional launcher/validation driver outside Git.
The driver defaults to offline preparation; its native branch has not run. Its
authorization reference must record real Matty approval, never invented approval.

The existing [Q09 agreement](../decisions/Q09_DEPLOYMENT_OCT20.md) requires explicit
bounded inference authorization before dispatch. Proposed validation is precisely:

- At most two serial calls on the public synthetic hand example, seed 101, no warmup.
- Actual PlainLLMPolicy.propose first, then the shared provider's Plan API; no
  simulator execution, tools, agent episode, study/held-out/cloud/paid run.
- Accepted 0.40.5/model/template/parameters, temperature 0.2/top_p 1, num_ctx 16384,
  num_predict 1536, stream=false/think=false/keep_alive 30m.
- Existing caps: 120s per call, 300s total, 2MiB response, no retry. Stop on failure,
  uncertain outcome or candidate/native-count discrepancy; retain all raw evidence.
- One actual shared ledger; failures stay spent. Metadata identity checked before
  and after; the owned isolated process is stopped afterward.

Native prompt_eval_count equivalence, actual effective settings/context/resources
and any remaining acceptance must be determined from real evidence. The validation
does not automatically adopt a counter or complete every A01 gate. Until actual
separate approval and measured results, #6 remains open and model calls remain 0.

Instruction 1.27, all task owners, exact merge/main-authority rules, F02, shared
locks/prompts/pins, independent evaluator and Matty's original ratings are preserved.
PR #64 still needs Nisha replay and Ved reproduction. No other member's task is
claimed complete by this A01 increment. Exact PR/main CI and merged-branch cleanup
are recorded after execution, independently of the local checks above.
