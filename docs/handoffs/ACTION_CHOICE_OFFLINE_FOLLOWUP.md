# Offline action-conflict investigation and prompt clarification

Later execution update: Matty approved this exact candidate and the
[completed public validation passed](I01_ACTION_CHOICE_VALIDATION_RESULT.md).
Its new independent receiving remains pending. The single-use ID is consumed;
the original offline pin/template status below is historical, not authorization
for another execution or scientific freeze.

Matty authorized this offline follow-up after the failed `RUN-15e69e6129b7`
validation. No model, runtime or source-CSV request is part of this investigation.
The original responses, traces, failed outcome and receiving records are unchanged.

## What the original evidence shows

The retained emergency request starts with “Single repair request.” Its initial
parsed plan starts J2 at slot 1. The provided checker feedback reports 110 kW IT
load against 100 kW capacity, with J1/J2 implicated. The raw replacement keeps
J2's slot-1 start and adds a J2 abstention citing the capacity constraint. F02
rejects the same job in both categories, and the strict wrapper stops without
silently dropping either action or spending another request.

The original proposal already requested one disposition per waiting job, and the
repair requested a replacement. The model failed that contract. Shared rules did
not spell out the three arrays' mutual exclusion or explicitly say to remove an
invalid start when choosing a refusal. That gap may contribute, but it is not a
proven sole cause of the model response or evidence that clearer wording will work.

## Offline change

- Shared task rules now say one visible waiting job in one category, explicit
  arrays, and no duplicate/cross-category job IDs. Future starts remain starts,
  not simultaneous deferrals. Changing a choice replaces the old entry.
- The same shared text reaches Plain, Agent proposal and Agent repair. Repair
  additionally says a replacement is not an addition to the initial plan.
- The instructions apply when returning a Plan or the plan inside PolicyOutput;
  they do not permit the explanation stage to emit or replace a plan.
- F02, production/evaluation checks, response grammar, sampler, limits, model,
  context equivalence and original outputs are unchanged. The parser continues
  to reject conflicting actions; no deterministic postprocessor repairs them.

All four prompt hashes change because their renderers include the shared file.
[Current offline pins](../evidence/i01-renderer-pins-2026-11-04.json) explicitly
declare no scientific freeze. The October preparation is preserved unchanged and
its hashes are checked against [the retained prompt sources](../evidence/i01-pre-action-choice-2026-11-04/prompts/shared/task_rules.md),
not overwritten to pretend the new wording existed in the original run. Current
readiness uses its own draft pin record, separate from that historical freeze.

## Verification and next boundary

Offline tests verify equal instruction delivery to the three planning paths,
retained one-attempt semantic failures for Plain and Agent, structurally legal
single-category alternatives, historical prompt preservation and refusal of a pin
record that claims scientific freeze or disagrees with Plain. These tests check
rendering and safeguards, not model compliance or recommendation quality.

The prepared candidate is `RUN-fd87c6c8a9cb`, configuration SHA-256
`fd87c6c8a9cbbc959fe0e047d54593db793787396945ff7d5daa0b13b8b2e506`,
source base `18f2cba0252e215e94ae7c2b54de0b3df8b810d5`.
Its pending ID is `I01-EPHAND1-fd87c6c8a9cb-20261104-choices-v3`.
The actual manager-host no-startup dry run passed at clean checkpoint `0c1c197`,
checking the revised execution/launcher/prompt pins and accepted local binary,
tokenizer and C/D bindings. It started no runtime, sent zero model requests,
consumed no authorization and created no proposed run directory.
The current candidate/readiness/dry-run/template keep their canonical November 2
filenames. The failed candidate's packet and all earlier sources are snapshotted.

Proposed scope remains one public EP-HAND1 exercise, six systems, LLM trial 0/
seed 101; at most 6 Plain, 18 Agent and 24 total requests; 150 seconds/request,
480 seconds/Agent decision, 3,900 seconds total; zero retries/warmups. No source
acquisition, held-out access, training, changed action semantics or study run is
proposed. Check actual actions, conflicts, stage origins, failed attempts and
cleanup rather than merely counting fields or calling fallback model scheduling.

Fresh exact approval is required before inference. Prompt/schema freeze and full
I01 remain blocked until genuine model behavior and acceptance evidence support
them. No new run, improvement or receiving PASS is claimed by this offline change.
