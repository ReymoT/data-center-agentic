# Offline explanation-limit assessment

Nisha's #185 clarifications are accepted by Matty in
[the November 8 reply](https://github.com/ReymoT/data-center-agentic/issues/185#issuecomment-6722945819).
Nisha owns extraction rule 11.9 and scorer tests. Complete checkable assertions
remain subject to normal labels; unfinished tails are recorded separately.
Completeness is rated as written, with cap-hit indicators and separate sensitivity
reporting. Earlier ratings remain intact.

The reproducible [measurement script](../../scripts/assess_explanation_limits.py)
uses the pinned Qwen3 tokenizer, version 0.23.3, and synthetic 20-job response
shapes. It extends only summary, four claim texts and four limitations.
Plan detail bounds stay at 96. F02 parsing passes for every constructed response.

| Text characters | Plain sentence-pattern tokens | Plain dense-pattern tokens | Agent explanation sentence / dense tokens |
| --- | ---: | ---: | --- |
| 96 | 1338 | 1563 | 352 / 577 |
| 192 | 1473 | 1824 | 487 / 838 |
| 256 | 1581 | 2067 | 595 / 1081 |
| 384 | 1753 | 2445 | 767 / 1459 |

The current output allowance is 1536 tokens. The 256-character Plain fixtures
exceed it. Even the 96-character dense fixture exceeds it slightly.
These patterns measure concrete synthetic JSON strings, not worst-case token
bounds, model output quality or guaranteed completion. Full prompt/schema and
output context accounting is still needed before an executable candidate is pinned.

Proposed next candidate for affected-owner review: 256 characters for explanation
summary, claim text and limitations, paired with a 4096-token output allowance
for both Plain and Agent. Keep plan detail limits separately unchanged. This gives
headroom above the measured fixtures but needs exact context counting and timing
checks before adoption. The proposal is not a change to runtime defaults.
Nisha and Ved should confirm the affected receiving/evaluation and context boundaries.
No new model call or validation run is authorized by this assessment.

[Measured evidence](../evidence/explanation-limit-assessment-2026-11-08.json)
retains tokenizer identity, counts and limitations. #185 remains open until the
scoring clarification is implemented and the adopted response treatment is settled.
