# Source acceptance audit

Reviewed against main `6c288c0978597fb7fd5b5dd01bea70fed3f4879e`, instruction
1.28. This audit uses the retained [D05 evidence](../../data/D05_SOURCE_EVIDENCE.md),
[document manifest](../../data/manifests/d05-document-evidence.json) and
[reproduction record](../../data/D05_REPRODUCTION.md). It does not reacquire
upstream data or authenticate a missing historical export.

| Gate | Existing evidence | Remaining acceptance input | Owner |
|---|---|---|---|
| B1 exporter/pollutant | Pinned CSV identity and exact fixed-factor arithmetic; comparison-code factors | Historical archive hash, original exporter/caller, factor boundary/GWP provenance tied to these bytes | Reimo; Ved verifies, Edison accounting input |
| B2 interval/mapping | UTC hourly labels; upstream EIA hour-ending guidance; conditional mappings documented | CSV-specific label convention and exact physical 30-slot mapping, then affected-consumer agreement | Reimo; Ved/Edison/Nisha/Matty consumers |
| B3 rights | Software licenses and EIA reuse policy indexed | Derived-CSV-specific applicability and required notices | Reimo supplies evidence; Ved verifies |
| B4 suitability | Historical generation-mix proxy interpretation; geography/accounting limitations documented | Exact site/BA/time/accounting use and evidence supporting intended claims | Reimo; Ved/Edison/Nisha review affected scope |
| B5 split/freeze | Allocated 40 development episodes materialized in PR #133; #112 closed | Separate held-out custody, no-overlap/content commitments, accepted scientific freeze and input permissions | Reimo produces; Nisha verifies isolation |

Resolved locally: the old claim that development contents are absent is obsolete.
This resolves development materialization only, not B5 scientific freeze.
The original six document hashes and structural/formula evidence remain retained;
repeating those checks would not supply B1-B4 evidence.

Manager disposition: continue already permitted development and public-fixture
receiving. Keep source files and private contents out of Git under existing rules.
Do not relabel the proxy as verified measured CO2/CO2e, shift intervals, grant
redistribution permission, or claim site-specific/avoided emissions to close #60.
An unavailable authoritative fact stays unresolved. Source acceptance and any
changed use/claims require the existing evidence and affected-owner process.

Next source deliverable is one evidence-or-unavailable entry per row above,
with exact document locator, applicability to the pinned bytes, and verifier result.
No new evidence in this repository resolves B1-B4, so #60 remains open.

## Issue #60 producer evidence follow-up

[The B1–B4 evidence-or-unavailable companion](ISSUE60_SOURCE_EVIDENCE.md) records
the refreshed main/issue review, bounded historical code search, all-slot conditional
comparison, data-rights boundaries and unsent maintainer questions. B1–B3 remain
UNRESOLVED and B4 PROVISIONAL. B5 remains separate under the existing matrix;
this source-only draft does not claim held-out custody or scientific freeze.
The historical audit is retained.
