# Agent and verification: development-evidence draft

Owner: Matty. Prepared against main
`d711d5d79960a17aaa1f3349e1d4e7dc9d580a60` for later report assembly with Nisha.
This section describes implemented mechanisms and one public development episode.
Final experimental findings, held-out results and release acceptance remain pending.

## Research question and design

We investigate whether an ontology-grounded, tool-verified agent improves accuracy,
faithfulness and safety of data-center sustainability recommendations compared with
a plain LLM. Workload scheduling at one simulated site supplies a bounded test
setting. Greedy A/B and learned decision-tree C/random-forest D are additional
scheduling references. Results must distinguish these comparisons.

The domain knowledge graph represents policy-visible jobs, constraints, forecasts
and evidence identifiers. LangGraph coordinates the agent workflow; it is separate
from that domain graph. Plain and Agent use equivalent visible facts, the same
model and matched generation settings. Private realized carbon, future arrivals,
held-out labels and reference solutions are excluded from policy inputs.

## Agent and execution method

The implemented agent retrieves context, proposes a plan and checks it. It may
make one repair. If no acceptable candidate remains, it can propose the actual
Greedy A fallback, which is checked before selection. An explanation is generated
within the same decision budget. Proposal, optional repair and explanation together
have a maximum of three model calls per decision. Completion slots spend none.

Physical feasibility checks cover identity, timing, deadlines, nonflexible work
and capacity. Evidence/claim support is distinct from physical feasibility: a
passing schedule check alone does not establish that an explanation is faithful.

The execution controller rechecks the selected plan against the latest state and
constraint snapshot before creating current-slot actions. Stale versions, changed
constraints, duplicate reservations and invalid selections are refused. Future
intentions do not become immediate actions. Immutable decision records retain
initial, repaired, fallback and executed stages, checks and call accounting.

Plain uses one combined PolicyOutput request per required decision, preserves
the original output, and has no tools, feedback, repair or fallback. Empty queues
use a deterministic zero-call path. Both systems execute through the same gate.

Independent evaluation reconstructs executed schedules and episode outcomes from
saved traces. Its replay does not call the production simulator or checker. Human
faithfulness evaluation uses independent original annotations, separate extraction
and label agreement, and a retained adjudication record. Nisha owns reliability
reporting; Matty contributes second ratings and joint adjudication.

## Observed public-development receiving

The authorized run used public EP-HAND1, one trial with seed 101, Plain first then
Agent, on accepted isolated Ollama 0.40.5 and qwen3:8b. Temperature was 0.2,
context 16,384 tokens and output ceiling 1,536 tokens. Both paths retained full
37/37 Arc/Vulkan offload and matching offline/native prompt counts. Runtime/model
identity checks passed before and after. No warmup or retry was made.

| Observation | Plain | Agent |
|---|---:|---:|
| Saved model requests | 5 | 12 |
| Decision records, including completion slots | 30 | 30 |
| Independent replay execution findings | 0 | 0 |
| Independent replay result mismatches | 0 | 0 |
| Records with repaired stage present | Not applicable | 4 |
| Records with fallback stage present | Not applicable | 4 |

Both units completed. Combined elapsed time was 320.281 seconds for 17 requests,
within authorized maxima of 6 Plain, 18 Agent and 24 combined requests, 150 seconds
per request, 480 seconds per Agent decision and 3,900 seconds total. Cleanup
confirmed the owned process exited and the isolated port was free.

Stage presence is not repair success. The four repaired stages and four fallback
stages may occur in the same records. The 23 executed Agent records include valid
no-op execution; they are not 23 job starts. Thirty traces are not thirty model
requests. Combined elapsed time includes orchestration and cannot be presented as
per-system inference latency or measured energy use.

## Interpretation and limitations

This exercise demonstrates that the implemented paths can run through the provider,
checker, controller, durable traces and independent replay on this fixture, with
repair and fallback recorded. It does not estimate an improvement over Plain.
Zero replay findings indicate consistency of recorded executions under the tested
protocol, not comprehensive safety or explanation faithfulness.

One public episode and one seed do not support statistical inference. Source
semantics, interval mapping, rights and scientific suitability remain gated by #60.
Actual trained artifacts and six-system I01 acceptance are pending. Calibration
comparison (#22), scientific freeze, full experiments, held-out annotations,
reliability repeat (#95), final reproduction and I04 acceptance remain unfinished.
Earlier timeout and zero-dispatch wrapper failures remain retained in their dated
records; this successful run does not erase them.

## Evidence and assembly handoff

- [Receiving record and private-artifact digests](handoffs/EP_HAND1_RECEIVING_F04_F05.md)
- [Run authorization](https://github.com/ReymoT/data-center-agentic/issues/18#issuecomment-6552944371)
- [Published receiving PR #140](https://github.com/ReymoT/data-center-agentic/pull/140)
- [Merged-main receiving CI](https://github.com/ReymoT/data-center-agentic/actions/runs/41270828883)
- [Source gate audit](handoffs/SOURCE_ACCEPTANCE_AUDIT.md)
- [I01 and trained receiving checklist](handoffs/I01_TRAINED_RECEIVING_CHECKLIST.md)
- [Backup demo walkthrough](R04_BACKUP_DEMO.md)

Nisha may reuse the method and bounded development observations with these limits.
Final report assembly must add the frozen experiment configuration, actual sample
counts, paired outcomes/intervals, annotation reliability and failures. Keep final
results pending until their actual artifacts are reviewed; R04 is not finally
accepted before its I04 dependency.
