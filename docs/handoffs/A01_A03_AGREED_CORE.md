# A01 and A03 agreed core implementation

Owner: Matty Anderson (MattyAnd). Technical contact: Nisha; F02 contract contact: Ved.
Date: 2026-10-12. Instruction deployment: 1.9. Base: e950d02, deployment 1.8.
Branch: matty/a01-a03-agreed-core. Tasks: [A01 issue #6](https://github.com/ReymoT/data-center-agentic/issues/6), [A03 issue #7](https://github.com/ReymoT/data-center-agentic/issues/7).
Matty explicitly requested development of the agreed portions and supplied hardware.
This completes the bounded deliverables below, not either full task or a live experiment.

## A01: local transport and accounting

[OllamaProvider](../../dc_sustainability/llm/provider.py) uses standard-library HTTP
against an explicitly configured loopback server. No unselected SDK or dependency
is added. It verifies runtime, full model digest and Q4_K_M metadata before a chat
attempt, sends the accepted Q09 settings and an existing F02 JSON schema, and strictly
parses Plan, PolicyOutput or Explanation. Model output cannot approve execution,
impersonate another policy, invoke tools or label its explanation as a template.

One instance is one run ledger, shared by both systems. It serializes requests,
reserves attempts before dispatch and enforces three agent / one plain attempts per
episode/slot plus an explicit run ceiling. Changing seeds does not reset a decision
budget. There are no automatic retries, repairs, warm-ups, installs or model switches.
Completion-slot calls are blocked. Socket connect/read operations share the smaller
of the caller's monotonic decision deadline and the 120-second call target.

Attempt records retain request JSON, full/partial raw response bytes, real HTTP status
and request header when available, a separate client trace ID, UTC start, measured
latency, usage/timing or None, errors and uncertain outcomes. A failed model attempt
still consumes budget. Missing usage is not recorded as zero. No compute cost is
inferred. The internal dataclasses do not replace the shared F02 trace contract.
The caller must persist attempts before further work; durable resume and controller
trace integration remain A04/E02 work. Do not recreate the ledger to resume a run.

Deployment requires explicit pins/limits and a referenced, validated model-specific
prompt counter that includes the rendered schema and template. No production token
counter or character approximation is supplied. Test counters are synthetic only.
The agreed final agent/plain output projections, installed artifact, validated context
boundary, SDK/framework integration and measured run configuration remain pending.
No live inference or SDK compatibility is claimed. See [hardware inventory](../HARDWARE.md).

## A03: actual fixed checks, no invented approval

[check_schedule](../../dc_sustainability/verification/checker.py) consumes and
revalidates F02 1.0.0 Plan, VisibleState and ConstraintSnapshot, returning CheckResult.
It binds the plan identity and checks visible job IDs, evidence references, authority
consistency, arrival/current time, completion deadlines, nonflexible starts, episode
end and half-open occupancy of proposed and already-running work. Background IT load
is counted before PUE. Capacity comes from the supplied constraint, never the model.
The 100-to-70 kW test changes the result without code or prompt changes.

Unknown/running/completed jobs cannot be newly scheduled. Missing capacity and
inconsistent snapshots produce errors, not unlimited capacity. Missing/unresolved
carbon does not fail the capacity subcheck but cannot support impact/savings claims.
Claim arithmetic and substantive support are not certified by this core. No private
episode, oracle, simulator action or independent evaluator is imported.

Q01 completion starts and Q02/Q03 partial-infeasibility/coverage/deferral behavior
remain unresolved. Q04 freshness is explicitly skipped, not marked passed. Known
violations are reported as failures unless an input/decision error also exists.
Otherwise, successful fixed checks return an explicit Q02/Q03 error. The core never
issues an overall pass or ApprovedActions. It cannot be used as an execution gate.
This is deliberately incomplete acceptance, with real subchecks and failure results.

## Verification and receiving work

Tests use labeled synthetic F02 fixtures and independent expected outcomes. The
provider tests send real HTTP to a local test server; its scripted responses are not
Ollama inference. The checker consumes Ved's committed examples unchanged. The
canonical interface, schema implementation, shared examples and dependency locks are
preserved. New code is limited to Matty's owned modules/tests and related documentation.

```powershell
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe scripts/validate_setup.py
.venv\Scripts\python.exe -m ruff check dc_sustainability scripts tests
.venv\Scripts\python.exe -m ruff format --check dc_sustainability scripts tests
.venv\Scripts\python.exe -m compileall -q dc_sustainability scripts tests
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts/smoke_dependencies.py
git diff --check
```

Local results: 258 tests and 19 subtests passed (65 new core tests). Lint, formatting,
compilation, pip consistency, dependency smoke, setup and whitespace checks passed.
The schema Git blob remains f139266bc9638208617e23c686ac97c442757fbf and canonical
interface blob remains 41ab733816ac171fa283f75c5252c658025c124d, matching the base.
Main/CI evidence is recorded in the task Issues after publication.
On this machine, TEMP/TMP use writable workspace tmp;
the sandbox blocks loopback sockets, so the HTTP test suite requires a scoped
network-enabled execution. Ordinary GitHub CI uses only its local test server and
does not contact Ollama, download data or make model calls.

Nisha can prepare a consumer against the adapter and existing records, keeping her
evaluation validator independent. Actual L01/L02 and A02 integration still requires
agreed projections and their context/impact prerequisites. Ved's contract compatibility
and downstream consumer adoption require their own evidence. Resolve Q01-Q04 and
the remaining Q09 inputs with affected teammates before full A01/A03 acceptance.
