# RULE-04 generator receiving — November 20

Owner Edison. This is the generator part of #242, not the complete evaluation or
accounting harness. Edison explicitly accepted review-2 sampling, units, metrics
and result mapping in [his actual reply](https://github.com/ReymoT/data-center-agentic/issues/239#issuecomment-7052918378).
That response is received; do not request it again. Ved and Nisha's earlier
agreements remain recorded. Implementation and scientific freeze are separate.

The generator uses one standard-library random stream, the specified draw order,
three strata and declared artificial weights. It imports no production checker,
scheduler, simulator or independent verifier. Its feasibility labels are claims
checked independently. Development-seed tests confirm the golden draw values,
counts, rejection accounting, identity conventions and checker compatibility.
They do not constitute final-set evaluation or verified policy results.

## Direct review and corrections

Matty reproduced 19 failing review regressions before correction. The updated
generator suite has 54 tests; the combined generator, independent case/trace
verifier and dummy-supervisor suite has 198 passing tests locally.

- A comment URL was accepted as the sole final-generation guard without checking
  its author, approval content, frozen inputs, consumed ID or resource limits.
  Both public and internal final-domain generation now refuse before constructing
  that RNG. Even an existing valid comment URL cannot enable it. This preserves
  the already recorded authorization boundary, not a new research restriction.
- The two output files could be left half-published. Both destinations are now
  exclusively reserved before generation. Serialization/write/sync/interrupt
  failures clean up only paths created by that invocation. Existing and replaced
  files are preserved. Pair publication is not filesystem-atomic: consumers must
  wait for successful command completion. Cleanup failure is a failure, not PASS.
- Zero, bool, fractional or oversized case/attempt limits could silently produce
  empty output, change counts or remove the intended bound. Development helper
  limits now require strict integers: 1–40 cases per stratum and 1–10,000 attempts.
  The normal CLI still uses the original 40/10,000 configuration.
- Invalid jobs/site values and unknown strata are refused rather than supplying
  nonsensical feasibility labels. Original development draw consumption, order,
  accepted predicates and golden values remain unchanged.

## Inputs and accounting separation

The visible set uses the existing independent case-reader shape. Development
fixtures pass its label, stratum, count, duplicate and supplied-overlap checks.
Missing-forecast cases expose scores as null. The separate accounting sidecar
contains all 30 weights and binds each case ID/full/workload hash to the complete
visible-set hash. Keep it out of policy inputs. Published code/seeds allow people
to reconstruct artificial weights; this is an input boundary, not secrecy.

The accounting format is an implementation handoff, not a claim of independent
accounting acceptance. Nisha's current checker does not validate the sidecar or
its hidden nonconstant profile. Metrics, rollouts, equal-work accounting and final
unit/result receiving remain pending. Do not equate a visible-case checker PASS
with those missing checks or with new safety/progress results.

## Reproduce ready preparation

```
python -m pytest tests/evaluation/test_rule_study_generator.py -q
python scripts/generate_rule_study_cases.py --domain development --out-cases <new-case-file> --out-accounting <new-accounting-file>
```

Parents must already exist; destinations must be distinct and absent. The CLI is
development preparation only. Its successful return does not authorize policy
rollouts, research batches or final generation.

## Remaining exact run gates

The final dispatcher is not implemented by this PR. It must bind the accepted
specification and exact generator/rule/verifier/environment hashes, actual retained
development content for exclusion (not a regenerated smaller helper subset), new
output location, unused single-use authorization ID and explicit bounds. It must
verify actual manager approval, preserve failures and run within the agreed
containment. Freeze that reviewed implementation before any final seed is drawn.
No final set was generated, including in tests. No policy/model/source/private-data
operation ran during this review; only development-seed unit fixtures were used.

Edison's remaining accounting/metrics checkpoint is November 23, 18:00 Arizona;
the full #242 deadline remains November 25. No masters, F02 contracts or old study
results change here. #239/#241/#242 remain open for their actual remaining freeze,
adapter, verification and evaluation evidence.
