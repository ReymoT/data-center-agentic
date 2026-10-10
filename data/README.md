# Data acquisition preparation

Owner: Reimo. No source data or validated fixtures are delivered here. Obtain and verify the final proposal's inputs before scientific claims:

- SustainDC/dc-rl Arizona file `AZPS_NG_&_avgCI.csv`, pinned commit `a92b4755aca560e34a98d14028dda629eb968482`: expected 8,760 hourly 2022 UTC records and `avg_CI`; verify CO2 versus CO2e, units and interval convention.
- Frontier job-information table: runtime, mean-power and wall-time distributions for scaled synthetic jobs. Validate job-versus-node units and exclusions. Flexibility/deadlines are synthetic. Do not load node telemetry.
- EPA eGRID: annual magnitude plausibility check. Record geography, year and factor alignment. Cambium is optional.

Record acquisition URL/date, source version/checksum, schema, units/time zones, preprocessing/exclusions, allowed redistribution and regeneration command in validated manifests. See Q05/Q06. No license/access or source validity is presumed. Keep raw/private/processed inputs outside Git; only validated permitted fixtures/manifests belong in version control.

Reimo supplies a tiny development hand fixture first; Ved independently reproduces a 24-hour window by Oct 16. If access/validation fails by then, the proposal permits clearly labeled synthetic fallback with narrower conclusions. Development and held-out windows must not overlap. Private manifests, future arrivals, realized scoring carbon and oracle answers must never enter policy context.
