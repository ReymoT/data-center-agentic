# November 4 latency, label-audit and readiness follow-up

Later status: [E06 table integration](E06_STUDY_TABLES.md) is implemented through
PR #179. Final scoring/analysis acceptance remains pending. The [later action-field
validation outcome](I01_ACTION_FIELDS_VALIDATION_OUTCOME.md) records the actual
failed attempt; preparation-only statements below retain their historical scope.

Matty approved the recommended analysis response, Agent latency fix, read-only
legacy-label audit and offline readiness refresh. This does not approve a live
model request, another owner's acceptance, or the scientific freeze.

## Delivered work

- Agent `DecisionRecord.latency_ms` now sums recorded request latency before trace
  persistence, matching Plain's meaning. If any attempt is missing latency, the
  total is missing; no-call records remain without an invented request latency.
  End-to-end `AgentDecision.elapsed_ms` is separate. Twenty-one harness tests pass,
  covering durable single/repair-call totals, missing latency and no dispatch.
  Existing historical traces are unchanged and remain missing where appropriate.
- [Manager analysis decisions](../decisions/E03_ANALYSIS_MANAGER_2026-11-04.md):
  broad unsafe rate primary, both measures/omissions reported; 10,000/95%/20261113
  percentile resampling; 24 core episodes primary and six withheld variants
  separate; genuine no-ops excluded and pending decisions uncredited. Requested
  affected confirmations/final I02 freeze remain open, not silently approved.
- [Read-only legacy audit](LEGACY_LABEL_AUDIT_2026-11-04.md): all 6,046 labels
  match 570 cache results; 40 development episodes, 1,411 positives/4,635 negatives.
  Flat forecasts were used historically. There are 1,075 local multi-candidate
  job-decisions, but no recorded global-optimum multiplicity. Mean/minimum agree
  exactly in 5,974 rows and within relative 10^-12 in all rows. All 1,143 protected
  files are unchanged; no CSV read, reference solve, model call or held-out access.

## Refreshed exact public-validation packet

The runtime-source base is `40dcd800babf0964e718a8a538548e454d9c0e3c`, the
latency-fix commit. The launcher has its own separate LF hash. Candidate:
`RUN-e670485639c9`, config SHA-256
`e670485639c93d0bf1b539f0c9aa04220b35c166ed04812eca03a4a65a12b30b`.

- [Candidate](../evidence/i01-offline-config-2026-11-02.json)
- [Readiness](../evidence/i01-unified-readiness-2026-11-02.json): LF SHA-256
  `97bfe6a30b21f3fcf434712055d244a526ed382805ea26298778b7335f244adc`.
- Launcher LF SHA-256:
  `d5ac4ab0d3f3ad6190843d1e5175e2113a0fdb22a5c1f16437283b4ebc362152`.
- [Actual no-startup dry run](../evidence/i01-launcher-dry-run-2026-11-02.json)
  passed after the clean task-branch checkpoint `2dfaa20`, using actual accepted
  local runtime, tokenizer and C/D artifacts. It created no proposed run directory,
  started no runtime, consumed no authorization and made zero model requests.
- [Pending single-use template](../evidence/i01-authorization-template-2026-11-02.json):
  `I01-EPHAND1-e670485639c9-20261104-v1`; approval fields are empty.

The prior `RUN-3225d3a29153` packet is preserved in
[the pre-latency snapshot](../evidence/i01-pre-latency-2026-11-04/i01-offline-config-2026-11-02.json).
The older [November 4 preparation](NOV04_READINESS_AND_STATUS.md) remains historical.
Neither old nor new pending template authorizes execution; the earlier candidate
does not bind the new harness. Canonical November 2 filenames are retained for
existing consumers, with current hashes/revision and refresh reason recorded.

Bounds are unchanged: all six systems on public EP-HAND1, one LLM trial/seed 101;
at most 6 Plain and 18 Agent requests, 24 combined; 150 seconds/request,
480 seconds/Agent decision and 3,900 seconds overall; zero retries or warmups.
Fresh exact approval and live identity/offload/counting/cleanup checks are required
before a new unified run and its independent receiving can be claimed.

## Remaining boundaries

Ved's November 4 conditional mechanics acceptance is received. His O02/C/D
compatibility certification is not received, and the legacy tie audit above is
not that certification. Edison still owes the existing forecast response unless
a later explicit reply arrives; the November 4 4:22 PM Phoenix boundary is unchanged.
The separate analysis-response window ends November 5 21:39:22 UTC.

I02 keeps zero frozen items. Broker/forecast adoption, Q08, source B1–B3 and
B4 suitability, actual held-out custody, E06 integration, final scoring/reliability,
I03 reproduction and I04 acceptance remain separate gates. No issue is closed
merely because the latency bug or the legacy provenance question is resolved.
