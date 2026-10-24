# S01 Option B receiving - Matty

October 24, 2026. Instruction 1.26; F02 1.0.0. Receiving base is Reimo's
PR #64 head e48a3432749cf4ae7985c809a23a4da400220664, based on main
2ec1e542c09066e2cf4d05953c5f076566a1e657. Reimo requested these five
checker-intake corrections in issue #7; Matty authorized implementation.

The four scenarios now use Q01's permitted False setting. A separate regression
requires the retired True option to raise, rather than keeping it as an alternate
experiment. For impossible arrivals, the expected illegal start is derived from
the visible job's duration and deadline, independently of the checker. The test
requires a real deadline failure; it does not relax all verdicts into success.
Raw proposals still cannot bypass ApprovedActions. All 30 rejection/clock slots,
no-new-occupancy and preserved unfinished outcomes remain checked.

Before correction: five failures and seven passes in the original receiving file.
After correction: 228 simulator/contract/receiving tests pass in 0.87 seconds.
One ordinary full offline suite: 1,147 pass, 19 subtests pass, one independent
replay failure remains in Nisha's infeasible S01 comparison (8.29 seconds).
The original failure is retained. No evaluator, simulator, schema, dependency,
prompt, source fixture or scientific-scoring code is changed by this receiving
commit. No model call or manufactured execution approval.

This is Matty's completed receiving correction, not full PR acceptance. Nisha owns
the independent replay change; Ved has been asked for actual independent S01
reproduction. PR #64 remains unmerged while checks fail. Record the final commit,
actual receiving acceptance and merged-main CI in #7 after those gates are met.
