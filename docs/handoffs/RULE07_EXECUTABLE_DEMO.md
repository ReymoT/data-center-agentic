# RULE07 executable demo receiving — November 22, 2026

Implementation: Ved. Direct receiving fixes: MattyAnd. The actual branch is
`ved/rule07-executable-demo` (PR #261). The original implementer handoff is preserved
in RULE07_IMPLEMENTER_HANDOFF_NOV22.md; its local paths, old file names, counts and
runtime statements are historical, attributed observations, not manager certification.

## Current capability

`dc_sustainability/rule_demo.py` reuses the real RULE02 cases, common runner, checker,
Greedy A fallback and simulator. It shows expected versus observed behavior, actual
rule/arithmetic evidence, checked fallback/refusal and separate completion outcomes.
A/B/B-fault/B-progress remain distinct. No model or network call is introduced.

Case A demonstrates timing preference, not a capacity breach: both jobs plus background
fit 60 kW. Case B's proposed one-job load is 50 kW; the excluded joint load is 80 kW.
The unchanged individual-abstention gate refuses the partial proposal and fallback.
B-fault is deliberate injection; B-progress is a separate feasible sequential case.
A complete 30-decision trace is not the same as completed jobs or P1 success. Artificial
score-kWh, including zero from no execution, is not emissions or equal-work savings.

## Direct fixes

- Saved replay uses the runner's read-only lookup and an explicit read-only constructor
  mode. It cannot execute a missing decision or recreate missing evidence directories.
  Complete contiguous decision/reservation/commitment files are required before replay.
- Exact raw decision/case/result bytes are checked; newline conversion is not normalized
  into a false match. Linked roots/evidence/outputs and oversized artifact inventories
  fail closed. The existing common runner's normal execution default is unchanged.
- Greedy A/B replay uses the same declared score convention as the original run, fixing
  a replay fingerprint mismatch. Baseline comparison stays distinct from rules-v1.
- `--all --policy greedy_a|greedy_b` is refused rather than silently running rules-v1;
  B-fault remains rules-v1 only. Invalid choices are rejected before allocating output.
- Archive/manifest bytes are preserved, and stale local-only/published status claims and
  inconsistent ae9c343/a7a71d0 archive names are superseded by this handoff.

## Safe read-only review

```
python -m dc_sustainability.rule_demo --list
python -m dc_sustainability.rule_demo --replay <supplied-saved-demo-directory>
```

Scenario/interactive execution is a capability, not research authorization. A new
controlled evidence run must use a clean pinned implementation and the exact approved
bounded supervisor/authority before execution. Do not run `--all` as a substitute for
an approved current-code verification or unseen evaluation. Review ran only ordinary
authored unit fixtures; no separate live demo/scientific batch was dispatched.

## Supplied archive receiving

The actual supplied files are `rule07-traces-a7a71d0.tar.gz` and
`rule07-traces-a7a71d0.sha256`. Their read-only receipt is
RULE07_ARCHIVE_RECEIVING_NOV22.json: 617 file hashes match, with 120 decisions across four
rules-v1 cases, bound to published original code a7a71d005e8b329415b665951b9c56a63ee94110.
Archive paths/types were checked without extraction or policy execution. The checksum
manifest is byte-preserved on Windows. Hash matching is local integrity evidence, not
proof of the submitter's runtime or validation of the corrected demo source.

## Remaining delivery

Nisha's current-code receiving harness is reviewed separately in PR #260. It is not an
executed independent finding or freeze. Edison owns visuals/storyboard/package and Ved
executable wiring/replay under #246; Reimo supplies methods/diagrams. Their existing
Nov25 18:00 Arizona deadline remains. Actual independent findings, current-code controlled
execution, final metrics where displayed and the integrated demo package remain pending.
The original Agent-versus-Plain research question remains unanswered. No new ML/source/
private/final-seed or model operation is performed or authorized by this merge.
