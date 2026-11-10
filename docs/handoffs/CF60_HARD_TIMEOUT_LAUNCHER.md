# CF60 offline hard-timeout launcher

Prepared for Matty on November 9, 2026 against main 07b73e09b3adc74bde8e2f9c2e376d4016b60839, instructions 1.28. This completes stop-control preparation only. No real source CSV was opened or hashed. No extract, comparison, model, solver, rollout, training or held-out execution was performed.

## What is implemented

The operational entry point is scripts/launch_cf60_ingest.py. Its child uses the existing extractor after the same approval preflight. Preflight validates the exact clean code revision, four LF code pins, source/output paths, exact indices, time bounds and authenticated-reference fields without reading source contents. JSON references do not authenticate consent: Matty must check the referenced human decisions separately.

The launcher snapshots those exact approval bytes. The worker checks the snapshot checksum and validates/uses those same bytes rather than reopening a mutable original approval. It must receive a one-byte release signal before opening approval/source inputs. The parent first assigns the worker to a Windows Job Object, with kill-on-close and no breakaway. If containment is unavailable or process creation returns after the deadline, no release occurs. Child stdout/stderr are discarded so tracebacks cannot publish raw values.

The external deadline starts before child process creation and uses the approved positive time_limit_s, at most 120 seconds. On expiry or interruption the job tree is terminated. Native synchronization handles and empty-job accounting verify termination. Cleanup has a separate three-second budget; failure to verify is cleanup_unverified, never success. OS process creation/API scheduling itself is not a hard real-time guarantee. A late-created child remains gated. Parent death after assignment closes the job handle and kills its tree; death before assignment closes stdin, so an unreleased worker exits without source access. There is no non-Windows fallback.

A direct child that leaves descendants running fails even if its exit code is zero. The lower-level extractor remains a cooperative helper for tests; do not use it directly as the operational hard-timeout entry point. This launcher is not a security boundary against another process under the same Windows account and does not establish evaluator-only storage.

## One-shot receipts and stop rules

A new entry in .cf60-dispatch-consumed-authorizations reserves the ID before spawning. A separate new <extract-name>.dispatch directory preserves authorization.json and intent.json; result.json records outcome, release state, cleanup verification, timing and approval checksum. The extractor independently retains its own consumption ledger and failure receipt. Nothing retries, overwrites, deletes failures, switches source or generates a replacement ID.

Accept an extract only when result.json reports succeeded with cleanup_verified true, its extract_sha256 matches the actual bytes, its approval checksum matches the authenticated approval, and normal source/index/provenance gates pass. Any missing/incomplete receipt, nonzero exit, timeout, orphaned descendant, unverified cleanup or extractor failure is a failed/incomplete attempt. A partial or even complete-looking output left behind by a failed attempt remains preserved evidence and must not enter comparison. A parent crash can leave intent without result; that is not success. The same ID cannot be retried by renaming output within its authorized ledger directory; the exact path also remains bound by approval. Never move to another ledger directory to reuse an ID.

## Offline verification and remaining inputs

Tests use real Windows jobs and synthetic processes: ordinary success/nonzero exit, timeout of a child plus grandchild, refusal to release on assignment failure or late setup, interrupt cleanup, supervisor death, descendant leakage, job creation failure, unverified cleanup, pending-approval rejection, missing release, single-use failure preservation and full synthetic extraction with matching receipts. No test opens the real source, calls a model, chooses a nonce or runs a policy.

Microsoft API rationale: https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects and https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject . Python process lifecycle: https://docs.python.org/3/library/subprocess.html .

This code changes the code pins, not F02, the development allocation, the scientific method or master instructions. Older pending packages/approvals are preserved and are stale for the new code. A new pending package must bind all four code files and later its actual clean merged revision.

Before real source access: authoritative source-use evidence; Nisha's accepted whole-file/all-timestamp footprint and pre-inspection nonce/isolation disposition; accepted executor/machine/storage; and Matty's fresh exact single-use ingest approval. B1-B3 remain unresolved and B4 provisional. The manager staging folder is not accepted evaluator-only custody. No actual extract/hash or complete saved states are available. A later comparison requires separate approval and must disclose all missing states. #60 stays open.
