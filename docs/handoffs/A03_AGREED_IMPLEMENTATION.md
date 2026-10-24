# A03 agreed physical checks and Q04 assessment

Owner Matty; issue #7. October 24, 2026, instruction 1.26, F02 1.0.0.
Base main 2ec1e542c09066e2cf4d05953c5f076566a1e657. Matty authorized the
recommended implementation. The exact Nisha/Matty/Edison/Ved proposals and
Reimo's October 24 confirmation in #7 supply the Q01/Q03/Q04 agreement.

## Implemented

The production checker now verifies complete, exactly-once waiting-job coverage,
valid later deferral under known running work and newly proposed current starts,
individually justified abstentions, and the prohibition of starts after slot 23.
An individually feasible job does not gain abstention credit from joint
contention. Missing carbon does not establish physical infeasibility. Missing
capacity remains an explicit error. All existing authoritative-capacity,
visibility, citation, schema, binding, timing and deadline checks remain.

Complete, physically valid plans receive a real passing result; incomplete or
invalid plans fail with actual findings. This is not a simulator execution
permit. The runtime must recheck and bind the action against current state.
The checker does not certify carbon savings or use independent evaluation as
truth. Existing F02 records/enumerations and independent evaluator code are
unchanged. Coordinated A03 consumer-test expectation updates are recorded in #7;
the independent hand-derived expected results remain unchanged.

The local Q04 assessment enumerates the full occupied union over individually
legal starts, retains beyond-horizon requirements, and distinguishes missing,
stale, future-issued and beyond-horizon evidence. Age exactly two slots is fresh.
An explicit trusted UTC decision time and authoritative freshness/capacity
constraints are required. It never infers an episode date from forecasts or
private observations. This helper is routing evidence, not an F02 migration or
source/scientific approval. Policies/runtime must actually adopt it and record
whole-decision checked-A fallback before Q04 integration is accepted.

## Actual validation and remaining gates

98 focused verification/receiving/independent-comparison tests pass in 0.43s.
The single ordinary full offline suite retains 1,153 passes, 19 passing subtests
and one existing A01 object-agent deep-response timeout in 17.72s. No rerun to
hide that failure; it is unrelated to changed checker code and remains in A01.
Setup, links, exact policies, Ruff lint/format (94 files), compile and whitespace
pass. 21 new hand-derived cases cover the implemented agreement and edge cases.
No model call, dependency/pin/schema/source/rating change or independent replay
replacement. Exact hosted PR/main CI is recorded in #7 after execution.

Full #7 acceptance remains open for actual S01 Option B integration, directly
affected Q08/reference resolution, consumer forecast-time mapping/routing,
controller integration and receiving evidence. A given plan's physical check
does not certify an optimal schedule, joint-infeasibility certificate, future
intention execution or completed end-to-end study.
