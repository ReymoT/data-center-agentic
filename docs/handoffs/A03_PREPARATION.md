# A03 test-case preparation handoff

Owner: Matty Anderson (MattyAnd). Technical contact: Nisha. Date: 2026-10-10. Instruction deployment: 1.4; proposed interface blueprint: 1.0, not adopted schemas.

Delivered the [checker case catalogue](../../tests/verification/CASES.md): 19 rule-focused cases with concrete synthetic inputs/expectations and four explicitly undecided Q01-Q04 scenarios. Added its link to the [test-area guide](../../tests/README.md). This completes case preparation only; A03 implementation and acceptance remain pending.

Coverage includes valid and boundary schedules, overload, changed constraints, running occupancy, half-open intervals, deadline boundaries, arrival/current time, nonflexible starts, duplicate/unknown IDs, invalid slot types, missing/fabricated evidence, immutable running work, unsupported carbon claims and an impossible deadline.

Implementation requires Ved's F02 schemas, Reimo's visible-state fixtures and accepted applicable Q01-Q04 rules. No schemas, production checker, execution gate, provider mock or experiment component was implemented. No scientific decisions, task allocations, source files or teammate modules changed. Future tests must use independent expected results and must not turn this catalogue into a second production/evaluation validator.

Verification: repository setup/link/task consistency and Git whitespace checks are run for this document-only change. These checks cannot execute the specified cases because their production target does not exist. No passing production-test result or full A03 completion is claimed. Applicable GitHub foundation CI is checked after publication.

Next work is deferred at Matty's instruction: provider mocks, decision resolution, checker/runtime implementation and agent integration. Resume with current upstream contracts and accepted decisions when Matty requests it.
