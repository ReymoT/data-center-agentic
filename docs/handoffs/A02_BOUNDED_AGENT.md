# A02 bounded agent core

Owner Matty; issue #18; Nisha technical contact. October 24, instruction 1.26,
F02 1.0.0. Based on real A03/A04 main 7f836be8. Matty authorized implementation;
the scope and missing real inputs were recorded in #18 before coding.

## Actual implementation

AgentHarness uses actual K02 retrieval, the shared OllamaProvider, independent
production A03 checks and the A04 controller. Its compiled LangGraph has a bounded
path: retrieve, propose, verify, at most one repair/verify, optional real checked-A
fallback/verify, explanation, and controller recheck/execution/trace. The graph
has no retry loop and a 16-step defensive limit. External LangSmith tracing is
disabled for this invocation; no monitoring service or checkpoint store is added.
Implementation uses the installed LangGraph 1.2.14 and its
[documented graph API](https://docs.langchain.com/oss/python/langgraph/graph-api).

The provider's actual ledger supplies spent/failed/uncertain call counts. Repairs
do not reset it; explanation is included in the three-attempt ceiling. Empty and
completion slots make zero model calls. Run/trial/seed identity is fixed within
one harness/provider. Duplicate decisions refuse new calls/steps. Unknown usage
remains None. Failed counting/runtime checks remain pre-dispatch failures.

Original HTTP response bytes and request/usage/pin metadata are saved exclusively
as lossless internal provider-attempt artifacts, linked to actual run, decision
and stage. F02 DecisionRecord remains unchanged. Conflicting artifact replacement
fails. A persistence failure withholds execution rather than losing evidence and
continuing as if successful. Selected plan/stage checks and initial/repair/fallback
records remain separate. A typed Explanation cannot replace the selected action.
Explanation rendering is provisional before the controller's final recheck; it
must not assert execution that has not happened. Actual execution/refusal is saved
by the controller. Full elapsed time is returned separately; no partial timing is
invented as total F02 decision latency.

## Explicit inputs and incomplete acceptance

The caller supplies Nisha's reviewed proposal, repair and explanation renderers,
Edison's actual P02 callable, an accepted provider/counter/runtime, authoritative
state/constraints, explicit IDs/trial/seed/deadline and the controller/trace store.
Renderers see only projected context and relevant stage evidence, not the full
snapshot, private episode, future arrivals or reference answers. P02 must return
actual greedy_a PolicyOutput with a proposed plan, then undergo the real checker.

These prompt/P02 inputs are not implemented by substitutes here. Missing renderers,
unavailable P02, retrieval/tool errors and expired deadlines are recorded explicitly.
Any test-only fallback/renderers/counter are labeled fixtures and are not imported
as production defaults. No new prompt decision, validated tokenizer, runtime pin,
source semantics, scoring rule or model-generated development episode is claimed.
Nisha still owns runner/CLI, experiment checkpoint/resume, sampling and independent
evaluation. The controller is the simulator's sole writer; a saved trace does not
restore an experiment. Full #18 acceptance remains open for actual P02/L02/runtime
receiving and the separately authorized real model-driven development episode.

## Actual tests

122 focused agent/runtime/verification tests pass in 3.41s. They use real loopback
HTTP, retrieval, checker, controller and filesystem traces with labeled synthetic
inputs; there is no approving checker/provider stub. They cover successful repair,
failed repair, explicitly test-only checked fallback, third explanation call,
malformed bytes, HTTP failure, pre-dispatch/runtime/run-cap failures, explanation
action injection, immutable raw evidence, missing inputs, run identity and all
30 zero-call slots. These are offline integration tests, not inference results.

One ordinary full local suite retains 1,190 passes, 19 passing subtests and two
existing A01 object-agent/object-plain timeouts in 30.56s. No rerun hides them and
no timeout fix is inferred. Lint/format (99 Python files), setup/links/policies,
compile and whitespace pass. Exact hosted PR/main checks, publication and cleanup
are recorded in #18 after execution. No model or external tracing call occurred.
