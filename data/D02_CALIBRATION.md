# D02 Frontier calibration: implemented tooling, blocked source acceptance

Owner: Reimo; technical contact: Edison. Prepared 2026-10-13 on
`feature/reimo-d02-frontier`, based on main
`dea17effd3394c1950759ad23ef8dd0ef343c9db`, instruction deployment 1.9.
No assigned D02 Issue exists in the repository issue listing read during this session.
No Issue was created or changed, and no independent receiver acceptance is claimed.
The latest audit read was `docs/team/REVIEW_RECORD.md`, including the subsequent
A01/F03 model setup (264 prior tests and 19 subtests).

## Exact source and access blocker

The local `Data_Center_Sustainability_Proposal_Short.doc`, section 2.1/reference 10,
names [Frontier Job-Centric Telemetry Dataset](https://doi.org/10.13139/OLCF/3013979):
approximately 39 MB, 26 fields, 152,400 job records. These are proposal expectations,
not inspected file facts. Its SHA-256 is
`913cb6c96049235dbafbcb484d20790aaceab348dbc6cc0b2b5920445b1b6fb7`.
The available longer September draft has SHA-256
`fc3d461156bf81bdef9f01a3afa8abf7b2b459735e24c92fb961e4913e136501`;
neither matches the historical final-document hash in `docs/SOURCE_REVIEW.md`.
The authoritative October final attachment remains unavailable; no document authority
has been replaced. The short version independently identifies the requested dataset.

[ORNL's source landing page](https://doi.ccs.ornl.gov/dataset/2cfa2292-3f9d-549c-b2d2-c9aff1557218)
confirms 152,400 selected jobs ending in 2024/2025, about 6.8% of nonzero-runtime jobs,
and Parquet storage. Selected-day sampling and leadership-sized workloads limit
representativeness. The observed release date is September 2, 2026.
Public page retrieved on 2026-10-13, SHA-256
`c7508efb7b1b0547ba4ec9eb966f038024350bcd3c4677086ac0643eb0ab35fb`.
This hashes the metadata response, **not the job table**.

Its [download link](https://app.globus.org/file-manager?destination_id=57618e0a-2c99-45ff-9694-24141b92fa17&destination_path=%2Fgen101%2Fworld-shared%2Fdoi-data%2FOLCF%2F202609%2F10.13139_OLCF_3013979%2F)
uses collection `57618e0a-2c99-45ff-9694-24141b92fa17`, directory
`/gen101/world-shared/doi-data/OLCF/202609/10.13139_OLCF_3013979/`.
The endpoint metadata API returned HTTP 400, code
`ClientError.AuthenticationFailed`, message `No credentials supplied`.
The browser tool had no connected browser; native Chrome was blocked by an existing
extension installation permission dialog, which was left untouched.
No job table, dictionary, license, or node telemetry was downloaded.

**Unblock:** obtain only the job-information Parquet file and its README/dictionary
through authorized Globus access or a publisher-provided direct download. Record
file name/version, byte checksum, acquisition UTC time and license. Verify exact
column names/types, runtime and requested-walltime units, mean-power dimensional
unit, aggregation across time/nodes, and IT versus facility/component scope. The
current adapter supports scalar seconds/minutes/hours and W/kW/MW, with job-total
or per-node mean power. Other encodings require implementation based on evidence.
Do not infer units from magnitude or multiply/divide node power without evidence.

## Implemented adapter and reproducible exclusions

`dc_sustainability.data.frontier` accepts an explicit `FieldMapping`; its names
are configuration, not a substitute shared schema or a claim about Frontier fields.
`inspect_parquet` verifies expected SHA-256 before reading configured job columns,
records actual schema, file size, acquisition/version evidence, F02 `SourceRef`,
row counts, exclusions, statistics, and a checksum of sorted normalized accepted rows.
Acquisition time must be UTC-aware; filesystem timestamps are never substituted.
Raw inputs and reports belong in ignored `data/raw/` and `data/processed/`.

Each row requires a nonblank string or integer ID; positive finite runtime, walltime,
power; and positive integral node count. Booleans, missing/non-numeric values,
zero/negative values, NaN/infinity, fractional nodes and conversion overflow are
excluded. All occurrences of duplicated IDs are excluded, including valid rows
whose duplicate has another invalid field. All applicable reasons and zero-based
row indexes are retained; reason counts overlap, whereas excluded-row counts do not.
Missing configured fields and duplicate Parquet field names fail the table.
No filling, imputation, success-status selection, arbitrary outlier deletion, or
runtime ≤ requested-walltime rule is applied. These criteria are reproducible
proposals; source-specific identifiers/status conventions still need inspection.

Runtime and requested walltime convert separately to seconds. Power converts to
kW and multiplies by node count **only** for an explicitly evidenced per-node mean.
No PUE multiplication occurs. Statistics cover the same joint complete-case cohort:
count, mean, population standard deviation, min/max, and p0/p1/p5/p25/p50/p75/p95/p99/p100.
Quantiles use linear interpolation at `(n-1)*p` (Hyndman-Fan type 7).
An empty cohort has null statistics in the inspection report; standalone statistics
raise an error. No empirical statistics or filtering counts are available yet.

After evidence inspection, instantiate `FieldMapping` with the verified names,
units, power scope and dictionary reference, then call:

```python
rows, report = inspect_parquet(
    Path("data/raw/<verified-job-table>.parquet"), verified_mapping,
    expected_sha256=verified_digest, source_version=verified_version,
    acquired_at_utc=recorded_acquisition_timestamp,
)
Path("data/processed/d02-report.json").write_text(
    json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
)
```

This is an API example requiring imports and verified evidence, not an available
CLI or a runnable source configuration. Report files should use a new destination.

## Proposed deterministic scaling: approval required

For each accepted original row, retain runtime/power pairing. For each marginal,
compute p05 and p95 on the accepted calibration population; clip values to those
anchors and calculate `z = (clipped_value - p05) / (p95 - p05)`.
Duration is `floor(1 + 3*z + 0.5)` hourly slots; IT power is `10 + 30*z` kW.
Degenerate anchor ranges fail, requiring an agreed alternative. The rule is
deterministic and independent of row order. No random sampling or seed is chosen.
Clipping changes tails; duration rounding and independent marginal scaling change
energy and joint dependence. This shapes synthetic demand and does not physically
reproduce Frontier or preserve energy. Requested walltime remains descriptive;
it supplies neither synthetic deadlines nor flexibility. No episodes are generated.

Q05 requires verified physical/source semantics and redistribution evidence.
Q06 requires Reimo/Edison/Ved/Nisha agreement on clipping, linear versus logarithmic
scaling, hourly rounding, job-total versus per-node calibration basis, sampling,
seeds and requested-walltime use before D03/freeze. The proposal's constant job
power and fixed PUE 1.2 (hand checks 1.0) remain explicit modeling assumptions.
Facility power must not silently be relabeled IT power. No shared setting is adopted
by this proposal function and no decision record is changed.

## Acceptance and scope

Offline tests use labeled synthetic field names/values, covering units, exclusions,
duplicates, checksum/schema failures, statistics, deterministic bounds, degenerate
ranges, provenance and construction/round-trip of existing F02 `Job` records.
F02 code/public contracts, D01 and all instruction files are preserved. D03, D04,
S01 and teammate components are untouched.

D02 acceptance is **not satisfied**: exact data acquisition, observed dictionary,
verified units, actual filtering counts/quantiles, approved calibration and independent
technical-contact reproduction remain outstanding. Passing synthetic tests establishes
tooling behavior only. No commit, push, receiving-member agreement or scientific
calibration success is claimed.

## Checks executed

Temporary environment: `/private/tmp/d02-venv`, CPython 3.12.15 on macOS ARM64,
installed from existing `requirements/requirements-core.in`. Dependency inputs and
Windows lock were not changed; this does not certify the Windows hashed environment
or resolve Q13 platform adoption. Commands run with that environment's Python:

```sh
python -m pytest tests -q
python -m ruff check dc_sustainability scripts tests
python -m ruff format --check dc_sustainability scripts tests
python -m compileall -q dc_sustainability scripts tests
python -m pip check
python scripts/smoke_dependencies.py
python scripts/validate_setup.py
git diff --check
```

Results: 297 tests and 19 subtests passed, including 33 new D02 synthetic tests;
lint passed; all 38 Python files formatted; compilation, dependency consistency,
offline dependency smoke and setup checks passed. The initial sandboxed test run
had 39 setup errors because binding the existing loopback HTTP test server was
denied; the authorized unsandboxed rerun passed the complete suite. No live model
calls or scientific experiments ran. Shared instructions and F02 are unchanged.
