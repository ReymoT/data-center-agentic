# A01: actual approved request reached its deadline

Matty approved at most two serial local requests with 120 seconds per request,
300 seconds total, no model retries, warmup, tools, simulator or study execution.
[The actual approval](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6401913520)
is the authorization for this development validation.

The first metadata-only preflight sent zero model requests. After the internal
display-order fix was verified and merged in PR #79, the same unused two-request
authorization was resumed. No new user approval was invented or needed for the
unchanged request bodies, settings and bounds. Earlier preparation language about
needing another approval was too restrictive: no model attempt had yet occurred.
The stopped preflight and original hashes/logs remain preserved.

## Actual result, not successful validation

Exactly one plain request went through the real PlainLLMPolicy and shared provider
on the public synthetic development example, seed 101. Its request SHA256 is the
reviewed `264630e066a9bc96f9cee6b0666e30168154d622cff7d35cbf3c75f0a3b42b90`.
It used accepted runtime 0.40.5/model/template/default values and the requested
temperature 0.2, top_p 1, context 16384 and generation cap 1536.

The request timed out at 119,993.66 milliseconds. No response body or HTTP status
was returned. The real ledger retains one spent attempt with uncertain_outcome=true,
error="timed out", unknown prompt/completion counts and no parsed output. An empty
raw response is retained as empty bytes, not replaced with generated content.

The driver stopped after that failure. The Plan request was not sent; there was
no model retry or warmup. The unused second-call allowance is not permission to
continue after this failed inference. This is one bounded development timeout,
not an experiment result, plain-versus-agent comparison or successful A01 run.

[Actual evidence](../evidence/a01-native-timeout-2026-10-25.json) includes the attempt,
request hash/settings, before/after inventory, measured resource subset and cleanup.
Full raw report and runtime logs remain outside Git. No private paths or binaries
are published. Both inventories compare under the strict accepted-value guard;
their original raw parameter hashes remain unchanged in each dated record.

## What was measured

Read-only runtime metadata reported the real model loaded on CPU, size_vram=0 and
context_length=16384. Runtime sampler logs showed temperature 0.200 and top_p 1.000;
the serial/max-loaded process settings were 1/1. These are observed subsets,
not proof of every effective setting or a passed native validation.

One runner sample measured 7,923,953,664 working-set bytes and 8,056,528,896 private
bytes, with 4,789,124 KiB free physical memory. These are individual observations,
not peak memory, GPU requirements or a performance benchmark. Runtime logs show
2291 prompt tokens and generation in progress before cancellation. That runner
count is distinct from the missing API prompt_eval_count; no native API usage
or full candidate/native equivalence is inferred from it.

The server stopped after the failed request. Its runner remained alive, so cleanup
verified the recorded runner PID 6444, parent PID 20492 and exact executable before
stopping only that owned process. The final proof records no remaining owned
server/runner/console process and no listener on 11435. The active desktop 0.40.11
service and original model manifest were not modified.

## Next action and acceptance boundary

Matty owns resolving this run-environment constraint. Recommended next step is a
more capable agreed host while preserving the accepted model, settings and budgets
for both systems. Nisha/Ved are the directly affected provider/evaluation consumers.
Ask for an available host and concrete resource/blocker evidence; do not create
another approval gate for ordinary internal code decisions.

Do not silently extend the deadline, shrink context, change the model, enable a
different acceleration configuration, retry until success or replace the failed
case. Any changed shared run setting needs affected-owner agreement and documented
evidence. Another inference run needs a new bounded authorization after the actual
timeout; none is implied by reporting this result.

Full A01 remains open: native count equivalence, complete effective settings,
context/resource acceptance and remaining receiving evidence are not established.
The internal display-order fix and offline tests remain verified separately.
No schema, lock, scientific rule, original rating, task ownership or instruction
deployment changes in this report.
