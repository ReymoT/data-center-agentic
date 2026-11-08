# Development forecast comparison driver

Matty authorized the offline driver preparation on November 8. The broker
implementation from PR #187 is merged. Nisha recorded a scoped library
receiving PASS for c09167451d66cf51018f8eb30278abd700286f57. Source access,
OS custody, scientific adoption and compatibility remain separate gates.

## What the driver does

Run scripts/compare_cf60_development.py with an explicitly approved row extract.
It validates the pinned 40-record allocation using the existing allocation reader.
It compares 30 issues under both interval hypotheses for each episode, giving
2,400 comparisons. The broker receives only the three candidate rows for its issue.
The driver retains recorded mapping, legacy dependencies, both CF60 footprints,
missing evidence and the broker receipts. It reads no CSV.

When supplied with saved F02 visible-state/snapshot entries, it holds their
operational histories fixed, substitutes the two forecast series, and uses the
existing Q04 assessment and candidate feature functions. It reports missing saved
states against 1,200 possible episode/slot positions. These comparisons do not
simulate different policy histories, certify O02 labels or establish C/D prediction
compatibility. The driver loads no classifier and makes no solver or model calls.

An extract is a JSON object with source_sha256 and rows, each containing index and
value. The source hash must match the pinned D01 snapshot. Extra/duplicate rows,
invalid values and checksum mismatches fail. Omitted rows mean unavailable extract
evidence. They do not prove the source itself is missing.
Saved states are an optional JSON list of objects with state and snapshot, using
their existing F02 JSON representations. Unknown episodes and duplicate slots fail.

## Bounded authorization before any real extract is opened

Authenticate the manager approval separately. A file saying approved is evidence
linkage, not proof of human permission. The approval JSON must include:

- A nonempty authorization_id, used once.
- Absolute extract_path and output_path, plus states_path when supplied.
- status set to approved and scope set to cf60-development-forecast-features-only.
- source_sha256, extract_sha256 and the explicit permitted_indices.
- code_sha256 with canonical LF hashes for scripts/compare_cf60_development.py,
  dc_sustainability/data/cf60_comparison.py and dc_sustainability/data/cf60_broker.py.
- states_sha256 when states are supplied, otherwise null or absent.
- time_limit_s, positive and at most 1800 seconds.

The final approval must also bind the exact extract/state paths, new private output
directory and code commit. Outputs include comparison.json and checksums.json.
The output directory must be new. An exclusive consumption record under its
parent is created before any extract is read. Repeated or concurrent use of the
same authorization ID fails, including when the requested output name changes.
A failure after output creation leaves failure.json.
Never reuse a failed output directory under the same single-use approval.

Use the project interpreter from the repository root:

    python scripts/compare_cf60_development.py --extract APPROVED_EXTRACT --authorization AUTHORIZATION_RECORD --states SAVED_STATES --out NEW_PRIVATE_DIRECTORY

Upper bounds are 2,400 broker issues and 7,200 candidate lookups, serial execution,
no retries, no source ingestion, and zero solver/model requests. The implementation
does not call the full-CSV acquire() helper. Deriving an extract needs its own
permitted read footprint and source/custody authorization.

## Actual preparation evidence

Four synthetic regression tests exercise every issue/hypothesis combination,
known numeric differences, Q04 and feature substitution, missing evidence,
out-of-footprint rows, invalid budgets, code/input pins, failure recording and
output reuse. Synthetic values are row indices. They are not observed carbon data.
The earlier private byte inventory matched all 40 materialized files to the
existing receipt and hashed 19 model files without selecting or loading them.

Next, bind an approved private extract and any saved-state inventory before real
execution. Ved and Edison review downstream reference and C/D implications after
the actual comparison. The [compatibility plan](CF60_DEVELOPMENT_COMPATIBILITY_PLAN.md)
still governs those steps.
