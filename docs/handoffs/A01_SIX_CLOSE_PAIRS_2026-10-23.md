# A01: six fixed close-timing pairs and current status refresh

Owner MattyAnd; [issue #6](https://github.com/ReymoT/data-center-agentic/issues/6).
Matty explicitly approved A01 first, then the small documentation refresh, followed
by E05/P02 review when the actual deliverables arrive. Base main
f6d786f2c222c69d3aeaaa35ca70881255a5c077; instruction 1.23 unchanged.
[The exact schedule was posted before measurement](https://github.com/ReymoT/data-center-agentic/issues/6#issuecomment-6377389187).

## Fixed plan and actual results

One original Python fixture/shared-provider reference capture was followed by six
native raw-socket pairs. The declared order was AB, BA, AB, BA, AB, BA, where
A is original close and B waits for client closure. Every native observation used
the same captured HTTP response, request body and already recorded native binary.
All comparisons ran serially, once, before ordinary tests, using the existing
ten-second raw-client deadline. There were no retries, substitutions, outcome-based
stops, extra pairs or run-until-green behavior.

| Pair | Declared order | Original close | Wait for client close |
|---|---|---|---|
| 1 | A then B | 23,360 bytes; timeout | 24,001 bytes; complete |
| 2 | B then A | 23,360 bytes; timeout | 24,001 bytes; complete |
| 3 | A then B | 23,360 bytes; timeout | 24,001 bytes; complete |
| 4 | B then A | 23,360 bytes; timeout | 24,001 bytes; complete |
| 5 | A then B | 23,360 bytes; timeout | 24,001 bytes; complete |
| 6 | B then A | 24,001 bytes; complete | 24,001 bytes; complete |

Thus original close failed in five of six observations and completed in one;
wait-for-client completed in six of six. The separate actual shared-provider
reference capture also timed out at 23,360 bytes and retained one uncertain synthetic
attempt. Count it separately, not as a seventh member of either native condition.
All 13 observations are retained. The native counts are diagnostic observations,
not new unit tests, model runs or independent scientific evaluation results.

[The full report](../evidence/a01-six-close-pairs-2026-10-23.json) retains the declared
schedule, pair/order, chunks, timings, errors, exact source/binary/request/wire/body
identities and reference headers. It permits reconstruction of the actual reference
wire from those headers and the source-defined synthetic body. Every native server
reported writing all 116 header and 24,001 body bytes. Each truncated response has
the same 23,360-byte prefix SHA256 as the older failures:
`d7adfc98bfb8099b9c6fd63d51e7220c9cf633bffcbac3a603c61e34e86697b6`.
The native binary matches the earlier PR52 measurement, not a newly chosen server.

The result supports a repeatable close-timing association on this machine, rather
than relying only on one favorable pair. It does not establish the precise OS,
driver, filtering, buffering or protocol cause, a reliability rate or a production
fix. The original-close completion in pair 6 stays in the result. The sample is
small, single-machine and deterministically order-balanced, not randomized. Each
condition uses a fresh connection/process and different ephemeral request port.
Instrumentation and host state remain limitations. Full writes mean the write
returned; they do not prove client delivery.

No close wait, socket setting, protocol, read size, payload, deadline, retry or
trimming change is adopted in the provider or original test fixture. All existing
production code, original tests, runtime/artifact pins, prompts, locks, budgets,
shared schemas, scientific choices, original ratings and instructions stay unchanged.
The actual shared-provider observation uses the existing explicitly synthetic HTTP
fixture/counter; it is not a validated counter or real model response. Model calls: 0.

## Reproduction and checks

```powershell
.venv\Scripts\python.exe scripts/compare_a01_close_modes.py --native-server '<explicit-local-native-reference>' --out ../new-six-pair-report.json
```

The native reference is the already available optional helper from
[the PR52 handoff](A01_WIRE_LIFECYCLE_2026-10-23.md). Compiler/binary remain isolated
outside Git, and no Go/application dependency is introduced. Use a fresh report path;
the runner refuses overwriting existing observations. Any execution error retains
completed rows and marks the report incomplete rather than retrying. Source hashes
are LF canonical; wire/body/binary hashes use raw bytes. Full local/hosted checks
include a single serial ordinary suite: **1,136 passed, 19 subtests passed and one
existing object-plain_llm timeout** in18.35s. No repeat-until-green full run is done.
The failure and ordinary log are retained; no payload/deadline/reader/assertion was
changed to hide it. Ruff lint/format (90 Python files), compile, pip consistency,
setup/versions/links/policies and whitespace checks pass. Exact PR/main CI will be
recorded in issue6 after actual execution and cannot cancel diagnostic failures.

## Small documentation refresh

Only the current A01 row in [coordination](../COORDINATION.md), its runtime-agreement
wording and the latest A01/runtime paragraphs in [the plan](../PROJECT_PLAN.md) are
refreshed. They previously presented 1057/19 plus one timeout and the older 1022-test
resume as current. The refresh links actual PR52 and this fixed comparison, keeps
runtime 0.40.5 accepted and 0.40.9 only as the dated October 22 observation, and records
Nisha's already received input separately from Ved's outstanding agreement. Earlier
dated evidence stays historical; no instruction deployment, task assignment or rule
change is needed. All 50 task records and exact seven-file policies are preserved.

## E05/P02 and other pending issues

At the start, GitHub had no new owner replies or open PRs. Matty's E05 original
remains submitted; Nisha's October 24 original checkpoint and Edison's October 25 P02
checkpoint were upcoming. Check again before publication/handoff. Review the actual
deliverables if supplied; do not invent ratings, adjudication, fallback code, a live
model episode or acceptance while they are missing. No duplicate reminders are sent.

Exact Reimo/Ved Q01-Q04/Q08, Ved counter/current-runtime, Nisha Q10/E01/receiving,
source/freeze and remaining allocation/platform inputs stay pending. S02's strict
unfinished-work savings guard stays unchanged. Actual runtime/tokenizer/native/
template/effective-setting/context/service/resource validation and separately
approved bounded inference still gate full A01. A03/A04/A02, integration and
scientific evaluation are not completed by this diagnostic. Keep issue6 and other
unfinished substantive issues open until their actual acceptance evidence exists.
