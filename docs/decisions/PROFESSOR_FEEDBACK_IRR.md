# Professor feedback: inter-rater reliability

Status: accepted project requirement, October 27, 2026. Authorized by Matty Anderson.

The professor asked the team to report inter-rater reliability for the human
faithfulness annotations, such as Cohen's kappa, so the evaluation shows whether
the rubric is applied consistently across reviewers.

## One accountable owner

Nisha Mahadev Kolekar (`nkolekar-nk`) is the sole accountable owner for this
reporting task under E07 and R05. Matty remains the independent second rater and
joint adjudicator, but he is an input to the task rather than a second owner. No
other teammate receives a new implementation assignment from this feedback.

## Required report

For the development review and the frozen held-out faithfulness review, Nisha must
retain both independent original ratings before discussion and report, before
adjudicated results:

- the number of matched, reviewable assertions;
- the label-by-label counts or confusion matrix and each rater's label marginals;
- raw percent agreement;
- Cohen's kappa for the jointly extracted assertion labels;
- `undefined`, rather than zero, when kappa cannot be computed;
- a plain-language interpretation, including prevalence or label-imbalance effects;
- extraction agreement separately from label agreement; and
- excluded no-ops, unmatched assertions, missing ratings and other denominators.

Adjudicated faithfulness scores remain separate from inter-rater reliability. The
team must not overwrite either original, calculate kappa on adjudicated labels, or
describe a high raw agreement or a low/undefined kappa without the supporting
counts. Development reliability is protocol evidence, not a substitute for the
same report on the final held-out annotations.

## Existing implementation and remaining work

PR #92 supplies tested comparison and adjudication tooling, including Cohen's
kappa and undefined handling. PR #91 and the earlier Matty ratings preserve the
two development originals. The remaining task is the human assertion matching,
saved agreement artifact, interpretation, joint adjudication and later held-out
application. Existing preliminary development calculations are not final until
the matching record is agreed and the result artifact is retained.

This requirement does not change F02, the annotation labels, sampling rules, task
ownership outside this focused reporting duty, or the independence of the two
original ratings.
