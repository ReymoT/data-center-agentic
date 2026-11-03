# PR title

D05 #60: propose causal CF60-v1 study forecast and isolation contract

# PR description

Issue #60 needs an exact causal study forecast before source/custody/freeze can
advance. This draft proposes **CF60-v1**, bounded last-available-observation
persistence; no production forecast adapter or scientific setting is adopted.

At trusted UTC issue I, propose simulated availability B=E+1h after physical
interval completion E. Strict B<I and a proposed four-hour completion-age bound
admit exactly E=I−2h/I−3h/I−4h. Read every present candidate and select latest E,
independent of value. Missing history stays missing; no future backfill or year
wrapping. Persist through latent slot 29, including leads >=24h, while retaining
F02's 24-slot policy view and Q04's freshness/required-coverage/checked-A rules.

The handoff separately derives E=L+1h for interval-start and E=L for interval-end.
CSV-specific physical interval meaning remains unresolved; neither hypothesis
shifts accepted source mappings. It defines complete history-read unions (maximum
32 rows across 30 issues), both directions of history-to-scoring isolation, legacy
development reads, related groups/folds and the conservative helper's limits.
The current custody allocator lacks these history checks: a versioned metadata-only
amendment and independent receiving must precede any actual selection. No seed
search, outcome-driven reranking or retry is permitted.

Review requests (accept exact parameters or identify the smallest change):

- @nkolekar-nk: bidirectional history/group/fold isolation, custody amendment and independent receiving.
- @vedp3705: conditional source mapping, completion/availability proof and O02 compatibility.
- @epez7: simulated lag/history-age bound, accounting and P03/P04/P05/E02 compatibility with unchanged trained policies.
- @MattyAnd: decision coordination, unresolved-question escalation and scientific freeze gates.

B1–B3 remain **UNRESOLVED**, B4 **PROVISIONAL**, B5 **PENDING**. Source semantics,
rights and actual custody cannot be supplied by passing synthetic tests. Existing
40 development content commitments, allocation/folds, Q04 rules and trained
models remain unchanged. No source observations, actual held-out selections,
model requests, retraining or rescoring are part of this change.

Validation: 21 synthetic proof tests; 137 focused tests; full offline suite
1,919 passed plus 19 subtests. Setup, Ruff lint/format, compilation,
dependency consistency/smoke and preservation checks pass locally on macOS /
CPython 3.12.15. Hosted Windows CI must be checked independently for the pushed
head. See the handoff for commands and limitations.

Four files only: proposal, ready-to-post Issue response, this PR description and
synthetic executable specification. The Issue response remains a draft for Reimo
to post; no GitHub comment, merge, closure or scientific adoption is requested.

Related: #60.
