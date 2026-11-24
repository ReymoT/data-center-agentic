# RULE-07 two-scenario demo: storyboard and runbook

Owners: Edison (storyboard, visuals, package) and Ved (executable wiring, replay,
commands), issue [#246](https://github.com/ReymoT/data-center-agentic/issues/246).
First reviewable package, November 24. Core deadline November 25, 18:00 Arizona.

The demo page is [`ui/rule_demo.html`](../../ui/rule_demo.html): one offline file,
no network access, built from evidence already on main. Nothing is run to make it.

## Provenance labels

Every panel on the page carries one label. Keep them when presenting:

| Label | Means |
|---|---|
| Expected | Specification text. Not a result |
| Observed | A saved trace, with its producer commit (`dbb8e6f` for the authored runs) |
| Independently checked | A receiving report (Nisha, comment 7117083623) |
| Pending | Not available yet. Never presented as a result |

## Storyboard and talk track

1. **Rules R01–R09** (Expected). The rule table, read from the RULE-01 specification.
   Say: rules-v1 picks most scheduled jobs first, then priority, then lowest artificial
   score, and executes only current-slot starts after the production check.
2. **Workflow** (Expected). Reimo's RULE-05 Figure 2 (#243): rules-v1 proposal →
   production check → checked Greedy A fallback → latest-state recheck → current-slot
   starts only, or refusal/drain with no new starts → trace → separate independent
   replay. The page lists its nodes, transitions and caption read from the Mermaid
   source in [RULE05_WORKFLOW_DIAGRAMS.md](../report/RULE05_WORKFLOW_DIAGRAMS.md);
   show the rendered figure there. Use Figure 1 from the same file for the introduction.
3. **Case A** (Expected, then Observed). Both jobs fit 60 kW at slot 0, so this is a
   timing choice, not a capacity problem. rules-v1 and Greedy B start J2 now and J1 at
   slot 1 (score 100 instead of 300); Greedy A starts both at once. Say: this delayed
   lower-score start is an observed authored example, not a measured advantage.
4. **Case B** (Expected, then Observed). Both rigid jobs need 20 + 30 + 30 = 80 kW
   against 60 kW, though each fits alone. The one-job proposal (50 kW) is not a capacity
   violation: the unchanged abstention gate refuses it because the other job's
   abstention has no individual physical justification. It refuses rules-v1's proposal
   and its checked Greedy A fallback, and Greedy A's and Greedy B's own proposals. No job
   starts; both end missed. Say: safe refusal with no partial progress; not a P1 success.
5. **Case B-fault** (Observed). A deliberately injected both-jobs proposal, shown with
   its arithmetic rejection (slot 0: 20 + 30 + 30 kW > 60 kW, excess 20). Say clearly
   that this is fault injection, not something rules-v1 proposed.
6. **Case B-progress** (Observed). The separate feasible subcase: J2 flexible with
   deadline 2, so both jobs complete one after the other.
7. **Verification** (Independently checked). All 202 required case-policy traces are
   fully replayed across the preserved attempts. The Nov 22 attempt stays INCOMPLETE as
   history; the Nov 23 continuation is PASS within its scope. S4 is NOT_RUN in the
   primary domain and PASS only for authored rules-v1 (B-fault). In the 12 jointly
   infeasible primary cases every policy starts no jobs.
8. **Metrics** (Observed, receiving Pending). The reviewed metric records for the 10
   authored runs: A 8,000 vs 12,000 artificial score-kWh, B-progress equal, B
   unavailable on a zero baseline (never zero savings). Artificial units; not emissions.
9. **Professor feedback** ([#231](https://github.com/ReymoT/data-center-agentic/issues/231)).
   The four dispositions, read from the working report: ten-fold refits and ML
   warm-start are future work; rule arithmetic is implemented without an LLM repair
   ablation; turnaround versus impact waits on accepted matched accounting.

Close with: finite bounded verification is not a universal proof; historical Agent/Plain
runs are not a matched comparison; missing-forecast cases are fallback/accounting
controls; the original Agent-versus-Plain question remains unanswered, and no result on
unseen synthetic cases exists yet. These caption limits follow
[Reimo's demo handoff](../handoffs/RULE05_DEMO_HANDOFF.md).

## Build the page

```
python scripts/build_rule_demo_page.py --out <new-file>.html
```

By default the metrics panel reads the reviewed records merged in #271,
`docs/evidence/rule04-dev-nov23/authored-metrics-reviewed.json` (SHA-256
`6d6b5630…8810dd8`, matching `REVIEWED_SHA256SUMS.txt`). `--no-metrics` shows that
panel as Pending. The page also lists the hash of `manager-review-receipt.json`. The original `authored-first-metrics.json` stays as historical producer output and is not the comparison shown. The output file is never overwritten.

Every archive member the page reads is checked against `AUTHORED_SHA256SUMS.txt`;
a mismatch refuses the build. Inputs and their hashes are listed at the end of the page.

## Executable replay (Ved)

Ved's demo CLI, from [the RULE-07 executable handoff](../handoffs/RULE07_EXECUTABLE_DEMO.md):

```
python -m dc_sustainability.rule_demo --list
python -m dc_sustainability.rule_demo --replay <supplied-saved-demo-directory>
```

Ved to verify these commands against the corrected merged source before the demo.
His older saved archive (`rule07-traces-a7a71d0`) is historical evidence bound to an
older producer; the page uses the Nov 23 authored traces (`dbb8e6f`) instead.

## Still to do

- Screenshots of the page for the report and a fallback recording. The local browser
  preview could not be opened during this build, so they are not included yet.
- No development-set or final-set results exist; they need separate authorization.
