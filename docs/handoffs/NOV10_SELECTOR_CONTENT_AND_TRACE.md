# November 10 offline readiness work

Manager: MattyAnd, with AI assistance. Base main 35f5598866347c0be3c8074dbd09c53157cb8d67; instruction 1.28. Matty authorized the four recommendations in order. Existing teammates' work and ownership, F02, masters, allocation, ratings, artifacts and model defaults are preserved.

## 1. Versioned forecast-history selector

Nisha's [November 9 reply](https://github.com/ReymoT/data-center-agentic/issues/60#issuecomment-6758314893) is received, not outstanding. She accepts whole-file bytes/all timestamps and development-only staging with the stated export limits, only after the amended selector is merged/pinned and her authenticated pre-inspection receipt passes.

The amended version is d04-held-custody-v2-forecast-union, algorithm sha256-rank-greedy-fixed-development-forecast-union-v2. It reads the original fixed 40 records; it never calls the joint development allocator. For every fixed development record it reserves literal recorded scoring indices, legacy preceding rows, and physical start/end scoring plus every CF60 candidate history row. For each candidate, the same union must be disjoint from all fixed development and previously chosen date unions on the same source. Parent/withheld variants share one date group. Missing/out-of-year rows fail, never wrap. The restricted metadata includes exact footprints and code pins. Older v1 receipts fail version validation; older code/drafts remain in Git history and are not silently accepted as v2.

The implementation checks both directions by disjoint full unions. It does not choose an interval interpretation or adopt CF60. Tests independently compare the 40 development footprints with the existing receiving calculation, prove fixed records unchanged, exercise recorded mappings differing from physical assumptions and scoring-disjoint/history-overlap rejection. All private selection tests use clearly synthetic authorizations/seeds; no real nonce, held-out selection or metadata was created by this work.

After publication, Nisha can review/pin v2, verify actual B5 storage (outside sync/Git, restricted ACL and deny test), then create her nonce, select privately, independently check isolation and post only the authenticated receipt locator/digest. This document is not her receiving PASS or permission to create those inputs. Reimo's source-use evidence is still required. Real ingest follows only a passing receipt, source permission and Matty's fresh exact single-use approval. The hard-timeout launcher is already merged through #204. No real CSV is opened here.

## 2. Saved explanation assessment and adoption decision

The [AI-assisted technical assessment](../evidence/cb85-content-assessment-2026-11-10.json) inspected all ten saved explanations and 39 claims from RUN-cb85f5a3425c. Each output has request/response/attempt hashes. None reaches the 256-character cap; this supports the measured field-length result, not a truth or completeness score. Formal human ratings, original evidence and adjudication files are unchanged.

Concrete findings include Plain's slot-0 capacity assertion despite 110 kW proposed load versus 100 kW capacity, its missing-forecast assertion despite visible slots 1-6, unsupported stale/optimization rationale, J2 claims citing J1-only deadline evidence, and Agent forecast facts accompanied by an unsupported emissions-calculation assertion. Citation applicability and value/text association remain distinct from correct field pairing. The assessment records seven finding groups, not a failure rate or a substitute for the independent rating protocol. Positive physical/check findings, pre-execution limitations and Agent's fallback attribution remain retained.

Manager decision: do not promote shared defaults on this single public technical PASS. Keep the 256/4096 opt-in profile and existing settings unchanged. Do not tune Plain alone to force this fixture to succeed or rewrite evidence. #185 retains the affected-owner prospective adoption/content-protocol decision and any formal assessment; the technical assessment and Nisha receiving are now available. No new model call is authorized. The research question remains unproven by this public fixture.

## 3. Future trace config binding

The experiment runner now binds ExecutionController to the actual full RunConfig.config_hash. Before reservation or execution, the controller validates/binds the existing optional F02 field and rejects conflicting config hashes or run IDs. This covers classical/trained policies, Plain, Agent, retrieval failures and completion slots through their shared controller. Standalone callers without a bound config retain their previous behavior. Already-completed units are still skipped; historical traces, including the 180 null-field cb85 records, remain unchanged. Old partial units require reconciliation, never automatic migration or replay under changed fingerprints.

Tests check all 30 slots of A/B, C/D and scripted Plain/Agent runs, mismatch-before-effect rejection and immutable replay with the bound hash. These are synthetic offline fixtures, not a new receiving/model run or contract change.

## 4. Status/course refresh and next work

The I02 manifest now distinguishes accepted cb85 receiving from pending explanation/default adoption and actual source/custody/freeze. Its status remains pre-freeze, not ready. Q13 wording now consistently records Nisha's confirmed project number 21 and December 9, 11:59 pm end-of-day report date. Official timezone and release/license details remain unresolved; Arizona remains her working assumption. December 7 is internal. No private instructor email was used.

Presentation content review uses the R04 saved-evidence draft, five-minute script and trace excerpts. Their stale waiting-for-Nisha statement is corrected and the content findings are disclosed. A complete current team deck is not published in this repository; do not claim a full-deck review or upload. The reported internal review window is November 9-11, rehearsal by November 13 and submission target November 14. Nisha's existing November 20-or-new-guidance checkpoint remains for unresolved official fields, not a reason to defer those earlier presentation preparations.

#95 remains blocked on frozen held-out ratings; development IRR/adjudication are complete. #164 remains I02 -> frozen C/D predictions -> Ved O04 -> Edison P07. #166 remains blocked on final E06/E07 artifacts, then Ved I03 and Matty I04. No redundant scoring/reproduction or invented final results are performed. None of those issues is closed by offline preparation.
