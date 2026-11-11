# Reimo R01 contribution draft

## Manager receiving note — November 11, 2026

Published through PR #208 as draft report contribution and historical producer
validation, not an accepted final paper. Deck repair/visual checks and the macOS
checks below are Reimo's reported preparation evidence; Matty did not rerun those
presentation checks or receive the local deck in this four-Markdown-file PR.
The `local-inputs/` and `local-outputs/` presentation files are not repository
artifacts or downloadable attachments here. Nisha should use the report text
with its stated limitations; any deck transfer remains a separate handoff.
The original local-session/no-publication statements below are historical and
do not negate Matty's explicit authorization to publish these four documents.

Group 15 / Project 21. Local draft, November 10, 2026 (Phoenix), reviewed against
fetched main `27083dc4e3be7c9fc32071fe3a6a33aff3218837`, instruction 1.28.
No authoritative record is replaced and no scientific result is invented.
Nisha assembles the presentation/report. Reimo owns R01 data/simulator content;
Ved is technical contact. Edison owns P01 formulas; Reimo integrates them in S02.

## Send to Nisha

Send the revised presentation copy together with the slide notes and the report
text below. The complete supplied ten-slide deck and all ten notes were read.
Keep the original deck unchanged. This contribution covers report §F datasets
(about 0.75 IEEE page), §E simulator/algorithms, Reimo's §I contribution and review
of §C problem statement. [Report assembly outline](../report/README.md) supplies
the current 5–10-page IEEE format and section ownership.

Internal targets: deck review November 9–11, rehearsal by November 13 and
submission target November 14. These are preparation targets, not invented
scientific deadlines. [Current course record](../decisions/Q13_OFFICIAL_REPORT_2026-11-02.md)
and [latest #16 comment](https://github.com/ReymoT/data-center-agentic/issues/16#issuecomment-6777223603)
confirm Project 21 and reported December 9 end-of-day report deadline. Official
timezone/release details remain with Nisha. The supplied local deck resolves the
missing review-input dependency for this session; no public team review link or
actual submission is claimed.

## Complete-deck review and focused revision plan

| Slide | Finding in original | Revision / boundary |
|---|---|---|
| 1 | Contributor names and Project 21 present; findings explicitly pending in notes | Preserve |
| 2 | General scheduling motivation reasonable; notes mention battery behavior although this study has no modeled battery control | Add precise R01 site/slot assumptions in notes and clarify battery is outside scope |
| 3 | “Observed grid-carbon” and broad “Arizona” risk implying measured site/state factors; Frontier status vague; source lineage detail absent | Use historical AZPS generation-mix proxy; give exact scenario counts, withheld variant, D01/D02/D05 boundaries and pins in notes |
| 4 | Related work contribution belongs to other owners | Preserve body and notes; no claim that this audit reverified every literature entry |
| 5 | Architecture is present; S01 state/step/rejection/completion semantics and independent reproduction caveat missing | Preserve diagram and other-owner content; append R01 simulator evidence/citations to notes |
| 6 | Formula says IT power × hours but carbon lacks facility PUE; S02 equal-work/missing-carbon checks absent | Correct formula with PUE and add hand-check results, 30-slot ledger and strict comparison guards in notes; preserve six policy descriptions |
| 7 | Planned counts correctly labeled; no pool/fold/private v2 protocol or current gate status | Preserve matrix/300 planned count; clarify private selection pending and append current D04 protocol/pins/ownership in notes |
| 8 | “kgCO2e” overstates unresolved source pollutant basis | Use modeled carbon proxy in kg; append S02 comparability caveat while preserving Nisha's evaluation design |
| 9 | Work sharing and milestones present | Preserve visual and teammates' scope; append exact Reimo remaining actions and latest gate status in notes |
| 10 | Source entry says Arizona, no exact source pin or exporter distinction | Use AZPS 2022 proxy wording; add exact data/method/licensing evidence in notes; preserve literature entries |

The original package has nine dangling content-type overrides for nonexistent
slideMaster2–10 and four invalid negative-height decorative lines on the cover.
PowerPoint requested repair. The revised copy removes the dangling declarations
and uses PowerPoint's native repair/save, which normalizes those four cover lines
to horizontal. All other shape positions/sizes, all authored visible text and all
speaker notes survive. This small cover-art repair is the only layout difference
found in the package comparison; no other contributor's text is rewritten.
Ten slides and the existing theme/design remain, with R01 detail in notes to avoid
crowding the 15-minute presentation.

## Slide-ready R01 material and speaking points

### Data and scenarios (existing slide 3)

- Historical source: 8,760 hourly UTC labels in the pinned 2022 AZPS proxy file.
- Workload: 40 materialized development episodes with three blocked folds.
- Normal 12 jobs/7 flexible; spike 20/12; limited 12/2; infeasible 12/7, with one
  deliberately impossible deadline. A normal variant withholds forecasts while
  retaining its private jobs and realized carbon.
- All job draws remain provisional synthetic assumptions. Frontier empirical
  calibration is unavailable. B1–B3 unresolved; B4 provisional.

Suggested spoken text: “Our historical carbon input is a fuel-weighted generation
proxy for AZPS, not a verified site electricity measurement. Existing D01/D06
records establish its pinned identity, hourly labels and numerical formula. They
do not authenticate the original exporter, pollutant boundary, physical interval
convention or derived-data rights. Jobs are deterministic synthetic draws. Forty
development episodes and their original content commitments exist; the held-out
cohort remains a separate private step. We have no empirical Frontier quantiles.”

### Simulator and impacts (existing slides 5–6)

- S01 reveals arrived jobs and immutable running work; future arrivals and private
  realized carbon stay outside policy views. A controller-approved current start
  occupies `[start, start+duration)` and must satisfy every capacity/deadline slot.
- Starts occur only at 0–23; 24–29 complete/account running work. Rejected starts
  create no new occupancy; the clock and existing work still advance once.
- IT capacity 100 kW includes 40 kW background. Generated power 10–40 kW,
  durations 1–4 h, arrivals 0–17, deadlines ≤30, fixed PUE 1.2 are assumptions.
- Facility energy = PUE × IT kW × hours. Carbon proxy kg = Σ(facility kWh ×
  source g/kWh)/1,000. Keep job/background/site ledgers separate for all 30 slots.
- S02 blocks savings claims for unfinished work or mismatched inputs/completion;
  missing carbon preserves energy but leaves affected emissions unavailable.

Synthetic hand-check table, suitable for the report (not a study-results chart):

| Same two jobs, 140 completed IT kWh | Starts 0/2 | Starts 2/4 |
|---|---:|---:|
| Seven-slot job carbon proxy, PUE 1.0 | 54.5 kg | 48.4 kg |
| Seven-slot background, PUE 1.0 | 116 kg | 116 kg |
| Seven-slot site, PUE 1.0 | 170.5 kg | 164.4 kg |
| Job carbon proxy, PUE 1.2 | 65.4 kg | 58.08 kg |
| Facility job energy, PUE 1.2 | 168 kWh | 168 kWh |

These are the shared synthetic seven-slot J1/J2 checks, not 30-slot totals or
measured site savings. The 30-slot test explicitly supplies 23 extra synthetic
carbon observations. [S02 evidence](S02.md),
[tests](../../tests/simulator/test_s02_impact.py),
[completed receiving #36](https://github.com/ReymoT/data-center-agentic/issues/36).

### Partitioning and outstanding science (existing slide 7)

“The development allocation and materialization are already delivered, including
the 16/12/12 episode fold map. We do not redraw them. The proposed held-out design
uses six dates in six months from the full 168-date days-15–28 pool, with four
core scenarios and a related withheld normal variant per date. The v2 selector
reserves scoring and legacy/CF60 history under both interval hypotheses, including
all fixed development records. Nisha has pinned v2 and reports private storage
ready. Reimo's exact restricted-record confirmation comes before her nonce,
selection, independent isolation and receiving. Source-use evidence and Matty's
fresh bounded ingest approval are separate. No held-out result or full freeze
exists. Legacy or CF60 are the only live v2 forecast candidates.”

The 30-episode matrix and 300 runs are planned. A flat persistence horizon gives
no forecast carbon timing signal among otherwise comparable starts. Report this
limitation and preserve unknown O02/Q08/C/D compatibility. A forecast-only first
comparison with all 1,200 saved-state positions missing cannot certify features,
labels or rollouts. [Accepted scope](../decisions/NOV10_PROFILE_ADOPTION_AND_FORECAST_SCOPE.md).

## IEEE report contribution — draft text

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
interval hypotheses across date groups. Actual private nonce/selection and
independent receiving remain pending Reimo's restricted-record confirmation.
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
nonflexibility and running-plus-proposed IT capacity. The controller authenticates
and binds a passing latest-state check before supplying approved actions. A
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
and independent replay have bounded development integration evidence. S01's
separate Ved reproduction remains recorded as pending in current main. The
latest public cb85 technical validation/receiving covers six results and 180
decision records; it does not establish comparative study superiority, complete
scientific I01/I02 acceptance, source rights or held-out findings. Saved explanations
retain contradicted/unsupported claims and both repairs failed checking. [D10–D12.]

### Research limitations

The setting is one simulated site/resource pool with synthetic flexibility and
fixed power/PUE. It has no live facility control or empirical Frontier calibration.
AZPS generation geography does not establish electricity supplied to a Phoenix
site; generation-average attribution is not consumption-adjusted, marginal,
market-based or avoided-emissions accounting. Original export/interval/pollutant
and rights gates remain open. Forecast availability is simulated, and flat
persistence cannot test choosing cleaner future hours. Existing labels/models
cannot be declared CF60-compatible without the separately authorized assessment.
Actual held-out custody, accepted freeze, final runs/scoring and final scientific
evaluation remain incomplete. Results must keep fallback, initial model actions,
failed repairs, omissions, missing evidence and unfinished work distinct.

### Reimo contribution statement (§I)

Reimo implemented the pinned-source adapter and evidence inventory (D01/D05),
Frontier calibration tooling (D02), deterministic provisional scenarios (D03),
development allocation/materialization and held-out custody foundation (D04),
the scheduling simulator (S01), and its integration with Edison's shared impact
calculations (S02). He owns source-evidence follow-up and the R01 data/simulator
report. Matty implemented the merged v2 selector amendment; Nisha independently
pinned it and owns private selection/isolation/receiving. Ved owns independent
source/reference verification; those duties are not transferred to Reimo.

## Exact evidence citations

| ID | Evidence / citation |
|---|---|
| D1 | [D01 manifest](../../data/manifests/d01-source-inspection.json), [D01 review](../../data/D01_ACCEPTANCE_REVIEW.md), [D06 verification](D06_F04_F05_VERIFICATION.md) |
| D2 | [D05 indexed claims C01–C15/S1–S8](../../data/D05_SOURCE_EVIDENCE.md), [six pinned document hashes](../../data/manifests/d05-document-evidence.json), [reproduction limits](../../data/D05_REPRODUCTION.md) |
| D3 | [SustainDC pinned README](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/README.md#L342-L370), [CarbonExplorer comparison code](https://github.com/facebookresearch/CarbonExplorer/blob/135f21862cb2427b3dbad690519bc05c5f6c539e/src/download_and_process.py), [Table 2](https://arxiv.org/html/2201.10036v3#S3.T2) |
| D4 | [Updated source-status draft](REIMO_SOURCE_EVIDENCE_STATUS_DRAFT.md), [Ved's independent applicability finding](https://github.com/ReymoT/data-center-agentic/issues/13#issuecomment-6457445441), [EPA comparator](https://www.epa.gov/system/files/documents/2024-01/egrid2022_summary_tables.pdf) |
| D5 | [D02 source status](../../data/manifests/d02-source-status.json), [calibration tooling/limitations](../../data/D02_CALIBRATION.md) |
| D6 | [D03 distributions/seeded evidence](../../data/D03_SYNTHETIC_SCENARIOS.md), [generator code](../../dc_sustainability/data/scenarios.py), [shared assumptions](../team/01_SHARED_RULES.md) |
| D7 | [D04 fold-map handoff](D04_DEVELOPMENT_FOLD_MAP_102.md), [materialization handoff](D04_DEVELOPMENT_MATERIALIZATION_112.md), [PR 133](https://github.com/ReymoT/data-center-agentic/pull/133), [development v2 receipt](../../data/manifests/d04-development-content-112-v2/receipt.json) |
| D8 | [v2 pin and exact review](REIMO_ISSUE60_V2_DECISION_DRAFT.md), [PR 206](https://github.com/ReymoT/data-center-agentic/pull/206), [Nisha's independent pin](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6782772091) |
| D9 | [Adopted method limit/current gates](../decisions/NOV10_PROFILE_ADOPTION_AND_FORECAST_SCOPE.md), [I02 checklist](../i02/freeze-manifest.json) |
| D10 | [S01 Option B/Q01](S01_OPTION_B_Q01.md), [current main README](../../README.md), [merged PR 64](https://github.com/ReymoT/data-center-agentic/pull/64), [simulator](../../dc_sustainability/simulator/core.py) |
| D11 | [S02 hand checks](S02.md), [closed technical receiving #36](https://github.com/ReymoT/data-center-agentic/issues/36), [accounting adapter](../../dc_sustainability/simulator/impact.py) |
| D12 | [cb85 result](A01_PAIRED_CLAIM_VALIDATION_RESULT_2026-11-09.md), [receiving PR 205](https://github.com/ReymoT/data-center-agentic/pull/205), [saved-content findings](NOV10_SELECTOR_CONTENT_AND_TRACE.md) |

## Other Reimo responsibilities, ranked by urgency

| Priority | Action personally owned / input owed | Boundary and current evidence |
|---|---|---|
| 1 | Authenticate exact restricted v2 record, then approve confirmation or post precise blocker | Immediate #60 request; public mechanics pass. No record locator supplied here; no personal acceptance invented. |
| 2 | Approve/post authoritative source evidence or unavailable-record/provider status; decide whether to send maintainer questions | B1–B3 unresolved, B4 provisional; external facts cannot be generated by coding. |
| 3 | Deliver/review R01 slide notes, §F/§E/§I text and §C problem-statement wording with Nisha | Current complete local deck read; review November 9–11, rehearsal by 13, internal submission by 14. Nisha owns assembly. |
| 4 | Supply affected-owner data/mapping/workload scope input when exact proposal/evidence arrives | D04/D05/Q05/Q06 role persists; any mapping/method/distribution change needs affected consumers and preserved originals. No blanket new confirmation request. |
| 5 | Maintain Reimo modules and fix demonstrated integration defects | S01/S02, D03, development folds/materialization, selector foundation and CF60 broker already merged. No new bug found requiring code here. |
| Deferred | Empirical Frontier calibration | No authenticated job table/dictionary/rights/units or access resolution found. Tooling is complete; no repeated access attempt or invented calibration. |

GitHub open-issue searches returned #60, #16, #95, #164 and #166, with #60 the
only open issue assigned to ReymoT. Other role duties can exist without an assigned
issue, which is why the master/checklist/report outline were also reviewed.
Do not reopen closed #7 (simulator), #36 (technical accounting receiving), #102
(fold map), #112 (materialization), #22 (sampling), or #185 (bounded profile
assessment/adoption). Older descriptions still contain historical pending work.
Latest issue state, accepted comments and main supersede those descriptions.

Nisha's private selection/receiving, I02, held-out reliability/reporting (#95),
official course guidance (#16), Ved's S01 reproduction/O04/I03 (#166), Edison's
P07 (#164) and Matty's execution approvals/I04 stay with their owners. Reimo
provides inputs and owns fixes to his components; he should not execute or take
over those tasks. #16 says all teammate policy-position replies are received:
do not ask Reimo to repeat old platform/license/access/retention replies.

## Validation and preservation record

Final revised deck: `local-outputs/Group15-Project21-FA26-Group-Project-Presentation-Reimo-R01-Final.pptx`.
Read all ten source slides and notes, then visually inspected all ten revised
slides in Microsoft PowerPoint. The final file was closed and reopened without
a repair prompt. All intended visible text and all ten notes match the edited
candidate after native save. The original remains byte-identical, SHA-256
`767c7cd20b0c0294c44b5c6b34bfd8af373f9c31b9954729e1d5bde34db51171`.
Final deck SHA-256:
`8c70f726086c08809a09b3d215ead23748c0317263dde3c5139c8a01f54c520f`.

| Check actually run | Result |
|---|---|
| Exact v2 source bytes and LF SHA against reviewed selector commit | Match |
| AST comparison against historical v1 | Only selection/metadata functions plus new footprint helpers and version/algorithm changes |
| `python -m pytest tests/data/test_held_out_custody.py tests/data/test_issue60_causal_forecast_proof.py -q --tb=short` | 72 passed, synthetic/public metadata only |
| `python scripts/validate_setup.py` | Passed, including local Markdown links, role inventories, deployment/contract and policy consistency |
| `python scripts/validate_i02_freeze_manifest.py docs/i02/freeze-manifest.json` | Valid checklist: 13 pending, 5 blocked, 0 frozen; not readiness |
| `python -m ruff check dc_sustainability scripts tests` | Passed |
| `python -m ruff format --check dc_sustainability scripts tests` | 244 files already formatted |
| Presentation package integrity validator on final deck | 10 slides, zero findings |
| Presentation geometry validator, original size 12192000 × 6858000 EMU, heading/bullet checks | Zero findings/warnings |
| Original/final preservation inspection | Original unchanged; all notes retained; all non-R01 visible wording retained; slides 2–10 geometry unchanged |
| `git diff --check` and explicit new-draft whitespace checks | Passed |

The bundled Artifact Tool runtime and `load_workspace_dependencies` entry point
are unavailable in this session. Used focused OOXML text/notes edits and native
PowerPoint repair/save rather than replacing the deck or installing a substitute
slide-authoring library. The original has been preserved. Geometry validation and
native visual checks replace the unavailable Artifact Tool import check; this is
disclosed rather than reported as a tool PASS. Initial synthetic-test collection
lacked joblib; adding pinned import dependencies resolved collection without test
changes. Validation used a temporary macOS CPython 3.12.15 environment and does not
certify the Windows dependency lock. No full-suite rerun, training, model calls,
real-source access, selection, solver evaluation or study execution occurred.

All tracked base files remain unchanged. Only these three draft handoffs and
the local presentation copy were created for review. The supplied original and
output directory remain untracked; no Git action will publish either. This is a
completed R01 content/visual draft review, not acceptance by Nisha or a completed
full-team scientific/report review. No commit, push, merge, issue posting or
maintainer contact was made.
