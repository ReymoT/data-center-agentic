# D05 reproduction and validation

Run from repository root on `reimo/d05-source-evidence`, based on main
`2ec1e542c09066e2cf4d05953c5f076566a1e657`. Source acquisition and the existing
adapter/checker use only the standard library; CPython 3.12 is the project target.
Linux/macOS shell commands below use a fresh temporary directory on every run.
Keep its raw data/reports private. No dependency lock or dataset is rewritten.

## Retrieve pinned data and validate identity

This retrieves an existing derived CSV. It does **not** regenerate it from EIA.
Network access is needed for the first command. Never remove an existing output
to make a rerun pass: rerun `mktemp` and use the new directory. Both adapter output
paths are exclusive; a failed checksum must stop acquisition without changing bytes.

```sh
D05_RUN=$(mktemp -d /tmp/d05-reproduction.XXXXXX)
python3.12 --version
python3.12 -m dc_sustainability.data.carbon_source "$D05_RUN/AZPS.csv" --download --report "$D05_RUN/acquisition.json"
python3.12 -m json.tool "$D05_RUN/acquisition.json"
```

Expected: exit 0; report `validation.pinned_checksum_matches=true`, `errors=[]`,
8,760 rows, SHA-256 `e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4`.
Timestamps and summary ranges are in C03/C13 of [the evidence matrix](D05_SOURCE_EVIDENCE.md).
Acquisition UTC is recorded by the adapter; it is not the historical EIA acquisition time.
For a previously acquired private file omit `--download`, select that file as the
source and choose a new report name. A validation failure exits 1; network and
overwrite failures raise errors. Do not loosen checks, sort, fill, round or shift rows.

The completed independent structural/window results are reused from
[D06](D06_REPRODUCTION.md) and [Matty's exact-code evidence](../docs/evidence/d06-matty-verification-2026-10-19.json).
For an independent reviewer who needs a new local report, the optional existing
command is below; D05 does not require repeating it to decide source meaning:

```sh
python3.12 scripts/d06_check_window.py "$D05_RUN/AZPS.csv" --day 2022-01-01 --report "$D05_RUN/window.json" --compare-adapter
```

Expected exit 0, `RESULT: PASS (structural)`, 24 UTC-calendar-day rows. This is not
a Phoenix 30-hour mapping or verification of units, rights or scientific suitability.

## Recalculate the supported fixed-factor interpretation

This checks arithmetic on the pinned CSV, not historical EIA-to-CSV regeneration.
With `D05_RUN` still set, it produces a compact exclusive JSON report and no hourly
values. Changing factors to force agreement is not allowed.

```sh
python3.12 - "$D05_RUN" <<'PY'
import csv
import hashlib
import json
import platform
import sys
from pathlib import Path

root = Path(sys.argv[1])
payload = (root / "AZPS.csv").read_bytes()
digest = hashlib.sha256(payload).hexdigest()
assert digest == "e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4"
factors = {"WND": 11, "SUN": 41, "WAT": 24, "OIL": 650,
           "NG": 490, "COL": 820, "NUC": 12, "OTH": 230}
rows = list(csv.DictReader(payload.decode("utf-8").splitlines()))
differences = []
for row in rows:
    generation = {fuel: float(row[fuel]) for fuel in factors}
    denominator = sum(generation.values())
    assert denominator > 0
    calculated = sum(generation[f] * factors[f] for f in factors) / denominator
    differences.append(abs(calculated - float(row["avg_CI"])))
report = {"python": platform.python_version(), "source_sha256": digest,
          "rows": len(rows), "max_absolute_difference": max(differences),
          "factors": factors, "scope": "arithmetic only; exporter unverified"}
with (root / "formula.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps(report, sort_keys=True))
assert report["rows"] == 8760 and report["max_absolute_difference"] == 0.0
PY
```

Expected: 8,760 rows, maximum absolute difference 0.0 and matching source checksum.
Numerical agreement does not authenticate the original exporter revision or CO2e boundary.

## Regenerate only the permitted synthetic development catalog

F02 records import Pydantic. Use an already installed project environment, or
create an isolated minimal environment as below (network/package cache needed for
installation). The version matches `requirements/requirements-core.in`; this
minimal macOS check does not certify the hashed Windows lock or full project setup.

```sh
python3.12 -m venv "$D05_RUN/venv"
"$D05_RUN/venv/bin/python" -m pip install pydantic==2.14.0
"$D05_RUN/venv/bin/python" -m dc_sustainability.data.scenarios "$D05_RUN/d03-jobs.json" --seed 42 --split development
cmp "$D05_RUN/d03-jobs.json" data/manifests/d03-provisional-jobs.json
```

Expected: both exit 0; `cmp` is silent; SHA-256
`ea8f414bf21035db04d75ca8ff1815aae94e940d02295ee7dd99a41e0dc38ad5`.
This regenerates labeled synthetic jobs only, without external data, carbon mapping,
40/30 allocation, calibration, held-out loading or fixture freeze. Original D03
verification used CPython 3.12.15; record the current runtime alongside outputs.
D02 has no verified real-data command/configuration: use its documented API only
after actual file, field dictionary, units and license evidence are obtained.

## Original EIA regeneration remains blocked

There is no verified end-to-end command/environment for recreating the pinned CSV
from historical EIA inputs. Do not execute upstream download/extract code against
the current mutable archive and call it reproduction. C09 lists exact missing
inputs. Once supplied, Reimo must pin archive hash, series, exporter, parameters,
dependencies and serialization; run into a new directory; compare all source
columns/timestamps and final bytes against the preserved pinned input; retain
exclusion/transformation/difference reports. A mismatch is evidence to investigate,
not permission to overwrite the original. Ved verifies this separately from suitability.

## Documentation and existing validation checks

```sh
python3.12 scripts/validate_setup.py
python3.12 -m unittest discover -s tests/data -p test_carbon_source.py -v
python3.12 -m unittest discover -s tests/data -p test_d06_window_check.py -v
git diff --check
```

These are offline checks; they require no pytest, paid calls or real model runtime.
The setup validator checks repository instruction/link consistency, not scientific
source validity. Broader data pytest checks require the project's installed
dependencies; no new tests are needed for this documentation-only change.

## Observed in this D05 session

macOS ARM64, CPython 3.12.15. Pinned document retrieval succeeded for all six
documents in [the document manifest](manifests/d05-document-evidence.json); the
three document hashes already in D01 match exactly. No upstream code was executed.

The pinned retrieval and formula blocks above were executed verbatim using
`/private/tmp/d05-reproduction.pCIPWy`. Acquisition succeeded at
`2026-10-24T22:21:58.008791+00:00`, with expected SHA-256, 8,760 rows and no errors.
The formula report returned max absolute difference 0.0. Private report hashes:

| Local artifact | SHA-256 |
|---|---|
| `acquisition.json` | `b97b8598bbf4693b0f0131a797b49e546eebc2a7fd12530129937ed0397316ea` |
| `formula.json` | `d301baf9e24e2c4c38f6eaee88fb783b2608234d3e8f7a0d3c3d7aad5f3a6b25` |

The first catalog attempt with bare Python failed with missing `pydantic`; this
did not create or modify the tracked catalog. Retried using isolated
`/private/tmp/d05-validation-venv` with Pydantic 2.14.0, pydantic-core 2.50.0,
annotated-types 0.8.0, typing-extensions 4.16.0, typing-inspection 0.4.4.
The same seed/split command wrote `/private/tmp/d05-catalog-20261024.json`;
byte comparison passed and its SHA-256 matched the expected catalog hash above.
The runbook now explicitly includes that environment prerequisite.

`scripts/validate_setup.py` passed, D01 unittest passed 12 tests, D06 unittest
passed nine tests, and `git diff --check` passed. The optional actual-source D06
window rerun was not performed: its existing accepted evidence is reused. No
full-suite/Windows-lock verification, live model calls, EIA regeneration,
held-out evaluation, scientific acceptance or independent Ved approval is claimed.
