# P03 constructor: Matty receiving review

Matty requested review, merge and merged-branch deletion for Edison's P03a and
P02b branches. This receiving starts at main af54294, instruction 1.27/F02 unchanged.
Edison's original P03 implementation and eight tests are preserved; current main
was merged into the branch without rewriting any of his commits.

The original constructor omitted unscheduled waiting jobs, left exact numeric-ID
ties dependent on input order, accepted invalid scores and could propose a finish
after the agreed slot-30 completion boundary. New receiving tests against that
source reproduced 11 failures and two passes before correction.

The correction adds explicit existing F02 abstentions for unscheduled arrived
jobs, a final lexical ID tie-break, finite real probabilities in [0,1] and the
agreed completion bound. It keeps injected temporary classifiers and existing
priorities. No schema, feature/training decision, dependency or scientific rule
changes. No production solver, heuristic substitute for trained C/D or fake
approved result is introduced.

Sixteen added cases cover checker-accepted individual infeasibility, missing
capacity evidence, shuffled exact ties, invalid scores, finish-at-30 versus
finish-after-30, and background/running/proposed IT load with PUE 1/2. Two cases
use explicitly test-only injected scores to traverse the real K02, A03, A04 and
S01 components for 30 slots under the C/D identifiers, retaining real traces.
They are constructor integration evidence, not trained-model or experiment results.

Actual local verification:

- Original receiving source: 11 failures, two passes, retained before the fix.
- First combined sandbox run: 105 passes and 19 temporary-directory setup errors;
  the normal-host run removes that environmental obstruction without test changes.
- Final focused training/checker/controller suite: 127 passes in 2.59 seconds.
- One ordinary full offline suite: 1,283 tests and 19 subtests in 19.64 seconds.
- Setup/50-task/policy/link checks, Ruff lint/format (111 files) and whitespace pass.

P03's remaining feature formulas, collection/rollout contract, labels, training,
model artifacts, forecast fallback and full P05/evaluation receiving are not
completed by this constructor increment. The common checker still decides
physical validity; existing Q08 joint-contention limits are not overridden.
No model inference occurred. Exact PR/main CI and deletion proof are recorded
in PR #77 after verification; an old green check is not used for the new head.
