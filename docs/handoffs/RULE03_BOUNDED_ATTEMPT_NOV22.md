# November 22 bounded receiving attempt: incomplete, preserved

Matty approved proceeding with the immediately preceding prepared-run recommendation
in this chat. The exact request was rechecked before the one-use contained launch:

- Code: `3daf00f7af5b130e8b17ae67b2f79a7dadb7ea00`, clean merged main, green CI.
- Request: `a96bc5388a9ddb4d94c40fd1a7602067b61868161c9901291bfc8ba4ea25591d`.
- Consumed ID: `rule03-primary-authored-3daf00f7-20261122`. Never reuse it.
- Maximum scope: 202 case-policy runs, 30 decisions each; primary plus authored,
  rules-v1/Greedy A/Greedy B, no optional extension or final-set generation.
- Combined ceilings: 10,000 states, 50,000 transitions, 600 seconds. No retries.

The [original report](../evidence/rule03-nov22/receiving-report.json) is retained
byte-for-byte with SHA-256
`f1e11a4f781c4d3efc920975a67d032d623cd7648ad60c63bd5bf2f6d008915e`.
The [attempt receipt](../evidence/rule03-nov22/attempt-receipt.json) records the
archive identity, runtime and original scope. The full synthetic trace archive
and file hashes are linked from [the receiving guide](../rule_study/RULE03_NISHA_RECEIVING_NOV22.md).

## What actually happened

The child exited with code 7 for INCOMPLETE after 107.172 seconds. It did not time
out or crash. Supervisor cleanup was verified. The combined state ceiling was
reached at exactly 10,000 states and 10,000 transitions: 5,760 actual-runner steps
and 4,240 replay steps. The code pin stayed stable. No retry occurred.

| Domain/policy | Generated traces | Complete replay | Recorded result |
| --- | ---: | ---: | --- |
| Primary rules-v1 | 64 | 64 | S1/S2/S3/S5/P1/P2 PASS within scope; S4 NOT_RUN |
| Primary Greedy A | 64 | 64 | S1/S2/S3/S5/P1/P2 PASS within scope; S4 NOT_RUN |
| Primary Greedy B | 64 | 13 | Properties INCOMPLETE: 51 traces have incomplete or absent replay |
| Authored, all eligible policies | 0 of 10 | 0 | NOT_RUN/INCOMPLETE after the ceiling |

All 192 generated primary traces passed the separate artifact/binding checks,
with zero recorded run errors and no artifact findings or refused traces.
The nested trace reader's external-binding field remains INCOMPLETE; its caller
performs the separate raw-file/source checks. Both original fields are retained,
not overwritten or presented as a separate person's acceptance.
This does not mean every job completed. For rules-v1 and Greedy A, P1 was checked
on 52 jointly feasible cases each; the other 12 are outside that completion claim.
No invalid proposal occurred in the primary domain, so S4 has zero checks and
is NOT_RUN, not PASS. Rules-v1 R04 arithmetic had 141 checks and zero mismatches.
No counterexample was recorded in completed replay; Greedy B's incomplete portion
and the authored cases cannot be treated as passing. Overall remains INCOMPLETE.

## Cause and smallest continuation proposal

The existing API charges both actual execution and replay against one ceiling.
Full 202-by-30 execution plus full 202-by-30 replay would require 12,120 charged
steps, exceeding 10,000. The approved stop worked; this is not evidence of a
scheduler defect. Do not raise a cap, remove charges or relabel the result.

The smallest separately authorized continuation is to preserve and reuse the
192 existing primary traces, replay only the remaining 51 Greedy B traces
(including the partially checked one), and generate/receive the 10 authored
case-policy traces. Use the same frozen scheduler/verifier and one fresh scoped
authorization/ID/output; do not rerun the completed primary policies. The simple
30-step estimate is 2,130 additional charged steps (1,530 saved replay plus
300 authored execution plus 300 authored replay), not a guarantee or permission.
Report both attempts and cumulative work; the original attempt stays incomplete.
The [machine-readable proposal](../evidence/rule03-nov22/continuation-proposal.json)
lists all 51 saved trace identities and result hashes; it grants no authority.

No continuation has run. Additional replay/execution requires fresh exact
authorization and containment; the consumed original ID cannot grant it. A later
scope-specific report needs Nisha's independent receiving before any freeze.

Edison's actual accounting/metric files, Reimo's focused methods/diagram and the
integrated demo package remain separate deliverables. No final unseen set,
LLM call, source/private input use, physical-emissions claim or original-question
answer is supplied by this finite-domain attempt.
