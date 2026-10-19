# D06 handoff verification and F04/F05 documentation

Owner: Matty Anderson (MattyAnd). D06 owner: Ved. Date: October 19, 2026.
Tracking: [maintenance issue #20](https://github.com/ReymoT/data-center-agentic/issues/20)
and [D06 issue #13](https://github.com/ReymoT/data-center-agentic/issues/13).
Instruction deployment: 1.13; F02 contract: 1.0.0.

Matty requested verification of Ved's merged handoff and the corresponding project
documentation. Branch: `matty/d06-handoff-docs`, based on merged main
`488ddfb3a4b8442e65d5d27140304bca6746e6fd`. No task ownership, scientific decision,
shared setting or production code changes are included.

## Evidence inspected and reproduced

[PR #19](https://github.com/ReymoT/data-center-agentic/pull/19) merged D06 head
`261c382af6aecc06a10c3970c9bffc6c3f03178c`. Its PR CI and merged-main CI passed.
The merged branch was subsequently deleted after ancestry and exact-head checks.
That merge alone did not establish source acceptance.

Ved's [original handoff](../../data/D06_REPRODUCTION.md) describes a Linux source
run, while [his issue reply](https://github.com/ReymoT/data-center-agentic/issues/13#issuecomment-6261979911)
states that earlier JSON lacks `year.valid_timestamp_rows`. The merged checker
requires that field to equal 8,760. Its test suite also contains nine checker tests;
the handoff's older three-test count describes earlier evidence.

Matty ran the unchanged merged D01 downloader and D06 checker in the existing
Windows Python 3.12.14 environment. The source came from the exact pinned public
URL and was saved to a new ignored filename. The new reports include the required
field. [The compact verification record](../evidence/d06-matty-verification-2026-10-19.json)
records acquisition/run times, source/code/report hashes, environment, structural
checks and limitations without the CSV or the individual hourly values.

Observed results:

- Source size: 601,730 bytes; SHA-256
  `e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4`;
  Git blob `d5337a654e77c938d0909e76d56efdf3ad491e83`.
- Exactly 8,760 source rows and valid timestamps, with no duplicate timestamps,
  non-hourly steps or reported problems.
- January 1, 2022 UTC: 24 contiguous observations and all expected hours present.
- All recorded annual/January 1 reference comparisons match. The separate adapter
  comparison has 8,760 rows and identical values for the inspected window.
- The real CLI exited 0 with `RESULT: PASS (structural)`; applying the merged
  `result_passes(..., compare_adapter_requested=True)` to its new report returned true.
- Focused synthetic tests: 21 passed and 19 subtests passed. Separate unittest runs
  passed 12 adapter tests and nine checker tests. These test fixtures are separate
  from the actual-source reproduction above.

This independently verifies the current code/report pairing on Windows. It does
not authenticate Ved's earlier JSON or claim that he regenerated those reports.
The original run is retained as historical evidence with a dated verification addendum.

## Reproduce the Windows verification

Run from the repository root in the existing environment. Use new filenames for
each run. Acquisition uses the network; inspecting the saved source does not.

```powershell
.venv\Scripts\python.exe -m dc_sustainability.data.carbon_source data/raw/matty-d06-source-run2.csv --download --report data/processed/matty-d06-adapter-run2.json
.venv\Scripts\python.exe scripts/d06_check_window.py data/raw/matty-d06-source-run2.csv --day 2022-01-01 --report data/processed/matty-d06-window-run2.json --compare-adapter
.venv\Scripts\python.exe -m pytest tests/data/test_carbon_source.py tests/data/test_d06_window_check.py -q
```

The verification used the same commands with the recorded `2026-10-19` filenames;
`run2` above prevents overwriting that evidence. The full JSON reports and CSV stay
in ignored `data/processed/` and `data/raw/`. Their checksums are in the compact
record; its hashes identify the actual reports but do not make their omitted
contents independently accessible from Git. A new reproduction produces fresh
timestamps/report hashes while source identity and structural results should match.

## Remaining limits and receiving work

This is source-integrity/window evidence, not an approved policy-facing carbon fact,
a frozen dataset or a completed scheduling experiment. Q05 pollutant basis,
interval convention, dataset rights and factor alignment remain unresolved.
Q06 distribution/seeds/splits/freeze and F02 carbon/forecast consumer adoption
remain separate gates. A UTC calendar day is not the Phoenix-midnight, 30-slot
episode mapping. No source values were transformed or supplied to a policy.

The unchanged D01 report still emits an older combined warning mentioning Ved's
independent reproduction. Treat that string as historical implementation text;
this handoff records the new bounded evidence without deleting other source warnings.
Ved's original evidence-version caveat remains attached to his original reports.
D06 issue #13 stays open for its remaining acceptance requirements.

README, plain-language architecture and diagram, data guidance, the plan and
instruction status references now acknowledge this bounded D06 result. No positive
research finding, semantic approval or completed integration is inferred. This
maintenance increment does not finish the ongoing F04/F05 duties.

Local publication checks also passed: 810 tests and 19 subtests; Ruff lint and
formatting for 49 Python files; compilation; installed dependency consistency;
setup validation of versions, links, task inventories and policies; whitespace.
The architecture SVG/PNG were regenerated and visually inspected. Hosted checks
are recorded in issue #20 after publication.

A01 remains waiting for Nisha/Ved's Q09 input. The unsent Q01-Q04 draft and deferred
D02/Q13 follow-ups are untouched. Final local/hosted publication checks are recorded
in issue #20 after they run.
