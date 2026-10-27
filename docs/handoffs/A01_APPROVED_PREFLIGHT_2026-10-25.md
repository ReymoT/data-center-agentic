# A01: approved validation stopped before native dispatch

Later October 25 actual result: the same unused authorization was resumed after
the internal metadata fix. One plain request timed out at its 120-second cap;
Plan was not called and no model retry occurred. [Actual evidence and next
action](A01_NATIVE_TIMEOUT_2026-10-25.md). The earlier preparation/preflight status
below is historical where superseded; no fresh approval was needed before the
first actual request because the earlier preflight dispatched zero requests.

Matty separately approved the prepared bounded two-call validation. [The actual
authorization](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6401913520)
records the user's reply and the reviewed launcher/driver hashes. It permits at
most two serial local requests, 120 seconds each and 300 seconds total, with no
retry, warmup, tools, simulator execution or study run.

## Actual result

One isolated runtime launch reached metadata preflight at 19:08:47 UTC on October
25. Runtime 0.40.5, the complete model digest and template matched the accepted
record. The displayed parameter-text hash did not match, so the launcher stopped
before starting the native validation driver. There were zero model requests,
zero native responses and no retry. This is not a failed generation attempt or
successful counter validation. The two requested paths were not exercised.

The listener belonged to the started child, PID 8888. Its executable identity was
checked before stopping it; the final record confirms stopped=true. Port 11435
has no remaining listener. The active desktop service/store was not changed.
Startup CPU discovery is not inference performance or context/resource acceptance.

Expected parameter-text SHA256:
`b486bc5b19b3a10c136f738b4105a741fa4d3384d7cccadff0a694a994d86545`.
Observed parameter-text SHA256:
`8ac335de6a31449a7839e1e0b00663f2adaca4f9c24a40b596a86740a9a97157`.
The earlier successful metadata match remains a valid dated observation; it did
not establish stable rendering order across launches.

[The evidence record](../evidence/a01-approved-preflight-2026-10-25.json) retains
the inventories, stopped-process facts and offline reconstruction. Full local
launcher logs and original observations are preserved outside Git. No raw model
response is invented, and no binary, model weight or private path is published.

## Explained display difference, not measured effective settings

The verified 120-byte parameter blob has SHA256
`cff3f395ef3756ab63e58b0ad1b32bb6f802905cae1472e6a12034e4246fbbdb`.
It contains these model defaults:

- repeat_penalty: 1
- stop, in order: `<|im_start|>`, `<|im_end|>`
- temperature: 0.6
- top_k: 20
- top_p: 0.95

These are stored defaults, not the accepted per-request temperature 0.2/top_p 1
or proof of effective generation settings. The request overrides were never sent.

Offline analysis formatted those same values exactly as the versioned source
does, then enumerated all 120 orders of the five key groups, keeping the two stop
entries in their original order. It reproduced both complete recorded SHA256
values. The accepted hash uses stop/temperature/top_k/top_p/repeat_penalty;
the preflight hash uses top_p/repeat_penalty/stop/temperature/top_k. The evidence
labels these strings as reconstructed hash preimages, not captured raw responses.

[Ollama 0.40.5 source](https://raw.githubusercontent.com/ollama/ollama/v0.40.5/server/routes.go)
formats parameter groups while iterating the model options map, then joins them
without sorting. The [Go specification](https://go.dev/ref/spec#For_range) does
not guarantee map traversal order. Together with the exact hash reconstruction,
this explains this display-order difference. It does not establish equivalence
of different runtimes or prove native settings, context, counters or resources.

## Verified internal correction, no new shared settings decision

Under Matty's coder-owned rule, this is an internal metadata-comparison bug fix.
It does not change a shared format, runtime, artifact, parameter value or scientific
rule. Nisha/Ved are informed consumers, not a new approval gate for the fix.

The comparator now accepts a display-order difference only when both inventories
have the exact accepted 0.40.5 runtime, full model digest and template, and both
raw parameter hashes belong to the 120 exact group orders of the verified pinned
defaults. The stop list's two values remain in order. Unknown reference hashes,
changed types/values, missing/extra/duplicate groups and unsupported formatting
still fail. Other artifacts retain exact raw-hash comparisons. All other identity
checks remain unchanged; no raw hash or inventory field is replaced or added.

An offline regression confirms the original comparator rejects the retained real
preflight, while the correction accepts the identical pinned values in their
supported display order. All 120 group orders and seven malformed/changed-default
cases are covered, along with runtime/model/template scoping, unknown reference
hashes, other identity drift and preservation of both originals. The focused
inventory suite passes 21 tests. One ordinary full suite passes 1,259 tests and
19 subtests in 16.26 seconds. These are offline tests, not model calls.

The original approved launcher, stopped run and logs are preserved. A fresh-output
conditional launcher is prepared outside Git using the corrected comparator;
its syntax and offline comparison are checked, and the real request hashes and
candidate counts are unchanged. It has not been started. No inference retry or
second runtime launch occurs in this increment. New launcher/driver hashes are
recorded in the evidence for a fresh bounded run approval.

Full A01 remains open for actual native count equivalence, effective settings,
context/resources and remaining acceptance. The old two-call authorization was
received and honored by stopping at preflight; it is not described as missing.
All task ownership, F02, locks, prompts, model pins, instruction 1.27 and original
ratings remain unchanged. No mandatory teammate review is introduced.
