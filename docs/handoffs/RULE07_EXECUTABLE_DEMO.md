# RULE-07 executable demo handoff (Ved)

Date: November 22, 2026, Arizona · Branch: `ved/rule07-v3-pinned-759a8c3` (local only) · Pinned integration base: `origin/main` `759a8c33f07aba52e3b016502b6c52c0e9e24137` (includes merged RULE-02, PR #257, and PRs #258 and #259) · 

Code commit: a7a71d005e8b329415b665951b9c56a63ee94110
PR: #261
Trace archive: rule07-traces-a7a71d0.tar.gz
Checksum manifest: rule07-traces-a7a71d0.sha256
Replay verification: passed
Archive checksum verification: passed
Manifest entries: 617
Extracted files: 617

Scope: the executable-wiring, repeatable-command and replay part of [RULE-07 #246](https://github.com/ReymoT/data-center-agentic/issues/246) that Ved owns. The RULE-02 scheduler, runner, records and cases are already merged and are reused unchanged. Nothing was pushed, no PR or issue comment was made, and nothing remote was touched.

This is not Nisha's independent verification, not a frozen-policy or research result, and does not answer the Agent-versus-Plain question. Scores are artificial score-kWh weights, not measured carbon intensity, g/kWh or emissions, and no CO2e-savings claim is made.

Source of the issue text: #246 was read through a web-page summary (the GitHub API was not reachable), so the requirement wording below is a close paraphrase, not a verbatim copy. Re-check it against the live issue before anything depends on exact wording.

Commit structure (parent chain from the pinned base): `5389f76` demo driver, `aa436a6` audit fixes, `ae9c343` explicit verification statuses (the **final code commit**, which the current traces bind to), then docs-only commits (this handoff). Nothing but this handoff changed after the current traces were generated. Changes on `origin/main` between the earlier base `d04ccc1` and the pinned base `759a8c3` (PR #259) added a worker-preparation script, docs and one test under `tests/runtime`; they touch nothing in `dc_sustainability/`, `docs/rule_study/specification.json` or `tests/rule_study`, so the three RULE-07 files were re-applied without conflict.

## 1. Implementation summary

One new module, `dc_sustainability/rule_demo.py`, wraps the merged pipeline and adds only what the merged `rule_study/demo.py` lacks:

- **Scenario selection and menu:** `--scenario A|B|B-fault|B-progress` (any letter case), `--all`, `--list`, and an interactive menu on a terminal.
- **Expected versus observed, kept separate:** expected text is read from `docs/rule_study/specification.json`; observed values come only from the saved decision and result records. Comparison rows are `MATCH`, `DIFFERS`, `BOUND-MET-LITERAL`, `BLOCKED` or `DOCUMENTED-LIMITATION`.
- **Overall scenario outcome, separate from the literal bound:** `COMPLETED` (every job completed), `PARTIAL` (some work ran, not all completed) or `BLOCKED` (nothing executed or completed; a safe refusal, not a scheduling success). Scenario B and B-fault report `BLOCKED`.
- **Arithmetic shown from the merged record:** the proposed load (rule R04), the hypothetical joint load of a rejected candidate (rule R05) and the checker's reason, each labeled.
- **Inputs section:** case, episode and scenario identities, jobs, site capacity, artificial score weights, and the synthetic origin.
- **Disk replay:** `--replay RUN_DIR` replays from saved evidence with the saved bindings. It requires `case.json` and checks its hash against the bound `case_sha256`; checks that every decision is served from saved evidence, that the simulator takes zero steps, and that the result rebuilt from evidence equals the saved result byte for byte.
- **Overwrite safety:** every run goes to a new directory (`results/runs/rule07_demo/<UTC>-<hex>/` by default); a supplied `--out-dir` must be new or empty, otherwise exit 2. The summary file is create-only.
- **Hashed summary:** `demo_summary.json` (`rule07_demo_summary_v1`) lists bindings, inputs, result and decision hashes, observed values, expected-versus-observed rows and replay results.

## 2. Exact changed files

Relative to `origin/main` `759a8c3`: three added files, no modified files.

| File | Change |
|---|---|
| `dc_sustainability/rule_demo.py` | added |
| `tests/rule_study/test_rule07_demo.py` | added (47 tests) |
| `docs/handoffs/RULE07_EXECUTABLE_DEMO.md` | added (this file) |

Not touched: F02 schemas, the production checker, simulator, Greedy A/B, Nisha's reader and verifier, `cli.py`, and every merged `dc_sustainability/rule_study/*` file. The module sits outside `rule_study/`, so the merged adapter-source binding hash (which covers `rule_study/*.py`) is unchanged by this work.

## 3. Reused RULE-02 interfaces

From `dc_sustainability.rule_study`: `cases.AUTHORED_CASES` and the four authored cases; `runner.run_case`, `RuleStudyRunner`, `replay_case`, `build_result`, `make_bindings`, `BindingError`; `records` (`RuleStudyDecision`, `RuleStudyResult`, `Bindings`, `study_json`, `study_sha256`, `POLICY_IDS`); `scheduler.ScoreKwhConvention`. Also `runtime.traces.IndeterminateExecution` and `simulator.SchedulingSimulator`. The scheduler, the unchanged production `check_schedule`/`recheck_schedule` and the unchanged Greedy A fallback run inside the merged runner; a test wraps them and asserts they are called. No second scheduler, checker, fallback, schema or trace format exists.

## 4. Environment and dependencies

Linux, Python 3.12, installed from `requirements/requirements-core.in` (the repository lock is Windows-only). Offline: no network, model, private or source data. Limitation: the merged `make_bindings` binds `environment_lock_sha256` to the Windows lock file, so that hash does not describe this Linux environment.

## 5. Exact demo commands

```bash
python -m dc_sustainability.rule_demo                       # interactive menu (terminal)
python -m dc_sustainability.rule_demo --list
python -m dc_sustainability.rule_demo --scenario A          # A | B | B-fault | B-progress
python -m dc_sustainability.rule_demo --all --json
python -m dc_sustainability.rule_demo --all --out-dir /new/dir
python -m dc_sustainability.rule_demo --replay /new/dir     # or a single .../rules-v1/A-rules-v1 folder
python -m pytest tests/rule_study -q
```

A real run requires a clean committed checkout (the merged binding refuses a dirty tree). `--policy greedy_a|greedy_b` is available for A, B and B-progress; B-fault is rules-v1 only.

## 6. Actual results (clean commit `ae9c343`, rules-v1, `--all`)

| Case | Slot-0 proposal | Production check | Fallback | Executed starts | Completed / missed / unfinished | Scenario outcome |
|---|---|---|---|---|---|---|
| A | J2@0, J1@1 (rules-v1) | pass | none needed | slot 0: J2; slot 1: J1 (J1@1 was advisory at slot 0) | J1, J2 / none / none | COMPLETED |
| B | J1@0, J2 abstained (rules-v1) | fail: "abstention lacks individual physical justification" | Greedy A built and checked: fail (same reason) | none | none / J1, J2 / J1, J2 | **BLOCKED** |
| B-fault | injected J1@0, J2@0 | fail | Greedy A built and checked: fail | none | none / J1, J2 / J1, J2 | **BLOCKED** |
| B-progress | J1@0, J2@1 (rules-v1) | pass | none needed | slot 0: J1; slot 1: J2 | J1, J2 / none / none | COMPLETED |

Synthetic impact (artificial score-kWh): A 8000, B-progress 12000, B and B-fault 0.

**Scenario B arithmetic as displayed.** The plan proposed in B starts J1 only: background 20 + J1 30 = **50 kW** against 60 kW (within the limit). The **80 kW** figure (background 20 + J1 30 + J2 30, 20 kW over) is the hypothetical joint start that the plan excluded, shown as "HYPOTHETICAL, not proposed". The checker rejects the plan because the abstention of J2 is justified only by joint capacity, which the unchanged production rules do not accept as an individual physical justification. The 50 kW proposal is not an overload. In B-fault the proposed load itself is 80 kW against 60 kW and is labeled as the injected (not natural) proposal.

The literal "at most one job completes" bound is met with zero completions (`BOUND-MET-LITERAL`), which is not progress; the overall outcome is `BLOCKED`. No successful fallback was observed or claimed. No new joint-exclusion semantics were adopted. The trace field `record status: complete` only says all 30 decisions were recorded.

## 7. Actual replay results

All four replays passed individually and as a directory (`--replay` on the `--all` output): 30 decisions each, served from saved evidence, 0 simulator steps, result rebuilt from evidence equals the saved result, no binding drift against the clean checkout. Re-running `--scenario A` into the non-empty `--all` directory was refused with exit 2. Replay is also tested to fail on 13 kinds of damaged evidence (missing or altered state, snapshot, decision (middle and last), extra decision, swapped decisions, reservation, completion commitment, transition (corrupt and missing), `case.json` (missing and altered), and `result.json` (missing)).

## 8. Test evidence, statuses and exit codes

| Command | Result | Exit |
|---|---|---|
| `pytest tests/rule_study/test_rule07_demo.py` | 47 passed | 0 |
| `pytest tests/rule_study` | 195 passed (148 merged + 47 new) | 0 |
| `pytest` (full suite) | 2847 passed, 29 skipped (the existing Windows-only tests), 158 s | 0 |
| `ruff check dc_sustainability tests/rule_study scripts` and `ruff format --check` on the two changed Python files | clean | 0 |
| `python -m compileall -q dc_sustainability tests/rule_study` | ok | 0 |
| Demo `--list`, `--scenario` A, B, B-fault, B-progress, `--all --json` | as intended | 0 each |
| Demo `--replay` on the whole output directory and on each of the four case folders; also on the extracted archive | pass | 0 |
| Demo into a non-empty `--out-dir` | refused | 2 |
| `scripts/verify_rule_study.py --traces <dir>/rules-v1 --rules-v1` (compatibility smoke) | S1-S5, P1, P2 and arithmetic consistency PASS; `binding_validation` INCOMPLETE | 2 |

**Verification statuses** (vocabulary: `PASS`, `FAIL`, `INCOMPLETE`, `NOT_RUN`):

| What | Status | Meaning |
|---|---|---|
| Independent verification (Nisha, #241) | **NOT_RUN** | Pending Nisha's actual findings. No bounds, counts or counterexamples are claimed here. |
| Trace-reader compatibility smoke (`scripts/verify_rule_study.py`, unmodified) | **INCOMPLETE**, exit 2 | The reader's own per-property checks pass on traces this demo produced, but binding validation cannot complete: external adapter, generator, environment and code artifacts and raw state/transition bytes were not supplied to authenticate the bindings. It is not independent verification. |
| Local replay from saved evidence | PASS | Zero simulator steps; result rebuilt equals saved. |
| Archive hash integrity | PASS | All manifest entries match (section 9). |
| Cross-platform / second machine | NOT_RUN | No Windows run. |

The demo report and `demo_summary.json` print these statuses (`independent_verification` is `NOT_RUN ...`). The 29 skips are the existing Windows-only tests.

## 9. Historical and current evidence; trace hashes

Two trace sets exist. Do not mix them.

| Set | Bound to | Based on | Files | What it proves | What it does not prove |
|---|---|---|---|---|---|
| **Historical** (delivered earlier): `rule07-traces-64511d6.tar.gz` + `rule07-traces-64511d6.sha256` | code commit `64511d6a6a776f6f2d971c31e83e92fef1612af7` (earlier branch `ved/rule07-executable-demo-v2`, base `d04ccc1`) | an earlier base | 617 files, 4 cases | That the code at `64511d6` produced these exact saved traces, which replay from disk. | That the current integrated code (`ae9c343` on `759a8c3`) behaves the same; it predates the explicit-status change. It is not verification of the current implementation. |
| Older still: `rule07-traces-9059d4c.tar.gz` | `9059d4cc0bbe489dd40a7f61685e086399072f5d` | `276c442` | 617 files | Same, for the first version (before the BLOCKED presentation fix). | Same. |
| **Current**: `rule07-traces-ae9c343.tar.gz` + `rule07-traces-ae9c343.sha256` | final code commit `a7a71d005e8b329415b665951b9c56a63ee94110` | pinned base `759a8c3` | 617 files, 4 cases | That the final integrated code produced these traces and that they replay from disk with 0 simulator steps. | Independent verification (NOT_RUN), second-machine behavior, any research or frozen-policy result. |

`176361a` is not a trace-binding commit: it is the merged RULE-02 implementation commit (ancestor of the base). No RULE-07 trace set binds to it.

Current set: written to one fresh output directory (default location `results/runs/rule07_demo/`, git-ignored); each case folder under `rules-v1/<case>-rules-v1/` holds `case.json`, `result.json`, `decisions/decision-00..29.json`, hash-addressed `states/` and `snapshots/`, `transitions/`, `.intents/` and `.completed/`; the directory also holds `demo_summary.json`. The archive root is `all/`; manifest paths are relative to that root.

| Case | `result.json` sha256 | `decision-00.json` sha256 |
|---|---|---|
| A | `f44b270e02264337d816d4030e79bbda7504f0599339ad3dda1c40fb39915e06` | `0e984e1f3b7c7bd1efb707c23ed8e799a155b10bde614d4a0d8193f0072c822f` |
| B | `d7a458704d67ed31ecb61da9e793d70f43508a7d3eb48ecebd632622a1bdbc1d` | `01e21b3efaa4407fd824d7d77aaf86729a37013598451a6513318f2f83563746` |
| B-fault | `0bd76b480716734b5e541ea0f862927995ff5074b301704f0020e6e37b528efd` | `86c9847511d504190ca7f6e7a511d3e84299809320039fad5980027d9447a621` |
| B-progress | `5a904d98f40fe28490de15401e9061bac035f15723084802754e8a2802964a01` | `4dd20be6721148c76aacbd106941df7bd2d861c550d22aba371fddca78b55709` |

Shared bindings (same as the historical set except the code commit): `spec_sha256` `9597931fcee09bc895605b65401483c9c3658da9e0bdf7c954f8669dfa8542bd`; `adapter_source_sha256` `6b4c4350f963ceece1260a7a0ca4dcc9e36f982c1ff9b1f5e8717681170a1c8c`; `generator_source_sha256` `ab7950847683a8411e906de06bf12346db9b3fc74cb302718d586399d5df4072`; `environment_lock_sha256` `38562754e7ff8c500933a48f8c497799e1ac6af0fa7602d3df312195cef9034c`. Per-case `case_sha256` is in each `result.json`.

Manifest validation (both sets): every manifest path exists under the archive root, every digest matches, no file is missing or unlisted: current set 617 checked, 0 missing, 0 mismatched, 0 unlisted; historical set 617 checked, 0 missing, 0 mismatched, 0 unlisted.

Bytes are not reproducible across fresh runs, because the unchanged production checker mints a random `check_id` per check. Behavior is deterministic and replay of saved evidence is exact. Archives and manifests are delivered as separate files and are not committed.

## 10. Issue #246 requirements and who owns them

| Requirement (paraphrased from #246) | Owner | Evidence | Status | Remaining action |
|---|---|---|---|---|
| Runnable or saved reproducible two-scenario demo | Ved (wiring/commands/replay), Edison (package) | `rule_demo.py`; four scenarios; saved traces | PASS (Ved's part) | Edison packages it |
| Normal carbon-aware case and overload/fallback-or-rejection case | Ved, Edison | A completes; B and B-fault show rejection and checked fallback | PASS | none |
| Show actual fail-closed fallback result, not a promised pass | Ved | B/B-fault: Greedy A built, checked, rejected; `BLOCKED` | PASS | none |
| A successful fallback | not required | #246 says the abstention rule "may reject Greedy A fallback too" and safe refusal is not success | NOT REQUIRED | Only Matty can change the rule; no change made |
| Exact commit and commands | Ved | Section 5, bindings, `code_commit` | PASS | none |
| Permitted synthetic input identities | Ved | Inputs section; `origin` states no private or source data | PASS | none |
| Expected and actual outputs kept separate | Ved | Separate report sections and summary fields | PASS | none |
| Explanation of verification and fallback | Ved (executable side), Nisha (verification findings) | Section 6 and 8 | PARTIAL | Nisha's independent findings |
| Tested launch instructions | Ved | Commands run and tests pass on a clean checkout | PASS on Linux; Windows not run | optional second-machine check |
| Fallback recording or screenshots "where useful" | Edison | none captured by this work | NOT VED'S RESPONSIBILITY | Edison |
| Explain fired rules and arithmetic | Ved, Matty | rules and arithmetic printed from the merged record | PASS | none |
| Scenario A: J2@0, J1 later, explained as timing preference | Ved | A: J2@0, J1@1 | PASS | none |
| Scenario B: 80 > 60 shown; injected fault labeled; feasible progress subcase separate | Ved | B, B-fault, B-progress kept separate | PASS | none |
| Independently verified evidence | Nisha (#241) | none yet; reader smoke is INCOMPLETE (exit 2) | NOT_RUN (not Ved's) | Nisha |
| Methods text and diagrams | Reimo (#243) | not part of this work | NOT VED'S RESPONSIBILITY | Reimo |
| Tag Matty and Nisha when ready | Ved/Edison | not done (no remote actions made) | PENDING | tag after the branch is pushed |
| Evaluation results where displayed (#242) | other owners | none displayed | NOT VED'S RESPONSIBILITY | none here |

## 11. Known limitations

- Scenario B and B-fault end `BLOCKED` with no execution, because the unchanged production gate refuses the partial-plan abstention and the Greedy A fallback. That is the documented, accepted outcome, not a success.
- The reader's binding validation is INCOMPLETE (exit 2): the external artifacts needed to authenticate the bindings were not supplied. This tool does not and cannot supply independent authentication. Independent verification is NOT_RUN.
- `environment_lock_sha256` is the Windows lock file hash; the run was on Linux. No second-machine or Windows evidence exists.
- Four separate things are not interchangeable: local replay (done), archive/hash integrity (done), Nisha's independent verification (not done), cross-platform validation (not done).
- Local hashes detect accidental change; they are not signatures. Run bytes differ between runs because of the checker's random `check_id`.
- Issue #246 was read through a page summary, not verbatim.
- The demo covers the authored synthetic cases only, under perfect artificial forecasts (a disclosed assumption, not accuracy evidence).

## 12. Dependencies on teammates

- **Nisha (#241):** independent verification of the merged implementation and reconstruction of bindings from supplied artifacts.
- **Edison:** presentation, storyboard, visuals, screenshots or recording of the fallback case; the required machine-readable output interface, if any. `--json` and `demo_summary.json` are offered; no format has been received.
- **Matty:** only if the team wants scenario B to execute one job: that requires a decision on the checker's joint-capacity abstention rule, which this work does not change. Also tagging and freeze.
- **Reimo (#243):** report integration; use the expected-versus-observed separation and the documented limitation as written.
