# D06 independent reproduction record and runbook

Owner: Ved (D06). Source owner: Reimo (D01/D02/D05). Status: **partial source evidence, not D06/Q05 acceptance** (see "What this does not settle").
This document reuses the existing F02 schemas and `docs/INTERFACES.md` unchanged; they are not needed for this check.

## Quick run (Linux/macOS shell; run from the repository root)

```sh
python3 -m venv .venv && . .venv/bin/activate     
python3 -m dc_sustainability.data.carbon_source 'data/raw/AZPS_NG_&_avgCI.csv' --download --report data/processed/d06-adapter-run1.json
python3 scripts/d06_check_window.py 'data/raw/AZPS_NG_&_avgCI.csv' --day 2022-01-01 --report data/processed/d06-window-run1.json --compare-adapter
```

Expect `RESULT: PASS (structural)` and exit status 0 from the last command. For a rerun use new
report names (`run2`); both tools refuse to overwrite. If `data/raw/` already holds the CSV, omit `--download` on the first command.
Commands above were run on Linux (Python 3.12.3). Windows PowerShell equivalents (`py -3.12 -m venv .venv`, `.venv\Scripts\Activate.ps1`) are **unrun/unverified**.

## 1. Prerequisites

- Work in the repository root (`git status --short` first; do not discard existing changes).
- The adapter and the checker use only the Python standard library. No install is needed for them.
- Tests need `pytest`. The repository's real install path is the hashed Windows lock in `requirements/README.md`
  (`--require-hashes`); it was not run here. On Linux the focused tests ran with `pip install pytest ruff` in a throw-away venv (not the project lock).
- `data/raw/` and `data/processed/` are gitignored. Never commit the CSV or reports.

## 2. Source and adapter (verified CLI: `source`, `--download`, `--report`)

| Step | Command | Success looks like | Failure / next |
|---|---|---|---|
| Acquire + validate | the first quick-run command | exit 0; a JSON report with `"pinned_checksum_matches": true`, `"errors": []` | checksum mismatch or network error: stop, record the exact message; do not edit the file |
| Show report | `python3 -m json.tool data/processed/d06-adapter-run1.json` | `row_count` 8760, first/last timestamps, min/max/mean | report path exists: choose a new name |
| Local file only | same command without `--download` | same report | missing file: run with `--download` or place the pinned file in `data/raw/` |

Source: `https://raw.githubusercontent.com/HewlettPackard/dc-rl/a92b4755aca560e34a98d14028dda629eb968482/data/CarbonIntensity/AZPS_NG_%26_avgCI.csv`.

## 3. Independent checker (`scripts/d06_check_window.py`)

It does not import the adapter for its own checks. It re-parses the CSV, computes SHA-256 and the Git blob SHA-1,
checks header, row count, explicit-UTC hourly continuity, duplicates, finite/nonnegative values for all numeric columns,
year min/max/mean, and prints the 24 UTC rows of `--day`. `--compare-adapter` is an additional cross-check against
`load_source`. The JSON copy is `--report` (local only). The window is a UTC calendar day, **not** the Phoenix-midnight episode mapping.

## 4. Results of the run recorded on 2026-10-19T02:54Z (sandbox clock; 2026-10-18 evening Phoenix)

Environment: Linux 6.18, Python 3.12.3. File size 601,730 bytes.

| Check | Observed in this run | Prior reference | Match |
|---|---|---|---|
| SHA-256 | `e05789a1…ef24ef4` (full value in the checker output) | same | yes |
| Git blob SHA-1 | `d5337a654e77c938d0909e76d56efdf3ad491e83` | same | yes |
| Header | `timestamp,WND,SUN,WAT,OIL,NG,COL,NUC,OTH,avg_CI` | same | yes |
| Rows / span | 8,760; 2022-01-01T00:00Z to 2022-12-31T23:00Z | same | yes |
| Duplicates / non-hourly steps / bad values | 0 / 0 / 0 | n/a | n/a |
| Year avg_CI min / max / mean | 251.22162645218947 / 749.1955146635997 / 575.0418721742574 | same | exact equality |
| 2022-01-01 UTC window rows | 24, contiguous | 24 | yes |
| Window first / last | 631.6617084572886 / 541.7221627408993 | same | exact equality |
| Window min / max | 541.7221627408993 / 672.2776436504105 | same | exact equality |
| Window mean (new in this run) | 627.8557634621563 | none | n/a |
| Adapter vs checker, 24 values | identical | n/a | yes |

The 24 individual values are kept in the local report, not in Git, because redistribution rights are unresolved.

## 5. Focused tests

```sh
python3 -m pytest tests/data/test_carbon_source.py tests/data/test_d06_window_check.py -q
python3 -m unittest discover -s tests/data -p test_carbon_source.py -v
python3 -m unittest discover -s tests/data -p test_d06_window_check.py -v
```

Passed means a line like `15 passed` (pytest) or `OK` (unittest) and exit 0. "Attempted" with
`ERROR`/`ImportError` is not a pass. Observed: 12 adapter tests and 3 checker tests passed.
Plain `python3 -m unittest discover -s tests/data` errored on `test_frontier` (`No module named 'pyarrow'`) and `test_scenarios`
(no `pytest` in the system interpreter): those are D02/D03 modules, not D06, and were not fixed here.
These tests use synthetic data; they are not source acceptance.

## 6. What this does not settle

- Units: g/kWh is supported by upstream code; CO2 vs CO2e, GWP, system boundary and exporter method remain unverified (Q05).
- Time: hourly UTC continuity does not show whether a label is interval start or end. The adapter's `episode_indices` start-convention helper stays provisional; the mapping is unchanged.
- License: the repository's MIT license is not shown to cover this dataset; keep data out of Git.
- eGRID: regional magnitude only; AZPS factor alignment unverified.
- Frontier D02 is separate: the latest record in the repo (2026-10-13, `data/manifests/d02-source-status.json`) says blocked on credentials/semantics. Today's status is unconfirmed.

## 7. Troubleshooting (never delete user work, loosen validation or edit source data)

| Symptom | Fix |
|---|---|
| `No such file` for the CSV | Run the adapter with `--download`, or check the quoted path (`&` needs quotes). |
| `ModuleNotFoundError: dc_sustainability` | Run from the repository root; the checker adds the root itself only for `--compare-adapter`. |
| `No module named pytest` / `pyarrow` | Install into the venv only (`pip install pytest`); `pyarrow` is only for D02 tests. |
| `unrecognized arguments` | Use only `--download` and `--report` for the adapter; check `--help`. |
| Network/download failure | The adapter rejects before saving; retry, or report network settings. Do not hand-edit a file. |
| Checksum mismatch / gap / bad timestamp | Stop. Keep the report and the file, report both to Reimo. Do not sort, fill or round. |
| `refusing to overwrite` / report exists | Use a new report name. |
| Existing Git changes | `git status --short`; commit or stash nothing you did not write. |

## 8. Safe handoff

```sh
git status --short
git diff --check
```

D06 deliverables: `scripts/d06_check_window.py`, `tests/data/test_d06_window_check.py`, `data/D06_REPRODUCTION.md`.
Local only (gitignored, never commit): `data/raw/*.csv`, `data/processed/d06-*.json`, `.venv/`.
Running the check does not require pushing, opening a PR or commenting.
