# A01 explanation candidate: authorized validation outcome

Matty explicitly authorized single-use ID explanation-bc420d3e8d72-20261109 in chat on November 9. The run ID is RUN-bc420d3e8d72. Candidate, readiness and launcher hashes matched the reviewed packet; code commit 6325398ae88a9c87537771a8d2d027ec2aab7427 is an ancestor of checkout f4ec2561c23d866ce7dc2b214b6a6b313eb29d50, whose exact main CI passed before dispatch. All 80 execution pins matched, the output folder was absent and the ID unused. The launcher consumed that ID before startup. The original pending template remains unchanged. The completed checklist was read in the prior chat turn, but its original Downloads path was unavailable for archival at launch; the explicit chat authorization is the execution authority. No checklist copy is claimed.

## Outcome

The validation failed closed at Agent slot 2 during explanation generation. The HTTP response completed with done_reason=stop and no uncertain outcome, but three Claim records supplied units while their numeric values were null. F02 requires value and unit together. The existing contract rejected the response; it was preserved in emergency evidence. No retry or replacement run occurred, and the consumed ID cannot be reused.

The failure was recorded after 386.453 seconds (about 6 minutes 26 seconds), below the 3900-second maximum; cleanup separately confirms no overall deadline overrun. There were 12 requests: five Plain and seven Agent, including the rejected Agent explanation. Eleven responses passed the record contract; one failed. All 12 saved native prompt counts match the postrun offline tokenizer counts. The longest recorded request took 49.400 seconds, below the 150-second maximum. The 480-second Agent decision ceiling and other fixed controls were unchanged.

Ollama recorded Intel Arc 140V / Vulkan and full 37/37 layer offload. Cleanup confirms the owned process exited, no listener remained and the overall deadline was not exceeded. Port 11439 was independently rechecked free after the run. The model was not restarted for auditing.

## Saved-result audit

A, B, C, D and Plain each have one complete result and 30 decision records. Postrun audit used the existing independent E01 replay/structural comparison: zero findings and zero result mismatches for all five. A/B/C/D completed J1/J2 and missed J3; Plain completed no jobs. Agent has two saved decision records, no complete result and the separately retained failing attempt at slot 2. The partial Agent trace is not a full-episode replay pass. In total, 152 decision records were saved.

Five contract-valid Plain explanations, two contract-valid Agent explanations and one malformed Agent explanation were inventoried separately. No summary reached the 256-character cap and no inspected explanation text field exceeded it. This small early-stop sample does not establish completeness, supported claims or a cap improvement rate. No formal new faithfulness labels or human ratings were produced.

## Evidence and remaining work

The [sanitized saved-data audit](../evidence/a01-explanation-candidate-outcome-2026-11-09.json) records request counts, timing, native-count parity, result replay, cleanup and text lengths. Raw requests/responses, full results, runtime logs, the failure, file hashes and the authorization-consumption receipt remain outside Git. They were not modified to pass validation.

This supplies native execution/count/timing evidence for the request shapes actually exercised, but not a successful six-system validation. Grammar-shaped JSON does not enforce every cross-field F02 invariant: numeric value/unit consistency is the immediate failure to address in a separately pinned offline follow-up. Do not fill missing values from prose or weaken the contract to accept this response.

Issue #185 remains open. Candidate adoption, complete I01, scientific freeze and the research comparison are unresolved. Any changed schema/renderer must receive offline regression checks, new exact pins and fresh single-use authorization before another model call. Existing defaults, earlier outputs, ratings, C/D binaries, source/custody gates and task ownership are unchanged. No source ingestion, solver run, training or held-out execution was performed.
