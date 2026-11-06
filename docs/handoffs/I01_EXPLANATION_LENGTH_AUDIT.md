# Offline explanation-length audit

Scope: the ten saved explanations in public development run RUN-fd87c6c8a9cb.
Read the decoded provider output before any downstream formatting. For Plain,
read the nested explanation. Count characters in summary, claim text, and each
limitation against the request-local maximum of 96. Plan-only responses carry
no explanation and are outside these counts.

| System and slot | Summary length | Claim lengths | Limitation lengths |
| --- | ---: | --- | --- |
| Agent 0 | 96 | 96, 95, 95, 93 | 81, 86, 79 |
| Agent 1 | 96 | none | none |
| Agent 2 | 96 | none | none |
| Agent 3 | 96 | 83, 67, 47, 54 | 96 |
| Agent 4 | 96 | none | none |
| Plain 0 | 96 | 65, 65, 74, 77 | 95 |
| Plain 1 | 86 | 53, 74, 72, 73 | 86, 89 |
| Plain 2 | 96 | 57, 37, 45, 45 | 86 |
| Plain 3 | 93 | 53, 59, 60, 68 | 68, 56 |
| Plain 4 | 93 | 53, 67, 68, 93 | 96 |

Seven of ten summaries, one of 28 claims and two of 11 limitations reached the
cap. Agent summaries 0 and 4 end mid-word or mid-clause, and the two capped
limitations end with unfinished thoughts. Agent summaries 1 and 2 have unusual
trailing characters of unknown cause. Plain 0 and Agent 3 have intelligible
complete summaries at the cap. A complete sentence can still be unsupported.
For example, check Plain's claims about actual starts and stale forecasts against
the structured plan, recorded gate, and visible forecast issuance.

Proposed E04 treatment for review in [#185](https://github.com/ReymoT/data-center-agentic/issues/185):
keep the original text and apply the same rule to both systems. Rate the
support of complete assertions against saved evidence. Flag visibly unfinished
fragments separately, preserve their counts and denominators, and report
completeness with the cap limitation disclosed. Never infer omitted wording or
automatically exclude all cap hits. Keep scoring treatment provisional until
agreed and document any sensitivity analysis separately. No new human ratings,
runtime setting changes or model calls were made.

