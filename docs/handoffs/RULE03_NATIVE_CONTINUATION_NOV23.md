# November 23 native-host continuation: PASS within scope, receiving pending

Latest: [Nisha's independent receiving is accepted](RULE03_NATIVE_INDEPENDENT_RECEIVING_NOV23.md). The historical pending state below describes publication before her reply; raw attempt reports remain unchanged. Accounting and whole-study freeze remain separate pending gates.

Matty explicitly approved the exact single-use native-host request in chat.
The clean merged host was `dbb8e6fc391850c8291dcc66e4a57006e8ecc13f`, with
exact merged-main CI green. Request SHA-256:
`b36e7f01c114121a5bf8547ed0016beccf0327f4ac2a1198c04db61cc129c1cb`.
Consumed ID: `rule03-native-c51a10-dbb8e6f-20261123`; do not reuse it.

The native host retained the reviewed Windows Job Object supervisor, exclusive
ledger/output, pre/post source and evidence guards, and no retries. Its single
combined ceiling was 10,000 states, 50,000 transitions and 600 seconds, with the
existing separate three-second cleanup deadline. It ran exactly 10 authored
case-policy runs and replayed the 51 named saved Greedy B traces. It did not
regenerate primary traces, generate final cases, call a model, train or read
restricted source/private inputs.

## Actual result

- Worker exit 0; continuation **PASS**; elapsed 54.265 seconds; cleanup verified.
- 2,130 charged states and transitions: 300 authored execution steps plus 1,830
  replay steps (300 authored + 1,530 saved Greedy B).
- Cumulative charged states/transitions: 12,130, including the original 10,000.
  The extra 10 relative to the 12,120 full-scope estimate repeat the previously
  partial saved trace prefix; this work is disclosed, not removed from counters.
- Authored: four cases / 10 runs, no run errors; all 10 artifact/binding checks
  PASS. Rules-v1 S1-S5/P1/P2 and arithmetic PASS. Greedy A/B S1-S3/S5/P1/P2
  PASS; their S4/arithmetic remain NOT_RUN because the injected fault and rule
  arithmetic are rules-v1-only.
- Saved Greedy B: 51/51 replays and binding checks PASS; S1-S3/S5/P1/P2 PASS;
  S4 remains NOT_RUN in the fault-free primary domain.
- Source/evidence stable; original saved producer remains `3daf00f7`; new
  authored producer is `dbb8e6f`. Neither historical pin was overwritten.

The original [November 22 report](RULE03_BOUNDED_ATTEMPT_NOV22.md) remains
INCOMPLETE. The intermediate [sandbox host failure](../evidence/rule03-nov22/continuation-host-failure-nov23.json)
remains FAIL with zero charged steps. Neither consumed ID was retried. The
successful native continuation is a separate authorized attempt and report.

## Retained evidence and next owner

- [Raw continuation report](../evidence/rule03-nov23-native/continuation-report.json)
- [Attempt receipt, hashes and limits](../evidence/rule03-nov23-native/attempt-receipt.json)
- [New authored artifact archive](../evidence/rule03-nov23-native/authored-artifacts.tar.gz)
- [All 1,540 authored file hashes](../evidence/rule03-nov23-native/AUTHORED_SHA256SUMS.txt)
- [Independent receiving instructions](../rule_study/RULE03_NATIVE_RECEIVING_NOV23.md)

Nisha receives this **new scope** independently; her original retained-evidence
receiving is already received and is not requested again. Manager packaging
checked all 1,540 new file hashes without another policy/replay invocation.
That is not a substitute for her receiving. Until the actual new receiving and
remaining accounting/freeze gates pass, do not claim scientific freeze, final-set
evaluation, generalization or superiority. Edison still supplies actual retained
development case/accounting files and metrics. The 12 zero-start jointly
infeasible primary cases remain a limitation; no policy was changed to hide it.
