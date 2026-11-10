# CF60 input and bounded-execution proposal

Prepared by Matty on November 9 against main 6a7630918a515a7a0b92e3eb57cfb7127d91de4c. This is a reviewable plan, not source-access permission or execution authorization. The [metadata receipt](../evidence/cf60-input-plan-2026-11-09.json) records what was actually checked. No source CSV contents were opened or hashed, no comparison ran and no saved state was invented.

## Proposed sequence

1. Resolve and record permitted source use/extract provenance and the physical read/custody scope below. Keep B1–B3 unresolved and B4 provisional until authoritative evidence exists. Manager authorization does not create third-party rights or resolve physical interval semantics.
2. Implement/verify any scoped extractor against synthetic input offline before source access. A real bounded local ingest into a new private extract requires separate explicit approval. No download, source mutation, training, solver, rollout or model call. The extractor is not implemented by this document; do not call the broad existing load_source/inspect_csv helpers, which calculate statistics from all rows.
3. Pin the actual extract bytes/hash and only then prepare final single-use comparison authorization. Its checksum cannot be honestly filled before the extract exists.
4. If complete saved states remain absent, run a separately authorized forecast-only comparison as a disclosed partial result. It must report all 1200 state positions missing; it cannot certify feature, O02/Q08, C/D prediction or rollout compatibility.
5. Add the fixed-history feature comparison only after saved states with actual provenance and hashes are supplied. Reference/solver and classifier implications remain separate bounded downstream work; do not infer certification from the broker or this driver.

## Exact proposed source boundary

The existing pinned D01 source checksum is e05789a1dbf940e0554b0e8db42d84ed5cc0279d0050206fb048ba832ef24ef4. Its candidate local file exists and has 601730 bytes by filesystem metadata; its current contents/hash were not verified. The canonical source schema contains 8760 hourly records and avg_CI. The fixed 40-development allocation requires 340 unique zero-based indices (minimum 1466, maximum 8123). The canonical index-list SHA256 is 61ab86cdc5024ecb188a377afba73b36be816fb5ea4660ff7f59bfd59de23967. The exact list and absolute private paths are in the manager-local pending plan, kept outside Git.

Recommended local-ingest proposal: one source-file read, maximum 1 MiB and 120 seconds, exact source SHA required, at most 8760 data rows with expected header/order preserved, and only the 340 approved avg_CI values exported. Output is a new JSON object with source_sha256 and rows[{index,value}]. Values must be finite and nonnegative; rows remain explicitly indexed, without sorting the source, backfill, resampling or interval shifts. Stop on mismatch, ambiguity, malformed data, duplicate/out-of-range indices or an existing output. No retry or alternate source.

Important physical footprint: hashing reads the entire source file, and a sequential CSV traversal decodes rows outside the 340 numeric exports. This is not a 340-physical-row-only access operation. Record whole-file byte access, decoded-row traversal and selected numeric value access separately. Before ingest, the source/custody decision must explicitly accept that footprint and its isolation implications. If it does not, supply a previously authorized extract through the existing custody mechanism rather than silently scanning the CSV. A selection/nonce or held-out-isolation acceptance cannot be inferred from the restricted numeric export. No ingest is authorized yet.

Both interval-start and interval-end hypotheses and the recorded legacy mapping remain in the comparison. No implementation convenience chooses the physical interpretation or CO2/CO2e semantics. Keep the values labelled as the existing source proxy, not verified site-specific avoided emissions.

## Saved-state input plan

The driver accepts a JSON list of {state: VisibleState, snapshot: ConstraintSnapshot}, validated through existing F02. Each entry must identify one of the 40 development episodes and one unique slot 0–29. There are 1200 expected episode/slot positions. Currently no complete saved-state input has been identified; label-cache state hashes and labels are not the states themselves.

For each supplied trajectory record the original run/policy, input and forecast hashes, state/snapshot hashes, exact missing slots and the pre-comparison reason for that trajectory choice. Preserve the same operational history while substituting forecasts. Do not choose trajectories after observing favorable CF60 differences. Do not invent states from hashes or infer private paths. Any new simulation/rollout to generate states requires its own reviewed bounded scope; none is requested or authorized here. A partial state list must retain the missing count and cannot be presented as all-cohort coverage.

## Later comparison bounds and fail conditions

The existing scripts/compare_cf60_development.py is unchanged and its three LF code pins were rechecked. Proposed maximum: 40 fixed development episodes × 30 issues × 2 hypotheses = 2400 broker issues, at most 7200 candidate lookups, serial execution, 1800 seconds, zero retries, model/solver/training calls or new source acquisition. The driver reads only the separately approved JSON extract and optional pinned saved states, never the CSV.

Final authorization must bind a new ID, exact extract/state checksums and absolute paths, exact code commit/pins, the allowed index list, time limit and a new output directory. Exclusive consumption occurs before opening the extract. Leave the current draft pending: extract and state hashes are null because those artifacts do not exist. Rejected approval or unknown source use is a blocker, not a reason to fabricate a checksum or replace missing state data.

## Deliverables now available and remaining inputs

Manager-local INPUT_PLAN_PENDING.json and COMPARISON_AUTHORIZATION_PENDING.json contain the exact indices, proposed paths and code pins. The downloadable plan package contains those proposals and guidance, no source values. The public receipt discloses the candidate file size and unverified status without publishing a private path. The earlier November 8 pending draft is unchanged.

Remaining before any execution: authoritative source-use/extract provenance, explicit read/custody-scope acceptance, implementation/offline verification of any newly needed extractor, actual extract/hash and fresh final comparison authorization. Complete saved states are additionally required before fixed-history feature coverage. Issue #60 stays open; source acceptance, method adoption and the scientific freeze are not completed by this plan.
