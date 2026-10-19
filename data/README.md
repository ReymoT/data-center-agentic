# Data acquisition preparation

Owner: Reimo for source acquisition; Ved owns independent D06 checks. D01/D06 inspection and D03 provisional synthetic fixtures are implemented, with separate acceptance limits. Complete the outstanding source verification before scientific claims:

- SustainDC/dc-rl Arizona file `AZPS_NG_&_avgCI.csv`, pinned commit `a92b4755aca560e34a98d14028dda629eb968482`: expected 8,760 hourly 2022 UTC records and `avg_CI`; verify CO2 versus CO2e, units and interval convention.
- Frontier job-information table: runtime, mean-power and wall-time distributions for scaled synthetic jobs. Validate job-versus-node units and exclusions. Flexibility/deadlines are synthetic. Do not load node telemetry.
- EPA eGRID: annual magnitude plausibility check. Record geography, year and factor alignment. Cambium is optional.

Record acquisition URL/date, source version/checksum, schema, units/time zones, preprocessing/exclusions, allowed redistribution and regeneration command in validated manifests. See Q05/Q06. No license/access or source validity is presumed. Keep raw/private/processed inputs outside Git; only validated permitted fixtures/manifests belong in version control.

The original internal plan targeted Ved's independent 24-hour reproduction for October 16. The merged D06 handoff and Matty's subsequent verification are recorded below; the historical date is not completion evidence. If access/validation fails by then, the proposal permits clearly labeled synthetic fallback with narrower conclusions. Development and held-out windows must not overlap. Private manifests, future arrivals, realized scoring carbon and oracle answers must never enter policy context.

## D01 acquisition and validation

The standard-library module `dc_sustainability.data.carbon_source` downloads only the pinned
Arizona file or inspects a local copy. It enforces SHA-256
`e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4`.
During inspection, the bytes also matched GitHub's pinned Git blob
`d5337a654e77c938d0909e76d56efdf3ad491e83`. No raw data is tracked.

From the repository root, using the project's proposed Python 3.12 environment:

```sh
python3 -m dc_sustainability.data.carbon_source 'data/raw/AZPS_NG_&_avgCI.csv' --download --report data/processed/d01-validation.json
```

To validate an existing file, omit `--download` and use a new report filename.
Download and report outputs refuse overwrites. A local inspection produces a report and
exit status 1 on validation failure. A failed download is rejected before saving.
Network access is required only for acquisition; unit tests run offline:

```sh
python3 -m pytest tests/data/test_carbon_source.py -q
python3 -m unittest discover -s tests/data -v
```

The [inspection manifest](manifests/d01-source-inspection.json) records the inspected source,
checksums, acquisition date, observed statistics, evidence URLs, transformations and blockers.
The [focused acceptance review](D01_ACCEPTANCE_REVIEW.md) records subsequent calculation,
interval and licensing evidence, classifications and the handoff needed from Ved.
It is local D01 evidence, not an adopted F02 schema. Acquisition time is recorded for new
downloads; loading an existing file leaves its unknown acquisition time null.

### Source dictionary and evidence

The exact observed header is
`timestamp,WND,SUN,WAT,OIL,NG,COL,NUC,OTH,avg_CI`.
The [pinned README](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/README.md#L342-L370)
identifies the timestamp, generation-source columns and average carbon intensity.
The [pinned calculation documentation](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/envs/bat_env_fwd_view.py#L218-L243)
multiplies kWh by CI and identifies gCO2/kWh in a comment, while its return documentation
says gCO2e. Thus g/kWh is supported by upstream implementation documentation, but the
pollutant basis remains unresolved. No generation-column physical units are inferred;
these columns receive only finite/nonnegative numeric validation and are not used to
reconstruct CI.

The acceptance review separately reconstructed all 8,760 CI values with CarbonExplorer's
generation-weighted factor formula, with maximum absolute difference 0.0. Its factor table
and paper use gCO2eq/kWh, supporting a modeled CO2e proxy interpretation. Exact exporter,
GWP and boundary provenance remain unverified; no scientific relabeling is applied.

The inspector requires exactly 8,760 ordered hourly observations, from January 1 2022
00:00 UTC to December 31 2022 23:00 UTC. Every timestamp must explicitly have zero UTC
offset. It rejects missing fields, duplicate timestamps, gaps, disorder, unexpected
columns/row widths, invalid or nonfinite numbers, and negative values. Repeated CI values
are permitted; identical timestamps are not. A broad 0–2,000 g/kWh numerical screen is an
explicit diagnostic assumption, not an accepted emission-factor range or calibration.
The inspected range is 251.22162645218947–749.1955146635997; hourly mean is
575.0418721742574. Nothing is sorted, filled, dropped, rounded, rescaled or interpolated.

`load_source(Path(...))` returns immutable `(UTC datetime, avg_CI float)` pairs and an
inspection report after checksum and validation checks. These are private source
observations, not policy forecasts or shared `CarbonFact` records.

### UTC and proposed episode mapping

The source timestamps remain UTC-aware. Per shared rules, Phoenix midnight is 07:00 UTC.
`episode_indices(day, interval_convention="start")` explicitly selects source indices for
30 hours starting there. Under that selected convention, slot s represents
`[07:00 UTC + s hours, 08:00 UTC + s hours)` on the episode date. January 1 maps to indices
7 through 36. Out-of-year windows are rejected, never wrapped. This helper neither selects
split dates nor generates episodes. The source's interval-start versus interval-end meaning
is not verified; callers must not treat this proposed mapping as source evidence. No issue
times, forecast visibility or freshness semantics are synthesized.

The review found that EIA specifies hour-ending timestamps and CarbonExplorer preserves
the labels. If this CSV follows that path, slot 0 needs the 08:00 UTC row (indices 8–37 for
January 1). This is stronger evidence for an end convention, but not proof of this export.
The current start-only helper is provisional and must not be used for accepted episodes
until the convention is verified and consumers agree on the mapping.

### Annual plausibility and remaining acceptance

[EPA eGRID2022 table 1, page 2](https://www.epa.gov/system/files/documents/2024-01/egrid2022_summary_tables.pdf)
reports AZNM WECC Southwest total-output rates of 776.0 lb CO2/MWh and 779.4 lb CO2e/MWh.
Multiplying by 0.45359237 yields approximately 352.0 and 353.5 g/kWh. The source hourly mean
is about 1.63 times these rates: the magnitudes are comparable, but agreement is not
established. AZNM is a broader region than the AZPS file; an unweighted hourly mean differs
from an annual generation-weighted factor. Pollutant basis is unresolved. No marginal
factor, transmission-loss adjustment or rescaling is used, and no arbitrary ratio threshold
declares the source scientifically valid.

The pinned repository [LICENSE](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/LICENSE)
is MIT, while its README describes some CC BY-NC 4.0-derived material. Dataset-specific
redistribution rights remain unverified; keep raw and processed data untracked. Q05 needs
pollutant, interval and licensing evidence plus source-specific factor alignment. F02 schema
adoption/consumer tests remain outstanding. Ved's bounded D06 reproduction and Matty's independent current-checker run are now recorded below; they do not resolve those scientific gates. D01 is not marked Done. The source-inspection module itself does not implement D02, scenarios or simulator integration.

Local verification on October 12: 12 D01 tests and 13 existing provider mock tests passed;
Ruff 0.17.0 lint/format checks and Git whitespace checks passed. The implemented downloader
and local loader both validated the actual pinned bytes. Available Python was 3.9.6;
the proposed 3.12 environment was not verified. `scripts/validate_setup.py` could not run
because that interpreter lacks `tomllib`. No dependencies, CI or shared configuration
were changed. No assigned D01 Issue or independent receiver acceptance is claimed.

## D03 provisional synthetic scenarios

[Generation, acceptance evidence and limitations](D03_SYNTHETIC_SCENARIOS.md)
describes the deterministic four-scenario generator, hand jobs and normal
withheld-forecast variant. The [tiny development job catalog](manifests/d03-provisional-jobs.json)
is explicitly synthetic and provisional, not Frontier-calibrated or a D04 freeze.
Use `python -m dc_sustainability.data.scenarios <new-output.json> --seed 42 --split development`
to reproduce it. No shared F02 schema or Q05/Q06 decision was changed.

## D06 independent source/window evidence

Ved's [D06 handoff](D06_REPRODUCTION.md) and checker merged through PR #19.
[Matty's October 19 verification](../docs/handoffs/D06_F04_F05_VERIFICATION.md)
ran the exact merged code in Windows Python 3.12 on a newly acquired, pinned source.
It recorded a structural pass with 8,760 valid timestamps, 24 expected January 1 UTC
hours and matching adapter values. The compact evidence records code/source/report
hashes without publishing the raw CSV or individual hourly values.

The earlier three-checker-test count is historical; the current focused suite passed
21 tests and 19 subtests (12 adapter tests plus nine checker tests). Synthetic unit
tests and actual-source reproduction are distinct evidence. Ved's old JSON caveat
is not silently cleared by Matty's separate new reports. Q05 semantics/rights, Q06
freeze and policy-facing adoption remain unresolved. Raw and processed outputs stay
outside Git. Use the verified Windows commands in Matty's handoff and new filenames
for reruns; preserve existing evidence.
