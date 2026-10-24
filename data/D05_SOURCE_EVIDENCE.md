# D05 source evidence inventory — Issue #60

Reimo owns this producer package; Ved independently verifies it in [#13](https://github.com/ReymoT/data-center-agentic/issues/13).
Prepared for the accepted October 26 inventory checkpoint in [#60](https://github.com/ReymoT/data-center-agentic/issues/60).
Reviewed October 24, 2026 against fetched main `2ec1e542c09066e2cf4d05953c5f076566a1e657`, instruction 1.26;
working instructions match main. Local task branch: `reimo/d05-source-evidence`.
This is a reviewable inventory with blockers, not source/scientific acceptance or freeze approval.

## Evidence index

Stable IDs below identify exact sources; pinned URLs and newly retrieved document hashes
are also in [the document manifest](manifests/d05-document-evidence.json).
No raw CSV, hourly values or upstream document copies are included.

| ID | Evidence and locator | Scope |
|---|---|---|
| S1 | [SustainDC README, CI section](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/README.md#L342-L370) | EIA bulk URL, column descriptions; not an exact export log |
| S2 | [Pinned plot](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/explore_ci.py#L39), [battery calculation](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/envs/bat_env_fwd_view.py#L218-L243) | gCO2/kWh plot; battery gCO2e return label and gCO2/kWh multiplication comment conflict |
| S3 | [CarbonExplorer method](https://github.com/facebookresearch/CarbonExplorer/blob/135f21862cb2427b3dbad690519bc05c5f6c539e/src/download_and_process.py#L13-L176) | Comparison implementation; not proven original exporter |
| S4 | [Carbon Explorer paper v3, Table 2](https://arxiv.org/html/2201.10036v3#S3.T2) | Eight gCO2eq/kWh factors; not CSV-specific provenance |
| S5 | [EIA-930 instructions, PDF page 3](https://www.eia.gov/survey/form/eia_930/instructions.pdf), [2021 EIA context](https://www.eia.gov/todayinenergy/detail.php?id=49216) | Hour-ending UTC and preliminary reporting; current PDF expires July 2029, not archived 2022 instructions |
| S6 | [SustainDC MIT license](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/LICENSE), [combined-work notice](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/README.md#L577-L591), [CarbonExplorer license](https://github.com/facebookresearch/CarbonExplorer/blob/135f21862cb2427b3dbad690519bc05c5f6c539e/LICENSE) | Mixed licensing; CarbonExplorer CC BY-NC 4.0 |
| S7 | [EIA reuse policy](https://www.eia.gov/about/copyrights_reuse.php) | EIA information products reusable/distributable with source/date acknowledgment; third-party protected-material exceptions |
| S8 | [EPA eGRID2022 summary, Table 1, PDF page 2](https://www.epa.gov/system/files/documents/2024-01/egrid2022_summary_tables.pdf) | Annual AZNM regional comparator only |
| R1 | [D01 manifest](manifests/d01-source-inspection.json), [acceptance review](D01_ACCEPTANCE_REVIEW.md) | Original primary byte/structure/formula evidence, October 12 |
| R2 | [D06 runbook](D06_REPRODUCTION.md), [merged-checker verification](../docs/handoffs/D06_F04_F05_VERIFICATION.md), [compact evidence](../docs/evidence/d06-matty-verification-2026-10-19.json) | Completed structure/window reproduction; Ved's original report-version caveat retained |
| R3 | [D02 status](manifests/d02-source-status.json), [D02 documentation](D02_CALIBRATION.md), [D03 documentation](D03_SYNTHETIC_SCENARIOS.md) | Empirical calibration blocked; provisional synthetic generation implemented |

## Indexed claim matrix and dictionary

“Verified” means only the bounded claim in that row. “Supported inference” does not
resolve a source field or authorize a shared setting.

| Claim | Status | Evidence / exact boundary |
|---|---|---|
| C01 Pinned source identity | Verified, existing | R1/R2: SustainDC commit `a92b4755aca560e34a98d14028dda629eb968482`, path `data/CarbonIntensity/AZPS_NG_&_avgCI.csv`; 601,730 bytes; SHA-256 `e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4`; Git blob `d5337a654e77c938d0909e76d56efdf3ad491e83` |
| C02 Acquisition and local transformations | Verified, existing | R1 acquired `2026-10-12T19:31:06.279633+00:00`; D01 GETs the pinned raw URL, parses UTF-8 CSV/UTC/numbers, excludes zero rows, changes no values; requires exact checksum and exclusive outputs |
| C03 `timestamp` labels | Verified, existing | R1/R2: explicit zero-offset UTC, 8,760 ordered hourly labels, Jan 1 00:00 through Dec 31 23:00 2022; no gaps/duplicates. Continuity does not establish represented intervals |
| C04 Generation columns | Partly verified | S1: WND wind, SUN solar, WAT hydro, OIL oil, NG natural gas, COL coal, NUC nuclear, OTH other. S3 describes input tuples as MWh; S5 describes hourly integrated MW. They are numerically equivalent over one hour, but the CSV-specific exporter dictionary/units remain missing; do not treat columns as measured instantaneous power |
| C05 `avg_CI` calculation and dimension | Verified numerically in prior primary evidence | R1: all 8,760 rows exactly match `sum(generation[f]*factor[f])/sum(generation[f])`, max absolute difference 0.0; positive denominators. S2 supports g/kWh (dimensionally also kg/MWh); S3/S4 provide factors WND 11, SUN 41, WAT 24, OIL 650, NG 490, COL 820, NUC 12, OTH 230 |
| C06 Pollutant and model boundary | Supported inference; unresolved acceptance | S3/S4 label factors CO2eq. S2 mixes CO2 and CO2e. Fixed-factor generation-mix proxy is strongly supported; direct measured hourly CO2 is not established. Exact exporter, factor origin, GWP horizon/version and lifecycle boundary are missing; no verified inventory pollutant assignment |
| C07 Physical interval | Supported inference; unresolved for CSV | S5 defines EIA hour-ending UTC. S3 parses/reindexes UTC without an explicit hour shift. If export preserved labels, row at `t` represents `[t−1h,t)`. Missing original export prevents declaring this CSV convention verified |
| C08 Phoenix alignment | Conditional only | Shared rules fix slot 0 at 07:00 UTC. For physical slot `[07:00,08:00)`, start labels select 07:00 (Jan 1 indices 7–36 for 30 slots); end labels select 08:00 (8–37). Existing `episode_indices(..., interval_convention="start")` implements only the former; do not use its tests to approve mapping. D06 checks a UTC calendar day, not a Phoenix episode |
| C09 Original EIA acquisition/export | Unresolved | S1/S3 identify bulk `EBA.zip` and candidate fuel-series pattern below; no dated snapshot/hash, exact export revision/command, environment, filters or transformation log tied to this CSV |
| C10 Dataset redistribution | Unresolved | S6 software MIT is not CSV-specific permission. S7 permits underlying EIA information reuse, not automatically the derived CSV. Need file-specific applicability/attribution clarification from SustainDC/CarbonExplorer rights holders |
| C11 Geographic suitability | Provisional | AZPS candidate BA generation mix is narrower than Arizona and differs from AZNM. No modeled site supplier/service-area match or import/export consumption accounting is established. Do not represent it as the actual electricity supplied to every Arizona data center |
| C12 Temporal/accounting suitability | Provisional | A 2022 replay supports bounded simulated comparisons once mapping is agreed; not present-day operations. A generation-weighted average proxy is not a marginal, consumption/import-adjusted, contractual market-based or avoided-emissions factor; no such adjustment is demonstrated by S3 |
| C13 Annual magnitude | Verified limited comparison | R1/S8: AZNM 2022 CO2 776.0 and CO2e 779.4 lb/MWh × 0.45359237 = 351.98767912 and 353.529893178 g/kWh. CSV unweighted hourly mean 575.0418721742574 differs in geography, weighting and model scope; no rescaling or equivalence/acceptance threshold |
| C14 Independent evidence | Completed structure/window, limited | R2 records Ved's reproduction and Matty's exact merged-code Windows rerun at `488ddfb3a4b8442e65d5d27140304bca6746e6fd`; does not settle C06–C12 or final acceptance |
| C15 Empirical workloads and freeze | Unresolved, separate | R3 and [D04/Q06 inventory](D04_Q06_STATUS.md); seed-42 synthetic catalog is not a frozen 40/30 split |

## Original methodology and missing export inputs

S3 downloads `https://api.eia.gov/bulk/EBA.zip`, reads JSON-lines `EBA.txt`
with PyArrow then pandas, and selects eight series
`EBA.AZPS-ALL.NG.{WND,SUN,WAT,OIL,NG,COL,NUC,OTH}.H` **if called with AZPS**.
It filters inclusive UTC start/end dates, constructs an inclusive hourly index,
sorts/reindexes, substitutes zero for missing series/hours/NaNs, converts generation
to integers, clips negatives to zero, and weights by fixed fuel factors. These are
observed comparison-code behaviors, not an authenticated preprocessing history of
the pinned CSV. The factors cancel generation units in the weighted mean; no
energy-unit conversion alone can resolve pollutant or lifecycle meaning.

The CSV labels imply a candidate selected label range of Jan 1 00:00 through
Dec 31 23:00 2022. S3's date-based midnight endpoints do not by themselves explain
that exact 8,760-row export: the original caller, endpoint trimming, column rename
and serialization are absent. If labels are hour-ending, the represented physical
coverage also crosses a calendar-year boundary. Do not force it into a full
physical 2022 year or wrap missing episode windows.

Reimo must obtain the historical EBA archive/version/checksum and original series
metadata (units, timezone, revision), exporter revision/caller, exact BA/fuel IDs,
start/end inclusivity, missing/negative handling counts, import/export treatment,
factor references/GWP/system boundary, rename/serialization settings and dependency
versions. SustainDC/CarbonExplorer maintainers are the external evidence providers;
no contact was sent in this work. A current API response or current `EBA.zip` is not
the historical input and cannot be promised to regenerate the pinned bytes.

## Rights and intended use

CarbonExplorer's CC BY-NC 4.0 permits conditional noncommercial sharing/adaptation
with attribution, license information and change indications; the applicable full
license and its restrictions still matter. SustainDC acknowledges a combined work.
Neither that notice nor MIT alone establishes which terms cover this derived CSV.
Keep raw/processed inputs and hourly reports outside Git until dataset-specific
permission and required notices are established. This package publishes only
documentation, hashes and acquisition instructions. Frontier data rights remain
separately unresolved in R3; no empirical job table was acquired here.

Intended use is an explicitly labeled historical generation-mix proxy for one
simulated Phoenix site, with fixed PUE and synthetic jobs. Accepted use still
requires verified semantics and affected-consumer agreement. It cannot support
public operational absolute-emissions or causal avoided-emissions claims yet.

## Blockers, owners and Ved's review

| Blocker | Evidence needed / responsible party |
|---|---|
| B1 C06/C09 exporter and pollutant | Reimo obtains upstream archive/export/factor documentation from source maintainers; Ved verifies provenance and Edison checks physical accounting interpretation |
| B2 C07/C08 interval and mapping | Reimo establishes source labels first, then proposes exact mapping to affected Ved/Edison/Nisha/Matty consumers; verify first/last physical intervals and all 30 slots before use |
| B3 C10 rights | Reimo obtains CSV-specific rights/notice clarification from relevant rights holders; Ved checks supplied evidence; no team vote substitutes for permission |
| B4 C11/C12 suitability | Reimo documents intended BA/site/time/accounting boundary; Ved and Edison review factors and Nisha reviews evaluation claims; record affected-owner agreement before adopting shared behavior |
| B5 C15 split/freeze | Reimo supplies missing D04 artifacts; Nisha verifies isolation, Edison/Ved review affected calibration/consumer boundaries; scientific freeze remains unapproved |

Issue #60 retains the original request `2026-10-23T21:12:52Z` and deadline
`2026-10-24T21:12:52Z`, already escalated, with Reimo's reply and Matty's accepted
October 26 inventory checkpoint (no exact hour). This package does not reset that
clock, post a new request, or claim new owner agreement.

Ved should review C01–C15 against S1–S8/R1–R3, especially whether authoritative
definitions actually apply to the pinned bytes, the later comparison revision,
conditional interval mapping, mixed rights, and separate retrieval/regeneration.
Reuse R2's completed structure/window results; do not repeat them to close B1–B4.
Record source-verification findings in #13 only when authorized. The package is
ready for the #60 inventory/blocker checkpoint; full D05 acceptance remains blocked.

Historical R1 statements that F02 code or independent reproduction are absent are
superseded by current F02 code and R2. D01-generated reports still carry historical
blocker text. They are not a live acceptance register; no legacy record/code was
silently rewritten. [Reproduction and validation](D05_REPRODUCTION.md) records current checks.
