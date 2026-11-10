# Corrected claim-pairing candidate: public validation result

Matty explicitly authorized one run of RUN-cb85f5a3425c under single-use ID claim-pairing-cb85f5a3425c-20261109. Candidate, readiness and launcher hashes matched the reviewed packet. All 80 execution pins matched; code commit 6ed0fd30a2e139f0eb2c23fffdac258a2f3e12b0 is included in checkout 44c889735d43f5aabcabdb0bd789d8b3f5ce5286, whose exact main CI was green before dispatch. The ID was unused and output folder absent. The launcher consumed the ID before runtime startup; it cannot be used again.

## Technical result

The approved public EP-HAND1 validation passed: six complete system results, 180 distinct decision records and 17 model requests (Plain 5, Agent 12), in 532.219 seconds. The longest request took 53.513 seconds. The 150-second request, 480-second Agent-decision and 3900-second overall limits remained unchanged; no retries or warmups occurred.

All 17 responses passed the existing F02 contract and finished normally. All 17 native prompt counts match the independent postrun offline tokenizer counts. Every request used the reviewed 4096-token output allowance and 16384-token context, and each prompt remained under the 12288-token ceiling. Runtime/model/template checks passed, and Intel Arc 140V/Vulkan with full 37/37 layer offload was recorded. Cleanup confirms the owned process exited, no listener remained and the overall deadline was not exceeded. Port 11439 was independently rechecked free afterward, without restarting the model.

The existing independent E01 replay/structural comparison was rerun by the manager on all six saved results: zero findings and zero result mismatches. This is an independent implementation check, not a separate person's receiving sign-off.

## What the saved outputs show

There are 39 generated explanation claims: 20 Plain and 19 Agent. All explicitly supply a numeric value and an allowed unit, with zero one-sided pairs. The null/null branch was not generated in this run; its coverage remains supplied converter/synthetic evidence rather than a native sampling observation. Valid pairing establishes structure, not whether a number is correct, cited faithfully or scientifically supported.

All five Plain and five Agent explanations were inventoried. No summary, claim text or limitation reached or exceeded the 256-character cap. This is one small public episode, not a matched experiment estimating cap/completeness improvement. No new human labels were assigned and no old rating was changed.

A/B/C/D and Agent completed J1/J2 and missed J3. Plain completed no jobs. The Agent started J1 at slot 0 through checked Greedy-A fallback, and J2 at slot 3 from its initial model plan. Both recorded repairs (slots 0 and 4) failed their checks; fallback was checked separately. The run must not be presented as the model alone solving both jobs.

Execution checks still record the trusted-decision-UTC limitation for freshness, with impact-claim support unsupported. A successful physical/structural replay does not resolve source semantics, freshness evidence, causal savings or CF60 compatibility.

## Evidence and remaining gates

The [sanitized saved-data audit](../evidence/a01-paired-claim-validation-2026-11-09.json) retains hashes, timing, request accounting, numeric-pair and length counts, stage origins, replay and cleanup. The 390 private run files were hashed after completion; raw requests/responses, logs, exact authorization and results remain outside Git. Earlier failed runs, including RUN-bc420d3e8d72, are unchanged and are not replaced by this success.

The scoped technical pairing-validation gate is passed for the request shapes exercised here. Separate-person receiving and explanation-content assessment for this run are not yet recorded. Shared/default setting adoption, complete I01, source/custody/CF60 acceptance and I02 scientific freeze remain separate unresolved gates. Issue #185 stays open for that receiving/assessment and the adoption decision; no held-out research conclusion follows. No source ingestion, solver, training or held-out run was performed. No further model calls are authorized.
