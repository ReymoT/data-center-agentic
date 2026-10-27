# D04/Q06 inventory — separate from source evidence

Owner: Reimo. Technical contact: Nisha for D04; affected calibration/fixture
consumers: Edison, Ved and Nisha. Reviewed October 24, 2026 on main
`2ec1e542c09066e2cf4d05953c5f076566a1e657`, instruction 1.26.
This inventory implements no split and approves no freeze.

| Item | Existing evidence | Missing artifact / owner and unblock condition |
|---|---|---|
| Development workload distributions | [D03](D03_SYNTHETIC_SCENARIOS.md), `dc_sustainability/data/scenarios.py`: explicit independent discrete uniforms; normal 12/7 flexible, spike 20/12, limited 12/2, infeasible 12/7; power 10–40 kW, duration 1–4, arrival 0–17; slack normal/spike/infeasible 2–10, limited 0–2, capped at deadline 30; one intentional slack −1 | Reimo supplies final distribution specification and affected Edison/Ved/Nisha agreement. Provisional implementation does not select Q06 |
| Spike and infeasible construction | Exactly eight spike arrivals in 6–9, remaining twelve outside; first selected flexible infeasible job gets slack −1 | Reimo records accepted choices and tests; construction is currently a development rule, not a scientific agreement |
| Empirical calibration | [D02](D02_CALIBRATION.md), [status manifest](manifests/d02-source-status.json): adapter/statistics/proposed p05–p95 scaling exist | Reimo obtains authorized job table, dictionary, units/power scope, license, exclusions and actual quantiles; Edison checks calibration. Frontier follow-up is deferred in #60; no renewed access attempt here. Alternatively record an explicitly accepted synthetic-only scope with narrower claims |
| Existing seed/artifact | `d03-provisional-v1`, seed 42, development catalog [manifest](manifests/d03-provisional-jobs.json), SHA-256 `ea8f414bf21035db04d75ca8ff1815aae94e940d02295ee7dd99a41e0dc38ad5` | This seed identifies a tiny job catalog only. Reimo must provide final date-selection, scenario/job and calibration sampling seeds, RNG/runtime versions and per-episode provenance |
| 40 development episodes | Shared rules specify 40 across four scenarios, source days 1–14 | No actual allocation/date/window manifest found. Reimo supplies IDs, dates, scenarios, 30 physical source-hour indices and hashes; 10 per scenario remains a recommendation unless agreed |
| 30 held-out episodes | Six dates (days 15–28, different months) × four scenarios plus six withheld-forecast variants | No selected six-date manifest or final selection seed found. Reimo supplies access-controlled private manifest and evaluator loader; Nisha verifies without releasing held-out inputs for tuning |
| Three blocked development folds | Required grouping of related/overlapping windows | No fold-group manifest or cross-fold overlap report found. Reimo assigns groups; Nisha independently checks; related withheld variants must stay with their parent |
| Overlap verification | D03 tests validate generation, not D04 temporal isolation | Reimo supplies source-identity + physical interval intersections across dev/test and folds, including 30-hour next-day tails; date labels/day-number partitions alone cannot prove nonoverlap. Need accepted Q05 mapping before authoritative window report |
| Freeze bundle and approval | None found; [open decisions](../docs/team/04_OPEN_DECISIONS.md) retain Q05/Q06 gates | Reimo supplies immutable manifest/checksums, code/environment, seeds/distributions/calibration and agreed interval mapping; affected owners record agreement and independent evaluation remains required. No freeze approval is supplied by this package |

Keep split/scenario/seed labels, future jobs, realized scoring carbon and reference
outputs in private artifacts, outside policy views. Share only permitted development
artifacts for review. Do not generate or inspect held-out data to fill this inventory.
The existing generator's `split` argument labels caller metadata; it does not allocate
dates, enforce fold isolation or authorize held-out tuning.

Q06 remains open independently of the source-documentation checkpoint. Once source
mapping and exact split proposal are available, record directly affected agreements
and required checks in the assigned Issue/decision record before adoption. Unresolved
shared requests follow the existing 24-hour escalation rule; no new request or
deadline was posted here. Reuse [D05's blocker ownership](D05_SOURCE_EVIDENCE.md#blockers-owners-and-veds-review).
