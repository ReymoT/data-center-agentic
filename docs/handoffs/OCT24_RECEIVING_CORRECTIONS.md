# October 24 receiving corrections and A01 investigation

Later status: [October25 delivery/runtime handoff](OCT25_P02A_AND_RUNTIME.md) supersedes missing-P02/latest-runtime/date-only E05 statements below. Preserve this dated record as history.

Owner MattyAnd. Matty approved all recommendations from the latest issue review,
including closing #21. Starting main was
679475027bf3b8f0ee025869fcd7ffff4bc36b43; instruction 1.27 and F02 1.0.0 remain
unchanged. This is a factual F04/F05 update and bounded A01/receiving verification,
not a new instruction deployment, experimental result or transfer of coding work.

## Received replies and issue actions

Reimo already supplied his full allocation confirmation, beyond source-bundle
ownership, in [reply6390308837](https://github.com/ReymoT/data-center-agentic/issues/21#issuecomment-6390308837).
All five confirmations are now recorded. Matty closed #21 for that confirmation
scope only, with [the closure handoff](https://github.com/ReymoT/data-center-agentic/issues/21#issuecomment-6392579498).
All 50 task rows, primary owners and technical contacts remain unchanged. This
does not establish completion of their implementation tasks or grant permissions.

Ved already supplied his affected reference-comparison agreement in
[reply6390310320](https://github.com/ReymoT/data-center-agentic/issues/61#issuecomment-6390310320),
before the original response deadline. Reimo's conditional agreement was also
received. The previous summaries saying these two replies were missing were wrong.
Matty corrected both issue bodies, preserving the previous bodies as historical,
and [tagged Nisha and the affected team](https://github.com/ReymoT/data-center-agentic/issues/61#issuecomment-6392579835).

Nisha can implement the agreed E03 comparison and independent tests: matching
completed/unfinished/missed sets, equivalent inputs and pairing, no executed
occupancy by unfinished jobs according to independent replay, and required actual
carbon present. Failed conditions are blocked/unavailable with reasons and counts,
never zero savings. #61 remains open for actual implementation/receiving. The
strict S02 helper and P01 calculations are unchanged; they were not authorized
for modification by this agreement.

## A01: one current full-suite investigation

[The fixed plan](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6392588774)
was posted before measurement. It runs the unchanged full offline test directory
once with pytest's four-second faulthandler watchdog and post-failure-only frame
capture. The watchdog dumps stacks without stopping the test or changing its
deadline. No socket wrappers, body/protocol changes, payload changes, retries,
runtime adoption or model calls were introduced.

The first attempt was obstructed by the restricted sandbox: 64 failed, 1,108
passed, 53 setup errors and 19 passing subtests in 22.83 seconds. Actual exceptions
include temporary-directory access denial and WinError 10013 on loopback HTTP.
This attempt and its full log are retained; it is not a valid reproduction of the
earlier partial-response timeout and is not hidden as a test success.

A separate host-permitted run, required to exercise local HTTP and normal temporary
files, passed **1,225 tests and 19 subtests in 12.92 seconds**, Python 3.12.14,
Windows 11 build 26300. No failing frame or stalled-stack dump was captured. It is
not a root cause, fix, counter validation, inference or experimental acceptance.
The earlier ordinary-suite object-agent/plain timeouts remain unresolved. No
production workaround or extra diagnostic feature was published from this pass.

The host report and original sandbox report/log are retained outside Git as
`output/oct24-approved-host-full-suite.json/.log` and
`output/oct24-approved-original-full-suite.json/.log` in Matty's workspace. The
one-off capture script is also retained there. These are local artifacts, not
download links or production commands. The equivalent existing test selection
and watchdog can be run from the repository with:

```powershell
.venv\Scripts\python.exe -m pytest tests -q -o faulthandler_timeout=4
```

The original run additionally used post-failure capture; instrumentation may
affect timing. It does not replace an ordinary-suite observation or peer evidence.
No repeat-until-green run was used; the second attempt specifically removed the
documented sandbox obstruction, with its own output rather than overwriting it.

Normalized source SHA256 values match before/after and the earlier capture:

| Source | LF-normalized SHA256 |
|---|---|
| dc_sustainability/llm/provider.py | 131b09abdd292fa1210214d7902132d8953bb347a78093d8d1d6062d42d36fa3 |
| tests/llm/test_ollama_provider.py | e24ae0ef414e73d556ecc38f30c86f1716d87d8e83960e627edd03f8ba9e2c54 |
| tests/contracts/fixtures.py | ab1f0793ea418482e17796ddb2cc8f1b032888781e050551666e14e3f9250039 |
| dc_sustainability/schemas.py | a3ebde01f7e3930a3c14ad0795eac28204d084ef3866171982af8a5da6d2591d |
| requirements/requirements-windows-py312.lock.txt | 38562754e7ff8c500933a48f8c497799e1ac6af0fa7602d3df312195cef9034c |

Next A01 evidence remains an exact-source/environment peer comparison and a
captured actual failure supporting a regression/fix, or a precise technical
blocker. Accepted runtime 0.40.5 remains unchanged; the dated 0.40.10 observation
does not authorize adoption. Actual tokenizer/native-count/effective-setting,
context/service/resource validation and separate bounded inference authorization
remain necessary. No passing control erases these gates.

## Available integration and new knowledge defects

The actual full-suite pass includes existing agent/runtime/knowledge/plain/S02
receiving tests. They connect real retrieval, HTTP transport, production checking,
controller execution/refusal and immutable files on labeled synthetic inputs.
They cover actual plan execution, repair routing, lossless attempt evidence,
capacity recheck, 30-slot controller draining, equivalent flat context and S02
impact receiving. Synthetic HTTP/counter/renderers/fallback remain test fixtures;
they are not a real model, reviewed L02 prompts or Edison's production P02.

- K01 PR #69 is merged. Matty independently reproduced completed-job SHACL
  rejection and acceptance of ambiguous raw RDF capacity evidence. Canonical unit
  mappings also need independent vocabulary verification. Ved owns corrections
  in [#71](https://github.com/ReymoT/data-center-agentic/issues/71), with
  [actual receiving findings](https://github.com/ReymoT/data-center-agentic/issues/71#issuecomment-6392389132).
  Do not fabricate missing completed-job fields or request a new capacity vote
  for an existing F02 invariant.
- K03 PR #73 is already merged. Its checker test passes the original snapshot
  rather than consuming the retrieved graph constraint. [#72](https://github.com/ReymoT/data-center-agentic/issues/72)
  stays open for Ved's real validated graph-to-typed-record-to-checker test, with
  [the receiving finding](https://github.com/ReymoT/data-center-agentic/issues/72#issuecomment-6392389405).
  A changed RDF literal cannot silently override authoritative F02 identity and
  provenance. Passing current CI does not close this proof gap.
- S01 PR #64 is still draft/unmerged at 3bb48b6. Matty's original five fixes and
  current-main receiving conflict are resolved. Nisha's independent infeasible
  replay remains failing; Ved's independent reproduction is requested. Preserve
  the branch until actual correction, passing checks and verified merge.

## Next owner actions

| Owner/task | Actual next deliverable |
|---|---|
| Matty A01 | Failure-led transport investigation and exact-source environment comparison; runtime/counter/run gates remain |
| Matty A02/A03/A04, I01 receiving | Consume available real components; review actual L02/P02/runner and knowledge fixes as delivered. Full six-system integration is not ready |
| Nisha E01, #24/#7 | Small independent Option B replay correction first; broader agreed evaluator PR October 27 |
| Nisha E03, #61 | Implement/test the now-agreed comparison; no repeated request for Ved/Reimo agreement |
| Nisha L02/E02, #18 | Reviewed renderers and actual runner integration against published core APIs |
| Nisha Q10, #22 | Exact Option B impossible-arrival eligibility proposal before freeze; synthetic selection checkpoint October 30 |
| Nisha/Matty E05, #42 | Receive Nisha's unchanged original/hash, then extraction/label comparison and separate human adjudication. Matty original remains unchanged; October 24 is date-only |
| Edison P02, #59 | Actual A/reusable fallback first, then B and receiving; recorded October 25 checkpoint, date-only |
| Ved K01/K03, #71/#72 | Correct validation and actual graph-to-checker proof with regressions; Matty reviews receiving, not task takeover |
| Reimo/Ved D05/D06, #60/#13 | Missing source/regeneration/freeze evidence and independent applicability findings; no repeated structural/window verification |
| Nisha/Edison Q08, #7 | Exact response to Ved's feasibility-certificate boundary; preserve original response clock and distinct policy objectives |
| Reimo/Ved Q13, #16 | Remaining release/platform/license/access/retention positions; Nisha posts actual official course requirements when available |

Original response clocks and date-only commitments remain unchanged. No renewed
agreement deadline is needed for #21/#61. No official course requirement, source
permission, scientific freeze, absent delivery, human adjudication or continuous
monitor is invented. Full project issues remain open unless their own acceptance
evidence is complete; #21 alone was ready for the approved closure.

README still starts with equally formatted teammates and groups Matty/Nisha.
README/architecture retain the reviewed systems, similarities, selection method
and bounded design rationale. This update changes factual summaries only; original
ratings, schemas, locks, prompts, provider/tests and all other implementation files
remain unchanged. Applicable publication checks and resulting exact PR/main CI
are recorded in the issue after they actually run.

Local publication checks pass: setup validates 50 task rows, matching role
inventories, acyclic dependencies, local links, versions, README preferences and
the exact seven-file policies. Ruff lint and formatting pass for 102 Python files;
compileall, pip check and whitespace checks pass. Raw SHA256 comparison preserves
294 other tracked files, including all implementation, tests and dependency locks.
Matty's original E05 file still hashes to
3b3e0c7509b9bb7c3580f9586260db7c1a9e4356fe570e04fe09a6640e46f16a.
The earlier check caught a misplaced changelog paragraph; its required deployment
header was restored and setup passed without changing the validator or version.
