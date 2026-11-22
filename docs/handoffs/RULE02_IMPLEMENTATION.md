# RULE-02 implementation handoff (issue #240)

Status: **IMPLEMENTED, NOT YET ACCEPTED.** Local commits only; nothing pushed, no PR, no issue comment.
Study `rule-study-20261119-v1`, adapter `proposal-1`. Synthetic authored inputs only; model calls: 0.
Scores are artificial `score-kWh` weights, not g/kWh and not emissions. This handoff is not independent
verification, not a scientific freeze and not execution authorization.

## 1. Acceptance criterion

Executable rules-v1 scheduler (R01-R09) and one common checked runner/fallback path that produce study-local
`rule_study_decision_v1` / `rule_study_result_v1` traces the merged RULE-03 strict reader accepts, for authored
cases A, B, B-fault and B-progress, with the production checker unchanged.

## 2. Base and final commit

- Base: `75d6ada` (origin/main, merge of PR #254), branch `rule02/final-implementation`.
- Frozen implementation commit: `c42376e94e7558cdd980c45a57150ab24c0b09ab` (code and tests only). All fresh traces bind this SHA
  (`bindings.code_commit`), generated from a clean tree.
- This handoff is a second, docs-only commit on top; it changes no code, so the traces' `code_commit` remains the frozen SHA.

## 3. Files (all new)

`dc_sustainability/rule_study/{__init__,scheduler,records,cases,runner,demo}.py`;
`tests/rule_study/{helpers,test_rule_scheduler,test_rule_runner,test_rule_records,test_rule_demo,test_rule_reader_compat}.py`.
Unchanged: `schemas.py`, simulator, Greedy A/B, F02 schemas, six-system registry, production checker, RULE-03 reader/verifier.

## 4. Algorithm

`propose_rules_v1` in `scheduler.py`: exhaustive bounded search over at most 4 waiting jobs and absolute start slots 0-5
(each job: legal starts plus unscheduled; 7^4 = 2401 assignments, none sampled/truncated; more than the bound is rejected
explicitly). Integer arithmetic; IT capacity checked before PUE (PUE not applied to the limit); half-open slot occupancy; background
and running load counted; nonflexible start == arrival; no restarts; no starts in slots 24+. Lexicographic objective:
(1) number scheduled, (2) inclusion vector in priority order, (3) summed artificial score, (4) sum of completion times,
(5) start vector with unscheduled = 99. Only starts at the current slot execute; later starts are advisory and re-evaluated.
Unusable forecasts (missing/partial/stale/future-issued) or missing freshness constraint disable optimization and route to checked Greedy A.

## 5. Runner and fallback

`runner.py`: serialized per decision; intent marker; production `check_schedule`/`recheck_schedule` on every stage;
state and snapshot re-read and refusal on change; `ApprovedActions.from_checked_plan` only from a passing check; `step(None)` for
real refusal-and-drain; replay from saved evidence only; an indeterminate operation is recorded and never retried. A rules-v1 proposal
that fails the production check routes to the actual Greedy A policy, which is checked independently by the same gate. The fallback is never
trusted. The outer `policy_id` is preserved (stage origin `greedy_a_fallback`).

## 6. Latest-state recheck

Production `recheck_schedule` runs after the first check, then state/snapshot are re-read again; any difference refuses and drains with
no step on the changed state. The recheck result is stored in the hashed transition file (`latest_state_recheck`). Tests:
`test_latest_state_recheck_is_performed_and_recorded`, `test_state_change_during_check_refuses_without_stepping`,
`test_constraint_change_during_check_triggers_one_refusal_and_drain`.

## 7. Scenario outcomes (fresh traces, `/tmp/rule-study-demo-final`)

| case | policy | stages (production check) | starts executed | completed | missed | impact (score-kWh) |
|---|---|---|---|---|---|---|
| A | rules-v1 | rules-v1 pass | J2@0, J1@1 | J1, J2 | - | 8000 |
| A | greedy_a | pass | J1+J2@0 | J1, J2 | - | 12000 |
| A | greedy_b | pass | J2@0, J1@1 | J1, J2 | - | 8000 |
| B | rules-v1 | rules-v1 **fail**, greedy_a_fallback **fail** | none | - | J1, J2 | 0 |
| B-fault | rules-v1 | fault_injection fail, greedy_a_fallback **fail** | none | - | J1, J2 | 0 |
| B | greedy_a / greedy_b | fail | none | - | J1, J2 | 0 |
| B-progress | all three | pass | J1@0, J2@1 | J1, J2 | - | 12000 |

Both B rows are a **rejected** fallback, not a successful one. No fallback passed in any scenario.

## 8. Rejected fallback (case B, B-fault)

Unchanged production checker message: "abstention lacks individual physical justification; carbon is not infeasibility". Each job fits alone,
so abstaining on the other is not an individual physical certificate. Greedy A's fallback is rejected for the same reason. Outcome: refusal and
drain, zero new starts, both jobs missed. Per `RULE01_SPECIFICATION.md` and `ADAPTER_RECORD_PROPOSAL.md` this is preserved, not
weakened. Note that rules-v1's own one-job B proposal (J1 start, J2 abstained) is also rejected by this gate; a joint-exclusion gate would be a new
proposal needing explicit Ved/Nisha acceptance and independent validation (not adopted here).

## 9. Score formula, unit, source

`score-kwh-v1`: impact = power_kW x 1 h x PUE(1.0) x artificial slot weight, summed over occupied slots; integer arithmetic; unit
"score-kWh (artificial)". Source: the merged RULE-04 generator accounting units and the specification's artificial weights. Edison accepted
artificial units per the acceptance record; independent accounting receiving is still pending. Not g/kWh, not emissions.

## 10. Trace schema conformance

Layout `case.json`, `result.json`, `decisions/decision-NN.json` (plus runner evidence directories the reader ignores). Field sets mirror the
reader's constants and are tested (`test_rule_records.py`, `test_rule_reader_compat.py`). Disclosed design choices: a STOP without stepping is recorded with
status `indeterminate` (no `state_after`); unscheduled / started_not_completed live inside `accounting.job_outcomes`; recheck result and fallback
reasons live in the hashed transition file; raw state/snapshot files are not referenced by records.

## 11. Bindings and their source artifacts

| binding | source | value (prefix) |
|---|---|---|
| spec_sha256 | canonical hash of `docs/rule_study/specification.json` | 9597931fcee0 (full in verifier JSON) |
| adapter_source_sha256 | canonical hash of per-file LF-sha map over `dc_sustainability/rule_study/*.py` | 76e789250439 |
| generator_source_sha256 | LF-sha of `rule_study_generator.py` | ab7950847683 |
| environment_lock_sha256 | LF-sha of `requirements/requirements-windows-py312.lock.txt` | 38562754e7ff |
| case_sha256 | canonical hash of each trace's `case.json` | per case (A dd52c12a601996cad06d8aac725ce4a5e5f8277661673a239568c88b04a47a10) |
| code_commit | real HEAD, only from a fully clean tree | c42376e94e7558cdd980c45a57150ab24c0b09ab |

Canonical hash: `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False)` + LF. All six are real, non-null.
The adapter hash covers `rule_study/*.py` at the frozen commit; editing any of those files requires regenerating the traces.

## 12. Verifier command and result summary

```
python scripts/verify_rule_study.py --traces /tmp/rule-study-demo-final/<policy> --system-id <policy> [--rules-v1 for rules-v1] --out /tmp/rule02-final-verify/<policy>.json
```
Exit code 2 (INCOMPLETE) for all three, solely because `binding_validation` is INCOMPLETE (external adapter/generator/environment/code artifacts and raw
bytes are not supplied to the reader, so bindings are not authenticated). No refused traces, no partial traces, no counterexamples.
rules-v1 (4 traces): S1/S2/S3/S5 PASS (120 checked), S4 PASS (3 checked), P1 PASS (2 eligible; out of scope: 1 fault_injected, 1 not_jointly_feasible),
P2 PASS (4), arithmetic PASS (8 checked, 0 mismatches), state-hash continuity 116 checked / 0 mismatches. greedy_a and greedy_b (3 traces each): S1-S3, S5 PASS (90),
S4 NOT_RUN (no invalid proposal occurred), P1 PASS (2), P2 PASS (3), arithmetic NOT_RUN (R04 arithmetic is rules-v1 only), continuity 87/0.
The greedy reports carry the reader's note that they are not rules-v1 results. This is the in-repo reader run by the implementer, not independent verification.

## 13. Test commands and counts (Python 3.12.3 venv with pinned `requirements-core.in`)

- `tests/rule_study`: 133 passed (scheduler 44, runner 35, records 26, reader-compat 19, demo 9).
- `tests/simulator tests/verification tests/runtime tests/policies`: 247 passed, 6 skipped (Windows-only containment).
- `tests`: 2694 passed, 29 skipped, 19 subtests passed.
- `ruff format --check`: 285 files already formatted. `ruff check`: all checks passed. `compileall`: ok.
- `scripts/validate_setup.py`: PASS. `scripts/smoke_dependencies.py`: all PASS (no model call).
- Environment note: the default interpreter here is 3.13 without project dependencies, so the commands were run in a 3.12 venv built from `requirements-core.in`
  (pinned versions, not the Windows hash lock). The lock file is bound only by its file hash.

## 14. Replay results and hashes

The demo replays every case from saved evidence with no simulator step ("identical saved evidence; simulator transitions unchanged", 10/10 cases in a second run).
A second full demo run (`/tmp/rule-study-demo-rerun`) matched the final run on result status, job outcomes, impact, bindings, per-decision execution status/starts/state hash and stage origins for
all 10 traces. Byte-identity across fresh runs is not expected because the production checker mints random `check_id`s; replay of saved files is exact.
Result hashes (sha256 of result.json): rules-v1 A 72441c6a1242676a60485f417a6d3d2a5c5123819c0a99c1bcbe0268798a99b7; B e6b163226f8e6a3c660ac1b86d2ec485fea965b4fc65785b5ec59ee050b42755;
B-fault 4d9b8230209232d4777bd8a4616cbfbbbb36fae9bdb239b384afec78798b1733; B-progress 38fa2b7d18185d5468f5215b03cfa6817271d22914a440f84368b34fee559194.
Full manifest of result/case hashes: `/tmp/rule02-final-verify/MANIFEST.sha256` (outside the repo; evidence dir not committed).

## 15. Blockers with owner

| blocker | owner |
|---|---|
| Frozen-system verification, authenticated bindings, separate bounded authorization (#241) | Nisha |
| Independent accounting receiving of score-kwh-v1; metrics checkpoint (#242/#239) | Edison |
| Decision on a joint-exclusion gate for case B (otherwise old-gate blocked result stands) | Ved / Nisha |
| Frozen run authorization and dispatch (#244) | Matty |
| Review and publication of this branch | Ved |

## 16. Authorization boundary

Used only authored synthetic cases. No real-source access, no held-out data, no 120-case RULE-04 evaluation, no new evaluation batch, no live model call, no training.
No push/PR/comment/issue change. The reader, verifier, checker, schemas, simulator and Greedy A/B were not modified. No independent evaluation result is claimed and artificial scores are not emissions.

## 17. What Nisha does next (#241)

Review the frozen commit; independently reconstruct bindings from the artifacts (adapter files, generator, lock, spec, case.json) and verify them against the traces; run her own verification of
the frozen system; confirm or reject the disclosed record-shape choices (indeterminate STOP status, job_outcomes placement); decide on the case-B gate question; issue or withhold the separate bounded authorization.

## 18. What Edison confirms (#242/#239)

That `score-kwh-v1` (power_kW x 1 h x PUE 1.0 x artificial weight) matches the independent accounting; that unscheduled/started_not_completed in `accounting.job_outcomes` is acceptable; and the metrics checkpoint.

## 19. Ready for review or blocked

**Ready for review as implemented, not accepted.** Not complete: authenticated bindings, independent accounting receiving, #241 verification and the bounded authorization are pending.
Scenario B's blocked/no-start outcome is the preserved old-gate result, not a defect hidden by the implementation.
