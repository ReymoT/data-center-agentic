# RULE-02 implementation handoff (issue #240)

Status: **IMPLEMENTED, NOT YET ACCEPTED.** Study `rule-study-20261119-v1`, adapter `proposal-1`.
Synthetic authored inputs only; model calls: 0. Scores are artificial `score-kWh` weights, not measured
carbon intensity and not CO2e. This handoff is not independent verification, not a scientific freeze and not execution authorization.

Three separate things are handed off here and must not be conflated:

| Item | Owner | State |
|---|---|---|
| Implementation and reviewer-accessible evidence for #240 (this document, `docs/evidence/rule02/`) | Ved | Delivered; self-run checks below |
| Implementation acceptance, including the open design decisions in section 15 | Matty | Not given |
| Independent RULE-03 verification of the frozen system and binding authentication (#241) | Nisha | Not done; the in-repo reader run below is a compatibility smoke test, not that verification |

## 1. Acceptance criterion

Executable rules-v1 scheduler (R01-R09) and one common checked runner/fallback path that produce study-local
`rule_study_decision_v1` / `rule_study_result_v1` traces the merged RULE-03 strict reader accepts, for authored
cases A, B, B-fault and B-progress, with the production checker unchanged.

## 2. Base and final commit

- Base: `75d6ada1785816c2e9b0ab1c08b18da23c9facd8` (merge of PR #254).
- Implementation commit (the only code under evidence): `176361ad23ba57940b1576828893ce3a7b1a1666`.
- Documentation commit before this update: `ee1de66aec897d481308e3ce35a583c026c1b3ee`.
- Evidence commit: the commit that adds `docs/evidence/rule02/` and updates this file (Git records its SHA; it cannot be listed inside the files it contains).
- **Binding correction.** An earlier version of this handoff named `c42376e94e7558cdd980c45a57150ab24c0b09ab` as the frozen commit. That SHA came from a
  different local commit of the same files and is not in the published history. The Git tree of `c42376e` equals that of `176361a`
  (`22b31ab5fb3dcf055cf91f6a7420d2c89660d75c`), so the code is identical, but the traces that carried that SHA were not reviewer accessible and are
  superseded. The traces in this repository were regenerated from a clean checkout of `176361a`; no metadata was edited. Every one of the 310 result/decision
  records has `bindings.code_commit` = `176361ad23ba57940b1576828893ce3a7b1a1666`.
- This evidence update changes no implementation file. It adds `docs/evidence/rule02/**` and rewrites this document.

## 3. Files

Implementation (unchanged since `176361a`): `dc_sustainability/rule_study/{__init__,scheduler,records,cases,runner,demo}.py`;
`tests/rule_study/{helpers,test_rule_scheduler,test_rule_runner,test_rule_records,test_rule_demo,test_rule_reader_compat}.py`.
Evidence update (new): `docs/evidence/rule02/` (README, MANIFEST.json, traces, compat, meta, tools). Modified: this file.
Unchanged: `schemas.py`, simulator, Greedy A/B, F02 schemas, six-system registry, production checker, RULE-03 reader/verifier.

## 4. Algorithm

`propose_rules_v1` in `scheduler.py`: exhaustive bounded search over at most 4 waiting jobs and absolute start slots 0-5
(each job: legal starts plus unscheduled; 7^4 = 2401 assignments, none sampled or truncated; more than the bound is rejected explicitly). Integer arithmetic;
IT capacity checked before PUE (PUE not applied to the limit); half-open slot occupancy; background and running load counted; nonflexible start == arrival;
no restarts; no starts in slots 24+. Lexicographic objective: (1) number scheduled, (2) inclusion vector in priority order, (3) summed artificial score,
(4) sum of completion times, (5) start vector with unscheduled = 99. Only starts at the current slot execute; later starts are advisory and re-evaluated.
Unusable forecasts (missing, partial, stale, future-issued) or a missing freshness constraint disable optimization and route to checked Greedy A.

## 5. Runner and fallback

`runner.py`: serialized per decision; intent marker; production `check_schedule`/`recheck_schedule` on every stage; state and snapshot re-read and refusal on change;
`ApprovedActions.from_checked_plan` only from a passing check; `step(None)` for real refusal-and-drain; replay from saved evidence only; an indeterminate operation is
recorded and never retried. A rules-v1 proposal that fails the production check routes to the actual Greedy A policy, which is checked independently by the same gate.
The fallback is never trusted. The outer `policy_id` is preserved (stage origin `greedy_a_fallback`).

## 6. Latest-state recheck

Production `recheck_schedule` runs after the first check; state and snapshot are then re-read again and any difference refuses and drains with no step on the changed
state. The recheck result is stored in the hashed transition file (`latest_state_recheck`). Tests: `test_latest_state_recheck_is_performed_and_recorded`,
`test_state_change_during_check_refuses_without_stepping`, `test_constraint_change_during_check_triggers_one_refusal_and_drain`.

## 7. Scenario outcomes (regenerated traces, `docs/evidence/rule02/traces/`)

Observed outcomes of the regeneration, not hardcoded expectations.

| case | policy | stages (production check) | starts executed | completed | missed | impact (score-kWh) |
|---|---|---|---|---|---|---|
| A | rules-v1 | rules-v1 pass | J2@0, J1@1 | J1, J2 | none | 8000 |
| A | greedy_a | greedy_a pass | J1 and J2 @0 | J1, J2 | none | 12000 |
| A | greedy_b | greedy_b pass | J2@0, J1@1 | J1, J2 | none | 8000 |
| B | rules-v1 | rules-v1 **fail**, greedy_a_fallback **fail** | none | none | J1, J2 | 0 |
| B | greedy_a / greedy_b | **fail** | none | none | J1, J2 | 0 |
| B-fault | rules-v1 | fault_injection **fail**, greedy_a_fallback **fail** | none | none | J1, J2 | 0 |
| B-progress | rules-v1, greedy_a, greedy_b | pass | J1@0, J2@1 | J1, J2 | none | 12000 |

Both B rows are a **rejected** fallback, not a successful one; no fallback passed in any scenario. The injected B-fault proposal (J1@0 and J2@0, 80 kW against a 60 kW limit)
is rejected and never executed.

## 8. Rejected fallback (cases B and B-fault)

The unchanged production checker says: "abstention lacks individual physical justification; carbon is not infeasibility". Each job fits alone, so abstaining on the
other is not an individual physical certificate, and Greedy A's fallback is rejected for the same reason. Outcome: refusal and drain, zero new starts, both jobs missed.
`RULE01_SPECIFICATION.md` and `ADAPTER_RECORD_PROPOSAL.md` say to preserve this old-gate result. Rules-v1's own one-job B proposal (J1 start, J2 abstained) is rejected by the
same gate. A joint-exclusion gate would be a new proposal needing Ved/Nisha agreement and independent validation; it is not adopted.

## 9. Score formula, unit, source

`score-kwh-v1`: impact = power_kW x 1 h x PUE (1.0) x artificial slot weight, summed over occupied slots; integer arithmetic; unit "score-kWh (artificial)".
Source: the merged RULE-04 generator accounting units and the specification's artificial weights. Independent accounting receiving by Edison is still pending.
The `score_convention_status` text in each result record cites an acceptance by Edison; that citation has not been re-verified here and should be confirmed by Edison. Not g/kWh, not emissions.

## 10. Trace schema conformance

Layout `case.json`, `result.json`, `decisions/decision-NN.json` (plus `states/`, `snapshots/`, `transitions/`, `.intents/`, which the reader ignores). Field sets mirror the reader
constants and are tested (`test_rule_records.py`, `test_rule_reader_compat.py`). Disclosed design choices for review: a STOP without stepping is recorded with status `indeterminate`
(no `state_after`); unscheduled / started_not_completed live inside `accounting.job_outcomes`; the recheck result and fallback reasons live in the hashed transition file;
raw state/snapshot files are not referenced by records.

## 11. Bindings and their source artifacts

| binding | source | value |
|---|---|---|
| spec_sha256 | canonical hash of `docs/rule_study/specification.json` | 9597931fcee09bc895605b65401483c9c3658da9e0bdf7c954f8669dfa8542bd |
| adapter_source_sha256 | canonical hash of the per-file LF-sha map over `dc_sustainability/rule_study/*.py` | 76e7892504396d0d42c5c8dbfd3b9c1f1d654f6bf32c04d698b425f5a928c247 |
| generator_source_sha256 | LF-sha of `dc_sustainability/evaluation/rule_study_generator.py` | ab7950847683a8411e906de06bf12346db9b3fc74cb302718d586399d5df4072 |
| environment_lock_sha256 | LF-sha of `requirements/requirements-windows-py312.lock.txt` | 38562754e7ff8c500933a48f8c497799e1ac6af0fa7602d3df312195cef9034c |
| case_sha256 | canonical hash of each trace's `case.json` | A dd52c12a601996cad06d8aac725ce4a5e5f8277661673a239568c88b04a47a10; B 6af1a09f42ede0402c5c45ace06087065f217a25590326686dd2a281675eef57; B-progress 6ccc27a709e9d9abf514c81a3d671306fdedaddafad43b2926f22923c2ebc948; B-fault b3e76ab08a78f2ac6f00c1dfd6e9787397ec5eb1df3fd025eb96805588e6008f |
| code_commit | real HEAD of a fully clean checkout | 176361ad23ba57940b1576828893ce3a7b1a1666 |

Canonical hash: `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False)` plus one LF. All six are real and non-null.
The reader cannot authenticate them from the traces alone (section 12). The adapter hash covers `rule_study/*.py`, so editing any of those files requires regenerating the traces.
The environment lock hash is the file hash of the Windows lock; the sandbox run used a Python 3.12.3 virtual environment built from the pinned `requirements/requirements-core.in`
(`docs/evidence/rule02/meta/environment.txt`, `pip-freeze.txt`), not that hash-locked Windows environment.

## 12. Evidence, verifier command and result summary

Artifacts are listed with sha256 in `docs/evidence/rule02/MANIFEST.json` (check with `python docs/evidence/rule02/tools/build_manifest.py check`). Generation commands (also in the manifest):

```
git clone <repo> rule02-clean && cd rule02-clean && git checkout --detach 176361ad23ba57940b1576828893ce3a7b1a1666
test -z "$(git status --porcelain)"
PYTHONPATH=. python -m dc_sustainability.rule_study.demo --output-dir <new empty dir outside the clone>    # exit 0
```

Compatibility commands (`docs/evidence/rule02/compat/commands.txt`; full JSON, stdout and exit code per command are saved beside it):

```
python scripts/verify_rule_study.py --traces docs/evidence/rule02/traces/rules-v1 --system-id rules-v1 --rules-v1 --out docs/evidence/rule02/compat/verify-rules-v1.json
python scripts/verify_rule_study.py --traces docs/evidence/rule02/traces/greedy_a --system-id greedy_a --out docs/evidence/rule02/compat/verify-greedy_a.json
python scripts/verify_rule_study.py --traces docs/evidence/rule02/traces/greedy_b --system-id greedy_b --out docs/evidence/rule02/compat/verify-greedy_b.json
```

Result: exit code **2 (INCOMPLETE)** for all three, solely because `binding_validation` is INCOMPLETE (external adapter, generator, environment and code artifacts and raw state/transition bytes are not supplied to the reader, so
the bindings are not authenticated). No refused traces, no partial traces, no counterexamples.

- rules-v1 (4 traces): S1, S2, S3, S5 PASS (120 checked); S4 PASS (3 checked); P1 PASS (2 eligible; out of scope: 1 fault_injected, 1 not_jointly_feasible); P2 PASS (4);
  R04 arithmetic PASS (8 checked, 0 mismatches); state-hash continuity 116 checked, 0 mismatches.
- greedy_a and greedy_b (3 traces each): S1-S3, S5 PASS (90); S4 NOT_RUN (no invalid proposal occurred); P1 PASS (2); P2 PASS (3); arithmetic NOT_RUN (rules-v1 only); continuity 87 checked, 0 mismatches.
  The reader marks these as not rules-v1 results.

What the reader validated: case content, the specification hash, decision-list hashes and within-trace consistency of the supplied records. What it did not: authentication of the six bindings, the raw state and transition bytes,
or the identity of the running system (`--rules-v1` is a caller flag). PASS therefore means "no violation in the supplied records". This is a compatibility smoke test run by the implementer, distinct from Nisha's independent RULE-03 verification under #241.
Reader source hashes recorded in the reports: verifier `9d25fcdb821a3cc1adec07a64d658f165c8a6049f18ccd862030a82fb667bc94`, trace reader `cfd20cb92f69d6620be620631984fe071d43f4c5c1161e6a0ce8ca41affd9c1d`.
Note: `main` has since advanced past the base (`e503c21`, PR #255, a generator accounting-sidecar checker). It does not change the reader or verifier files used here; this evidence was not re-run on the new main.

## 13. Test commands and results (Python 3.12.3, pinned core requirements; every command exits 0)

Logs: `docs/evidence/rule02/meta/regression-*.txt`.

| command | result |
|---|---|
| `PYTHONPATH=. python -m pytest tests/rule_study -q` | 133 passed |
| `PYTHONPATH=. python -m pytest tests/simulator tests/verification tests/runtime tests/policies -q` | 247 passed, 6 skipped |
| `PYTHONPATH=. python -m pytest tests -q` | 2694 passed, 29 skipped, 19 subtests passed; no failures; no warnings reported |
| `ruff format --check dc_sustainability scripts tests` | 285 files already formatted |
| `ruff check dc_sustainability scripts tests` | All checks passed |
| `python -m compileall -q dc_sustainability scripts tests` | no output |
| `python scripts/validate_setup.py` | PASS |
| `python scripts/smoke_dependencies.py` | all PASS (no model call) |

All 29 skips are Windows-only containment/launcher tests. The default interpreter in the sandbox is 3.13 without project dependencies; the commands above ran in the 3.12 virtual environment.
The demo cannot be re-run in a tree that has uncommitted files because the runner refuses to bind `code_commit` from a dirty tree; the demo run recorded in section 12 was made from the clean checkout.

## 14. Replay results and hashes

1. In-process replay inside the demo: 10 of 10 cases "identical saved evidence; simulator transitions unchanged" (`meta/demo.stdout.txt`).
2. Replay from the committed files (`compat/replay-from-saved.json`, exit 0): a fresh runner and simulator on a copy of each saved trace returns all 30 saved decisions without stepping the simulator; every decision hash equals the one recorded
   in `result.json` (10 of 10). A tampered decision file is detected (checked on a throwaway copy: exit 1). This checks determinism of saved evidence, not a from-scratch re-run.
3. Fresh runs are not byte identical (the production checker mints random `check_id`s). Earlier sandbox runs showed the same behavior, statuses, starts and bindings.

Result hashes (sha256 of `result.json`): rules-v1 A 26a91eea23781f14bf2195e316d78d5784871070bb89e04269f7c35e73f9ee8a; B a8788c269200163d0603e8d9595021ddfd743c0518a04fa26b0a1d26e6802c9b;
B-fault 47a5286de8b67b06f4f05e28fa7faa7a8d1def1f6b0e624e99d2e14e28e94eb6; B-progress 1d02f5cacb50124eeb6a0eab6c3fea936801f367a4dc38f9d49bc8423ffc3cfb. Hashes of the other six traces and of every file are in `MANIFEST.json`.

## 15. Blockers with owner

| blocker | owner |
|---|---|
| Frozen-system verification, authenticated bindings, separate bounded authorization (#241) | Nisha |
| Independent accounting receiving of `score-kwh-v1`; confirm the acceptance citation in the result records (#242/#239) | Edison |
| Decision on a joint-exclusion gate for case B (otherwise the old-gate blocked result stands) | Ved / Nisha |
| Implementation review and acceptance of the disclosed record-shape choices (section 10) | Matty |
| Frozen run authorization and dispatch (#244) | Matty |
| CI on the current base before merge (`main` has advanced) | Ved |

## 16. Authorization boundary

Used only authored synthetic cases. No real-source access, no held-out data, no 120-case RULE-04 evaluation, no new evaluation batch, no live model call, no training. The reader, verifier, checker, schemas, simulator
and Greedy A/B were not modified. No independent evaluation result is claimed and artificial scores are not emissions.

## 17. What Nisha does next (#241)

Review the exact published commit `176361a`; independently reconstruct the six bindings from their source artifacts and compare them with the traces; verify the frozen system with her own harness (not the `--rules-v1` flag alone); decide
on the case-B gate question; issue or withhold the separate bounded authorization.

## 18. What Edison confirms (#242/#239)

That `score-kwh-v1` (power_kW x 1 h x PUE 1.0 x artificial weight) matches the independent accounting; that unscheduled/started_not_completed inside `accounting.job_outcomes` is acceptable; and the acceptance citation noted in section 9.

## 19. Ready for review or blocked

**Ready for review as implemented and evidenced, not accepted.** Not complete: authenticated bindings, independent accounting receiving, #241 verification and the bounded authorization are pending, and Matty has not accepted the implementation.
Scenario B's blocked, no-start outcome is the preserved old-gate result, not a defect hidden by the implementation.
