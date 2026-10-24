# Production checker test cases

October 24 implementation: [agreed checks](../../docs/handoffs/A03_AGREED_IMPLEMENTATION.md) now enforce Q01/Q03 coverage, deferral and individual abstention. Actual physical passes are possible; controller execution, Q04 routing and Q08 certification remain distinct. [Hand-derived regressions](test_agreed_rules.py) cover the new boundaries. Earlier dated preparation notes below are historical where superseded.

Task: A03 preparation. Owner: Matty Anderson (MattyAnd). Technical contact: Nisha. Prepared 2026-10-10 from instruction deployment 1.4 and the final October proposal.

Status update 2026-10-12: Ved's F02 1.0.0 records and Matty's fixed checker core now exist. [Executable tests](test_checker.py) exercise the fixed expectations, including boundary/type/missing-evidence cases. Q01-Q04 scenarios remain unresolved; successful fixed subchecks do not approve execution. See [the handoff](../../docs/handoffs/A01_A03_AGREED_CORE.md). This catalogue does not define a second validator or scientific decision.

## Common setup and assertions

Use small synthetic development examples only. Capacity is IT power: 100 kW including 40 kW background, before PUE. Occupancy is the half-open interval [start, start + duration). All job powers/durations below are within the proposal's ranges. Each case has only the jobs stated in that row; use valid, current evidence and constraints unless the case deliberately removes or corrupts them.

The hand example uses flexible J1 and J2, both arriving at slot 0 with duration 2 and completion deadline 6. J1 uses 40 kW; J2 uses 30 kW. Their legal starts 0 and 2 do not overlap. For a capacity-boundary variant only, change J2 to 20 kW. Variants are isolated test inputs, not selected dataset distributions or frozen experiment fixtures.

Each expectation below concerns the named validation rule. A rule passing does not establish that a complete plan is approved: coverage, deferral and partial-infeasibility semantics remain Q02/Q03. Do not select an error-code spelling, return shape or omission status before F02 defines it. Reject/error results must identify the offending job or constraint and must not masquerade as a successful check.

For each adopted case, assert that checking does not mutate the plan, visible state or authoritative constraints. Capture the input state version, plan identity/hash, performed checks and relevant evidence in the F02-defined result. The production checker must never read private future arrivals, scoring carbon or oracle answers to produce its verdict.

## Cases with established rule expectations

| ID | Setup and proposed action | Expected rule result | Basis |
|---|---|---|---|
| V01 | Hand example: J1 starts 0; J2 starts 2; current slot 0. | Timing and capacity checks pass. Peak IT load is 80 kW. J2's future start remains an intention, not immediate execution permission. | Nonpreemptive occupancy; current-only execution |
| V02 | Boundary variant: J1 40 kW and J2 20 kW both start 0; background 40 kW. | Capacity check passes at exactly 100 kW IT. PUE 1.2 makes facility power 120 kW, which must not be compared to the IT capacity limit. | Capacity is IT load before PUE |
| V03 | Original J1 and J2 both start 0. | Capacity violation: 40 + 40 + 30 = 110 kW in slots 0 and 1. | Shared hand example |
| V04 | One J1 starts 0. Check once with authoritative capacity 100 kW, then with 70 kW; background remains 40 kW. | Capacity rule passes at 100 and fails at 70: IT load is 80 kW. No hardcoded or prompt-supplied 100 kW may override the changed constraint. | Graph-driven constraint requirement |
| V05 | Current slot 1; J1 is already running from 0 to 2. Propose J2 at 1. | Capacity violation at slot 1: running occupancy counts, so load is 110 kW. | Running work is immutable and counts toward capacity |
| V06 | Current slot 2; J1 has finished at boundary 2. Propose J2 at 2. | Occupancy/capacity rules pass; J1 contributes no power in slot 2. This also checks the legal 0/2 hand schedule. | Half-open occupancy intervals |
| V07 | Only flexible J1; propose start 5 with duration 2 and deadline 6. | Deadline violation: completion boundary 7 is later than 6. Checking only start time is insufficient. | Completion deadline |
| V08 | Only flexible J1; propose start 4 with duration 2 and deadline 6. | Deadline rule passes at the exact completion boundary 6. | Completion deadline is inclusive at its boundary |
| V09 | Current slot 4; a visible job arrived at 4, uses 10 kW for one slot, deadline 8. Propose start 3. | Timing violation: start precedes both arrival and current time. | No start before arrival/current slot |
| V10 | Current slot 3; a flexible job arrived at 0, uses 10 kW for one slot, deadline 8. Propose start 2. | Current-time violation even though arrival and deadline rules are satisfied. | No backdated starts |
| V11 | Current slot 0; a nonflexible job arrives at 0, uses 10 kW for one slot, deadline 3. Propose start 1. | Nonflexible-arrival violation, despite feasible capacity and completion. | Nonflexible jobs start on arrival |
| V12 | Only J1 is visible. The proposal contains two start entries for J1, at 0 and 2. | Duplicate-job violation even though the two entries would not overlap. | Known, unique job IDs |
| V13 | Only J1 is visible; propose an action for J99. | Unknown-job violation. Do not look in a private fixture to make J99 valid. | Visible-state boundary and known IDs |
| V14 | Otherwise valid single-job action; replace its integer start with each of true, 0.5, NaN and infinity. | Each variant is rejected at parsing/schema validation; Boolean values must not be accepted as integer slots. Exact transport representation awaits F02. | Strict proposed interface requirements |
| V15 | Otherwise valid J1 start; remove the required authoritative capacity relation/evidence. | Missing-evidence failure; no default or unlimited capacity and no approval for execution. | Required constraint evidence |
| V16 | Current slot 1; J1 is running from 0 to 2. Attempt to move its start to 1, pause it or split its run. | Each attempted modification is rejected; its original occupancy remains unchanged. | Running jobs cannot move, split or pause |
| V17 | Authoritative capacity is 70 kW. Propose J1 at 0, but cite a fabricated or unrelated constraint saying 100 kW. | Invalid evidence cannot override the 70 kW constraint; the 80 kW load still violates capacity. | Source-linked evidence and authoritative constraints |
| V18 | Feasible J1 schedule with valid capacity evidence; carbon evidence is missing, but explanation claims a numeric emissions saving. | Savings claim is unsupported and must not be certified. Missing carbon alone is not proof of physical infeasibility. Final eligibility/fallback behavior follows Q04. | Feasibility and claim validity are distinct |
| V19 | Current slot 4; flexible J3 arrives at 4, duration 3, power 10 kW, deadline 6. Propose its earliest start 4. | Deadline violation: earliest completion is 7. Retain the structurally valid impossible job for evaluation. Treatment of other jobs awaits Q02. | Proposal's deliberately impossible hand case |

V04 starts with injected authoritative records. Its later graph-to-checker integration counterpart requires Ved's K03 graph fixture; creating that graph is outside this preparation task. V18 establishes the unsupported-claim result only, not an assumed complete-plan verdict.

## Cases waiting for a scientific decision

These are prepared scenarios with deliberately unselected expected outcomes. Add the accepted decision record and exact assertions before converting them into executable acceptance tests. Do not skip them and report full A03 completion.

| ID | Scenario to retain | Missing decision |
|---|---|---|
| D01 | An arrived flexible job has a planned start at slot 24 and can finish by 30. Verify completion-slot execution, recheck and cancellation behavior under every system. No completion-slot model call is allowed regardless of the selected start rule. | Q01: whether new starts are allowed in slots 24-29 |
| D02 | One arrived job is impossible and another has a feasible current start. Verify per-job rejection versus whole-decision abstention, returned statuses and comparison-work accounting. | Q02: partial infeasibility |
| D03 | Compare a full plan with an omitted arrived job, an explicit deferral, an empty plan and malformed/no output. Verify required coverage, statuses and scoring treatment without assuming those outputs are equivalent. | Q03: coverage, deferrals and denominators |
| D04 | Vary forecast issue age across the two-slot freshness boundary; include a future issue time and missing/partial coverage. Verify evidence/claim eligibility and fallback granularity for agent, B, C and D. | Q04: exact freshness edge, partial coverage and fallback scope |

## Conversion and completion evidence

1. Ved supplies adopted F02 schemas/examples; Reimo supplies the immutable visible-state hand fixture. Map these specifications to those records rather than creating a second schema.
2. Record accepted Q01-Q04 rules and add the missing decision-specific assertions. Source-specific carbon semantics still require Q05 verification; the synthetic examples establish no physical dataset claim.
3. Implement Matty's A03 checker and the cases under tests/verification. Use direct rule expectations and hand arithmetic; do not use the checker itself as the oracle for expected results.
4. Run the implemented suite and retain actual commands/results. At least ten meaningful tests must pass, including invalid and missing-evidence cases; a catalogue, test count or dependency smoke run is not checker acceptance.

All six policies use the same production checker. Parameterized adapter integration comes later when those policies exist. Nisha's independent evaluator must keep separate validation logic. Execution-gate tests, provider mocks and LangGraph work are deferred under Matty's current instruction.

Sources: [Matty master](../../docs/team/MASTER_MATTY.md), [shared rules](../../docs/team/01_SHARED_RULES.md), [interface blueprint](../../docs/INTERFACES.md), [open decisions](../../docs/team/04_OPEN_DECISIONS.md) and [source provenance](../../docs/SOURCE_REVIEW.md).
