# Agent and verification: development-evidence draft

November 4: [Nisha's independent content receiving is accepted](handoffs/I01_NISHA_RECEIVING_ACCEPTANCE_2026-11-04.md)
for the six original public-development units. Her unchanged report and a manager
corroboration supplement retain zero replay findings/result mismatches and all
scope limits. This resolves receiving of those existing records, not final I01,
explanation faithfulness or a unified comparative study.

Current follow-up: [development-fold metrics](../models/DEVELOPMENT_FOLD_METRICS.md)
now accompany the C/D references, and the [manager follow-up](handoffs/NOV02_MANAGER_FOLLOWUP.md)
records offline pin refresh, accepted custody safeguards and remaining unified-run
and official-information gaps. These additions are development evidence, not
another model-driven run or final study result.

Owner: Matty. Prepared against main
`227d2ebabd863d58f0a1b7bf2e56b6acdb02e1d4` for later report assembly with Nisha.
This section describes implemented mechanisms and one public development episode.
Final experimental findings, held-out results and release acceptance remain pending.
The November 4 additions below are reviewed against main
`bb9bf3ea5bdc83e9779e5c0e8c26ddb81c98ab7c`; the original preparation base above
is retained as history.

Follow-up: [the I01/P05 receiving record](handoffs/I01_LOCK_P05_PRIVATE_RECEIVING.md)
corrects the LF lock pin, connects P05 fallback to E02 and records actual C/D
public fresh/missing-forecast receiving. All four units replay without findings
or result mismatches; missing-forecast units have three checked fallback records
each. No new LLM or held-out run is implied. [Matty's contribution statement](report/MATTY_CONTRIBUTIONS.md)
is available for report assembly, with ownership and completion limits stated.

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

## Real learned-policy development receiving

Matty subsequently produced actual C/D models from all 40 verified development
episodes, with 6,046 certified rows (1,411 positive and 4,635 negative). All 15
candidate/fold cells were evaluated. Selected models were a depth-8 decision tree
and a 100-tree depth-10 random forest. Both refits were saved and reloaded;
probabilities matched over 100 rows. Seed 20261031 is the recorded development
script setting, not a newly accepted scientific seed.

On the same public EP-HAND1 bundle, A/B and the actual C/D binaries each produced
30 traces, completed two jobs and had zero independent replay findings or result
mismatches. This run used no model requests. Actual binary/source/summary hashes
and private custody are in the [P04 handoff](handoffs/P04_REAL_DEVELOPMENT_ARTIFACTS.md).

The LLM and classical receiving exercises used different run identities and code
commits. They demonstrate six implemented paths, not one frozen six-system
comparison. They provide no measured improvement, held-out estimate or final I01
approval. The [acceptance audit](handoffs/I01_ACCEPTANCE_AUDIT_2026-11-02.md)
retains that distinction. Private raw/derived contents and binaries stay out of Git.

## Interpretation and limitations

The [reviewed E03 forecast-tie diagnostic](handoffs/E03_EQUAL_WORK_COMPARISON.md#forecast-tie-rate-november-4)
is implemented independently of production policies/checks. It classifies
individual-job choices from replay and visible forecasts, before contention
between waiting jobs. Tied and distinct decisions form its denominator;
no-choice, uncovered and unverifiable decisions are separate counts. An empty
denominator is undefined. On the public Greedy B EP-HAND1 schedule, an actual
November 4 calculation reproduced nine decisions: six distinct, three no choice,
zero tied, with no uncovered or unverifiable cases. This is a fixture diagnostic,
not a study rate or evidence of carbon savings. E06 integration remains pending.

CF60-v1 is still a proposal. A flat forecast supplies no relative cleaner-hour
signal, so realized emissions differences cannot be attributed to forecast-driven
selection of cleaner hours. The shaped alternative remains unadopted; C/D
forecast compatibility, source facts and custody must be resolved before freeze.

The [new offline authorization packet](handoffs/NOV04_READINESS_AND_STATUS.md)
passed no-startup dry-run checks. It is not another inference result.

This exercise demonstrates that the implemented paths can run through the provider,
checker, controller, durable traces and independent replay on this fixture, with
repair and fallback recorded. It does not estimate an improvement over Plain.
Zero replay findings indicate consistency of recorded executions under the tested
protocol, not comprehensive safety or explanation faithfulness.

One public episode and one seed do not support statistical inference. Source
semantics, interval mapping, rights and scientific suitability remain gated by #60.
Actual trained artifacts exist; full I01 acceptance remains pending. Calibration
#22 is closed with originals preserved and prospective clarifications approved.
Scientific freeze, full experiments, held-out annotations,
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
