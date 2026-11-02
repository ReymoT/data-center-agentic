# I01 development acceptance audit

Follow-up: the [offline configuration and evidence index](I01_OFFLINE_CONFIGURATION_2026-11-02.md)
are now prepared; the source/private-custody and independent acceptance limits
below remain. [Nisha's new course report](../decisions/Q13_COURSE_UPDATE_2026-11-02.md)
supersedes the earlier partial-course investigation at the end of this audit.

Matty audited published evidence and manager-local P04 summaries at main
`227d2ebabd863d58f0a1b7bf2e56b6acdb02e1d4`. This is an evidence reconciliation,
not a fresh model run, new scientific setting or independent final approval.

## Evidence by system

All six paths have actual receiving evidence on public EP-HAND1. They were not
executed as one frozen six-system experiment. Preserve the original run identities.

| System | Actual evidence | Commit | Remaining acceptance limit |
|---|---|---|---|
| Greedy A | 30 traces, 2 completed jobs, zero replay findings/result mismatches | `94839dc4b547c3f1e50fabed0e50b1653173b3ad` | Same four-system receiving run, not full I01 |
| Greedy B | 30 traces, 2 completed jobs, zero replay findings/result mismatches | Same as A | Same limit |
| Decision tree C | Actual reloaded depth-8 binary, 30 traces, 2 completed jobs, zero replay findings/result mismatches | Same as A | Development artifact; scientific seed/freeze not adopted |
| Random forest D | Actual reloaded 100-tree depth-10 binary, 30 traces, 2 completed jobs, zero replay findings/result mismatches | Same as A | Same limit as C |
| Plain LLM | 5 saved requests, 30 traces, zero replay findings/result mismatches | `482842968edd1fe963a647db9ed826bf3a195c40` | Earlier separately authorized receiving, one seed |
| Agent | 12 saved requests, 30 traces, zero replay findings/result mismatches; repair/fallback stages retained | Same as Plain | Earlier separately authorized receiving, one seed |

The public bundle LF SHA-256 is
`8bef36ace7bc4a3cf2debdce81c75edd87e175b20592a520a5449ec1fb0cddd6`.
A/B/C/D run identity is `RUN-1f6e4c4c2afb`. The two LLM paths use accepted
Ollama/Qwen settings and seed 101. C/D training used development script seed
20261031, not a newly accepted scientific seed. These differences prohibit
presenting this table as a matched statistical comparison or superiority result.

## Trained-artifact receiving reconciliation

| Criterion | Observed result | Limit |
|---|---|---|
| Input identity | Pinned source verified; all 40 development contents match v2 receipt | Source rights/physical interpretation not established |
| Labels | 6,046 definite rows: 1,411 positive, 4,635 negative | Certified development labels, not final held-out references |
| Fold selection | All 15 configuration/fold cells evaluated; training partition class counts retained | Scientific freeze still pending |
| Refit/reload | Both selected models refitted; saved/reloaded probabilities match over 100 rows | Trusted local binaries only; no remote transfer |
| Runtime | Real trained factory, matching digest settings, production checker/controller and independent replay used | One public fixture; not comprehensive safety |
| Final independent acceptance | Not recorded | Matty's technical audit is not Nisha's independent sign-off |

Binary hashes, summary hashes, manifests and custody are recorded in the
[P04 handoff](P04_REAL_DEVELOPMENT_ARTIFACTS.md). Earlier
[Plain/Agent receiving](EP_HAND1_RECEIVING_F04_F05.md) retains its own authorization,
attempt accounting and original failures. No new requests were dispatched here.

## Acceptance verdict and next executable steps

I01 remains **partial**: six actual paths are evidenced; a reconciled final
acceptance record, independently verified receiving and complete common-protocol
coverage remain unaccepted. Existing offline failure tests are regression
evidence, not proof of a new full integration execution. I04 is not ready.

The next independent work is to assemble a same-protocol configuration and
artifact/trace index offline, then review coverage against the existing
[I01 checklist](I01_TRAINED_RECEIVING_CHECKLIST.md). Reuse existing outputs only
where identities and configuration are demonstrably compatible. Do not silently
combine different commits or spend another model request. A fresh unified
LLM-inclusive run requires an exact bounded manifest and fresh authorization.

Scientific readiness separately requires source evidence and actual private
custody/freeze (#60), followed by authorized experiments, held-out references,
scoring, independent ratings/reliability (#95), reproduction and I04.
#16 governs official course requirements, not technical integration approval.

## Source and course investigation

A bounded public search on November 2 found the current upstream
[SustainDC README](https://github.com/HewlettPackard/dc-rl/blob/main/README.md)
and [exploration consumer](https://github.com/HewlettPackard/dc-rl/blob/main/explore_ci.py).
They describe EIA origin and consume `avg_CI`; neither search result supplies a
historical exporter tied to the pinned bytes, CSV-specific physical intervals,
or file-specific rights. These mutable current pages are discovery references,
not replacements for the pinned evidence inventory. B1-B3 remain unresolved,
B4 provisional, B5 actual custody/freeze pending. No new permission or source
acceptance was inferred and no external maintainer was contacted.

For #16, the available GitHub record contains Nisha's partial Canvas attribution
and the completed evaluations index, not a complete official requirements
record. No authenticated course-system session or complete official artifact was
available to this audit. Exact remaining course fields stay unresolved. No
private email content was reused or forwarded. Neither issue can truthfully close.
