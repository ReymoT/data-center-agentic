# RULE02 historical evidence receiving — November 22, 2026

Submitter: Ved. Receiving: MattyAnd. Submitted commit:
`f3f5be05bcaf7fa978dc4e81ec4cb76deb5575cc`.

## What arrived

The recreated `rule02-publish` branch adds 1,270 archived artifacts plus their manifest:
10 authored case/policy traces, 300 decisions, raw states/snapshots/transitions, implementer
logs, compatibility reports and original tools. They bind the published original code
`176361ad23ba57940b1576828893ce3a7b1a1666`. They are not traces of main's later receiving
fixes in `8df03b1` / merge `276c442`.

The supplied tree is preserved byte for byte under `docs/evidence/rule02/`. Its README,
commands, tools and local-run claims are historical records. The incoming handoff is
preserved separately in `RULE02_EVIDENCE_SUBMISSION_NOV22.md`; the current implementation
handoff retains main's later fixes and scientific limits.

## Problems fixed

Windows automatic LF-to-CRLF conversion initially invalidated all 1,270 listed hashes.
We restored the exact submitted Git blobs and added a recursive `-text` Git attribute so
future Windows checkouts preserve evidence bytes. We did not rewrite the trace hashes.

The incoming handoff was based on the older branch and conflicted with main. We retained
the corrected implementation and merged the new evidence without reverting its safety
or replay controls. Original commits and both handoff versions remain traceable.

The archived manifest checker checks file hashes but does not authenticate all actual
record bindings, sizes or path safety. Its replay tool imports whichever runner is on the
Python path; it cannot establish replay compatibility with today's hardened runner.
Do not use it on current main to claim current-system replay or fabricate new completion
markers for old traces. The new `scripts/check_rule02_evidence.py` checks safe unique
paths, exact file inventory, sizes/hashes, the original Git-source pins, all result/decision
bindings, decision-list commitments and raw state/snapshot/transition references. It reads
files only and never constructs a simulator or runs a policy.

## Actual receiving result

`RULE02_EVIDENCE_RECEIVING_NOV22.json` records this static receiving check:

- 1,270 archived artifact hashes match; 10 traces and 300 decisions are present.
- Historical adapter/spec/generator/lock source hashes match the original published Git
  commit. This checks file identity, not the submitter's installed environment or runtime.
- The existing strict trace reader refuses no supplied trace and reports no counterexample
  in these records. Its external `binding_validation` remains `INCOMPLETE`.
- Scenario B remains a blocked, jointly infeasible authored example. It does not establish
  progress on a jointly feasible input. B-fault is deliberate fault injection.
- No model call, policy execution, generation or new scientific evaluation was performed
  during receiving. Supplied runtime logs remain attributed implementer reports.

## Repeat the read-only receiving check

From a checkout with the original implementation Git object available, use the pinned
Python environment:

```
python scripts/check_rule02_evidence.py
```

A shallow clone may lack `176361a`; obtain that existing public commit before checking
historical source bindings. The checker fails rather than guessing if the object is absent.
Ordinary offline tests validate inventory/reference behavior without requiring a network
fetch or claiming Git-source authentication from a shallow checkout.

Nisha's independent frozen-current-system receiving (#241), Edison's accounting receiving
(#242), the exact scientific freeze and fresh bounded manager authorization remain separate.
This merge accepts an archival handoff only. It supplies no final-seed or execution approval.
