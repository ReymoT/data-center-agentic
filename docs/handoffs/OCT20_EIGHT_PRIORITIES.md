# October 20: eight-priority maintenance and handoffs

Matty authorized all eight recommendations item by item. Base main: b06cda7f1018bbd935603a2ea0d460b21f6fdf81; task branch: matty/eight-priority-maintenance; instruction deployment 1.15. [F04 bug issue #27](https://github.com/ReymoT/data-center-agentic/issues/27) records the corrections before edits. Dates use the America/Phoenix project day; the new Nisha replies are dated October 21 UTC. This is a bounded maintenance/development increment, not completion of dependent teammate work.

| Item | Action taken | Exact remaining gate / receiving owner |
|---|---|---|
| 1. A01/F03 #6 | Instrumented the existing synthetic HTTP regression; added a reproducible diagnostic and metadata-only GGUF tokenizer inspection with malformed/truncated/limit tests. Developed a restricted real-BPE/Go-template counter candidate and recorded actual local tokenizer metadata and reference comparison. Accepted Nisha's runtime revalidation conditions in the Issue. | Matty: resolve the partial-body timeout and develop/validate the real runtime-specific rendered-prompt counter. Ved: agree 0.40.6 revalidation. Keep accepted 0.40.5 pin until agreed replacement evidence. Service settings/context evidence and explicit bounded inference authorization are still needed. |
| 2. F04 #27 | Corrected stale coordinator/publisher/transport/pin/seed text, synchronized all ten package headers/changelog, refreshed current Issue summaries and dated coordination record. | Publication checks and a refresh-main handoff; no new scientific or permission decision. F04 remains ongoing maintenance. |
| 3. Q01-Q04/A03 #7 | Reconciled current body with existing Reimo/Nisha/Ved/Matty replies and the specific outstanding Edison request. Preserved implementation gates. | Edison Q01-Q04 input; affected owners' joint-infeasibility/Q08 rule. Do not manufacture an overall approval or implement an unagreed rule. |
| 4. E01 #24 | Recorded [Nisha's receiving adoption](https://github.com/ReymoT/data-center-agentic/issues/24#issuecomment-6306107674): fetched b06cda7 and passed 906 tests/19 subtests. [Confirmed she can continue independent replay](https://github.com/ReymoT/data-center-agentic/issues/24#issuecomment-6306238312). | Nisha opened [PR #28](https://github.com/ReymoT/data-center-agentic/pull/28) for independent replay while this maintenance was underway; it is separate, open and unmerged. Matty answered her executed_starts question from the existing F02 contract; A04/E02 persistence is not implemented. Full protocol, claim-unit/reference selection and real saved-output acceptance remain open; no duplicate Matty replay work. |
| 5. Q10 #22 | [Accepted revised summary-assertion extraction and retained-pair/shortfall rules](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6306238057); updated the partial decision record. | Ved sampling/analysis agreement and exact slot eligibility. Matty recommends the original slots 0–23 manifest frame until an exact alternative is agreed. Nisha owns worked examples/rubric/selection code; no frozen sampling map or invented ratings. |
| 6. Q11/Q12 #21 | Corrected current status: Matty coordinator/publisher, Nisha backup, both allocations confirmed. Preserved existing tagged requests and all task rows. | Reimo, Ved and Edison must confirm allocations or specify exact changes, blockers and next evidence checkpoint. No reassignment, new permission or duplicate same-day reminder. |
| 7. Q13 #16 | Reconciled current body with Nisha-reported course dates and conditional platform/release reply, preserving attribution and unknowns. | Nisha: authoritative timezone/rubrics/delivery/code facts. Remaining contributors: OS/Python and license/access/retention agreement. Keep November 16 class readiness; no presentation production, LICENSE or visibility change. |
| 8. D06 #13 | Reconciled current body with completed version-matched Windows structural verification and exact remaining source/adoption questions. | Ved/Reimo: pollutant basis, interval convention, dataset rights, factor alignment and consumer adoption evidence. No invented source meaning. The separately deferred Frontier D02 follow-up remains deferred. |

## A01 evidence and limitations

The unchanged full suite reproduced the deep-object JSON failure. In one diagnostic, 905 tests and 19 subtests passed; the failing plain-LLM case received HTTP 200 and 23,360 of the declared 24,001 bytes, then timed out waiting for 641. A second instrumented run, including the first ten metadata tests, had 915 passes and 19 subtests plus the agent variant of that same failure. The server's write returned 24,001 bytes. This localizes the observed symptom to incomplete body reception before parsing; it does not establish the root cause or prove the production transport is fixed. No deadline, payload, assertion or attempt cap was weakened. Focused deep-JSON diagnostics also passed, so a successful rerun is not proof of a fix. Hosted CI is separate evidence.

Reproduce without contacting Ollama:

```powershell
python scripts/diagnose_provider_http.py --full-suite --out <new-local-report.json>
```

Use a new output path; prior reports are never overwritten. The command runs the actual existing synthetic socket tests and preserves their failure exit code. The [compact diagnostic](../evidence/a01-http-diagnostic-2026-10-20.json) records counts/errors, not model responses or scientific results.

The new [GGUF inspection tool](../../scripts/inspect_gguf_tokenizer.py) read only the installed artifact's 5,932,859-byte metadata prefix, not its tensor data. [Actual metadata evidence](../evidence/qwen3-tokenizer-metadata-2026-10-20.json) records 151,936 token entries, 151,387 merge entries, GPT-2 tokenizer with qwen2 pre-tokenization, add_bos_token=false and embedded-template SHA256. The source artifact is the previously inventoried Qwen3 Q4_K_M blob identified in [storage evidence](../evidence/ollama-qwen3-storage.json); the prefix hash is not a fresh full-weight checksum. No tokenizer artifact, weights or restricted data are redistributed.

```powershell
python scripts/inspect_gguf_tokenizer.py --gguf <installed-model-blob> --out <new-local-report.json>
```

This is real artifact inspection, not a prompt counter. A real counter still needs exact byte-level pre-tokenization/BPE/special-token behavior and runtime rendering equivalence for both request shapes. The research-only tokenizers 0.23.3 package and a hash-verified official Go compiler were isolated outside the repository/project environment. Neither is added to shared locks or an adopted runtime. No constant/character estimate was substituted, and prepared request token counts remain unknown.

### Real counter candidate, with explicit validation limits

[measure_q09_counter_candidate.py](../../scripts/measure_q09_counter_candidate.py) uses actual tokenizers 0.23.3 BPE from the hash-pinned official Qwen tokenizer JSON and [a restricted Go template helper](../../scripts/qwen3_legacy_render.go) compiled with isolated Go 1.27.3. It verifies three hand-derived whitespace/Unicode/template-marker vectors, then renders the actual two prepared request shapes using the installed template. [The measured candidate](../evidence/q09-counter-candidate-2026-10-20.json) contains real counts: plain 2,291 tokens and agent 2,003 tokens **on this restricted legacy-rendering candidate**. These are not Ollama prompt_eval_count measurements or validated production context counts. Format-schema bytes remain recorded separately because the legacy template has no format variable; actual runtime/schema behavior still requires validation. This does not establish the 12,000-token ceiling for real runs, general repair/history prompts or K02 inputs.

[Direct artifact comparison](../evidence/qwen3-tokenizer-comparison-2026-10-20.json) found all 151,669 reference token IDs match the GGUF entries and merge order is identical. GGUF has 267 additional token IDs; matching tables alone do not establish pre-tokenization/special-token/runtime behavior. The candidate stays blocked, is not injected into OllamaProvider and makes zero API/model calls. Its output hashes and renderer source/binary hashes are retained. No tokenizer JSON, compiler, wheel or binary is committed.

Reproduce in an explicitly isolated research environment with tokenizers==0.23.3; obtain tokenizer.json from the pinned Qwen commit linked below and verify SHA256 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4. Use the installed template blob matching the recorded hash:

```powershell
go build -o <local-renderer.exe> scripts/qwen3_legacy_render.go
python scripts/measure_q09_counter_candidate.py --tokenizer <tokenizer.json> --template <installed-template-blob> --renderer <local-renderer.exe> --preparation docs/evidence/q09-probe-preparation-2026-10-20.json --out <new-local-report.json>
```

Before adoption: affected owners must agree to the proposed tokenizers dependency, establish the actual runtime's rendering path, validate token IDs/counts against that tokenizer without assuming the Go/HF path, and add general-history/edge-case coverage. Runtime/service/resource agreement and explicit bounded inference authorization remain separate. Do not substitute these research counts into the prepared probe's unknown production counts.

Primary-source review: the [GGUF specification](https://github.com/ggml-org/ggml/blob/master/docs/gguf.md), pinned Ollama 0.40.6 [prompt rendering](https://github.com/ollama/ollama/blob/v0.40.6/server/prompt.go), [template processing](https://github.com/ollama/ollama/blob/v0.40.6/template/template.go) and [chat routing](https://github.com/ollama/ollama/blob/v0.40.6/server/routes.go). The latter has native and template rendering paths, so the separate template hash alone does not establish counter equivalence. The official [Qwen tokenizer configuration](https://huggingface.co/Qwen/Qwen3-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/tokenizer_config.json) is a candidate comparison artifact, not an adopted dependency or proven equivalent counter. No inference or debug-render request that could load a runner was sent.

## Preserved boundaries and refresh

All 50 task rows/owners/dependencies, exact seven-file merge/authority policies, canonical F02 schemas and interfaces, locks, shared generation settings, teammate implementations, historical evidence and unrelated local worktrees are preserved. Current Issue summaries retain their earlier body under an explicitly historical heading. No open scientific gate is marked Done or closed merely because documentation is current. No new same-day reminder repeats an unchanged request; substantive replies address Nisha's new messages.

After publication, fetch current main, preserve local/unpublished work, read deployment 1.15 and this handoff before resuming. Nisha's recorded b06cda7 adoption is receiving acceptance of E01 preparation only; adoption of 1.15 must be reported by each receiving session, not inferred from a mention or push.

## Publication validation

The final ordinary local run passed all **918 tests and 19 subtests**. The 12 new binary metadata/reference-comparison cases passed independently. Ruff lint/format passed for 62 Python files; setup/version/link/task/policy checks, compilation, pip check, dependency smoke checks and whitespace checks passed. The isolated Go helper compiled, and all three hand-derived renderer vectors plus both actual public request-shape measurements succeeded. Canonical F02 schemas/interfaces and the shared dependency lock were compared to base and are unchanged.

Earlier instrumented runs still exposed the documented local partial-body timeout; the final successful run does not establish a fix. No transport/test deadline/assertion was changed. Final commit/PR/exact-head CI links are recorded in #27 after publication. Receiving adoption of deployment 1.15 remains unconfirmed until a receiving session replies.
