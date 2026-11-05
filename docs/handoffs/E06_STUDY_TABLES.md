# E06 study tables

Task ID / Issue: E06 preparation, [#60](https://github.com/ReymoT/data-center-agentic/issues/60). Owner: Nisha. Technical contact: Edison.
Objective: turn saved runs into the study tables using the merged E03 helpers, so final scoring is one reproducible command once frozen outputs exist.

Changed paths:
- `dc_sustainability/evaluation/study_tables.py` (new): `planned_episode`, `score_runs`, `observations`, `paired_rows`, `savings_rows`, `scenario_rows`, `tie_rows`, `study_report`.
- `scripts/build_study_tables.py` (new): builds the report from explicit bundles and unit folders.
- `tests/evaluation/test_study_tables.py` (new, 28 tests).
- `docs/report/R05_EVALUATION.md`, `docs/i02/freeze-manifest.json`: status wording only.

What it does:
- **Scoring.** Each saved run goes through `run_metrics`. A planned run that's absent stays missing in the paired counts, and a saved run E03 refuses is listed with its reason.
- **Cohorts.** Core episodes are the main comparison, and withheld-forecast episodes are reported apart, following [the recorded analysis response](../decisions/E03_ANALYSIS_MANAGER_2026-11-04.md).
- **Paired rows.** Candidate minus baseline for every metric, each with episode and date intervals and exclusion counts. Both unsafe measures appear at every stage.
- **Emissions.** Raw emissions are not paired, because that would compare runs that did different work. Paired emissions come only from the equal-work savings rows, and scenario summaries still describe them.
- **Savings.** Only systems with the same trials are compared. Pairing one classical run with three LLM trials stays refused until that rule is agreed.
- **Forecast ties.** Pooled from Greedy B's runs by cohort.
- **Labels.** A report covers exactly one split, states that split and carries `not_a_frozen_result`, so development tables can't pass as held-out findings.

Limits:
- The analysis decisions are a manager response awaiting affected-owner confirmation. This code follows them, but it doesn't freeze them.
- The script treats a unit without `result.json` as missing, so `units_without_result` is a count and doesn't name the unit.
- References and exact gaps (O03/O04), claim scoring, faithfulness scores, figures and the failure analysis aren't part of these tables yet.

Tests: 28, with hand values for 54.5 and 48.4 kg (savings 6.1 kg). Mutation check: fifteen deliberate bugs each made tests fail, and the code was restored. Review before testing also removed a paired raw-emissions row.

Private receiving check: the report ran on the six saved EP-HAND1 development units held under the I01 receiving custody. All six scored, Plain-against-Agent savings were blocked for different work, and the Greedy B tie counts match the published example. Those records and the output stay private.

Input and output contract/config versions: F02 1.0.0, unchanged.
Artifact locations and checksums: none.

Exact reproduction commands:

```powershell
.venv\Scripts\python.exe -m pytest tests/evaluation/test_study_tables.py -q
.venv\Scripts\python.exe scripts/build_study_tables.py --bundle <bundle.json> --unit-dir <unit folder> --out <new private file>
```

Repeat `--bundle` and `--unit-dir` as needed, and use `--model-trials` when a run has fewer than three LLM trials. Write the output to private storage until its contents are reviewed.

No model calls, held-out data or source values were used.
