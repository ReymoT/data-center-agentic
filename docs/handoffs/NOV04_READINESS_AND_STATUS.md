# November 4 offline readiness and manager status

Superseded for the current candidate by the later
[latency/label/readiness follow-up](NOV04_LATENCY_LABELS_AND_READINESS.md).
`RUN-3225d3a29153` and its checks below remain historical; the current candidate
is `RUN-e670485639c9`, with its own pending exact authorization.

Matty authorized the recommended offline preparation, factual documentation and
issue follow-ups. No model execution or scientific freeze is authorized here.

## Actual offline verification

Source base: `bb9bf3ea5bdc83e9779e5c0e8c26ddb81c98ab7c` (merged PR #171).
The launcher pins that base; its separate LF hash binds the reviewed launcher.
Candidate: `RUN-3225d3a29153`.

- [Candidate](../evidence/i01-offline-config-2026-11-02.json):
  `3225d3a2915396d7cdfcd35cd77544d90dc2eab90cb35ccadbb13c7572ff424e`.
- [Readiness](../evidence/i01-unified-readiness-2026-11-02.json): LF SHA-256
  `b390f75ddf5e9144d6d55e7459c802f6212561492a3d167f993636c1cc7b0beb`.
- Launcher LF SHA-256:
  `cb4c690a3adfd7699e9a613ee08b00785dc77efc179a13c740f75699db045499`.
- [Actual dry-run record](../evidence/i01-launcher-dry-run-2026-11-02.json):
  passed on the real manager-host runtime, tokenizer and C/D files. No runtime
  startup, model request, approval consumption or proposed output directory.
- [Pending authorization](../evidence/i01-authorization-template-2026-11-02.json):
  `I01-EPHAND1-3225d3a29153-20261104-v1`; approval fields remain empty.

The two initial preparatory dry-run invocations stopped at the launcher's clean
tracked-worktree check. No runtime was started. After committing the offline pin
refresh on the task branch (`187b5b7`), the same no-startup check passed. These
were preparation refusals, not failed/retried model requests. The successful
record retains its actual checkout commit. The original readiness/candidate,
dry-run and pending template are preserved in
[the pre-refresh snapshot](../evidence/i01-pre-nov04-2026-11-04/i01-offline-config-2026-11-02.json).
Canonical filenames retain November 2 for existing consumers; their current
candidate/base and dry-run verification date identify the November 4 refresh.

Exact proposed single-use bounds: all six systems on public EP-HAND1, trial 0 /
seed 101 for each LLM, Plain at most 6 requests, Agent at most 18, combined 24;
150 seconds/request, 480 seconds/Agent decision, 3,900 seconds total; no retries
or warmups. Fresh approval of the exact hashes/bounds is still required.
Live runtime/model/template/counting and Arc/Vulkan checks remain part of the
authorized launcher, not facts proved by this no-startup dry run.

## Existing evidence and current task status

- PR #169 accepted Nisha's existing-run receiving PASS, with her unchanged report
  and a separate manager manifest check. That transfer/review task is complete.
- PR #170 published the R05 development evidence. It is not a unified comparison.
- PR #171 published the independent forecast-tie helper and two regression fixes.
  E06 integration and measured study rates remain pending. The actual public
  EP-HAND1 check gives 9 decisions, 6 distinct, 3 no choice, 0 tied.
- I01 remains partial. Another development rating/receiving pass on the same old
  packet is unnecessary; a new unified run needs its own actual receiving.

## Management direction and remaining issues

Keep CF60-v1 as the lower-cost working proposal. Defer the shaped alternative
unless a concrete development-only compatibility assessment shows it fits the
schedule. This is manager direction for resolving the proposal, not adoption on
behalf of affected consumers. Nisha's three custody clarifications remain required:
the recorded index plus both interval hypotheses, legacy plus CF60 footprints
for all forty development episodes, and a merged/pinned new selector version
before any nonce. Ved and Edison still owe their exact responses by the existing
November 4, 4:22 PM Phoenix boundary; no replacement deadline or overdue claim.
Production broker, independent receiving and actual custody remain gates.

All five issues stay open:

- #60: source B1–B3 unresolved, B4 provisional; forecast/custody/freeze incomplete.
  A management decision cannot manufacture authoritative source facts or rights.
- #16: Nisha's next course-source checkpoint remains November 20 or new guidance;
  project number, midnight/timezone and release/license fields remain unknown.
- #95: development ratings/adjudication complete; frozen held-out repeat remains.
- #164: I02 freeze → frozen C/D outputs → Ved's O04 labels → Edison's P07 scores.
  No duplicate wrapper, retraining or invented labels/paths is requested.
- #166: final E06/E07 inputs → Ved's I03 reproduction → Matty's I04 review.
  No overdue ready reproduction task or final-platform certification is claimed.

F04/F05 and R04 are updated factually; their final acceptance and R06 release
still depend on real final evidence. No held-out contents were read or generated.
