# Contained RULE03 receiving preparation

Owner: Matty, #241/#244. Nisha's receiving implementation is preserved; the
production scheduler/checker and independent verifier remain separate. This
wrapper changes host plumbing, not rules, F02 formats or scientific limits.

`scripts/prepare_rule_study_receiving.py` prepares Nisha's primary + authored
proposal on clean merged main. It uses her independent source reconstruction
and case identities, plus all Python, lock and specification source commitments.
The final merged commit must be pinned again after publication; the older
759a8c3 pin and adapter hash in her original comment are historical after #261.

Scope: 64 primary cases and four authored cases, rules-v1/Greedy A/Greedy B,
excluding baseline fault injection, at most 202 case-policy runs and 30 decisions
per run. The optional 1,024-case supplement is deferred. No final unseen set,
private inputs, source recovery, model call or ML training is involved.

One combined 10,000-state / 50,000-transition / 600-second budget covers actual
decisions and replay. The existing Windows Job Object supervisor also stops the
whole child at 600 seconds, including startup; cleanup has its existing separate
three-second deadline. These are ceilings, not guaranteed coverage. The wrapper
does not reset the budget per policy/domain or retry failures. A stopped run
stays incomplete/failed, and partial evidence and the consumed ID are retained.

Public preparation commands, which never execute the policy:

```
python scripts/prepare_rule_study_receiving.py --draft --out <new-pending-request.json>
python scripts/prepare_rule_study_receiving.py --inspect <request.json> --out <new-assessment.json>
```

The pending request proposes an external absent output folder and unused ID;
neither a JSON flag nor a comment URL grants approval. The trusted host must
authenticate Matty's fresh exact decision against the request digest, merged
commit, limits, operation, ID and output. It must verify the relevant handoff
records. `dispatch_once` then checks Windows/Python3.12/locked versions, reserves
that ID durably and exclusively, rechecks drift, and invokes only the fixed
stdin-gated child. Without authority it does not read the request or touch a ledger.
The child verifies request/source bytes before project import, then repeats
preflight before calling the existing `run_receiving` API. It cannot import a
caller-selected module or launch an arbitrary command.

The wrapper reserves its outer output directory exclusively before failure
handling; the receiver writes beneath `traces/`. A destination created after
preflight is refused without adding a failure file to someone else's folder.
The receiving report is saved exclusively. Zero exit alone is not success:
containment cleanup and a retained PASS report are needed. PASS remains scoped
to those finite cases; it is not generalization, final accounting acceptance,
an unbounded proof, or an automatic scientific freeze. Nisha receives/interprets
actual findings before Edison generates a final evaluation set.

Offline tests cover closed stdin, changed bytes, source/domain drift, untrusted
approval fields, expanded limits, missing/wrong authority, single-use IDs,
post-approval drift, timeout/no retry, missing/failed/incomplete reports and
preserved backend failures. Research supervision and receiving are mocked in
these new host-wiring tests. No actual receiving batch has run here.

Edison's retained case/accounting/metric handoff is still needed for separate
accounting acceptance and final evaluation. It is not silently fabricated or
loaded as an input to the closed-case verification domain.
