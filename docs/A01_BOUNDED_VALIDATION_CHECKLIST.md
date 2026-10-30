# A01 bounded-validation checklist

This checklist prepares one public-development transport validation. It is not a
runner and does not authorize a model request. Stop whenever a required item is
missing; do not substitute silence, a passing unit test or an earlier authorization.

## Before authorization

- [ ] Nisha and Ved have each accepted the exact per-request and paired deadlines,
      with direct issue-comment references.
- [ ] The manifest's deadline status and both agreement records match those replies.
- [ ] The exact future run commit is frozen and contains the reviewed response bounds.
- [ ] Plain prompt content is frozen by SHA-256.
- [ ] The Agent Plan renderer is reviewed and frozen by an exact repository reference.
- [ ] The checked-in manifest validates offline.
- [ ] The manifest also passes `--require-ready`; a blocked result means no dispatch.
- [ ] Matty records a fresh authorization that names the exact commit, two-request
      maximum, order, deadlines, model/settings and stop conditions.
- [ ] The authorization reference is copied into a per-run manifest; never edit an
      older evidence record or reuse a spent authorization.

Offline validation command:

```powershell
.venv\Scripts\python.exe scripts/validate_a01_bounded_manifest.py `
  docs/evidence/a01-bounded-validation-manifest-2026-10-30.json
```

Do not use `--require-ready` as a way to change the manifest. It only verifies that
separately recorded agreements, freeze fields and authorization are already present.

## Identity and host preflight

- [ ] Use an isolated loopback runtime and model store; do not modify the active service.
- [ ] Verify accepted Ollama 0.40.5 binary and `qwen3:8b` model/template/parameter hashes.
- [ ] Verify the exact host, driver and required environment variables.
- [ ] Verify zero loaded models and sole ownership of the selected loopback listener.
- [ ] Record the pre-run identity and metadata. Metadata readiness is not inference proof.
- [ ] Confirm Plain and Agent use the same host, runtime, model and generation settings.

## Bounded request sequence

- [ ] Start the paired total deadline before the first dispatch.
- [ ] Dispatch Plain first through `PlainLLMPolicy.propose` on the public development state.
- [ ] Persist the attempt before any model-derived action; retain raw bytes and errors.
- [ ] Continue only if Plain returns HTTP success, strict `PolicyOutput`, `done_reason=stop`,
      matching native/offline count, full 37/37 Arc/Vulkan offload and unchanged identity.
- [ ] Dispatch at most one Agent Plan request. Do not call repair or explanation.
- [ ] Make no warm-up, retry, tool, simulator, held-out, cloud or study request.
- [ ] Stop on any manifest stop condition. Never extend a deadline during the run.

## Evidence and cleanup

- [ ] Record request/response hashes, raw output location, status, stop reason, usage,
      latency, prompt counts, backend/offload and every attempt outcome.
- [ ] Verify runtime/model/template/parameter identity again after the sequence.
- [ ] Stop only the exact owned process and verify no owned process or listener remains.
- [ ] Preserve failed and uncertain evidence; do not replace it with a rerun.
- [ ] Report Plain and Agent separately. A missing Agent attempt is not a paired success.
- [ ] Label the result development validation only, never experiment readiness or findings.

## Completion rule

The validation is successful only if both bounded requests satisfy every gate and the
cleanup evidence passes. Even then, A01 study readiness and a complete A02 development
episode require separate acceptance. This checklist never authorizes a subsequent run.
