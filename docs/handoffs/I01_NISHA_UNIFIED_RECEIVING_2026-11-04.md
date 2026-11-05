# Nisha's unified public-run receiving

Matty received Nisha's report and verifier output directly in the project chat.
Her decision is **PASS for evidence receiving**, with a high-priority structured
plan finding that must be addressed before prompt/schema freeze. Matty accepts
that scoped receiving result, not scheduling quality or final scientific acceptance.

- [Original report](../evidence/I01_NISHA_UNIFIED_REPORT_2026-11-04.txt), raw SHA-256
  `351d89b7c8a03653083a69df457c819e28733f5bf19c5a9830de621531ae4c0d`.
- [Supplied verifier output](../evidence/I01_NISHA_UNIFIED_VERIFIER_2026-11-04.txt),
  raw SHA-256 `3a82a9004118a3f24c3beb7750ec121a168e91cdbf11c49fe76bc1675f7f30d0`.
- Run `RUN-e670485639c9`; package SHA-256
  `5e74b38470843d21b0b5fa30fa2f40d82e0514e396411c6dac8c9ba8e29d4bf9`.

Nisha reports all package/reference checks, six identities/180 traces, zero replay
findings/result mismatches, 17 matching request/response hashes and counts, token
agreement and Arc/Vulkan identity/offload checks. Her verifier output matches the
hash in her report. Her separate review script, its JSON output and initial
timestamp-comparison failure were not supplied; their hashes are attestations,
not additional files independently inspected by Matty. She disclosed correcting
that reviewer timestamp comparison and rerunning it, without rerunning the model.

The report discloses assistant help, historical-cleanup observation limits, the
chat-approval authentication limit, and temporary storage in synced Downloads.
The 150/480-second controls are in the bound configuration/summary, not explicit
fields of the approved receipt's outer-controls object. Her highest Agent timing
is summed request latency, not independent observation of wall-clock enforcement.
No stronger receiving claim is inferred. E01 is her implementation, independent
of production checks, not a newly separate third validator.

## Confirmed structured-plan finding and offline fix

Matty read the actual original raw responses, not just parsed F02 objects:
all 13 plan responses (5 Plain plus 8 Agent proposal/repair) omitted `starts`,
`deferrals` and `abstentions`. F02 supplies empty defaults when parsing them.
Plain started no jobs; Agent's actions came from checked Greedy A fallback.
The omission pattern is established; optional grammar fields are a plausible
contributing cause, not proven to be the model's sole reason for choosing no actions.

The request-local grammar now requires those three arrays in both Plain and
Agent plans. Plain's successful output must contain a non-null plan. The provider
also checks the original JSON before F02 defaulting; omissions/null or wrong-shaped
arrays become retained, spent failed responses with no retry. Explicit empty arrays
remain legal. No job is forced into a plan, nor is feasibility or faithfulness
manufactured. F02, prompts, generation settings, checker rules and old records stay
unchanged. Offline regressions cover required fields, valid explicit empty actions,
missing fields/non-null plan and retained one-attempt failures on both paths.

This removes the demonstrated silent-defaulting path; it does not demonstrate
better live scheduling. Any new inference needs a new exact single-use candidate,
fresh bounded approval and its own retained success/failure and receiving result.
Do not freeze the old schema or infer Agent superiority from this fallback exercise.
