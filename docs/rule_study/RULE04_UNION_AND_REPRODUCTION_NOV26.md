# Combined evidence and clean reproduction — November 26

November 26 accepted update: [Nisha's new-output and combined receiving](../handoffs/RULE04_COMBINED_RECEIVING_ACCEPTED_NOV26.md) is accepted within scope. Development coverage is 360/360; the 178-pair approved continuation succeeded with verified cleanup. Do not repeat receiving or seek authorization for that consumed run again. Actual clean scientific reproduction, final/unseen evaluation and final PDF/demo/release acceptance remain pending. [Offline next-scope preparation](RULE06_NEXT_SCOPE_OFFLINE_NOV26.md) is not execution approval. Earlier dated preparation statements remain historical.


Matty implemented `scripts/build_rule04_union.py` as read-only reporting preparation
for #242/#244. It executes no scheduler, simulator, verifier replay, generator or
model. Tests use declared artificial file fixtures. No new actual continuation,
combined scientific result or independent reproduction is claimed.

## Combined-results contract

The new external receipt has exactly these fields:

```
{"kind":"rule04_union_v1",
 "request":{"path":"<absolute suffix request.json>","sha256":"<raw hash>"},
 "artifacts":{"<relative suffix-output filename>":"<raw hash>","...":"..."}}
```

Create the complete artifact inventory only after the real contained attempt has
stopped and cleanup is verified. Review its raw receipt hash, preserve original
files and pass that exact hash to:

```
python scripts/build_rule04_union.py --receipt <receipt.json> --sha256 <raw hash> --out <absent separate directory>
```

The receipt must bind the actual consumed request, never a prospective request or
invented result. The original authenticated parent receipt and canonical consumed
ledger must remain available at their recorded locations. Local hashes corroborate
retained bytes; they are not signatures or proof of independent review.

Checks retain the parent's failure/status, distinct authorities and producer commits;
authenticate the original ordered prefix and only the selected unexecuted suffix;
check complete raw inventories, unchanged scientific/input pins, cleanup, pair
source identities and recomputed saved accounting; reject duplicates, gaps,
unacknowledged pairs, invalid counters and cross-attempt missing-forecast control
differences. Hashes and inventories are checked again after arithmetic.

The split overloaded/impossible case20 has rules/A on the parent source and GreedyB
on the suffix source. Producer bindings are never rewritten to make these appear
identical. The existing equal-work checker therefore retains `source_bindings_differ`
for that cross-source comparison. Coverage can include all three authentic runs
while that comparison remains unavailable. No scientific comparison rule changes.

`COMPLETE` means all360 expected development pairs are acknowledged, unique and
accounted for, with a corroborated successful suffix. It is not study acceptance,
unseen evaluation, universal verification or independent-person receiving. A stopped
suffix remains PARTIAL. Recovered unacknowledged pairs are refused pending separate
review; they are never silently retried. Known completed-pair counters are added;
unknown partial work and eligibility costs are not represented as zero. Per-attempt
limits/statuses remain separate, with no retroactive pooled execution budget.

## Ready reproduction preparation for Ved

1. Prepare a separate clean Windows/Python3.12 environment with the published hashed
   lock. Preserve current work. Record exact commit, dependency versions and commands.
2. Read the current rule specification, the163-pin scientific baseline and actual
   Nisha receiving record. Do not request the already accepted parent receiving again.
3. Receive the actual new output, exact request/approval, consumed ledger result,
   complete inventories and union receipt after a real attempt, if approved.
4. Static hash/accounting checks may proceed read-only. A new policy/replay batch
   is a separate scientific operation requiring its own reviewed bounds, unused ID,
   absent output and exact manager authorization. Never reuse either original ID.
5. Nisha checks new-output accounting/coverage and the combined reporter separately.
   Her original receiving is accepted only within its recorded scope; this document
   does not fabricate a new PASS from her or Ved.

November26–27 is the repair/reproduction window. The audited candidate remains due
November28 at18:00 America/Phoenix. Final isolation/evaluation, reproduction, report
integration and release audit are still unpassed; #242/#244 remain open.

## Report and professor-feedback disposition

Use the [actual received partial findings](../handoffs/RULE04_NISHA_RECEIVING_NOV25.md).
The182-pair parent attempt stopped at the wall-time reserve, not exhausted charged
state/transition counters. Missing-forecast coverage is0. Rules-v1 and GreedyB have
identical starts on60 jointly run cases. On four normal-feasible cases they leave10
jobs missed/unfinished while GreedyA completes them; missed/unfinished overlap.
Do not repair the frozen scientific scheduler inside reporting/controller work.

Grouped10-fold refits and ML warm-start remain future work. Exact rule arithmetic
is not an LLM repair-feedback ablation. Turnaround/artificial-impact comparisons
retain matched denominators, unavailable values and the artificial-unit label.
The evidence does not demonstrate unseen generalization or policy superiority.
After actual results integration, review the final PDF and demo for all four
feedback dispositions before closing #231; #223 also requires final assembly/audit.
