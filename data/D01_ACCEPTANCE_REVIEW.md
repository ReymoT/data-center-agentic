# D01 acceptance review — October 12, 2026

Owner: Reimo. This is an evidence review, not a shared decision or F02 approval.
Reviewed main: `51d7ab8a57f8dc5dc3a7b3ad3139705e7e801c29`, instructions 1.6.
The working implementation remains uncommitted. No D02 work was performed.

## Quantity and calculation

**Confirmed:** the pinned SustainDC CSV contains `avg_CI`. Its
[README](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/README.md#L342-L370)
calls it average carbon intensity. The pinned
[plot](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/explore_ci.py#L39)
uses gCO2/kWh, while the
[battery calculation](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/envs/bat_env_fwd_view.py#L218-L243)
contains both CO2 and CO2e labels.

The numerical definition is reproducible as `sum(generation[f] * factor[f]) / sum(generation[f])`.
Comparison factors are WND=11, SUN=41, WAT=24, OIL=650, NG=490, COL=820, NUC=12, OTH=230.
They reproduce every one of the 8,760 `avg_CI` values exactly in local floating-point
comparison: maximum absolute difference 0.0. All denominators are positive.
First-row numerator 1,486,300 divided by denominator 2,353 yields 631.6617084572886.

These factors and the weighted-average algorithm occur in
[CarbonExplorer code](https://github.com/facebookresearch/CarbonExplorer/blob/135f21862cb2427b3dbad690519bc05c5f6c539e/src/download_and_process.py#L93-L176).
Its factor table and [paper table 2](https://arxiv.org/html/2201.10036v3#S3.T2)
identify gCO2eq/kWh. The comparison revision is dated April 3, 2026; it is not a proven
exporter revision for the older SustainDC file. SustainDC's pinned README acknowledges
CarbonExplorer-derived material, but the exact Arizona export procedure was not located.

**Inference:** the series is a fixed-factor generation-mix emissions proxy with a CO2e-labeled
model basis, rather than direct measured hourly CO2 emissions. Numerical agreement strongly
supports this interpretation; it does not establish the exporter provenance, GWP convention
or lifecycle boundary. Those remain unverified. Do not relabel scientific outputs as measured
CO2, or claim a fully verified CO2e inventory. The manifest retains its unresolved pollutant
field and records the stronger supporting evidence separately.

## Timestamp interpretation

**Confirmed:** the CSV has zero-offset UTC timestamps and an uninterrupted 2022 hourly sequence.
[EIA-930 instructions, page 3](https://www.eia.gov/survey/form/eia_930/instructions.pdf)
specify hour-ending reporting in UTC. This is the current instructions document, not the
exact historical bulk snapshot. An [EIA publication from 2021](https://www.eia.gov/todayinenergy/detail.php?id=49216)
also describes Grid Monitor observations by the hour ending at the displayed time.
CarbonExplorer's extraction function parses EIA timestamps, sorts/reindexes them and does
not shift their labels. It can fill missing generation with zero and clip negative generation;
these are upstream behaviors, not verified transformations of this particular file.
SustainDC's CI manager ignores the timestamp column, interpolates values and uses positional
indices; that simulator behavior does not establish physical interval boundaries.

**Inference:** hour-ending is the better-supported source convention. If the export preserved
EIA labels, a row at t describes `[t−1 hour, t)`. Then Phoenix slot 0 `[07:00,08:00 UTC)`
uses the row labeled 08:00, not 07:00. January 1's 30-hour window would use indices 8–37.
The current helper implements only an explicitly selected interval-start proposal (7–36).
Its successful tests prove that implementation, not its suitability for this source. Do not
use it for accepted episodes until export evidence and affected-consumer agreement exist.
No timestamps or code were shifted during this review.

## Licensing

**Confirmed:** the pinned SustainDC LICENSE is MIT; its README describes a combined work
including CC BY-NC 4.0 material. CarbonExplorer's reviewed
[LICENSE](https://github.com/facebookresearch/CarbonExplorer/blob/135f21862cb2427b3dbad690519bc05c5f6c539e/LICENSE)
is CC BY-NC 4.0. That license permits sharing/adaptation subject to noncommercial use,
attribution, license information and change indications; see the
[license deed](https://creativecommons.org/licenses/by-nc/4.0/).
[EIA's reuse policy](https://www.eia.gov/about/copyrights_reuse.php)
permits reuse/distribution of its information products and requests source/date acknowledgment.

**Unresolved:** which license applies to the derived Arizona CSV, and which notices accompany
its redistribution. Permission for underlying EIA records does not establish the applicable
terms for this derived package. No MIT-only or unrestricted-redistribution conclusion is made.
Continue sharing acquisition instructions and evidence while keeping raw/processed data out
of Git. File-specific author/license clarification can resolve this without a scientific vote.

## F02 compatibility and coordination

Main still has no `dc_sustainability/schemas.py`, adopted schema examples or F02 handoff.
The interface document explicitly remains a proposed blueprint. The only repository Issue
returned by the review concerns Q09; no D01/F02 agreement was found. Accordingly, compatibility
with an agreed F02 implementation cannot be claimed and no speculative adapter was added.

Coordinate with Ved to obtain versioned `CarbonFact` examples, confirm source/pollutant and
valid-interval fields, stable fact IDs, checksum references and validation of unsupported units.
Keep realized observations private; a separate, agreed adapter must create visible forecasts
and Q04 issue times. Never equate observation time with forecast issue time. Ved should independently
reproduce the download/checksum, weighted formula and a 24-hour window. Edison should verify
physical unit/model interpretation. Record affected consumers' agreement before changing slot
mapping, shared formats or settings; shared instruction changes remain Matty's responsibility.

Reimo can independently seek exporter/archived EIA evidence, clarify file licensing through
an authorized request, inspect factor/GWP references, and prepare reproduction evidence. The
team must agree on representation/use of unresolved evidence, not vote on source facts.

## Acceptance classification

| Criterion | Status | Evidence or precise unblock condition |
|---|---|---|
| Exact pinned acquisition and byte identity | PASS | SHA-256 and pinned Git blob match; module download/load succeeded |
| CSV schema, 8,760 rows, UTC continuity, duplicates and missing values | PASS | Full-year validation; no errors |
| Numerical unit and reproducible `avg_CI` formula | PASS | g/kWh dimension; all 8,760 fixed-factor weighted values match |
| Fully verified pollutant/model scope | BLOCKED | Obtain exact exporter/factor provenance, CO2e basis and boundary clarification |
| Physical timestamp start/end convention | BLOCKED | Establish whether this CSV preserves EIA hour-ending labels |
| Accepted episode-slot mapping | REQUIRES TEAM DECISION | Agree consumer mapping after source convention is verified; current start helper is provisional |
| Plausibility screening and annual magnitude comparison | PASS | Finite/nonnegative/range checks and limited 2022 eGRID regional comparison; no scientific equivalence claimed |
| Dataset-specific redistribution permissions | BLOCKED | Establish derived CSV license applicability and required notices |
| Provenance, checksums, transformations and uncertainties | PASS | Manifest plus this review; no source values changed |
| Automated unit tests | PASS | 12 D01 tests and 13 existing mock tests passed again during review |
| Proposed Python 3.12/current-base full checks | BLOCKED | Available runtime is 3.9.6; full setup cannot run without `tomllib` |
| Primary window inspection | PASS | Primary 24-hour checks and formula comparison; not independent acceptance |
| F02 producer/consumer integration | BLOCKED | Ved delivers adopted schemas/examples; record agreement and run consumer tests |
| Independent reproduction and final accepted handoff | BLOCKED | Ved records independent 24-hour evidence; integration/publication acceptance remains pending |

Overall D01 remains BLOCKED for scientific/integration acceptance. No merge or approval is claimed.
