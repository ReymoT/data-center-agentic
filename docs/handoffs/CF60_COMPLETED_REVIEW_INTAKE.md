# CF60 completed AI-assisted review and direct fix

Matty received the completed package on November 13, 2026 (America/Phoenix).
Archive SHA-256:
342734ce2a1c844f69f5e619a7c346b6bc915b55ef01eca1ad8799955b27678d.
Reviewed baseline: 7bb8b39f1ab3f5e46e76c12e2345601789960e80.
This is an AI-assisted technical review supplied by Matty, not an independent
human rating, source permission or fresh execution authorization. Original review
files are preserved unchanged outside the repository.

## Confirmed finding and fix

D1 is confirmed: recovery preflight accepted an empty original_state_hashes map.
With an explicitly synthetic empty input and matching dispatch reservation, the
worker could publish zero recovered states as a successful recovered_original
export. Two regression cases fail on the unchanged exporter. Preflight now
requires 1-1200 original-state commitments; existing coverage equality then
requires at least one authenticated state. Partial nonempty recovery remains
allowed and missing positions remain explicit. No shared format is changed.

The submitted worker regression also needed a correction: its modified synthetic
approval bytes did not match its original dispatch reservation. Without updating
that synthetic reservation, it failed on the reservation guard rather than the
empty-recovery defect. Matty corrected the test setup, reproduced both intended
failures on the baseline and verified they pass after the production fix.

## Validation and advice disposition

The supplied Linux test counts are attributed review claims, not Matty's rerun.
Matty's focused Windows run passes all 19 export cases, including real gated
worker/process-tree timeout cleanup. Lint and formatting are checked before
publication; exact PR and merged-main CI remain required.

The review's R1 (pre-consumption aggregate sizing/environment record) and R2
(supervisor provenance cross-check) are advisory hardening suggestions, not a
grant of acceptance. The existing aggregate read cap still applies; actual
environment/lock and input-size sufficiency must be authenticated in the exact
approval review. A successful dispatch is only eligible for independent receiving,
which must verify approval/state/provenance hashes and coverage before acceptance.
Neither advisory is resolved by pretending missing private evidence is supplied.
No additional production behavior is changed in this narrow integrity fix.

## Current readiness

The code defect is fixed; readiness remains BLOCKED_MISSING_EVIDENCE. Source-use
basis, exact private inputs/provenance, executor/machine/storage/custody/environment,
bounds sufficiency and fresh single-use approval are still absent. No private
candidate was read or searched, no real export ran, and no source rights, receiving,
compatibility, forecast adoption or I02 freeze is claimed. Keep #60 open.

Earlier downloadable pins refer to the pre-fix exporter. Refresh the reviewed
revision and all production-code pins in a new pending package after merge.
Preserve older review packages; do not silently authorize their use with new code.
