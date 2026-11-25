# RULE04 retained-output summary review — November 24

Edison supplied `build_rule04_summary.py`, `rule04_summary_core.py` and their tests.
Matty reviewed and fixed the branch directly, preserving Edison's original commit.
The utility reads retained outputs only: it does not execute a policy, checker,
scientific replay, simulator, generator, training or model. No new study results
were produced during review.

## Corrections

- A PASS header alone could label an empty or incomplete batch COMPLETE. Completion
  now requires every frozen case/policy combination, matching counts and no failed pairs.
- Saved metric JSON was trusted without checking its traces or arithmetic. The loader
  now checks the fixed input hashes, retained artifact commitments, expected case,
  saved replay status, execution signature and recomputed metrics, including hidden
  evaluator weights. Changed metrics, mixed source/request identities and unbounded,
  linked, duplicate-key or nonfinite inputs are refused. This is retained-data
  consistency; it does not create independent scientific/person receiving.
- The host supervisor's fallback summary was ignored. Failure now takes precedence
  over a PASS report, and a complete host summary can accompany an original truncated
  child record. Completed results beyond an older checkpoint are reported explicitly
  as recovered/unacknowledged; missing or failed work is not silently passed.
- The plot could combine reduction and delay statistics from different case subsets.
  Both axes now use the joint matched subset, with its own count. Reductions use a
  dimensionless percent axis with numeric ticks. Missing-forecast controls stay out
  of rankings/plots, and expected versus unevaluated counts remain visible.
- Empty impact groups show unavailable rather than measured zero. Output is exclusive,
  unlinked and outside the retained run; input files are not overwritten.

## Use after actual evidence exists

```
python scripts/build_rule04_summary.py --run-dir <retained-run> --out <new-separate-directory>
```

The default case set is the frozen 120-case development set; `--cases` can relocate
the identical bytes, not substitute another experiment. Outputs are `summary.json`,
`RULE04_TABLES.md` and `turnaround_vs_impact.svg`. Missing comparisons retain reasons;
missed and unfinished overlap; artificial score-kWh is not emissions. Partial output
is not representative of unexecuted strata or unseen generalization. It does not
close #242 or #244 or establish that the original research question is answered.

16 summary checks pass, including read-only recomputation from the retained authored
archive and rejection of tampered metric values. Synthetic aggregation fixtures are
explicitly marked and refused by the real CLI; they are not scientific outputs.

## Source identity consequence

Two reporting scripts expand the required Python-source inventory from 169 to 171.
All previous 169 hashes and all 163 accepted scientific bindings remain unchanged.
[Revision 4 metadata](../rule_study/RULE04_PROTOCOL_FREEZE_NOV24_REPORTING.json) records
the added files without changing rules, inputs, order, metrics arithmetic or caps.
The unapproved request `3166a21c…4ef05` is superseded. A fresh clean merged-source
request and exact informed authorization remain required before an actual run.
