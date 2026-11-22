# Data and simulator methods (R01)

November19 manager review: this is Reimo's retained historical data/simulator methods contribution. The [focused rule-system study](../decisions/NOV19_RULE_STUDY_PLAN.md), instruction1.30, is now the primary delivery; the original source-dependent held-out study is not being resumed by this PR. #60 is closed NOT_PLANNED while B1-B3 remain unresolved and B4 provisional. Newly authored synthetic rule-study inputs require their own declared provenance and accepted protocol; this historical source/corpus is not an authorized substitute. Reimo owns report/methods/diagrams; Edison and Ved own demo production in #246 and request needed materials.

The reviewed-main/instruction1.29 statement below records the original November18 drafting context, not current instruction authority. Current published masters on main supersede it. No new study, bounded proof or generalization result is claimed here.

Owner: Reimo Tamme. Draft handoff for issue [#223](https://github.com/ReymoT/data-center-agentic/issues/223), covering IEEE sections E/F/I and the simulator portion of C. Derived from [the existing contribution draft](../handoffs/REIMO_R01_CONTRIBUTION_DRAFT.md); historical source preserved. Reviewed main: `cd272e93a58af8e373bfa8ed96d1191687b919fc`, instructions 1.29, November 18, 2026. This supplies methods for assembly, not final scientific acceptance.

### Datasets, preprocessing and partitions (§F)

The carbon input is the 2022 AZPS file distributed by SustainDC at upstream commit
`a92b4755aca560e34a98d14028dda629eb968482`, path
`data/CarbonIntensity/AZPS_NG_&_avgCI.csv`. Retained acquisition and independent
structural evidence identify 8,760 ordered hourly UTC labels, no gaps or duplicate
timestamps, and SHA-256
`e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4`.
The D01 adapter parses the pinned file without shifting, imputing or rescaling
its values; the recorded validation excluded zero rows. Existing primary checks
find exact agreement with an eight-fuel weighted-average formula. Related
CarbonExplorer code/paper supply matching fixed factors, but the original EIA
archive/version, exporter/caller and serialization chain remain unauthenticated.
Pollutant/GWP/system boundary, CSV-specific interval convention and derived-file
rights remain unresolved in issue #60. We therefore describe the input as a
historical generation-mix proxy, not measured site, marginal or avoided emissions.
The EPA eGRID annual AZNM rate supplies a limited plausibility comparison, without
geographic equivalence or rescaling. [Sources D1–D4 below.]

Jobs are deterministic provisional synthetic records, with constant IT power
10–40 kW, duration 1–4 hourly slots, arrivals 0–17 and deadlines no later than
slot 30. Normal demand contains 12 jobs with 7 flexible; spike contains 20 with
12 flexible and eight arrivals in slots 6–9; limited flexibility contains 12
with 2 flexible; infeasible contains 12 with 7 flexible and one intentionally
impossible deadline. Joint capacity feasibility is not guaranteed or filtered.
Slack is deadline minus arrival minus duration. Nonflexible jobs must start at
arrival. Frontier job-table access remains unavailable in the retained D02 status:
the Globus request lacked credentials, and no actual schema, units, license,
filtering counts or empirical quantiles are available. D02 calibration tooling
and its proposed scaling are not evidence of calibrated workloads. [D5–D6.]

Forty development episodes have an immutable allocation, content receipts and
three blocked chronological folds containing 16/12/12 episodes. Related windows
and variants stay grouped. The separate proposed held-out design comprises
24 core episodes from six dates in six months plus six normal variants with
forecasts withheld; each variant retains its parent's jobs and private realized
carbon. The v2 selector ranks the agreed full days-15–28 candidate pool using
SHA-256 and distinct selection/job seed domains while preserving development
records. It reserves recorded scoring and legacy/CF60 history unions under both
interval hypotheses across date groups. Nisha has completed metadata-only private selection and reports independent
receiving PASS, following Reimo's exact revision-2 acceptance. Matty accepted
that authenticated report for coordination; this is not a rerun or inspection
of the private report by Matty or this review. The metadata preparation produced
no source-derived held-out contents. [PR #211](https://github.com/ReymoT/data-center-agentic/pull/211).
No held-out contents, evaluation results or scientific freeze are established.
Both interval hypotheses remain conditional; existing mapping is unchanged.
[D7–D9.]

### Simulator and accounting (§E / §C)

Our custom deterministic scheduling simulator implements reset, visible state and
atomic current-action stepping over 30 hourly slots. The first 24 admit starts;
the remaining six drain running work and retain accounting. At each boundary,
policies see only arrived waiting jobs, running/completed work and permitted
evidence. Future jobs and realized scoring carbon stay private. Nonpreemptive
work occupies half-open intervals and must respect arrival, deadline,
nonflexibility and running-plus-proposed IT capacity. The trusted runtime controller binds a passing latest-state check before
supplying typed approved actions. That capability is not cryptographic
authentication and does not protect against unrelated code mutating simulator state. A
rejected batch starts no work but advances existing work and the clock once.
Impossible arrivals remain visible for the agreed arrival decision, become missed
at the next boundary and receive no completion credit. The site assumptions are
100 kW IT capacity including 40 kW background and fixed PUE 1.2. [D6, D10.]

S02 passes executed placements and all 30 slot observations to Edison's shared P01
impact implementation. It retains job, background and site facility-energy/
carbon-proxy ledgers separately. Facility kWh equals PUE times IT kW times slot
hours, and proxy kg equals the sum of facility kWh times g/kWh divided by 1,000.
Missing carbon does not erase energy; affected emissions remain unavailable.
Completed IT work excludes PUE and background, while the current shared
`completed_work` field remains unset. Comparisons enforce matching inputs and
completion evidence; the strict S02 helper additionally blocks savings when any
episode job remains unfinished. Under fixed power/PUE, shifting equal work changes
the modeled carbon weighting, not that work's energy. [D11.]

Synthetic hand checks establish 140 completed IT kWh with 54.5/48.4 kg job proxy
values at PUE 1.0 and 65.4/58.08 kg at PUE 1.2 for two schedules; these validate
arithmetic, not operational savings. Simulator, checker, controller, accounting
and independent replay have bounded development integration evidence. At the original November18 drafting checkpoint, S01's separate Ved
reproduction was recorded as pending; this historical statement is not
acceptance of the new RULE-06 reproduction task. The
latest public cb85 technical validation/receiving covers six results and 180
decision records; it does not establish comparative study superiority, complete
scientific I01/I02 acceptance, source rights or held-out findings. Saved explanations
retain contradicted/unsupported claims and both repairs failed checking. [D10–D12.]

### Current development availability and preparation evidence

All 40 Matty development episode files are present and byte-hash matched to the
public v2 receipt, as recorded in merged [PR #221](https://github.com/ReymoT/data-center-agentic/pull/221).
This is the published aggregate availability result; no private files were opened
or rehashed for this documentation review. D05 preserves source identities,
dictionaries, acquisition/regeneration documentation and limitations; structural
reproducibility does not establish source-use rights or scientific suitability.

Merged [PR #222](https://github.com/ReymoT/data-center-agentic/pull/222) implements
legacy development bundle assembly. [PR #225](https://github.com/ReymoT/data-center-agentic/pull/225)
fixes producer/consumer provenance handling and retains the exact extract bytes/hash.
The [preparation handoff](../handoffs/DEVELOPMENT_BUNDLE_PREPARATION_NOV15.md)
records synthetic-only validation. No real bundles were produced. No real extract,
full 1,200-state export, authorized compatibility finding or I02 scientific freeze
exists. B1–B3 source evidence remains unresolved; B4 remains provisional. Metadata
receiving does not waive source-use, operational custody, independent receiving
of actual later artifacts or exact execution authorization. Frontier empirical
calibration remains unavailable. Flat persistence supplies no timing signal for
choosing cleaner future hours; neither code availability nor synthetic parity
establishes a completed comparative experiment.

### Research limitations

The setting is one simulated site/resource pool with synthetic flexibility and
fixed power/PUE. It has no live facility control or empirical Frontier calibration.
AZPS generation geography does not establish electricity supplied to a Phoenix
site; generation-average attribution is not consumption-adjusted, marginal,
market-based or avoided-emissions accounting. Original export/interval/pollutant and rights evidence remains unresolved;
#60 is discontinued for active delivery, not resolved scientific acceptance. Forecast availability is simulated, and flat
persistence cannot test choosing cleaner future hours. Existing labels/models
cannot be declared CF60-compatible without the separately authorized assessment.
Metadata selection/receiving is complete; source-derived held-out content,
accepted freeze, final runs/scoring and final scientific evaluation remain incomplete. Results must keep fallback, initial model actions,
failed repairs, omissions, missing evidence and unfinished work distinct.

### Reimo contribution statement (§I)

Reimo implemented D01/D05 source adapters and evidence documentation, D02 calibration tooling, and D03 deterministic provisional synthetic scenarios.
Reimo delivered D04 development allocation/materialization and the held-out custody foundation, S01 scheduling simulation, and S02 integration with the shared accounting module.
Edison owns the shared P01 impact formulas and classical policies; Reimo's S02 work integrates those formulas rather than claiming their authorship.
Matty implemented the v2 selector amendment and later bounded bundle preparation; Nisha completed private metadata selection and independent receiving and owns report assembly and reliability reporting.
Ved owns ontology/reference methods and independent source verification; Reimo supplies data/simulator methods and limitations for R01.

## Exact evidence citations

| ID | Evidence / citation |
|---|---|
| D1 | [D01 manifest](../../data/manifests/d01-source-inspection.json), [D01 review](../../data/D01_ACCEPTANCE_REVIEW.md), [D06 verification](../handoffs/D06_F04_F05_VERIFICATION.md) |
| D2 | [D05 indexed claims C01–C15/S1–S8](../../data/D05_SOURCE_EVIDENCE.md), [six pinned document hashes](../../data/manifests/d05-document-evidence.json), [reproduction limits](../../data/D05_REPRODUCTION.md) |
| D3 | [SustainDC pinned README](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/README.md#L342-L370), [CarbonExplorer comparison code](https://github.com/facebookresearch/CarbonExplorer/blob/135f21862cb2427b3dbad690519bc05c5f6c539e/src/download_and_process.py), [Table 2](https://arxiv.org/html/2201.10036v3#S3.T2) |
| D4 | [Updated source-status draft](../handoffs/REIMO_SOURCE_EVIDENCE_STATUS_DRAFT.md), [Ved's independent applicability finding](https://github.com/ReymoT/data-center-agentic/issues/13#issuecomment-6457445441), [EPA comparator](https://www.epa.gov/system/files/documents/2024-01/egrid2022_summary_tables.pdf) |
| D5 | [D02 source status](../../data/manifests/d02-source-status.json), [calibration tooling/limitations](../../data/D02_CALIBRATION.md) |
| D6 | [D03 distributions/seeded evidence](../../data/D03_SYNTHETIC_SCENARIOS.md), [generator code](../../dc_sustainability/data/scenarios.py), [shared assumptions](../team/01_SHARED_RULES.md) |
| D7 | [D04 fold-map handoff](../handoffs/D04_DEVELOPMENT_FOLD_MAP_102.md), [materialization handoff](../handoffs/D04_DEVELOPMENT_MATERIALIZATION_112.md), [PR 133](https://github.com/ReymoT/data-center-agentic/pull/133), [development v2 receipt](../../data/manifests/d04-development-content-112-v2/receipt.json) |
| D8 | [v2 pin and exact review](../handoffs/REIMO_ISSUE60_V2_DECISION_DRAFT.md), [PR 206](https://github.com/ReymoT/data-center-agentic/pull/206), [Nisha's independent pin](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6782772091) |
| D9 | [Adopted method limit/current gates](../decisions/NOV10_PROFILE_ADOPTION_AND_FORECAST_SCOPE.md), [I02 checklist](../i02/freeze-manifest.json) |
| D10 | [S01 Option B/Q01](../handoffs/S01_OPTION_B_Q01.md), [current main README](../../README.md), [merged PR 64](https://github.com/ReymoT/data-center-agentic/pull/64), [simulator](../../dc_sustainability/simulator/core.py) |
| D11 | [S02 hand checks](../handoffs/S02.md), [closed technical receiving #36](https://github.com/ReymoT/data-center-agentic/issues/36), [accounting adapter](../../dc_sustainability/simulator/impact.py) |
| D12 | [cb85 result](../handoffs/A01_PAIRED_CLAIM_VALIDATION_RESULT_2026-11-09.md), [receiving PR 205](https://github.com/ReymoT/data-center-agentic/pull/205), [saved-content findings](../handoffs/NOV10_SELECTOR_CONTENT_AND_TRACE.md) |
