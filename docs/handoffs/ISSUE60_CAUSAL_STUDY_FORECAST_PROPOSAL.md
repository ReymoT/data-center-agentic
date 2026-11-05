# Issue #60 causal study forecast proposal

## Current publication and receiving status

Matty authorized review, necessary fixes, publication and merged-branch cleanup
in this chat on November 3. Merging this proposal publishes its specification
and synthetic proofs; scientific adoption and production implementation remain
pending the affected-owner responses and acceptance gates below.

Reimo posted the actual request at 2026-11-03T23:22:02Z, before the manager's
deliverable deadline. [Matty's technical review and parameter response](https://github.com/ReymoT/data-center-agentic/pull/168#issuecomment-6620949015)
is recorded. Later November 4 replies include Nisha's conditional scope acceptance
with custody clarifications and Ved's conditional mechanics acceptance; O02/C/D
compatibility remains uncertified. Edison's response was still absent at the
manager's post-deadline check. The original response boundary was November 4
at 4:22 PM Phoenix time (23:22Z); it is not restarted. See the
[development compatibility plan](CF60_DEVELOPMENT_COMPATIBILITY_PLAN.md).
The review found no causality defect in the conditional equations. It corrected
stale publication wording and a branch-dependent link before deletion. Tests
are synthetic specifications, not an implemented production forecast broker or
independent custody acceptance. The dated preparation/publication logs below
retain their original scope and do not override this current status.

Proposal **CF60-v1**, 2026-11-03. Producer/coding decision owner: Reimo.
**Proposed, conditional, not adopted.** Reviewed fetched main and clean starting tree
`87621d879ea48b02ecf8b6306516a4bcc774cf83`, instruction 1.28, F02 1.0.0.
Local branch: `reimo/issue60-causal-forecast-spec`. No production adapter is changed.
Reviewed merged PRs #133 (legacy development forecasts/receipt), #146 (source
inventory), #147 (custody), #158 (P05/E02 and conservative isolation) and #163
(P06/readiness), plus all newest #60 comments through Ved's November 3 response
[6615266554](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6615266554).
Main's files match the local starting checkout; no instruction conflict was found.

## Recommendation and precise decision

Adopt one deterministic **bounded last-available-observation persistence** method,
conditionally on affected-owner agreement to the parameters below. It is a simulated
forecast of a historical carbon proxy, not a measured forecast, authenticated
historical forecast, verified CO2e, or evidence of historical real-time availability.
“Causal” here means information available before simulated issuance; it does not
establish causal or avoided physical emissions.

The proposed lag is **one hour after physical interval completion**, with **strictly
before issuance** eligibility. Search only interval ends two, three and four hours
before issuance. The four-hour evidence-age bound is a new proposed study parameter,
separate from Q04's already accepted two-hour **forecast issue age**. Neither the
lag nor this bound is an empirically verified reporting latency.

## Trusted clock, equations and exact inputs

Let h=1 hour. A physical episode anchor A is local Phoenix date midnight expressed
as UTC, i.e. `YYYY-MM-DDT07:00:00Z`. Physical slot v is `[A+vh,A+(v+1)h)`.
The trusted runner/simulator clock, not a policy or CSV label, supplies decision
instant `D_t=A+th`, t=0..29. Decisions that may start work remain t=0..23;
24..29 are accounting/finishing slots. Require explicit UTC-aware hourly instants;
reject naive/non-UTC timestamps and off-hour anchors.

Retain each original CSV timestamp L_i and immutable row identity/checksum.
Under hypothesis c:

- start: interval `[L_i,L_i+h)`, completion `E_i=L_i+h`;
- end: interval `[L_i-h,L_i)`, completion `E_i=L_i`.

Declare **simulated availability** `B_i=E_i+h`. Never replace L_i with B_i or
represent B_i as observed historical publication time. Forecast issue `I_t=D_t`.
Publish atomically after constructing the issue, before that slot's policy view;
it becomes visible at I_t, never earlier. No issue is available at an earlier
clock instant, even if an offline file contains its precomputed representation.

Exact algorithm (descending candidates, no value-based ranking):

```text
I = trusted A + t*h
candidate ends = (I-2h, I-3h, I-4h)
candidate labels = end-h if start hypothesis, else end
attempt exactly these three keyed row accesses, restricted to pinned year
read values of every existing candidate; record all attempts and read row IDs
reject malformed/duplicate/nonfinite/negative source evidence as an input error
select existing candidate with largest completion E, irrespective of its value
if none exists: emit no forecast; explicitly mark every visible slot missing
else for every v=t..29: F[t,v] = selected avg_CI
project only v=t..min(t+23,29) into the current F02 VisibleState
```

For present candidates, `R_t={i:E_i in {I_t-2h,I_t-3h,I_t-4h}}` is the exact
value-read set, including candidates not selected. Record missing-key attempts
separately. The selected dependency is `j_t=argmax_{i in R_t} E_i` and
`F[t,v]=x[j_t]`. R_t and j_t depend on timestamps/presence, never outcomes or
carbon magnitudes. All three existing candidate values are intentionally counted
as reads. No full-series value scan belongs in the forecasting broker. Source
identity validation/acquisition is a separate privileged operation; the broker
receives a timestamp-indexed, access-controlled history interface only.

Maximum attempted footprint per issue: three rows. Start labels lie in
`[I_t-5h,I_t-3h]`; end labels in `[I_t-4h,I_t-2h]`. Across all 30 issues:
start labels span `[A-5h,A+26h]`, end labels `[A-4h,A+27h]`, at most 32
unique rows. Missing rows reduce actual reads, never extend the search.
There is no unbounded latest-observation search and no fallback to older years.

## Causality, horizon, missingness and Q04

For every read, E_i <= I_t-2h, so B_i=E_i+h <= I_t-h < I_t. Thus every
input is strictly available before issuance under the declared simulation rule,
under either interval hypothesis. Valid slot v never participates in input
selection; the proof holds for v-t=24..29 as well as short horizons.

At t=0 the latent issue supports v=0..29 (lead 0..29 hours); at t=23 it supports
23..29; at t=29 it supports only 29. Every hourly issue is recomputed from its
own eligible history. No prior missing issue is backfilled after future data
arrive. The withheld variant exposes no forecast at any slot, preserving jobs
and private scoring carbon. A failed issue does not silently retain an earlier
issue; missing slots remain explicit. A separately supplied cached fact still
must pass Q04 and is not part of this recommended issue schedule.

F02's existing visible horizon is `[t,min(t+24,30))`, not an authorization to
expose all 30 latent values. In particular, v>=24 at t=0 stays invisible.
Reissuance makes later valid slots visible in their appropriate windows. If an
otherwise legal candidate needs occupied slots outside the visible horizon,
Q04 still finds insufficient coverage. Do not widen the view or shrink candidate
starts to conceal this limitation.

Required compatibility checks preserve Q04: trusted decision time, issue age
`0 <= D-I <= 2h` (age two accepted, age three stale, future issue invalid), full
fresh coverage of the required occupied-slot union for all otherwise legal
candidates, and decision-wide checked A for B/C/D when unusable. Missing carbon
is not physical infeasibility; unsupported impact claims are withheld. P03
features/O02 labels must use visible forecasts only; P04 binaries/training and
P06 scores are unchanged. CF60-v1 is not equivalent to the legacy preceding-row
adapter: affected owners must assess the changed forecast inputs against the
existing trained policies before freeze. Schema compatibility alone does not
establish scientific compatibility or authorize retraining. P05/E02 retain fallback
origin/reasons and propagate classifier errors rather than retrying them. Passing this proof harness does
not establish consumer adoption; validate the eventual adapter through those
real boundaries after agreement.

Same-hour-yesterday would set a forecast for V from label V-24h. At lead 24,
that label equals I, whose interval/lag is not available strictly before I;
at lead 29, it equals I+5h, explicit future data. Checking only the label's
relation to V is insufficient. CF60-v1 avoids this because its selected input
does not depend on V. It sacrifices daily shape and makes no accuracy advantage
claim; a constant forecast across a decision's horizon may produce many ties.

Missing history means no eligible candidate, no invented zero/mean/interpolation,
no future backfill, no wraparound. Older than four hours from interval completion
is insufficient evidence even if the new issue would itself be fresh. Invalid
source data fails preflight; missing candidate keys are distinguishable from
malformed evidence. Missing scoring rows separately invalidate a complete
30-slot scoring window; forecast availability cannot repair private actuals.

## Conditional synthetic examples (all values invented)

For A=`2022-06-01T07:00Z`, assign values 701, 702, 703 to labels 02Z,03Z,04Z,
and 704 to 05Z. These are distinguishable synthetic values, not source samples.

| Case | Interval-start hypothesis | Interval-end hypothesis |
|---|---|---|
| t=0, issue 07Z | read 04Z/03Z/02Z; choose 04Z=703, completion 05Z, available 06Z | read 05Z/04Z/03Z; choose 05Z=704, completion 05Z, available 06Z |
| valid v=29, issued at t=0 | latent value 703 at June 2 12Z; invisible in t=0 view | latent value 704 at same valid time; invisible in t=0 view |
| t=23, issue June 2 06Z | labels June 2 03Z/02Z/01Z; latest 03Z=901 (synthetic), availability 05Z | labels June 2 04Z/03Z/02Z; latest 04Z=902 (synthetic), availability 05Z |
| only second candidate exists | choose label I-4h, end I-3h | choose label I-3h, end I-3h |
| none of three exists, but later/older rows exist | all visible slots missing | all visible slots missing |
| January 1 00Z issue, source begins Jan 1 00Z | all candidate labels absent, no forecast | all candidate labels absent, no forecast |
| December 31 07Z issue | latest label Dec 31 04Z; physical scoring tail beyond year fails preflight | latest label Dec 31 05Z; physical scoring tail beyond year fails preflight |
| that December episode's t=29 (Jan 1 12Z) | no candidate in pinned year; no wrap | no candidate in pinned year; no wrap |

At actual January 1 Phoenix midnight (07Z), both hypotheses can have valid
history within the pinned year; do not reject it merely because it is January 1.
At Dec 31 23Z, forecast history can exist even though future private score rows
do not. This distinction is why full-window preflight remains mandatory.
No actual accepted index or materialized development hash is shifted here.
Conditional physical score rows are label A+vh (start) versus A+(v+1)h (end).
Neither is adopted until CSV-specific evidence establishes semantics and affected
consumers agree. Existing raw-index development artifacts remain historical,
provisional evidence, not silently reinterpreted physical-time artifacts.

## Complete isolation and custody acceptance procedure

Reimo proposes honoring Nisha's conditions A and B exactly; this assistant draft
is not a posted human acceptance. Matty's recorded acceptance is retained.
Nisha must independently recompute the following without inspecting outcomes:

1. Pin source bytes, timestamp origin, method/version, lag, search bound, clock,
   convention, visibility schedule and unchanged development allocation/content
   commitments. Audit the **actual historical development adapter** separately:
   it reads current recorded index minus one at each issue, not CF60-v1's R_t.
   Let its forecast-value dependency union be R_dev_legacy. The current legacy
   function also calls `carbon.load_source`, which parses/validates the full CSV
   in a trusted offline process. That bulk ingestion is not evidence of a bounded
   causal history interface. Record loader access separately; do not describe its
   entire execution as reading only preceding rows. The new study broker must
   receive only restricted eligible history after privileged source validation.
   Independent receiving must audit that boundary as well as the value dependencies.
   Never certify old reads by applying
   the new formula retrospectively. Any authorized future development use of
   CF60-v1 gets its own R_dev_new and new forecast commitments; originals stay.
2. Under each c in {start,end}, derive all 30 scoring row identities S_g(c)
   and exact read union R_g(c)=union_t R_t(c), including unselected candidates,
   accounting slots, related scenarios and normal/withheld pairs. The withheld
   variant has no forecast value reads, but shares its parent's isolation group.
   Maintain both original recorded-index scoring sets and conditional physical
   sets while unresolved; any disagreement blocks physical certification.
3. Require S_dev intersect S_held empty; R_dev intersect S_held empty; and
   R_held intersect S_dev empty for every cross-split pair. R_dev includes the
   legacy footprint plus any separately approved new footprint in scope. Include
   all fixed development scoring rows, even when not read for a particular issue.
   For conservative protection of shared source information, group any pair whose
   `(S union R)` footprints overlap, including history/history intersections.
   Related/overlapping groups must never cross splits or blocked development folds.
   If the fixed accepted fold map fails this stronger forecast audit, record a
   blocker and request amendment; do not rewrite it or retrain automatically.
4. Independently compare every pair under both conditional hypotheses; preflight
   out-of-year/missing scoring labels fails, never modulo-indexes. Record attempted
   and actual history row IDs privately, convention, hashes and PASS/FAIL. Timestamp
   metadata alone can establish the full potential footprint before value access.
   The pinned source is complete, so the three-row potential footprint is exact;
   with missing history actual reads are the present subset. Do not publicize
   held-out dates, row IDs, nonce, seeds, paths or contents.
5. `forecast_isolation.footprint(..., history_hours=5, convention=c)` is reusable
   as a **conservative envelope**, not the exact R_g. It includes all scoring rows
   and some rows this method never reads. `conflicts` checks scoring/history in
   both directions, but does not establish related-group/history-history isolation,
   actual missing-row handling, or authenticate the forecast algorithm. A pass
   for this envelope bounds CF60-v1's reads only for its defined complete windows;
   a failure may be conservative and needs exact dependency inspection.
6. The merged `held_out_custody._records` currently enforces scoring-window
   overlap, not these exact forecast-history rules. **Adoption blocker:** after
   agreement, add version-pinned metadata-only footprint eligibility checks to
   the deterministic greedy selection and independent receiving implementation.
   Use the precommitted rank order and skip only objectively ineligible windows
   based on metadata, not outcomes. Record amendment to algorithm/receipt identity;
   existing `sha256-rank-greedy-fixed-development-v1` must not silently change.
7. No outcome-driven seed selection, reranking, candidate-method selection or
   retry. Shortfall, prohibited/equal/colliding seed or failed isolation fails
   closed and requires explicit amendment, never a new nonce search. No actual
   held-out selection or metadata is created by this proposal or harness.

A changed source, availability, lag, clock, physical mapping, forecast convention,
lookback or visibility schedule invalidates any **unverified** prior isolation
claim and requires a new audit/commitment. Accepted historical evidence remains
retained within its original scope. A passing 30-hour score-window test alone
never establishes forecast-history isolation.

## Separate source-evidence disposition

PR #146's [existing inventory](ISSUE60_SOURCE_EVIDENCE.md) and
[audit](SOURCE_ACCEPTANCE_AUDIT.md), accepted within its bounded scope by
[Ved's independent review](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6594292048),
remain the evidence record. No new authoritative evidence was found in the
reviewed main/PR/issue material; no new external source investigation is claimed.
B1 exporter/archive/pollutant/GWP and B2 CSV-specific interval convention and B3
derived-CSV rights remain **UNRESOLVED**. B4 remains **PROVISIONAL historical
simulation proxy**. A simulated availability assumption cannot resolve B1/B2.
No new source inventory or repeated D05 structural/formula verification is needed.

Concise maintainer questions, **not sent**: which dated archive/hash and exporter
commit/caller generated the pinned bytes; does a specific label denote its next
or previous hour (show first/last intervals); what exact pollutant/GWP/boundary
and factor citations apply; what permission covers this derived CSV and intended
academic use/derivatives? Exact pinned identity and fuller questions already
appear in the inventory. Neither permission nor external contact is inferred.

## Affected-owner decision request and freeze impact

Reimo owns the specification and later adapter implementation. Request time is
**2026-11-03T23:22:02Z**, recorded in [the posted response](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6618029295). The response/
escalation deadline is that timestamp plus 24 elapsed hours, without resetting
Matty's November 3 21:01 Phoenix deliverable deadline (Nov 4 04:01Z).

- @vedp3705: accept/reject the conditional interval-completion availability model,
  strict causality proof, source-row mappings and O02 compatibility; identify any
  smallest equation/mapping correction. This does not ask for source approval
  or repeated D06 structural checks.
- @nkolekar-nk: accept/reject exact bidirectional history/group/fold audit and
  metadata-only custody-algorithm amendment before any actual selection; retain
  no-retry condition, restricted receipt/access verification and independent code.
- @epez7: accept/reject one-hour simulated lag, four-hour completion-age bound,
  flat persistence horizon, F02 projection and required-coverage/fallback behavior
  for accounting/P03/P04/P05/E02; identify smallest parameter correction. No new
  P04 training/P06 scoring is requested or performed.
- @MattyAnd: coordinate recording exact agreement and smallest unresolved changes,
  then authorize any shared decision publication through existing authority.
  Escalate unanswered/disputed shared parameters within 24 elapsed hours.

Unapproved inputs/decisions: study forecast method/lag/history-age bound and
schedule; actual physical mapping/CSV interval semantics; source rights and
pollutant/exporter lineage; intended proxy suitability; custody selection amendment,
restricted parameters and actual storage/receipt verification; independent
forecast-adapter/consumer/isolation acceptance; final scientific freeze. No private
realized arrays, future jobs, oracle/reference results or outcomes may be broker
inputs or policy fields. Only typed persistence forecasts and explicit missing
slots enter the existing visibility-safe F02 projection; provenance must resolve
its source reference, with unresolved pollutant/rights and unvalidated quality.

This delivers a complete **conditional** causal method, not an evidence-based
real-time latency assertion. It does not change schemas, Q04 rules, source indices,
receipts, development episodes, model binaries, training, scoring or scientific
defaults. Source gates, actual custody and independent acceptance still block
scientific freeze; passing synthetic tests does not remove them.

## Verification

Executable specification: `tests/data/test_issue60_causal_forecast_proof.py`.
Synthetic distinguishable values only; no source/model/API calls or actual
held-out allocation. Historical preparation results are retained below; publication validation follows.

Executed on macOS arm64, CPython 3.12.15, temporary environment
`/private/tmp/issue60-venv`, installed from unchanged `requirements/requirements-core.in`.
Core versions are pinned there; resolved transitive packages are not a certification
of the Windows hashed lock. No environment/lock file in the repository was changed.

- `python -m pytest tests/data/test_issue60_causal_forecast_proof.py -q`:
  **17 passed** (0.36s). Covers both hypotheses, all 30 issues and tracked reads,
  latent lead 29, F02 projection/context round trips, actual Q04 age 2/3/future
  assessment, missing/invalid/too-old inputs, UTC validation, deterministic ordering,
  future-value perturbation, year failures and both directions of history overlap.
- Focused proof/isolation/custody/P03/O02/P05/E02 suite: **133 passed** (8.51s),
  command: `python -m pytest tests/data/test_issue60_causal_forecast_proof.py tests/data/test_forecast_isolation.py tests/data/test_held_out_custody.py tests/training/test_features.py tests/reference/test_labels.py tests/policies/test_learned.py tests/experiments/test_runner.py -q`.
- Final `python -m pytest tests -q`: **1,915 passed, 19 subtests passed** (39.58s).
  Initial sandbox run had 128 setup errors because localhost HTTP test fixtures
  could not bind sockets; the authorized rerun permitted local synthetic servers.
  No live provider/model or held-out evaluation was used.
- `python scripts/validate_setup.py`: PASS, including local links/policy checks.
- `python -m ruff check dc_sustainability scripts tests`: PASS;
  `python -m ruff format --check dc_sustainability scripts tests`: 208 files formatted.
- `python -m compileall -q dc_sustainability scripts tests`: PASS.
- `python -m pip check`: no broken requirements;
  `python scripts/smoke_dependencies.py`: PASS (imports, SHACL/SPARQL, tiny integer
  program, synthetic classifier round trips and bounded mock LangGraph).
- Initial preparation Git snapshot: fetched main equals original HEAD; clean before work; only the four new
  proposal/response/PR-draft/proof files are untracked. Tracked production, data,
  models and instruction files compare unchanged against main. Whitespace checked.
  No commit, push, merge, GitHub comment, PR publication or external maintainer
  contact. Hosted Windows CI has not run for this local draft.

### Publication review (CF60-v1 remains PROPOSED)

Publication was explicitly authorized by Reimo after the initial preparation above.
Refetched main is still `87621d879ea48b02ecf8b6306516a4bcc774cf83`, instruction
1.28. Issue #60 and recent comments remain unchanged through comment 6615266554.
GitHub connector and authenticated Git CLI identify `ReymoT` (ID 52417582);
repository-local commit identity is `Reimo Tamme <52417582+ReymoT@users.noreply.github.com>`.
The earlier uncommitted four-file draft was preserved outside the repository
before review edits. The authorized publication scope is these four files only,
a focused commit, branch push and draft PR; no merge or Issue comment is authorized.

Independent mathematical review confirms `E=L+h` (start), `E=L` (end), and
`B=E+h`. Eligibility `B<I` with maximum completion age four hours on an hourly
grid gives exactly `E in {I-2h,I-3h,I-4h}`. The enhanced synthetic test independently
derives eligibility from every physical interval rather than reusing the selector's
label calculation. It also checks the exact 32-row union, magnitude-independent
selection, explicit F02 `missing_carbon_slots`, and January 1 history at 07Z.
No mathematical causality defect was found. The missing custody integration,
legacy/new forecast compatibility and unapproved scientific assumptions remain
explicit adoption/receiving questions; the proof is not an independent evaluator
approval or a source-semantics finding.

Preservation check: the fixed 40-record allocation and fold pins validate; all
40 public content commitments match main byte-for-byte. The retained v2 receipt
SHA-256 is `33c8dce514cdbcba53f9ed03399219be8a511d628ab61def694eedaac894b319`.
Production code, F02/Q04, source mappings, instruction files, development data
and trained models have no changes relative to fetched main. No source-derived
private corpus was opened, rematerialized or selected for this review.

Current local publication results supersede the earlier preparation counts:

- Synthetic proof module: **21 passed** (included in focused and full runs).
- Same focused command above: **137 passed** (8.19s).
- Full offline suite: **1,919 passed, 19 subtests passed** (39.89s).
- Setup/link/instruction validation, Ruff lint/format (208 files), compilation,
  dependency consistency and dependency smoke checks: PASS.
- Environment remains macOS arm64 / CPython 3.12.15 with unchanged core dependency
  input; synthetic localhost fixtures require execution outside the socket sandbox.
- Hosted Windows CI is separate and was not run locally. Its exact-head status
  must be read from GitHub after push; no result is inferred from local tests.

B1–B3 remain UNRESOLVED, B4 PROVISIONAL and B5 custody/scientific freeze PENDING.
The review requests above are proposals for affected-owner receiving, not recorded
acceptances. Record the actual request time when the human posts the Issue reply;
publication of this draft does not reset the historical manager deadline.

### Manager publication validation

Matty rebased no history: merged current main `31487bf0167849e8868f4b0d40ff3d7ab98a6c4f`
into the proposal branch, preserving Reimo's commits. The corrected documentation
uses a relative handoff link that survives branch deletion and records the actual
request timestamp. The manager-host focused proof/isolation/custody/P03/reference/
P05/E02 run passed **205 tests, with two custody symlink tests skipped** because
the host could not create symlinks. The skips do not establish access-control
acceptance. Setup/local-link validation, lint, formatting and whitespace passed.
Exact updated PR and merged-main CI must pass before final branch cleanup.
No production adapter, source mapping, forecast default, model or shared scientific
setting was changed. The pending owner responses and adoption gates remain explicit.
