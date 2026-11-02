# Issue #60 source evidence and unavailable records

Producer: Reimo. Independent source verifier: Ved; accounting contact: Edison;
evaluation/custody contact: Nisha. Local review uses fetched main
`6e653e85c0432ffc135d11194914dade6173e6db`, instruction 1.28.
This companion preserves [the historical audit](SOURCE_ACCEPTANCE_AUDIT.md).
It is producer evidence for independent review, not a new independent approval.

## Current authoritative state

Read #60 and all 15 comments, including
[Ved's latest applicability review](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6566631218).
That review accepts existing identity/structural/formula evidence, leaves B1–B3
unresolved, B4 provisional and B5 incomplete. No new producer record resolving
those findings or accepted held-out parameters was found in main or the reviewed
#60/#102/#112/#22 discussions. This is a bounded inspection, not a claim that no
private artifact exists anywhere.

[#102](https://github.com/ReymoT/data-center-agentic/issues/102#issuecomment-6486639018)
closed the development fold-map handoff after Nisha/Edison/Ved receiving.
[#112](https://github.com/ReymoT/data-center-agentic/issues/112#issuecomment-6549199234)
closed development materialization through
[PR #133](https://github.com/ReymoT/data-center-agentic/pull/133), merge
`717a99e420e404cfbf13dd66ce4fd6db86cc0338`. Its v2 receipt and preceding-row
persistence forecast support bounded development receiving only.
[PR #141](https://github.com/ReymoT/data-center-agentic/pull/141), merge
`d711d5d79960a17aaa1f3349e1d4e7dc9d580a60`, reconciled source blockers without
new source acceptance. [I02](../i02/freeze-manifest.json) is a pre-freeze checklist,
not frozen authority. Its dated development/calibration descriptions must be read
alongside the newer issue evidence. [#22](https://github.com/ReymoT/data-center-agentic/issues/22#issuecomment-6565985861)
still needs extraction calibration/rule resolution; it grants no held-out opening
or D04 selection approval. No shared records are changed here.

## B1–B4 evidence-or-unavailable matrix

All rows concern commit `a92b4755aca560e34a98d14028dda629eb968482`, path
`data/CarbonIntensity/AZPS_NG_&_avgCI.csv`, SHA-256
`e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4`.

| Gate/status | Existing evidence and applicability | New evidence / fact versus inference | Missing input and responsible producer | Independent verifier and smallest next action |
|---|---|---|---|---|
| B1 **UNRESOLVED** | [D05 C01/C05/C06/C09](../../data/D05_SOURCE_EVIDENCE.md): pinned identity and numeric factor match directly concern these bytes; comparison methodology does not establish historical provenance | [Bounded historical code search](../../data/manifests/d05-historical-code-review-60.json) at exact upstream commit; consumer and documentation evidence below. No authenticated exporter/archive discovered. Similar method remains inference | SustainDC producers: historical EBA archive/version/hash, exporter/caller/parameters/environment; CarbonExplorer/factor authors: authoritative references, pollutant/GWP/system boundary and link to export | Ved verifies applicability, Edison accounting. Reimo obtains those records; requires external evidence, not a vote. Historical regeneration remains unavailable |
| B2 **UNRESOLVED** | D05 C03/C07/C08: labels directly verified, physical meaning unknown; EIA guidance is related upstream evidence | [All-slot comparison artifact](ISSUE60_INTERVAL_COMPARISON.json) and standalone regeneration below; mathematical conditional mappings only | SustainDC exporter author must authenticate preservation/shift of labels and endpoints | Ved verifies original convention; Reimo proposes any resulting mapping to Ved/Edison/Nisha/Matty. External evidence then affected-owner agreement required; do not shift existing indices |
| B3 **UNRESOLVED** | D05 S6/S7 and document hashes: actual licenses/policy, no conclusive derived-CSV applicability | Current EIA policy reread; CarbonExplorer pinned license re-read. Software and underlying-data permissions remain distinct | SustainDC and relevant CarbonExplorer rights holders: file-specific terms, attribution and third-party provenance | Ved checks supplied applicability; Reimo sends draft only after human authorization. External permission/evidence required; silence grants none |
| B4 **PROVISIONAL** | D05 C11–C13: historical AZPS generation-mix interpretation and limited annual magnitude comparator | Exact proposed claim boundary below; no new site supply, consumption or causal evidence | Reimo proposes bounded simulated scope; source/site operator would need actual supply/flow/accounting evidence for broader claims | Ved/Edison verify accounting, Nisha evaluation. Record affected scope agreement; expanded claims additionally need external evidence |

Passing tests verifies implementation behavior, never historical facts or scientific
acceptance. B1–B3 remain UNRESOLVED and B4 remains PROVISIONAL. B5 remains
separate under the existing audit and the independent custody preparation PR.

## B1: bounded historical investigation

[The complete upstream tree](https://api.github.com/repos/HewlettPackard/dc-rl/git/trees/a92b4755aca560e34a98d14028dda629eb968482?recursive=1)
was returned without truncation. The new search manifest lists 30 read files and
Git blob IDs: all Python source outside HARL/Sphinx, plus the two relevant CI
documentation pages. The stated literal search did not identify an exporter or
caller. This is a bounded search of one revision; it cannot establish historical
nonexistence. Raw CSV bytes were not downloaded or opened, and completed D06
reproduction was not repeated.

New direct code evidence:
[SustainDC `CI_Manager`](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/utils/managers.py#L317-L380),
Git blob `ea9c67936db29ae94051cda352ac82065a44f1c0`, reads the existing `avg_CI`
column, truncates to 8,760 values, casts floats, has NaN substitution, interpolates
and rolls the consumed array for its environment. It does not construct the
historical CSV. These downstream transforms are not our D01 preprocessing or
proof of source interval meaning. The tree also shows the AZ and AZPS filenames
have identical blob `d5337a654e77c938d0909e76d56efdf3ad491e83`, size 601,730.
Renaming does not establish statewide electricity attribution.

Related method, explicitly not authenticated historical exporter:
[CarbonExplorer `download_and_process.py`](https://github.com/facebookresearch/CarbonExplorer/blob/135f21862cb2427b3dbad690519bc05c5f6c539e/src/download_and_process.py#L13-L176),
Git blob `c4204e4bb636c5072f927846ad7edf626cf586ae`, downloads unversioned EBA.zip,
reads EBA.txt with PyArrow/pandas and, if called with AZPS, selects
`EBA.AZPS-ALL.NG.{WND,SUN,WAT,OIL,NG,COL,NUC,OTH}.H`.
The start/end filters include both midnight endpoints; its hourly reindex also
includes endpoints. Missing series/hours/NaNs become zero, values become integers,
negative generation is clipped before the weighted mean. It has no demonstrated
imports/exports or consumption-flow adjustment. It returns `carbon_intensity`,
where the pinned CSV uses `avg_CI`. Caller/end trimming/rename/CSV serialization
are missing. A caller using Jan 1 to Dec 31 at midnight would not produce the
observed full last day; a Jan 1 to next Jan 1 caller would include an extra endpoint.
Exact historical filtering cannot be recovered from those function defaults alone.

The eight factors (11, 41, 24, 650, 490, 820, 12, 230) are labeled gCO2eq/kWh
in that comparison code and [paper Table 2](https://arxiv.org/html/2201.10036v3#S3.T2).
The same function's comment says kg CO2/MWh; SustainDC also mixes CO2/CO2e terms.
Numerical equality does not determine pollutant, GWP horizon/version, combustion
versus lifecycle scope or the factor provenance actually adopted by the CSV author.
No authoritative factor/GWP/boundary record tied to the pinned export was found.
Do not fill that gap from a similar IPCC table without exporter-specific evidence.

Still unavailable: original archive retrieval date/version, ZIP and EBA.txt SHA-256,
series metadata/revision, actual exporter/caller revision and exact command,
endpoint and timezone treatment, exclusions/imputation counts, rounding/ordering,
rename/serialization settings, dependency versions, factor references and boundary.
A fresh EIA download would be a new revision, not the missing historical snapshot.
There is no truthful historical regeneration command until those inputs arrive.

## B2: reproducible conditional physical mapping

The [current EIA-930 instructions](https://www.eia.gov/survey/form/eia_930/instructions.pdf),
page 3, describe hour-ending UTC integrated reporting; the current PDF expires
July 2029 and is not an archived 2022 exporter specification. This supports a
hypothesis about original labels, not CSV-specific proof.

For physical Phoenix slot `s` (0–29), let `P = date at 07:00 UTC + s hours` and
`i = hours(P − 2022-01-01 00:00 UTC)`. Start interpretation selects row `i`, label
`P`, interval `[P,P+1h)`. End interpretation selects row `i+1`, label `P+1h`,
representing the same physical interval. Both are conditional, not adopted.
Indices are zero-based data rows, excluding the CSV header.

The [reproducible comparison artifact](ISSUE60_INTERVAL_COMPARISON.json) contains
all 30 slots for Jan 1, Jan 31, Dec 30 and Dec 31 (generic boundary examples, not
held-out selections). The following standalone command checks every row and exact
LF serialization using only the standard library. It reads no carbon source,
allocation or custody input. Missing source rows are `None`, never wrapped. Run
from the repository root; it requires no companion PR code:

```sh
python - <<'PYTHON'
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

hour = timedelta(hours=1)
origin = datetime(2022, 1, 1, tzinfo=timezone.utc)
result = {
    "status": "conditional_comparison_not_source_evidence_or_study_selection",
    "source_values_read": False,
    "index_basis": "zero-based data row excluding CSV header",
    "dates": {},
}
for day in ("2022-01-01", "2022-01-31", "2022-12-30", "2022-12-31"):
    start = datetime.fromisoformat(day).replace(hour=7, tzinfo=timezone.utc)
    rows = []
    for slot in range(30):
        physical = start + slot * hour
        index = int((physical - origin) / hour)
        rows.append({
            "slot": slot,
            "physical_start_utc": physical.isoformat(),
            "physical_end_utc": (physical + hour).isoformat(),
            "start_label_utc": physical.isoformat(),
            "end_label_utc": (physical + hour).isoformat(),
            "start_row": index if 0 <= index < 8760 else None,
            "end_row": index + 1 if 0 <= index + 1 < 8760 else None,
        })
    result["dates"][day] = rows
path = Path("docs/handoffs/ISSUE60_INTERVAL_COMPARISON.json")
expected = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
assert path.read_bytes().replace(b"\r\n", b"\n") == expected
print("PASS: all generic conditional interval rows regenerate exactly")
PYTHON
```

Jan 1: start rows 7–36, end rows 8–37; physical coverage Jan 1 07:00 through Jan 2
13:00 UTC, end exclusive. Slots 0–23 span the local day; slots 24–29 cover the
next six local hours. Jan 31 likewise crosses into Feb 1. Dec 30 remains within
available rows under both hypotheses. Dec 31 lacks its next-day tail under both,
and the end-label interpretation first runs out one physical hour earlier.
The first source label under end semantics represents the preceding year's final
hour; the final label does not include physical `[Dec 31 23:00, Jan 1 00:00)`.
All 30 slots, month tails and year bounds are compared without source observations.

Existing development materialization retains its start-conditional rows and v1/v2
content hashes unchanged. If end labels are authenticated, every episode's physical
mapping would require a +1 row lookup; forecast issuance/availability also needs
review, including EIA reporting latency and subsequent revisions. The prior-row
adapter's label ordering alone is not proof that historical data was available in
real time. Revised development contents require a separately authorized amendment,
new receipt and consistent consumer reruns; preserve originals. Held-out metadata
under current D04 tooling is start-conditional and cannot become final physical isolation
proof until Q05 and affected-owner mapping acceptance are satisfied. Uniform shifts
preserve overlap relationships for this single regular source away from edges;
that observation is not a substitute for authenticating coverage and data identity.

[Nisha's PR #133 receiving review](https://github.com/ReymoT/data-center-agentic/pull/133#issuecomment-6548635772)
confirms preceding-row causality for bounded development using a distinct-value
source double. It also records that the flat horizon supplies no carbon timing
signal and proposes same-hour-yesterday forecasts. That proposal is not adopted
here. Any accepted forecast history must be included in the source-access footprint:
a 24-hour lookback can intersect a development tail even where the held-out
30-hour scoring window is disjoint. Freeze therefore also needs the exact forecast
algorithm, history/availability boundary and an independent expanded-footprint
leakage check. Existing 30-hour isolation checks do not certify that future
forecast design or historical real-time availability.

## B3: rights by use and artifact

| Asset | Substantiated terms | Internal reproduction / teammate sharing / publication / redistribution / derivatives |
|---|---|---|
| Original EIA information | [EIA reuse policy](https://www.eia.gov/about/copyrights_reuse.php) permits use/distribution of its information products with source/date acknowledgment; protected third-party exceptions apply | General underlying EIA reuse is supported for those uses, subject to exceptions/attribution; it does not identify the historical archive or convey upstream derived-CSV rights |
| SustainDC software/documentation | [Pinned MIT license](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/LICENSE) and combined-work notice in README | MIT grants software rights with notice retention; no conclusive CSV-specific grant was located. Do not infer all five data uses from software terms |
| CarbonExplorer software/method/assets | [Pinned CC BY-NC 4.0 license](https://github.com/facebookresearch/CarbonExplorer/blob/135f21862cb2427b3dbad690519bc05c5f6c539e/LICENSE), blob `a115f899f8d09ef3b1def4a16c7bae1a0bd50fbe`; method header points to it | Conditional noncommercial sharing/adaptation with attribution, license and change notices, subject to actual licensed scope and third-party rights. Applicability to SustainDC's CSV remains unknown; do not copy code/assets as MIT |
| Pinned derived CSV and source-derived episodes | Software notices and underlying EIA policy are evidence but not conclusive applicability | Rights remain UNRESOLVED for internal reproduction, teammate transfer, public results derived from it, redistribution and derivative contents. Existing bounded development authorization is not an external rights grant. Keep raw/derived private contents outside Git |
| This evidence documentation | References, hashes and generic timestamp arithmetic; no source observations or copied exporter implementation | Reviewable documentation only; no selected held-out inputs or content permission |

Before any permissible sharing, preserve source/version/date attribution and all
applicable MIT/CC notices, identify modifications, and check third-party exclusions.
Do not assert those notices alone resolve the missing file-specific scope.

## B4: exact proposed interpretation and claims

Proposed experiment interpretation: **a historical 2022 AZPS generation-mix
carbon-intensity proxy used in a simulated Phoenix data-center scheduling study**,
with synthetic jobs and explicit fixed power/PUE assumptions. This wording labels
the interpretation; it is not final acceptance of the data or mapping.

| Allowed wording within permitted development scope | Unsupported wording without additional evidence |
|---|---|
| “We tested scheduling code using a historical AZPS generation-mix proxy; source pollutant and interval semantics remain unresolved.” | “Measured hourly CO2/CO2e emissions at a Phoenix data center” |
| “The proposed simulated site is located in Phoenix; AZPS supply attribution has not been established.” | “This is the electricity actually supplied to the Phoenix site” or “Arizona-wide carbon intensity” |
| “The arithmetic uses a fuel-weighted average factor; imports/exports and consumption-flow accounting are not established.” | “Consumption-adjusted, marginal, contractual market-based or supplier-specific emission factor” |
| “Under stated proxy, workload and PUE assumptions, the model computes a carbon-proxy quantity.” | “Verified operational absolute emissions” or “causal/avoided emissions attributable to scheduling” |
| “After authorized experiments, report paired simulated proxy differences only with completion/equal-work checks and explicit limitations.” | Invented numerical improvements, field savings, present-day operational benefit, or displacement of marginal generation |

EIA BA generation geography is not site geography or a service-area supply contract.
Generation-average attribution is not a consumption inventory and does not represent
a marginal response to changed load. Proxy arithmetic may be internally valid while
an external physical/causal claim is unjustified. Fixed nonzero low-carbon fuel
factors suggest more than direct combustion, but do not authenticate lifecycle scope.

The [existing EPA eGRID2022 AZNM comparison](../../data/D05_SOURCE_EVIDENCE.md)
compares annual magnitude only. AZNM geography, annual weighting and pollutant
method differ; it neither calibrates AZPS nor establishes site validity or a
numerical acceptance threshold. No rescaling is proposed.

## Draft maintainer clarification request (not sent)

For SustainDC maintainers, identify the exact commit/path/SHA-256 above and ask:

1. Can you supply the original dated EIA ZIP and extracted EBA.txt identities,
   SHA-256 values, retrieval/version record and original series metadata, including
   any later revisions? If unavailable, please state which records no longer exist.
2. Which exact exporter repository/commit/file and caller/command created these
   bytes? Supply BA/fuel IDs, UTC date filters/inclusivity, label shifts, missing and
   negative treatment/counts, rounding, column renaming, CSV serialization and environment.
3. Does label `2022-01-01T07:00Z` describe `[07:00,08:00)` or `[06:00,07:00)`?
   Was EIA's hour-ending convention preserved or shifted? Please provide the code
   or export dictionary establishing both first/last physical intervals.
4. Which authoritative references define these exact eight factors? Specify CO2
   or CO2e, gases, GWP version/horizon, lifecycle/operational boundary and imports/
   exports treatment actually used for this CSV, not merely a related implementation.
5. Which license applies specifically to this derived CSV and source-derived
   episode artifacts? Does it permit internal academic reproduction, teammate
   sharing, publication of aggregate findings, redistribution and adaptation?
   Please specify attribution, notices, noncommercial conditions, third-party
   exclusions and who can authorize each use. No response will be treated as permission.

For CarbonExplorer maintainers, ask whether their exact comparison revision/factors
were used for that SustainDC export, request the original factor citations and
GWP/boundary record, and clarify CC BY-NC applicability to derived numerical data
versus code/assets and any upstream third-party restrictions. EIA's data team may
supply archived series definitions/revisions, but cannot authenticate a downstream
exporter or grant another rights holder's permission. Reimo owns the requests;
Ved independently reviews received evidence. No external contact was made.

## Publication review boundary

This source-only draft is independent of the custody implementation PR. It changes
no instructions, source indices, accepted development records/hashes, shared schemas
or scientific settings. The bounded search manifest and generic four-date comparison
contain no source observations, selected held-out IDs/dates/seeds or evaluator inputs.
Maintainer questions remain unsent; Ved must independently verify applicability.

## Independent PR publication validation

Refetched origin/main remains `6e653e85c0432ffc135d11194914dade6173e6db`,
instruction 1.28. GitHub account `ReymoT` and Reimo's repository-local ID-based
commit email were verified before publication. This branch contains four
evidence/documentation files only and is independent of the custody branch.

After separation, the full offline suite passed **1,734 tests and 19 subtests**
(36.74 seconds). The standalone command above reproduced all 120 generic slot
rows and exact serialized bytes. Ruff lint/format (182 Python files), compilation,
setup/local-link validation, dependency consistency/smoke, I02-manifest validation
and staged whitespace checks passed. Existing development allocation, folds and
v2 content-receipt bytes were compared unchanged. No source observations, actual
held-out allocation/IDs/dates/seeds, evaluator secrets, custody paths or shared
instruction changes are published. B1–B3 remain UNRESOLVED and B4 PROVISIONAL;
passing tests supplies no missing historical record, permission or scientific acceptance.
