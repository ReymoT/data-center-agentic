# Reimo source-evidence status draft for issue #60

## Manager review — November 11, 2026

Published as supporting draft evidence through PR #208. The November 10 audit
and unsent external-request templates below are retained with their original
scope. [Reimo has posted the source/blocker status to #60](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6787639650); do not request
that same status again as though no response exists. Authoritative B1–B3 evidence
and B4 acceptance remain outstanding. External author requests are still drafts;
no sending, external response or source-use approval is established here.

Local unsent producer draft, November 10, 2026 (Phoenix). Reviewed fetched main
`27083dc4e3be7c9fc32071fe3a6a33aff3218837`, instruction 1.28. It preserves
[D05 evidence](../../data/D05_SOURCE_EVIDENCE.md),
[reproduction history](../../data/D05_REPRODUCTION.md),
[D04/Q06 status](../../data/D04_Q06_STATUS.md),
[source acceptance audit](SOURCE_ACCEPTANCE_AUDIT.md) and
[issue #60 source handoff](ISSUE60_SOURCE_EVIDENCE.md). None is overwritten.
No CSV was opened, hashed, parsed, downloaded or extracted. Existing primary
observations below are attributed to retained evidence, not newly repeated.

## Decision-ready issue response

> @MattyAnd @vedp3705 My source-evidence inventory is delivered, but I do not have
> the missing authoritative records that would close B1–B4. B1 remains unresolved:
> the historical EIA archive/ZIP/EBA identities and checksums, exact exporter/caller,
> preprocessing/serialization/environment and pollutant-factor/GWP boundary tied to
> the pinned CSV are unavailable in the inspected evidence. B2 remains unresolved:
> no authenticated exporter record establishes this CSV's start/end labels and
> first/last physical intervals. B3 remains unresolved: the available software
> licenses and EIA policy do not establish the exact derived CSV's applicable
> terms/notices for our intended uses. B4 remains provisional: only a historical
> 2022 AZPS generation-mix proxy for a simulated Phoenix scheduling study is
> supportable, pending source/mapping/rights and affected-owner acceptance.
>
> The primary evidence providers are SustainDC's data/export authors and rights
> holders, with CarbonExplorer's method/factor authors and rights holders for their
> lineage and licensed scope. EIA can clarify historical archive/series records,
> not authenticate another project's export. I have a precise unsent clarification
> request ready for approval. No maintainer has committed a response date, so an
> authoritative resolution ETA is unknown. Ved's completed identity/structure/
> formula review stands; another structural test cannot replace these records.
> This source gate is separate from my restricted v2 parameter review and Nisha's
> subsequent private selection/isolation/receiving. No source ingest or study run
> is authorized by this response.

This text is ready for Reimo to approve/post. It makes no commitment to contact
anyone before his approval. Preserve the original #60 escalation clocks; this draft
does not restart them or promise a response from an external party.

## Exact object under review

- Repository: `HewlettPackard/dc-rl`, upstream commit
  `a92b4755aca560e34a98d14028dda629eb968482`.
- Path: `data/CarbonIntensity/AZPS_NG_&_avgCI.csv` (locator only, not accessed).
- Historical expected SHA-256:
  `e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4`.
- Retained identity evidence: [D01 manifest](../../data/manifests/d01-source-inspection.json)
  and [version-matched D06 verification](D06_F04_F05_VERIFICATION.md).
  Recorded size 601,730 bytes, Git blob `d5337a654e77c938d0909e76d56efdf3ad491e83`,
  8,760 ordered hourly UTC labels in 2022, no gaps/duplicates, zero row exclusions.
  Existing formula evidence records all 8,760 weighted averages matching exactly.
- [Ved's independent applicability review](https://github.com/ReymoT/data-center-agentic/issues/13#issuecomment-6457445441)
  accepts bounded identity/structure/formula work, not B1–B4 acceptance.
  [Later #60 applicability finding](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6566631218)
  retains unresolved provenance/interval/rights and provisional suitability.
  [Latest source/forecast review](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6641566110)
  accepts conditional CF60 mechanics only; [compatibility follow-up](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6667103300)
  requests separately approved development evidence, not another structural rerun.

## Evidence index and applicability

| ID | Exact source | What it establishes |
|---|---|---|
| E1 | [Pinned SustainDC README](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/README.md#L342-L370), retained SHA-256 `3c556ddf75430c85774e24a3361a56119d9934a755264844185434084a913e7c` | EIA bulk source attribution and fuel labels. No original export log. |
| E2 | [CarbonExplorer comparison code](https://github.com/facebookresearch/CarbonExplorer/blob/135f21862cb2427b3dbad690519bc05c5f6c539e/src/download_and_process.py), SHA-256 `6e1f124e251aad4a73dcf70ee0acbecdcf85032860607d9c515f4fdc855d0412`, Git blob `c4204e4bb636c5072f927846ad7edf626cf586ae` | A related implementation at this revision, not authenticated original producer of the CSV. |
| E3 | [CarbonExplorer paper Table 2](https://arxiv.org/html/2201.10036v3#S3.T2) | Related fixed factors labeled gCO2eq/kWh. Does not bind pollutant/GWP/lifecycle provenance to the export. |
| E4 | [EIA-930 instructions](https://www.eia.gov/survey/form/eia_930/instructions.pdf), page 3; [2021 EIA context](https://www.eia.gov/todayinenergy/detail.php?id=49216) | Hour-ending UTC guidance; current PDF is not an archived 2022 exporter specification. |
| E5 | [EIA reuse policy](https://www.eia.gov/about/copyrights_reuse.php) | EIA information reuse with source/date acknowledgment and protected-material exceptions; reread in this review. |
| E6 | [Pinned SustainDC MIT license](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/LICENSE), SHA-256 `ef0f2b1973f2ea351a8edaca64888b019ae4b08f50d2eaef4fd7643462140da6`; [combined-work notice](https://github.com/HewlettPackard/dc-rl/blob/a92b4755aca560e34a98d14028dda629eb968482/README.md#L577-L591) | Software/documentation license and mixed-work notice, no conclusive CSV-specific applicability. License reread, no data fetch. |
| E7 | [Pinned CarbonExplorer license](https://github.com/facebookresearch/CarbonExplorer/blob/135f21862cb2427b3dbad690519bc05c5f6c539e/LICENSE), SHA-256 `7c6858d0e71dc8b858255270ad4b5004e80b5b058bf5bbc408a28430d6ddbf4b`, Git blob `a115f899f8d09ef3b1def4a16c7bae1a0bd50fbe` | CC BY-NC 4.0 conditions for applicable licensed material. Reread through GitHub connector after web fetch failed; no applicability assumption. |
| E8 | [EPA eGRID2022 summary tables](https://www.epa.gov/system/files/documents/2024-01/egrid2022_summary_tables.pdf), Table 1 | Annual AZNM magnitude comparator only, with different geography, weighting and pollutant scope. |
| E9 | [Historical code search manifest](../../data/manifests/d05-historical-code-review-60.json) | Bounded 30-file search at the exact upstream commit, complete tree metadata and blob identities. No exporter/caller found within that search; no claim of nonexistence across all history. |
| E10 | [Conditional interval artifact](ISSUE60_INTERVAL_COMPARISON.json) | 120 generic timestamp-only rows at four boundary dates; no source values or selected held-out metadata. |

The six historical document hashes are in
[d05-document-evidence.json](../../data/manifests/d05-document-evidence.json).
They identify documents, **not the missing EIA archive**. Rereading a policy does
not retroactively authenticate a historical export or establish new source acceptance.

## B1 — Historical provenance: UNRESOLVED

**Independently verified:** Ved accepts the existing file identity, continuity,
bounded adapter/window reproduction and recorded all-row formula match. E1/E2/E3
support a fuel-weighted proxy interpretation. The historical search E9 records
SustainDC `CI_Manager` as a consumer of existing `avg_CI`, not an exporter.

**Inference:** E2, if invoked for AZPS, selects
`EBA.AZPS-ALL.NG.{WND,SUN,WAT,OIL,NG,COL,NUC,OTH}.H` and weights by
11/41/24/650/490/820/12/230. It reads unversioned EBA.zip/EBA.txt with
PyArrow/pandas, inclusively filters/reindexes UTC hours, fills missing values with
zero, casts generation to integers and clips negatives. It returns
`carbon_intensity`, while this CSV uses `avg_CI`. Similar formulas and exact
numerical agreement do not establish original caller, endpoint trimming, rename,
preprocessing, pollutant assignment or serialization. No EIA-to-CSV regeneration
procedure tied to these bytes is verified.

**Missing authoritative record:** original EIA-930 archive/version/retrieval and
revision record; original ZIP and extracted EBA identities/SHA-256 values; actual
BA/fuel series metadata/units; exporter repository/commit/file plus caller/command;
date inclusivity, timezone/shift, missing/negative handling counts, rounding,
ordering, renaming, CSV encoding/serialization, environment; exact factor citations,
gases, CO2/CO2e, GWP version/horizon, lifecycle/operational boundary and
imports/exports treatment. No element is filled from a later comparable program.

**Provider/action:** Reimo requests the export record from SustainDC data authors;
CarbonExplorer authors supply factor lineage and confirm whether their method
actually generated this export. EIA can help recover archive/series identities.
Ved checks applicability, Edison physical accounting. The smallest next action is
approve/send the exact request below. No external response commitment or ETA exists.

## B2 — CSV interval semantics: UNRESOLVED

**Independently verified:** ordered UTC labels and the public conditional arithmetic
in E10. E4 describes upstream hour-ending reporting. It does not prove preservation
through this export.

**Inference:** if a row at label `t` is hour-ending, it represents `[t−1h,t)`.
For Phoenix physical slot `[07:00,08:00)`, start interpretation uses label 07:00,
end interpretation label 08:00. Existing start-conditional mapping stays unchanged.
The first label under end semantics crosses into the previous physical year, and
year-tail missing rows cannot wrap.

**Missing authoritative record:** original exporter/data dictionary demonstrating
start/end convention, any shift/trim, and the exact first/last physical intervals.
Historical observation availability/revisions also remain distinct from label time;
CF60's one-hour simulated lag is an assumption, not a verified reporting delay.

**Provider/action:** SustainDC exporter author supplies the record; Reimo then
proposes any warranted mapping amendment to Ved/Edison/Nisha/Matty with all 30 slots
and forecast footprints checked. No index shift now. No owner-promised resolution
ETA exists. v2 union isolation preserves both hypotheses without deciding B2.

## B3 — Rights and attribution: UNRESOLVED for exact derived material

This is a record of available license evidence and missing applicability, not a
new legal determination. EIA policy and both pinned licenses were reread. The
following distinctions apply to each proposed use, subject to the actual rights
holder's scope and third-party exceptions.

| Material | Internal academic use | Teammate sharing | Aggregate publication | Redistribution | Derivatives |
|---|---|---|---|---|---|
| EIA information products (E5) | General reuse supported | General distribution supported | General use supported | General distribution supported | Reuse supported within policy scope |
| SustainDC software/docs (E6) | MIT software grant | MIT with notices | Software use supported with notices where applicable | MIT with notices | MIT with notices |
| CarbonExplorer licensed code/assets (E7) | Noncommercial license, within licensed scope | Conditional noncommercial sharing | Citation alone does not decide licensed scope of copied material | Conditional noncommercial sharing | Conditional noncommercial adaptation |
| Exact SustainDC derived CSV | Applicability unresolved | Applicability unresolved | Intended use requires clarification, no blanket approval | File-specific grant/notices missing | File-specific applicability missing |
| Source-derived episode artifacts/results | Source-use basis unresolved | Source-use basis unresolved | Do not equate aggregate reporting with raw redistribution; exact applicability still needs clarification | Embedded hourly values need applicable permission | Derived numerical content needs applicable terms |

EIA asks for source/date acknowledgment and identifies protected-material
exceptions. MIT covers its defined software/documentation, with copyright and
permission notice retention. CC BY-NC 4.0 covers rights the licensor controls in
licensed material, with noncommercial limits, attribution/license information and
modification notices. None authenticates the chain into this exact CSV. Prior team
development authorization is not an external license grant. Private source-derived
contents stay outside Git, with no new transfer/publication authorized here.

**Missing/provider/action:** SustainDC's relevant rights holder must identify the
CSV's applicable terms, author/source chain and required attribution; CarbonExplorer
rights holders clarify applicable code/method/data scope and third-party factors.
Ask separately about all five uses above. Ved independently reviews received
evidence. No response ETA exists. A maintainer response must be attributable to a
person authorized to clarify the rights; silence is not permission.

## B4 — Suitability: PROVISIONAL

**Independently verified:** existing source arithmetic/structure and the stated
simulation assumptions. E8 is an annual AZNM magnitude comparison, not AZPS
calibration, site attribution or an acceptance threshold. Existing method evidence
supports a fixed-factor historical generation-mix proxy, with unverified boundaries.

**Proposed narrow claim:** “A historical 2022 AZPS generation-mix carbon-intensity
proxy in a simulated Phoenix data-center scheduling study using synthetic jobs and
fixed power/PUE assumptions.” Use only in permitted development with the unresolved
source/mapping/rights caveats; final acceptance still needs affected-owner agreement.

**Inference/missing record:** no evidence establishes actual modeled-site supplier,
service area, consumption/import/export flows, market-based claims, marginal
response, causal avoided emissions or verified operational carbon savings. A
physical/site claim would require actual supply/accounting evidence from a site or
utility operator and a justified emissions method. Broader claims are unnecessary
for the proposed bounded study.

**Provider/action:** Reimo proposes the narrow scope; Ved/Edison review physical
accounting and Nisha evaluation wording. Resolve B1–B3 and record scope agreement,
or explicitly narrow/defer the affected scientific claim with Matty. No external
site-data acquisition or alternative dataset substitution is authorized. No grounded
completion ETA exists.

## External request draft — not sent

**To:** SustainDC / HewlettPackard `dc-rl` data/export maintainers through their
[repository](https://github.com/HewlettPackard/dc-rl). Ask them to route to the
original exporter and authorized rights holder. No named person's authority or
private email is assumed.

**Subject:** Provenance, interval convention and permitted uses of pinned AZPS CSV

We are preparing an academic simulated scheduling study and need to clarify
`data/CarbonIntensity/AZPS_NG_&_avgCI.csv` at commit
`a92b4755aca560e34a98d14028dda629eb968482`, recorded SHA-256
`e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4`.
Could the original data/export author or authorized rights holder supply:

1. The historical EIA-930/EBA archive version, dated ZIP and extracted EBA
   identities/checksums, actual series metadata and exporter revision/caller/command.
   Please include date endpoints, missing/negative handling, any timestamp shifts,
   rename/rounding/CSV serialization and dependency versions, or identify which
   original records no longer exist.
2. The CSV-specific interval definition: does label `2022-01-01T07:00Z` mean
   `[07:00,08:00)` or `[06:00,07:00)`? Please cite export code/dictionary and
   first/last physical intervals, including any trimming.
3. The factor references and actual pollutant/gases, GWP horizon/version,
   operational/lifecycle and imports/exports boundary. Was the cited CarbonExplorer
   implementation used for this exact export, and at what revision?
4. Terms and attribution applying specifically to the CSV, source-derived episodes
   and results: internal academic use, teammate sharing, aggregate publication,
   redistribution and adaptations. Please identify third-party restrictions and
   the rights holder authorized to clarify them separately from the software MIT
   license. We will not treat silence as permission.

An authoritative record or a precise statement that a record is unavailable would
both help. We will preserve original data and avoid operational/marginal/avoided
emissions claims. Thank you.

**Follow-up to CarbonExplorer method/factor maintainers:** through
[facebookresearch/CarbonExplorer](https://github.com/facebookresearch/CarbonExplorer),
reference comparison commit `135f21862cb2427b3dbad690519bc05c5f6c539e`. Ask whether
it actually generated the SustainDC export, for original factor/GWP/boundary
citations, and for the scope of CC BY-NC 4.0 across code/assets and any derived
numerical dataset. Ask them to identify the relevant rights holder and upstream
third-party restrictions. Do not imply they can authorize HPE material.

**Escalation to EIA only if needed:** ask the EIA data team for archived EBA series
definitions/revision identities and recoverability of the historical snapshot.
EIA cannot certify the downstream caller or another author's licensing scope.

## Immediate actions and realistic timing

| Next action | Accountable owner | Timing grounded in evidence |
|---|---|---|
| Approve/post precise blocker or supplied authoritative record to #60 | Reimo | Matty requests a response today/as soon as possible; no invented exact hour |
| Approve the external request and chosen channel | Reimo | Draft ready now; no contact made |
| Return historical export/rights clarification | Upstream authors/rights holders | Unknown; no actual commitment |
| Verify new evidence without repeating D06 structure work | Ved, with Edison accounting input | No new committed ETA found |
| Exact v2 restricted-record confirmation | Reimo | Separate immediate gate, see [decision draft](REIMO_ISSUE60_V2_DECISION_DRAFT.md) |
| Actual nonce/selection/isolation/receiving | Nisha | Her conditional within-two-days commitment after remaining inputs, not a source ETA |
| Fresh bounded ingest authorization | Matty | Only after source-use and authenticated receipt gates |

No source acceptance, interval change, source read, run, freeze or public posting
was performed in this audit.
