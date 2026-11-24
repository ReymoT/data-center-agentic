# RULE07 first demo package receiving — November 24, 2026

Implementation: Edison, original PR #275 head `3699684bbcf4dd0656754e2300d35529482084ac`.
Direct review/fixes: MattyAnd. Base main `7aeff4cfb46d91f8cbc5d2009f6e3b8b7094bd85`,
instruction 1.30. Preserve Edison/Ved ownership of final demo production under #246.

The offline HTML page presents rules, workflow source, A/B/B-fault/B-progress,
saved production checks/refusal, accepted finite verification, reviewed authored
metrics and all four feedback dispositions. It does not execute policies or models.

## Problems fixed directly

- The archive reader previously required only a case, result and decision zero for
  each run it happened to find. Missing whole runs or later decisions could silently
  produce a partial presentation. It now requires all ten expected case-policy runs,
  every decision 0–29, matching identities/indexes, complete results and each decision's
  result commitment; duplicate archive members/checksum names refuse the build.
- The metrics option previously read arbitrary JSON without checking the published
  reviewed checksum or binding it to these authored inputs. Metrics and receipt now
  require the sibling reviewed checksums, matching archive digest and producer pin.
  These integrity checks do not replace Nisha's independent accounting acceptance.
- A relative link called a Markdown source file a rendered diagram and broke when
  the standalone HTML moved. The page now identifies editable source plainly and
  retains the embedded node/transition table without that broken link.
- Long provenance hashes can wrap inside tables; metric labels are escaped once.
- The HTML was rebuilt using the corrected builder and the source inventory includes
  the demo sources, tests, storyboard, page and this handoff.

Six new regressions cover missing runs, missing later decisions, duplicate members,
tampered metrics, missing review material and portable source labeling. All 57 focused
demo-page/source-guard tests pass. Exact final-head PR and merged-main CI remain the
merge/cleanup gates; their actual results are recorded in PR #275 and #246.

## Visual and command review

Matty opened the rebuilt local HTML in Chrome and inspected scenario A's load/score
chart and the expanded B-fault stage table on November 24. The latter shows
20 + 30 + 30 > 60 kW, excess 20, then refused Greedy A fallback and no executed starts.
The separate B-progress section remains distinct. Dedicated report screenshots and a
fallback recording remain final-package work; browser inspection is not a claim that
those deliverables were included. `rule_demo --list` succeeds; source inspection and
ordinary offline replay fixtures cover the documented replay wiring. No real saved
scientific replay or new batch was dispatched during this review.

Only retained evidence was read to build the page. Raw provenance hashes describe
the build checkout and do not authenticate their own source. No changes to the frozen
scientific package, masters, inputs, scientific outcomes or independent approvals.
Accounting receiving, whole-study freeze, authorized 120-case comparison and unseen
generalization remain pending. This receives the first reviewable package, not final
completion of #246. First draft deadline is November 24 at 18:00 Arizona; core remains
November 25, repair/reproduction November 26–27, candidate November 28 at 18:00.
