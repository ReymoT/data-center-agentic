# S02 receiving verification and approved issue actions

Owner: MattyAnd. Technical contacts: Nisha/Ved; S02 owners Reimo/Edison.
[Maintenance issue #50](https://github.com/ReymoT/data-center-agentic/issues/50).
Base main `4932b014945c38bdcbd9e08cdb2e5af536c02944`, instruction 1.22;
this authorized maintenance publishes instruction 1.23. Matty explicitly approved
all recommendations and the sequential receiving/diagnostic/documentation work.

## What is delivered

Reimo already merged [S02 PR #49](https://github.com/ReymoT/data-center-agentic/pull/49).
Matty did not merge it twice. Exact main CI40016727997 passed 1,122 tests and
19 subtests. Edison subsequently [accepted the exact convention and facility/IT
boundary](https://github.com/ReymoT/data-center-agentic/issues/36#issuecomment-6374656136),
reporting Windows 11/Python 3.12.10 receiving tests. His actual acceptance is received,
not inferred from the merge. S02 code, S01 behavior and P01 formulas stay unchanged.

Matty's initial S02/P01 focused run passed 35 tests on Windows/Python 3.12.14.
Nine new `tests/e2e/test_s02_receiving.py` cases exercise actual S01/S02/F02/E01:

- Real simulator starts, 30-slot accounting, independent structural replay,
  completion IDs/IT work, missing actual carbon, serialized results and hand totals.
- Completed IT work is 140 kWh; at PUE 1.2 facility job energy is 168 kWh.
  Thirty-slot site energy is 1,340 kWh times PUE; full-carbon baseline site
  emissions are 262.5 kg times PUE. Tail values are explicitly synthetic.
- Unfinished work remains in independent outcomes and earns no completion credit.
- An out-of-order slot sequence is already rejected when S02 revalidates the F02
  EpisodeResult. No redundant slot guard or schema change is needed.
- The real unresolved A03 checker cannot supply ApprovedActions or mutate S01.

Synthetic test action capabilities are not production approvals or model/policy
outputs. This is receiving evidence, not A04, A02, I01 or a complete runner. The
independent E01 replay compares structural outcomes and loads, not impact totals;
hand truth separately checks those totals. No evaluator production code is changed.
The first new checker test incorrectly used generated jobs while naming hand-fixture
J1; that test-author fixture error was corrected, not reported as a production defect.

## A01/F03 diagnostic result

Reimo reported two nested-pin assertions failing on macOS arm64/Python 3.12.15,
where the actual cause was AttributeError rather than the expected RecursionError.
Both existing tests pass here on Windows/Python 3.12.14. A controlled decoder that
accepts the nested array's outer list type reproduces both old assertion failures;
this is explicitly a test control, not a macOS rerun or successful model response.
[Retained diagnostic](../evidence/a01-pin-parser-portability-2026-10-23.json).

Production already catches both causes as CallBlocked before chat dispatch. The
existing test now accepts the actual decoder-dependent cause; its original 8,001
bytes, HTTP path, deadline, blocked status and zero chat/attempt assertions remain.
Six additional deterministic branch cases enforce exact cause identity/type, exact
metadata request sequence, zero chat, zero ledger entries and no reserved budget:
parser rejects nesting, parser accepts a non-object, and a real ordinary JSON list.
No provider, HTTP reader, payload, deadline, protocol or limit changes were made.
MacOS certification is not claimed; Reimo should rerun after safely refreshing.

Six fixed same-process body-content controls (raw socket and curl for each original
nested object, same-length ASCII and same-length shallow JSON) all received the
complete 24,001 bytes. The actual captured shared-provider request stays 3,399 bytes
with SHA25604ebdb9574c77c0b30678005bb99083b82769a245090da35423bcd7036f43e3d.
[All observations](../evidence/a01-body-controls-2026-10-23.json) retain hashes,
chunks, server write counts and timings. Single successful observations do not show
reliability, identify a content-dependent cause, erase earlier failures or fix the
known partial-body timeout. The portable next diagnostic can be run on a second
machine; no service, driver, security, socket or update setting was changed.

Reproduce only the new owned synthetic controls (fresh output filename required):

```powershell
.venv\Scripts\python.exe -m pytest tests/e2e/test_s02_receiving.py tests/llm/test_pin_parser_boundaries.py -q
.venv\Scripts\python.exe scripts/diagnose_a01_body_controls.py --out ../a-new-body-control-report.json
```

Fifteen new consumer/parser cases pass. The ordinary full local suite reports
**1,135 passed, 19 subtests passed, two existing object-response timeouts**
(agent and plain). Original deep-chat bodies, deadlines and assertions are unchanged;
this is not an all-pass local claim. The full log remains outside Git and the compact
result below retains both names. The run overlapped dependency smoke and a focused
sandboxed check; timing sensitivity is not a causal diagnosis. No repeat-until-green
full run was performed.

One sandboxed smoke/focused check was blocked by temporary-file/socket permissions.
With permitted loopback access and a workspace-local temporary directory, unchanged
smoke and six focused parser checks pass. This permission correction did not alter
provider code or test expectations. Lint/format (88 Python files), compile, pip check,
setup/versions/links/policies, and actual SHACL/SPARQL/MILP/classifier/LangGraph smoke
pass. The diagram was rendered and visually inspected. Exact PR/main CI will be
recorded in issue #50 after actual execution and cannot erase local failures.
Model calls: zero; no research counter/dependency adopted.

## Issue actions and remaining gates

[Verified Matty comment](https://github.com/ReymoT/data-center-agentic/issues/36#issuecomment-6374827280)
supports retaining the current strict unfinished-work savings guard. Edison asked
whether jobs missed on arrival should ever be exempt, since the infeasible scenario
otherwise has no reportable savings. Nisha/Reimo/Ved exact input is still needed.
No exemption, scoring change or zero-valued savings is introduced. Report blocked
comparisons, completed quantities and unfinished/missed work separately.

Each approved issue action is handled as follows:

| Issue | Actual action / remaining condition |
|---|---|
| #36 | Received Edison convention acceptance; Matty receiving tests and strict-guard recommendation. Keep open for savings/scoring question, production adoption and remaining scientific acceptance. |
| #6 | Requested only Ved's missing dependency/runtime direction; parser-assertion diagnosis delivered. Transport/counter/native equivalence/context/service/resources and separate inference authorization still gate full A01. |
| #7 | Recorded Edison exact Q04/window/conditional optionB reply. Requested only remaining Reimo/Ved detailed boundaries and joint-Q08 rules; no shared default adopted. |
| #24 | Acknowledged Edison facility/IT input. Asked Nisha for the agreed-portion PR checkpoint and Nisha/Ved for optional future tolerance agreement or explicit deferral. Current completed_work remains None. |
| #22 | Requested Nisha's exact refined temporal-window confirmation/tested selection; preserve sample, failures/no-ops and no-replacement rules. No freeze. |
| #42 | Matty first pass stays submitted unchanged; no reminder or fabricated adjudication before Nisha's October 24 checkpoint. Joint review waits for both originals. |
| #17/#18 | Updated actual S02 input/readiness; full A04/A02 remain blocked by exact decisions, usable A01/A03/P02/controller/runner and actual authorized integration. Receiving checks do not substitute for them. |
| #12 | Requested Nisha's own K02 consumer evidence; no duplicate request for older receiving checks, no unvalidated live run. |
| #13 | Asked only for missing Q05/Q06 source/freeze evidence/checkpoints, not a repeated D06 structural check. Separate Frontier access follow-up remains deferred. |
| #21 | Requested only Reimo/Ved allocation confirmations; all 50 task rows/owners/dependencies stay unchanged. |
| #16 | Received Edison platform/license/access/retention positions; requested remaining Reimo/Ved positions; await Nisha's next actual course update without repeating the unpublished-rubric question. No license/permissions/settings change. |

The nine posted named-owner comments are verified as MattyAnd; the local action
manifest retains their URLs and exact drafts. Do not claim an email was delivered.
Nisha's October 24 and Edison's October 25 checkpoints are upcoming, not overdue.
The maintenance issue can close only after actual publication/checks/handoff/branch
cleanup. None of the 12 substantive issues meets full closure criteria on this evidence.

README still begins with equal teammate roles and groups Matty/Nisha. Reviewed-system
comparison/rationale and the single research question stay intact; architecture and
its generated diagram reflect S02 without claiming an integrated experiment. All
original ratings, canonical E04, F02/interfaces, locks, prompts, pins, policies and
teammate commits/worktrees are preserved. Original source attachments are read-only.
