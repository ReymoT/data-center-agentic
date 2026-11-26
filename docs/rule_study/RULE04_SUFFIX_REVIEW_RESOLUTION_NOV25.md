# Matty's suffix-package review: resolution and remaining gates

Matty supplied an AI-assisted preparation review of the `d7d15800` packet. Its
verdict was preparation/integrity PASS with conditions, not execution approval,
new-output receiving or independent reproduction. The reviewer's Linux/Python3.13
scratch copy lacked Git metadata and rdflib; those environment failures do not
replace the required native Windows/Python3.12 and exact merged-main checks.

## Direct corrections

- Hash-bound JSON is now parsed from the exact bytes just verified, using one
  bounded read. Parent receipt/request/status/pair checks use that reader; control
  carryover also rechecks the receipt and each hidden-control pair before using
  their signatures. Changing a file after verification cannot substitute a second
  unverified read. Later checks still detect changes to the retained files.
- `--inspect` writes an exclusive `BLOCKED` JSON report and exits2 for unreadable,
  malformed or invalid parents/requests. It never reserves an ID or dispatches.
- New resource stops distinguish `wall_time_reserve` from
  `state_transition_budget`. The historical raw failure remains unchanged. Its
  generic wording is not evidence that the counters were exhausted: Nisha's actual
  receiving identifies the wall-time reserve as the limiting resource.
- Suffix-specific offline tests exercise source-commit/pin/input drift before
  policy release, failures/timeouts/failed cleanup after one completed pair,
  rehashed control reads, one-read race behavior, and BLOCKED inspection. Shared
  containment, source, one-use ID and environment tests continue to apply.

## Time risk: explicitly retained

The parent took837.625seconds for182 pairs (about4.6seconds/pair). Scaling that
observed average suggests about819seconds for178 pairs, leaving little room once
the64-second next-pair reserve and preparation/eligibility/checking costs matter.
This is a rough observation, not a completion-time prediction: missing-forecast
timing has never been measured. Another incomplete stop is a material risk, not
merely a remote possibility. Keep900seconds,60seconds/pair,256MiB observed-output
stop threshold and separate3-second cleanup unchanged. No retry, warmup, time
extension, case reordering or execution is authorized by this review.

## Split-case union/accounting plan: pending implementation and acceptance

The original parent contains rules-v1 and GreedyA for
`development-overloaded_impossible-20`; its GreedyB pair is the first proposed
suffix pair. The parent source is `7c21d48c`; the reviewed suffix proposal named
`d7d15800`, which is superseded for future requests by these controller fixes.
All163 accepted scientific pins must still match across a later exact source.

A suffix-only summary correctly leaves this case unpaired against its absent
GreedyA run. Do not report zero reduction, omit the unavailable reason, duplicate
the parent pair, or silently pool the two attempts to fill it.

Before any combined result is accepted, a separate read-only union reporter must:

1. Authenticate each attempt's original request, authority, source, retained
   artifact hashes, input/specification/scientific pins and actual status.
2. Enforce the exact disjoint original-order partition, reject duplicates/unknown
   or failed/in-flight pairs, and retain incomplete statuses rather than rewriting
   the parent as PASS. A full union requires360 distinct completed validated pairs.
3. Join all policies by the same case identity and case-facts hash. Specifically
   test the split case above; its comparison becomes available only after the
   cross-attempt join passes the same frozen equal-work rules.
4. Preserve each producer/controller source and both authorization IDs. Report
   per-attempt and cumulative known states/transitions, wall time, failures and
   unknown partial-work bounds. Do not call the sum of completed-pair counters
   a complete total if a failed pair has unknown work.
5. Test conflicting case hashes/pins, missing baseline, partial suffix, duplicate
   pairs, modified artifacts and exact full-union coverage, without running new
   cases. Independently receive the resulting report before final use.

This document is the union plan, not an implemented or tested union reporter.
Union accounting, any new-output receiving, Ved's clean reproduction, final/unseen
evaluation, final PDF/report and audit remain open gates. Do not infer them from CI.

## Evidence/wording corrections in the supplied review

PR #283 merged at `ce4d35f9`; PR #284 merged at `d7d15800`, which includes both.
The parent root contains checkpoint and pair-request files as well as its failure
record; the failure is the only root status file, not the only root file. These
wording corrections do not change the reviewed partition or artifact integrity.

No scientific policy/verifier/metric definition or original artifact changes here.
New source hashes require a new reviewed request and fresh exact single-use
authorization. The earlier preparation PASS does not approve a revised run.
