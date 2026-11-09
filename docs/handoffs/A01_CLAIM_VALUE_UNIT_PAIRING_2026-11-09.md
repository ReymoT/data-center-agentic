# A01 claim value/unit pairing: offline fix

Owner: Matty (A01). Prepared November 9, 2026 from snapshot `3507f11cd45e2603efbe2ebaeccf506198b3f3f7`.
This is an offline change. No model request, runtime start, retry or replacement run is part of it.
The consumed authorization `explanation-bc420d3e8d72-20261109` and the failed run `RUN-bc420d3e8d72`
stay as recorded in [the validation outcome](A01_EXPLANATION_VALIDATION_OUTCOME_2026-11-09.md).

## Diagnosis

The run stopped at Agent slot 2 because three explanation claims carried a unit with a null value
(C1 and C3 `g/kWh`, C2 `slot`). F02 `Claim` rejects that, correctly. The request-local schema did not:
`dc_sustainability/llm/response_bounds.py` sent `value` and `unit` as two independent nullable fields,
because the pairing rule lives in a Pydantic model validator that is not part of the generated JSON schema.
Converting the old request schema with the pinned converter confirms it: the grammar accepts the observed
claim shape and every other one-sided combination.

## Fix

`bounded_response_schema` now replaces the request-local `Claim` with two complete object branches under
`anyOf`, for Plain (nested in `PolicyOutput`) and Agent (`Explanation`) alike:

- nonnumeric: `value` null and `unit` null;
- numeric: `value` a number and `unit` one of `kW`, `kWh`, `slot`, `h`, `g/kWh`, `kg`.

Both branches require the same five keys (`claim_id`, `text`, `evidence_ids`, `value`, `unit`). The converter
writes required keys before optional ones, so equal required sets keep one key order and the branch is chosen
only at the `value` token. Generation therefore writes explicit nulls and an explicit, possibly empty, evidence
list. The stored F02 contract is unchanged: omitted value/unit and omitted evidence remain valid F02 records.

Unchanged: F02, prompts and prompt hashes, Plan request schemas (byte-identical for both profiles), claim and
limitation counts, text lengths (96 legacy, 256 candidate), plan detail length 96, evidence limits, runtime,
model, temperature, token budgets, request/decision/run limits and the launcher. F02 validation of every parsed
response remains the final gate; a rejected response is still a spent, retained attempt with no retry.

## Converter evidence

Ollama 0.40.5 (tag commit `d919272e53593d1d55d40e1180eaa06dfbede3ac`) converts a `format` schema by calling
its bundled llama-server, built from llama.cpp `b11669` (commit `620d2225cc436ab0b001e3200e590e3b286ef9ab`),
which uses `json_schema_to_grammar`. Ollama's llama.cpp patch does not touch the converter. In that source:

- `anyOf` and `oneOf` become a grammar alternation (`oneOf` is not exclusive);
- a node with `anyOf` ignores its sibling keys, so each branch must be a complete object;
- `if`/`then`/`else`, `not`, `dependentRequired` and `dependentSchemas` are never read.

[The converter record](../evidence/a01-claim-pairing-grammar-2026-11-09.json) was produced by
`scripts/probe_a01_claim_grammar.py` with `scripts/a01_claim_grammar_probe.cpp` compiled against b11669.
For Agent and Plain at 96 and 256 characters, all synthetic cases matched the expected verdicts:
one-sided pairs, booleans, strings, unknown units, extra keys and count/length/evidence overruns are rejected;
numeric (including zero and negative) and null/null claims and empty claim lists are accepted. A control schema
using `if`/`then`, `dependentRequired` and `not` still accepted both one-sided pairs, so those keywords would
have been silently ineffective.

This is converter evidence with synthetic strings, not model output. It does not show sampling behaviour,
the installed Windows binary, prompt counts or timing.

To reproduce: build llama.cpp `b11669` with `-DLLAMA_BUILD_TESTS=ON -DLLAMA_CURL=OFF`, compile the probe
against `common`, `llama` and `ggml` from that build tree, then run
`python scripts/probe_a01_claim_grammar.py --probe PROBE --llama-cpp LLAMA_CPP_SOURCE --out NEW_FILE`.

## Tests

`tests/llm/test_claim_value_unit_pairing.py` checks the request schema separately from F02 with a small
checker for the keywords the converter reads, for both systems and both profiles. It also sends both
systems through the real provider entry point with synthetic HTTP: the request carries the paired schema,
a one-sided reply is a retained failed attempt with the original bytes and no retry, and a valid numeric
reply parses. Against the previous `response_bounds.py`, 34 of its 81 cases fail.
Existing tests were updated to read both Claim branches; the November 8 context research script still reads
the single-object Claim found in saved November 4 requests.

## Pins and remaining gates

Only one execution pin changes: `dc_sustainability/llm/response_bounds.py`. A new candidate, readiness and
launcher check must be prepared from the merged commit with the real C/D artifacts and tokenizer; the
`RUN-bc420d3e8d72` preparation must not be reused. Native grammar behaviour with the model, prompt-count
parity, timing and cleanup for this schema remain unvalidated until a fresh, exactly bounded authorization.

## Manager intake verification

The patch was applied against its stated base on the real Windows checkout. The 358 focused tests pass. The supplied converter result is retained as supplied evidence, not a newly reproduced Windows probe: no C++ compiler/probe build is available in this environment. GitHub's upstream tag refs and the three converter-source SHA256 values were independently checked and match the supplied record. Ollama's pinned LLAMA_CPP_VERSION is b11669. These are source checks, not installed-binary validation.

The manager hardened the optional probe helper: it now rejects mismatched converter source bytes before execution, fingerprints the supplied binary and explicitly records that its build/source binding is not independently attested. Individual subprocess probes have a 60-second timeout. Three regression cases verify that each source-file mismatch blocks execution. Original supplied converter evidence is unchanged.
