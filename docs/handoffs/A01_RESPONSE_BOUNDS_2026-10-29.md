# A01 offline response bounds

Owner: Matty Anderson (`MattyAnd`). Technical contact: Nisha Mahadev Kolekar.
Issue: [#6](https://github.com/ReymoT/data-center-agentic/issues/6).
Base: main `6e2dc75c91f1f414f008489d12fbfbfbc8ec7922`, instruction 1.28.

## Delivered offline behavior

`dc_sustainability/llm/response_bounds.py` builds one request-local JSON schema for
Plain `PolicyOutput` and Agent `Plan`/`Explanation`. It does not modify F02 records.
The limits use only the current `VisibleState` and fixed constants:

- each Plan action category permits one entry for every waiting job;
- job IDs, decision identity, proposed status and visible evidence IDs are restricted
  to the requesting state;
- Plain and Agent use the same four-claim, four-limitation, 96-character text and
  two-evidence-ID limits;
- Plain `raw_response` is null in the generated shape because the L01 caller retains
  the actual original response separately;
- the provider still accepts only `done_reason="stop"`; length stops, deadlines and
  malformed output remain failures with no retry or repair.

The policy layers retain the accepted empty-queue no-call behavior. The low-level
adapter defines a zero-entry grammar for an empty state so an exhausted run budget
cannot be bypassed by changing the queue.

## Offline measurement

The deterministic measurement in
`docs/evidence/a01-response-bounds-2026-10-29.json` uses the 20-job provisional
development spike and the hash-pinned Qwen3 tokenizer candidate. It starts no
Ollama process, loads no model and sends no request.

| Bounded shape | UTF-8 bytes | Candidate BPE tokens |
|---|---:|---:|
| Plain PolicyOutput | 5,590 | 1,264 |
| Agent Plan | 4,078 | 931 |
| Agent Explanation | 1,372 | 298 |

The largest measured valid shape is 1,264 tokens, leaving 272 tokens below the
accepted `num_predict=1536` ceiling. These are deterministic offline fixture counts,
not generated output or a successful live validation.

## Proposed deadline for affected-owner agreement

The retained October 28 log measured approximately 14.29 generated tokens/second
and about 16 seconds of cold-load plus prompt overhead before the 120-second cutoff.
At that measured rate, 1,264 tokens require approximately 88.5 seconds of generation;
adding the observed 16 seconds and a 30-second operating margin gives 134.5 seconds.

Recommendation: **150 seconds per request and 330 seconds for the two-request paired
validation**. The paired total allows two complete request ceilings plus 30 seconds
for before/after identity evidence and cleanup. This is a proposal, not an adopted
setting or run authorization. Nisha and Ved must agree to the numeric setting and
Matty must separately authorize any later inference.

## Verification

Focused offline suite, including real synthetic loopback HTTP but no Ollama/model:

```text
pytest tests/llm/test_response_bounds.py tests/llm/test_ollama_provider.py
       tests/llm/test_plain.py tests/agent/test_harness.py -q
106 passed
```

Ruff check and formatting pass for every changed Python file. Full repository tests,
setup validation, compilation and dependency checks also pass locally: 1,552 tests
and 19 subtests. The whole-tree Ruff format check separately reports two unchanged
documentation code blocks in `data/D02_CALIBRATION.md` and
`docs/handoffs/D04_DEVELOPMENT_FOLD_MAP_102.md`; changed-file formatting passes and
this A01 branch does not rewrite those teammate records. Exact hosted CI is recorded
with the PR rather than claimed before it runs.

## Remaining gates

- Directly affected owners agree to or replace the proposed 150/330-second deadlines.
- Matty records a fresh bounded authorization before any model request.
- A later live validation must preserve identity, effective settings, full Arc/Vulkan
  offload, native counts, raw outputs, stop reason and cleanup evidence.
- Successful paired output and experiment readiness remain unproved.
