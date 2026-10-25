# P02 B: Matty receiving review

Matty requested review/merge and deletion of Edison's merged P03a/P02b branches.
Edison's original Greedy B implementation and eight tests are preserved. Current
main, including reviewed P03, is reconciled without rewriting his commits.
Instruction 1.27, F02, dependencies, scientific settings and task ownership stay.

## Review result

B uses the actual Q04 assessment on the full occupied-slot union of individually
legal candidates, with an explicit trusted UTC time. It ranks complete fresh
coverage by job emissions, breaks equal-emission ties by earlier start, and uses
whole-decision A for missing/partial/stale/future/beyond-horizon coverage. It does
not shorten the candidate window to convenient forecasts or invent carbon values.

Review found an inherited window mismatch: loose deadlines allowed A to propose
completion past slot 30, and B could then crash looking up unavailable slot-30
carbon. With valid independent test inputs, the original code reproduces two
failures and eleven passes. Bound the shared greedy window by 30-duration and
apply the same end-at-30 bound to nonflexible jobs. This is the existing Q01 rule,
not a new scientific decision. Finish exactly at 30 remains allowed.

Nineteen new cases cover both policies' flexible/nonflexible completion boundary,
age-two/age-three freshness, explicit UTC, whole-decision partial fallback, running
load's effect on the required union and an empty queue. Two use real K02/A03/A04,
S01/S02 and immutable traces for 30 slots, with explicit public synthetic forecasts
or withheld forecasts. Requested system stays B; effective A is recorded in the
fallback stage with its actual check and reason. No fake approval is used.

The hand calculation is J1 at slots 2/3 (300+250), then J2 at 4/5 (400+480 beats
the remaining 0/1 at 500+450). Withheld forecasts use A at starts 0 and 2. Both
runs complete the jobs with 140 IT kWh and 1,340 site kWh. These are synthetic
receiving checks, not accepted source semantics, experiments or trained models.

The initial new test fixture omitted a required unit, and the initial E2E setup
omitted explicit forecast input. Those setup errors were corrected before branch
assessment; S01 correctly treated omitted forecasts as unavailable. An initial
hand expectation was also corrected using the arithmetic above, without changing
the policy's ranking. The separate logs remain outside Git, not misattributed as
policy defects.

Actual validation: 36 policy/receiving cases; 178 combined policy/training/E2E/
checker/controller cases in 6.64 seconds; one ordinary complete offline suite
passes 1,310 tests and 19 subtests in 19.56 seconds. Updated exact-head PR/main CI
is required before merge/cleanup. No model request or inference retry occurred.

This receives B's implementation and checked fallback boundary, not the full
six-system runner, independent E01 acceptance, frozen study or learned training.
P03 feature/collection/label/training work and the actual A01 CPU timeout remain
separate. Existing Q08 joint-contention behavior is not changed or waived.
