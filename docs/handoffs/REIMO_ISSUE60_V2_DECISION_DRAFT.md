# Reimo issue #60 v2 decision draft

Local draft for Reimo's review, November 10, 2026 (Phoenix). Not posted, approved,
or a replacement for accepted records. Fetched main and working base:
`27083dc4e3be7c9fc32071fe3a6a33aff3218837`; instruction 1.28, F02 1.0.0.
Branch: `reimo/issue60-v2-decision-drafts-20261110`. Authenticated GitHub login
`ReymoT`; existing repository-local email `52417582+ReymoT@users.noreply.github.com`.
No commit, push, merge, comment or external contact is authorized by this draft.

## Decision in one paragraph

The public selector matches the accepted v2 mechanics and all four requested pins.
No public-code disagreement was found. **The exact authenticated restricted
parameter/destination record has not been supplied or located through an authorized
locator in the inspected records.** Reimo must privately authenticate and review
that record before using alternative A. This audit did not search unrelated private
storage or instantiate any study input. Use alternative B now if that review remains
unavailable. Source B1–B4 are a separate gate and cannot be confirmed by this audit.

## Current authenticated decisions

- [Matty's v2 implementation and pin](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6777235119),
  [exact-main CI](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6777330450).
- [Nisha's independent v2 pin](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6782772091):
  independent 40-record footprint arithmetic and 150 synthetic selections reported.
  These are her checks, not checks rerun or independently authored by this assistant.
- [B5-ready report](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6783459234):
  storage outside sync/Git, restricted ACL, deny test passed, BitLocker on. Private
  verification record remains with Nisha. Her earlier November 12 storage ETA is
  superseded by readiness, not an outstanding request.
- [Matty's forecast-limit acceptance](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6783536274)
  and [publication](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6783699060)
  supersede the earlier pending answer. [Latest urgent request](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6785196308)
  asks Reimo for the exact restricted v2 confirmation or smallest disagreement and
  separately source evidence or an unavailable-record statement.
- [Published scope decision](../decisions/NOV10_PROFILE_ADOPTION_AND_FORECAST_SCOPE.md)
  permits legacy persistence or CF60 only. It does not adopt the final forecast.

## Public verification matrix

Code: [held_out_custody.py](../../dc_sustainability/data/held_out_custody.py),
[split contracts](../../dc_sustainability/data/splits.py),
[v2 handoff](NOV10_SELECTOR_CONTENT_AND_TRACE.md), and
[historical v1 proposal](ISSUE60_HELD_OUT_CUSTODY.md).

| Assertion | Verified public behavior | Remaining human check |
|---|---|---|
| Exact pin | Version `d04-held-custody-v2-forecast-union`; algorithm `sha256-rank-greedy-fixed-development-forecast-union-v2`; reviewed commit `fda701d9cbebc7df954b0f15e80610d4a83d3aeb`; LF SHA-256 `2eec2778b4957f6bad3755467e9ab5adc517a2eab3fed151aacf018eb9914bfd`. Current source bytes match that commit and hash. | Authenticate matching restricted-record version/algorithm and decision locators. |
| Pool | `_parameters` requires an explicit sorted unique ISO list, valid 2022 dates with day 15–28. Every month has 14 such dates, giving the proposed 168-date full pool. | Code allows smaller valid pools. Confirm the restricted record contains **all 168**, not a subset. No real candidate list was created here. |
| Six dates | SHA-256 canonical JSON ranking `[VERSION, selection_seed, ISO_date]`, date tie-break, greedy first eligible date per month, stop at six, chronological output. Shortfall raises. | Actual selection is Nisha's future private action. |
| Fixed development | `_development()` loads pinned allocation, never joint reallocation. Exact 40 records, IDs/dates/seeds/groups/folds and content receipt preserved. Content-receipt pin `33c8dce514cdbcba53f9ed03399219be8a511d628ab61def694eedaac894b319`. | Nisha independently checks actual metadata and downstream development allowlists. |
| Thirty held-out episodes | Each of six dates has four core scenarios plus a normal withheld variant. Thus 24 core + 6 variants = 30; total with development = 70 unique IDs. Held-out folds/content hashes remain null. | Future content equality and content commitments require separate authorization. |
| Root bounds | Both roots are explicit integers, excluding booleans, `0 <= root < 2**128`; unequal; neither 42, 19, 2026102801 nor 2026102802. | Authenticate derivation and future values privately. No root is generated or inspected here. |
| Nonce derivation | Historical accepted rule: Nisha uses one private OS-CSPRNG 256-bit nonce before source/outcome inspection; first 32 hex digits of canonical SHA-256 in separate `selection` and `jobs` domains. Selector itself accepts roots and does not generate/check the nonce derivation. | Exact version tag in the derivation must be explicit in the authenticated v2 record. The historical formula literally names v1; newer public comments accept the v2 replacement while retaining pool/seed-domain rules. Do not silently choose a tag or reuse a v1 receipt. |
| Episode identity | Base `identity = digest([VERSION, ISO_date, scenario])`; ID `EP-` + first 24 hex. Episode seed = integer first 16 hex of `digest([VERSION, job_root, identity])` (64-bit). Variant ID uses `[VERSION, identity, "withheld"]`. | No actual IDs/seeds were produced here. |
| Related groups | `digest([source_sha256, ISO_date])`; scenarios on a date share group/window. Normal variant retains parent scenario/seed/window/group, distinct ID and parent pointer. `validate_isolation` checks collisions and transitive related/overlap components across partitions/folds. | Receiving independently verifies the actual combined private record. |
| Forecast isolation | Union includes literal recorded 30 scoring rows, legacy preceding rows, physical start/end scoring rows and both CF60 candidate-history sets. Fixed 40 development records reserve both methods whether used or not. Candidate and chosen unions must be mutually disjoint across distinct groups on the same source. | Nisha's actual independent isolation/receiving PASS remains pending. |
| Exact CF60 ranges | For physical anchor index `p`, start reads `p-5..p+26`, end reads `p-4..p+27`, each 32 rows over slots 0–29. Scoring covers `p..p+29` / `p+1..p+30`; legacy is the preceding row of literal recorded scoring. Out-of-year rows fail without wrap. | Both interpretations remain conditional; no timestamp mapping changes. |
| Forecast limit | Those unions cover legacy and CF60. Same-hour-yesterday and longer lookbacks are outside v2 per Matty's accepted decision. | Reimo explicitly accepts this limit. A new method needs a versioned, affected-owner amendment **before** any nonce. |
| Failure handling | Invalid roots/receipts, insufficient isolated dates, failed isolation or existing/partial destination fail. No loop, seed search, automatic redraw, overwrite or resume exists. | Conditions A/B prohibit a caller from manually retrying with changed roots after failure. Library checks alone cannot enforce human behavior. |
| Receipt identity | Exact v2 version/algorithm required. `_authorization` binds canonical receipt digest, destination, scope, nonempty decision locators and storage fields. v1 is rejected. | Digest proves integrity, not human identity/approval or actual ACL correctness. Authenticate both owner decisions and external checksum custody. |

The nonce rule comes from [Nisha's parameter acceptance](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6588980217).
Her [history amendment](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6622770964)
retains conditions A/B. No real nonce exists according to the latest reports.
The pre-nonce review can approve the exact future derivation and destination without
claiming to have inspected nonexistent derived integers. Nisha later binds and
checks those integers in private before selection.

## What changed from v1

Compared reviewed v2 with its first parent. `_parameters`, `_authorization`,
`_development`, `prepare` and `verify` are structurally unchanged. Changes are the
version/algorithm constants, new footprint helpers, union eligibility/final
validation in `_records`, and added footprint evidence/isolation status in
`build_metadata`. The metadata shape now contains `forecast_footprints` and an
updated `isolation_status`; manifest and code hashes consequently change.

There is no unrelated pool, seed-bound, scenario, storage-API or development-content
change. **Do not say all outputs are identical:** VERSION is a hash domain for
ranking, held-out IDs and episode seeds, so v2 identities/possible ranking differ
even with the same hypothetical roots. Existing source/date related-group formula
is unchanged. Old v1 receipt identities cannot certify v2. Nisha reports the
history guard excludes no additional dates beyond scoring for today's full pool;
that does not waive the guard or permit other forecast methods.

## Alternative A — only after Reimo's private review and explicit approval

Do not post this alternative based only on this public audit. Replace the private
decision reference through the authenticated channel, never with a public path,
nonce, seed or date. Reimo must verify the exact derivation version tag rather than
assume it from the historical example.

> @MattyAnd @nkolekar-nk I have privately authenticated and reviewed the exact
> restricted v2 parameter record and accept it: `d04-held-custody-v2-forecast-union`,
> algorithm `sha256-rank-greedy-fixed-development-forecast-union-v2`, selector commit
> `fda701d9cbebc7df954b0f15e80610d4a83d3aeb`, LF SHA-256
> `2eec2778b4957f6bad3755467e9ab5adc517a2eab3fed151aacf018eb9914bfd`.
> I confirm its complete sorted 168-date pool, six distinct months, unchanged 40
> development allocations, 24 core plus six related withheld variants, separately
> domain-derived bounded roots and agreed new private destination/storage record.
> I accept conditions A and B: no seed search, outcome-driven revision or automatic
> retry; isolation reserves literal recorded scoring, legacy and CF60 history under
> both interval hypotheses for development and held-out date groups.
>
> I accept the legacy-or-CF60-only limit. Same-hour-yesterday and longer lookbacks
> require a new versioned affected-owner amendment before any nonce. This is the
> v2 replacement, not reuse of an old v1 receipt. Nisha owns nonce creation, private
> selection, independent isolation and receiving in the agreed order, sharing only
> the authenticated locator/digest. This confirms parameters only. Source-use
> evidence, fresh exact ingest authorization, comparison approval and scientific
> freeze remain separate; it authorizes no source inspection or study execution.

## Alternative B — smallest truthful blocker available now

> @MattyAnd @nkolekar-nk The public v2 selector matches the agreed pins and protocol,
> including full forecast-union isolation and the accepted legacy-or-CF60-only
> limit. I found no public-code disagreement. I cannot yet confirm the **exact
> restricted record**: its authenticated v2 parameter/destination record is not
> available in this review. Please make that record available through our existing
> restricted channel, including the explicit version tag used in nonce-derived
> seed domains. Keep all private values out of this issue. I need to authenticate
> its complete 168-date pool, derivation/bounds, new destination, storage evidence
> and decision bindings before claiming exact acceptance. No nonce or selection
> should start on this public-code review alone. Source B1–B3 remain unresolved and
> B4 provisional; my separate source-status draft identifies the unavailable
> upstream records and providers. No external response ETA is committed.

Reimo may personally accept the public method limit when posting, but this assistant
has not supplied his acceptance or authenticated a private agreement. No review ETA
is invented. Nisha's latest commitment is selection/isolation/receiving within two
days of the remaining parameter and forecast-limit inputs; the forecast-limit input
is already received. This is her conditional commitment, not a guaranteed completion
date or a new Reimo commitment.

## Execution boundary and PR reconciliation

| PR | Merged main | Completed scope |
|---|---|---|
| [202](https://github.com/ReymoT/data-center-agentic/pull/202) | `531caddee32e469c22b4705050e9c0e60343a68b` | 340-index development input proposal, 1,200-state gap, R04 refresh |
| [203](https://github.com/ReymoT/data-center-agentic/pull/203) | `07b73e09b3adc74bde8e2f9c2e376d4016b60839` | Offline bounded extractor and comparison input gates |
| [204](https://github.com/ReymoT/data-center-agentic/pull/204) | `bd2abd0493d27f076775e48967438007c5cedf72` | Hard-timeout launcher/stop control; refresh four execution pins |
| [205](https://github.com/ReymoT/data-center-agentic/pull/205) | `35f5598866347c0be3c8074dbd09c53157cb8d67` | cb85 technical receiving and transfer-hash condition resolved |
| [206](https://github.com/ReymoT/data-center-agentic/pull/206) | `fda701d9cbebc7df954b0f15e80610d4a83d3aeb` | v2 selector, saved-content assessment, future trace config binding |
| [207](https://github.com/ReymoT/data-center-agentic/pull/207) | `27083dc4e3be7c9fc32071fe3a6a33aff3218837` | Prospective response profile adoption, v2 method limit |

All six PRs are merged per GitHub metadata. Do not repeat these completed coding
tasks. After Reimo's exact parameter decision, Nisha owns private preparation and
independent receiving. Matty owns fresh exact single-use ingest approval after
source-use and authenticated pre-inspection receipt gates. Nisha's agreed later
ingest footprint allows whole-file hashing/all timestamps only after that receipt,
exports exactly 340 approved development values and no other numeric rows. No such
read is authorized now. Comparison needs its actual extract hash and separate
approval; without saved states it is forecast-only, with all 1,200 positions missing
and no O02/C/D/feature/rollout compatibility certification. [I02](../i02/freeze-manifest.json)
remains pre-freeze with null freeze identity. No consumed single-use run may repeat.

## Validation performed for this draft

Current selector hash and exact reviewed-commit bytes matched; AST comparison
confirmed the v1/v2 change boundary above. Existing synthetic custody and causal
forecast proof tests: **72 passed** on macOS / CPython 3.12.15. Temporary environment
uses repository direct pins for Pydantic, pytest, Ruff and training import
dependencies; this is not Windows lock certification or training. An initial
collection lacked joblib; after adding import dependencies, the complete focused
command passed. No test changes or assertions were weakened.

Final documentation/lint/pre-freeze checks are recorded in the companion
[R01 contribution draft](REIMO_R01_CONTRIBUTION_DRAFT.md). No real source bytes,
source hash, nonce, private seeds/destination, actual selection or held-out contents
were inspected or created.
