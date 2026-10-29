# D04 reproducible provisional split tooling

October 28: [Issue #102 concrete 40-episode development proposal](../docs/handoffs/D04_DEVELOPMENT_FOLD_MAP_102.md)
now includes exact IDs, dates, development-only seeds and a P03-compatible fold map.
Affected-owner adoption agreement remains outstanding; this is not scientific freeze.
No actual episode contents or held-out allocation are generated. Earlier missing-map
statements below describe the historical snapshot.

Reimo owns D04; Nisha independently verifies the split/evaluation boundary.
Reviewed fetched authoritative main `be87f581f39c1488ab429775b0d83fcff4b1e424`,
instruction 1.27, F02 1.0.0, on October 26, 2026. Working task branch:
`reimo/d04-episode-splits`; current checkout matches that main before these edits.
Read [assignment/context #60](https://github.com/ReymoT/data-center-agentic/issues/60),
[Q06 inventory](D04_Q06_STATUS.md), [source evidence](D05_SOURCE_EVIDENCE.md),
[D03](D03_SYNTHETIC_SCENARIOS.md) and [F02](../docs/INTERFACES.md).
No GitHub write, scientific approval or final freeze is part of this work.

## Implemented boundary

[The module](../dc_sustainability/data/splits.py) implements a private local D04
metadata format, **not a new F02 contract or an adopted runner interface**.
It does not fetch/read source carbon, generate jobs, instantiate any episode,
produce forecasts/reference labels, invoke models, score outcomes or train policies.
The only held-out artifacts exercised in new D04 tests are allocation metadata, never
held-out episode contents or realized-carbon values. No actual study allocation
manifest or selected held-out inputs are checked into the repository.

`propose_allocation` requires explicit development candidate dates, held-out
candidate dates, date-selection seed and job-seed root; it has no scientific seed
or date-pool defaults. It ranks dates by SHA-256 of the version, seed, partition
and ISO date, with lexical ties. From that order it greedily selects ten separated
development dates, then six separated held-out dates in distinct months. All
candidates must be in 2022, days 1–14 for development and 15–28 for held-out.
Insufficient isolated candidates fail; there is no automatic seed retry, window
wrapping, fallback distribution or outcome-dependent selection. Input order has
no effect. Greedy failure does not prove no feasible allocation exists: supply an
explicitly reviewed alternative pool/algorithm rather than searching by outcomes.

Each selected development date gets all four D03 scenarios (40 allocations).
Each held-out date gets all four plus a normal withheld-forecast allocation
(30 total). The withheld allocation references its normal parent and shares its
window and job seed. The caller must preserve identical normal jobs/actuals when
contents are eventually materialized; this module does not materialize them.
Per-date/scenario seeds use the first 16 hex digits of the versioned SHA-256
seed derivation recorded in the manifest. Episode IDs are opaque hashes without
partition/scenario/seed prefixes; IDs still belong outside policy-side split maps.

## Complete windows and folds

`Window` delegates to unchanged D01 `episode_indices(..., interval_convention="start")`.
It records all 30 zero-based source-hour indices and half-open proposed UTC bounds.
Jan 1 is indices 7–36, `[Jan 1 07:00, Jan 2 13:00)`; adjacent dates share six
hours. Day-number partitions alone cannot establish separation. Dec 31 and
out-of-year windows fail, without trimming or wrapping.

These are **conditional physical indices**, not verified physical intervals.
Source labels remain unverified. If labels are hour-ending, the Phoenix slot
`[07:00,08:00)` needs the 08:00 row, not 07:00. Q05 must establish the original
CSV convention before an authoritative physical mapping/report can be frozen.
No source observations or CarbonSemantics records are relabeled here.

`overlap_report` compares full half-open windows by source-byte SHA-256, including
next-day and cross-month tails. Caller aliases/path changes cannot evade a match.
Related groups additionally join windows even across byte identities. Revised,
shifted or duplicated datasets with different hashes need an authoritative common
source-identity/crosswalk before combined scientific use: hashes alone cannot
prove independence of physically related data. This proposal accepts only the
single pinned D01 source.

`blocked_folds` computes transitive components from related groups **or** overlap.
All scenarios of a selected date stay together. Distant related dates absorb
intervening components so temporal blocks cannot interleave. It divides ordered
components into three contiguous blocks, balancing group counts with remainders
in earlier folds; it does not balance outcomes or fit preprocessing. Fewer than
three independent chronological groups fails. Ten isolated proposed development
dates give fold sizes 16/12/12 episodes, with identical scenario counts within
each date group. This boundary is proposed, not an approved stratification rule.
`validate_isolation` rejects any related/overlapping component spanning partitions
or folds; same-fold/date sharing is reported and permitted. Nisha must independently
check these results. Edison must fit preprocessing/class weights using training
folds only; this tooling does not implement his training component.

## Provenance and custody

Private manifests record candidate pools, exact selections, both root seeds,
per-episode IDs/scenarios/seeds/parents/folds, source URL/path/commit/checksum,
30 indices/bounds, D03 distribution specification/version, F02 version, Python
implementation/version, Pydantic version, selection/RNG algorithms, supplied code
revision and actual bytes' hashes for splits/D01/D03/schemas. The file hashes
identify dirty code independently of the supplied base SHA; a SHA string is not
proof that a checkout is clean or approved. Freeze still needs the full environment
locks, D02 calibration evidence and other assets listed below.

Each allocation and manifest has a canonical sorted compact UTF-8 JSON SHA-256.
The manifest digest excludes its own `manifest_sha256` field; each allocation
hash likewise excludes its own hash. Human-readable files use UTF-8 LF. Store
original bytes and an externally protected checksum for tamper detection; hashes
inside the same mutable file are not signatures or access control.
`episode_content_sha256` remains null, explicitly distinguishing an allocation
hash from the hash of a real F02 PrivateEpisode. At authorized materialization,
retain the existing D03 private provenance and `PrivateEpisode.canonical_hash()`
in a separate custody receipt bound to this allocation hash. No null content hash
can satisfy scientific freeze or count as evidence of actual fixture generation.

Use `Proposal.development_records()` / `development_record(id)` only in private
development tools. The ID lookup rejects held-out IDs. `development_manifest`
exports only development rows and common provenance, excluding held-out dates,
root seeds, candidate pools and combined overlap pairs. It still includes private
development scenario/seed/fold metadata and must never enter policy state/context.
The full `Proposal.records` and `private_manifest` are evaluator-custody objects,
not a security capability granted to development consumers.

`write_private_manifest(proposal, directory, code_revision=...)` writes the combined
metadata once, refuses existing output and refuses a directory inside any Git
checkout (including worktrees). The custodian must first provide an existing,
access-controlled directory outside Git. POSIX owner-only creation mode supplements
actual evaluator storage permissions; Windows ACLs/external access controls must
be verified separately. This is not encryption or isolation from the machine owner.
No held-out content loader or materializer is enabled. Nisha's eventual evaluator
loader belongs to the independent evaluation path and stays gated by freeze and
separate run authorization. Do not pass the combined plan to development tuning.

## Local use and verification

From the repository root on the supported Python 3.12 environment:

```python
from datetime import date
from dc_sustainability.data.splits import propose_allocation

# Synthetic metadata demonstration only; these pools/seeds are NOT study choices.
plan = propose_allocation(
    development_candidates=tuple(date(2022, m, d) for m in range(1, 13) for d in range(1, 15)),
    held_out_candidates=tuple(date(2022, m, d) for m in range(1, 13) for d in range(15, 29)),
    date_seed=42,
    job_seed=19,
)
development_rows = plan.development_records()  # private development metadata only
# Custodian supplies actual code revision and controlled output directory later.
```

No demonstration or test seed is adopted as the experimental seed. Tests inspect
metadata to verify structural rules; they never inspect generated held-out data
to choose settings. Reproduction commands:

```sh
python -m pytest tests/data/test_splits.py -q
python -m pytest tests/data tests/contracts -q
python -m pytest tests -q
python -m ruff check dc_sustainability scripts tests
python -m ruff format --check dc_sustainability scripts tests
python scripts/validate_setup.py
python -m compileall -q dc_sustainability scripts tests
git diff --check
```

Local results are recorded in the verification note below. Ordinary CI remains
offline; existing D01–D03 code/source files, F02 schemas, shared instructions,
scientific defaults and other owners' components are unchanged.

## Proposed choices, blockers and exact freeze requirements

The shared plan requires 40 development episodes across four scenarios, 30 held-out
(six dates/four scenarios plus six missing forecasts), day-number restrictions,
three blocked development folds and source-window isolation. The ten development
dates/all-four-scenarios-per-date design, equal ten-per-scenario allocation,
candidate pools, exact dates/seeds, SHA-ranked greedy selection, seed derivation,
group-balanced 16/12/12 fold proposal and D03 workload distributions remain Q06
proposals. Implementing a proposal behind an explicit provisional boundary does
not change an adopted shared setting.

| Gate | Exact unblock evidence / affected owners |
|---|---|
| Q05 physical mapping | Reimo obtains CSV-specific interval/export evidence; Ved verifies applicability; Edison, Nisha and Matty confirm affected accounting/evaluation/runtime mapping. Recompute all 30 physical indices/bounds and overlap reports under the accepted convention. |
| Q05 meaning, rights, suitability | Reimo supplies missing exporter/pollutant/system boundary and CSV-specific permission; Ved verifies provenance/rights, Edison checks factor/accounting, Nisha checks evaluation claims. Reuse [D05 B1–B4](D05_SOURCE_EVIDENCE.md#blockers-owners-and-veds-review); checksums do not close these gates. |
| Q06 workloads/calibration | Reimo specifies final marginals, dependencies, spike and infeasible construction, calibration sampling/quantiles/scaling and seeds; Edison/Ved/Nisha agree at affected boundaries. Obtain authorized empirical calibration or explicit synthetic-only scope with narrower claims. |
| Q06 allocation/folds | Reimo proposes exact pools/dates/scenario counts/date+job+calibration seeds and group/fold algorithm; Nisha independently verifies separation and evaluator custody; Edison verifies training-fold consumption; Ved checks affected labeling/schema use. Record agreement before consumers adopt settings. |
| Scientific fixture freeze | Immutable selected metadata plus real private content hashes, full provenance and accepted source mapping; exact code SHA/dirty status, environment locks/runtime/RNG versions, source/calibration/ontology/model checksums, prompts/provider/trial settings, solver and scoring/annotation protocols. Required development consumer tests and Nisha's independent replay/isolation evidence must be recorded; remaining Q01–Q13 gates applicable to the actual run must be resolved. |
| Controlled held-out run | Frozen configuration, storage/loader access checks and explicit authorized evaluator execution. Preserve contents/responses; no tuning from held-out data or labels. Post-freeze defects need a recorded protocol amendment and consistent reruns. |

This document is a local proposal record, not a newly sent agreement request.
Coding decision owner: Reimo. Exact proposed change: the provisional D04 allocation,
seed and fold rules above. Directly affected consumers: Nisha evaluation/runner,
Edison training/calibration, Ved labels/contracts; Matty only where shared runtime
mapping or unresolved escalation is affected. Required checks: deterministic
regeneration, counts, independent 30-hour overlap report, fold isolation, custody,
provenance and actual consumer tests. **Request time: not sent. Response deadline:
not started.** When Reimo authorizes sending the exact proposal, record its actual
UTC request time and deadline at +24 elapsed hours, obtain affected-owner replies,
and escalate unresolved portions to Matty within that period. Existing #60 clocks
and escalations are preserved; this document does not restart them. No GitHub
comment or external message was sent in this session.

Nisha must independently reconstruct the selected physical windows without relying
on this module's isolation verdict, verify source identity/mapping and all tails,
compare 40/30 counts/parents/seeds/hashes, check chronological folds and transitive
related groups, demonstrate held-out contents/actuals/references cannot enter
training or policy views, and validate evaluator custody/materialization receipts
against immutable frozen inputs. A production-tool test pass is not independent
scientific evaluation. Her runner/loader acceptance and actual content hashes
remain pending. D04 **tooling is ready for review**, not final scientific freeze.

## October 26 local verification note

Executed on macOS, CPython 3.12.15, using the pre-existing local environment
`/private/tmp/s01-integration-20261026-venv/bin/python`. This is local evidence,
not certification of the Windows dependency lock or a scientific environment freeze.

- New D04 suite: **36 passed**.
- Focused data/contracts: **674 passed, 19 subtests passed**.
- Final full offline suite: **1,416 passed, 19 subtests passed** (11.76 seconds).
- Ruff lint and formatting: pass (123 Python files checked for formatting).
- Setup/documentation validation: pass, including Markdown links, 50 task records,
  instruction/contract versions and unchanged shared policies.
- Compilation, dependency consistency, dependency smoke and whitespace: pass.
  Smoke exercises SHACL/SPARQL, the tiny integer program, both classifier
  persistence paths and a bounded no-provider LangGraph route; no model call.

The initial sandboxed full run had 1,305 passes and 110 setup errors because the
sandbox prohibited loopback socket binds. The permitted outside-sandbox run
passed; the final full run after provenance-validation edits also passed as above.
No existing test was skipped or rewritten to conceal those restrictions.
No source reacquisition, real held-out content generation/inspection, scientific
selection by results, commit, push, merge, GitHub comment or acceptance claim occurred.
All changes remain local for review. Actual freeze inputs, owner agreements and
Nisha's independent findings remain the gates listed above.
