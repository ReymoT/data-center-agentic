# Related works (R05 draft)

Owners: Matty and Nisha. **Status: draft of section D**, about 0.5 pages. Citation keys match [the reference list](REFERENCES.md). Nisha reports source checks on November 4, 2026; manager review checked linked abstracts/metadata and primary public posts. This is a scoped source review, not a systematic search.

## III. Related works

**Carbon-aware scheduling.** Moving flexible work to cleaner hours is an established idea. Wiesner et al. [Wiesner] use simulation to study how much temporal workload shifting can reduce emissions, and how time constraints, scheduling strategy and forecast accuracy affect the result. Radovanovic et al. [Radovanovic] describe a production system at Google that delays temporally flexible workloads using day-ahead capacity limits. Carbon Explorer [CarbonExplorer] studies carbon-aware datacenter design more broadly. This work optimizes schedules directly. Our question is different: whether safeguards change the quality of recommendations made by a language model.

**Learned control and simulation benchmarks.** SustainDC [SustainDC] provides environments for multi-agent reinforcement learning across workload scheduling, cooling and battery control, and we use the Arizona carbon-intensity file from its repository. LC-Opt [LC-Opt] benchmarks reinforcement learning and agentic AI for liquid cooling, using a simulation of a supercomputer's cooling system. Both show the value of testing decisions in simulation before applying them. Our simulator is far smaller and covers only job scheduling at one site, but it lets us check every decision and replay it independently.

**Grounded language-model agents.** ReAct [ReAct] interleaves reasoning with actions, and retrieval-augmented generation [RAG] conditions a model on retrieved text. AssetOpsBench [AssetOpsBench] evaluates agents on industrial asset operations and maintenance. Mandarapu and Kunkunuru [KG-Assets] investigate the data layer behind agent tools using a typed knowledge graph. We likewise give the agent typed facts with stable identifiers and give Plain equivalent facts in flat form. This compares the combined safeguards under matched model/facts; it does not isolate each component or remove the difference in call budgets. Schneider Electric's Resource Advisor Copilot announcement [ResourceAdvisor] illustrates conversational access to sustainability data. It does not establish citation faithfulness or measured recommendation safety.

**Safe autonomous control.** DeepMind's data-centre cooling system [DeepMind] screens actions by confidence, verifies operator-defined constraints twice, can fall back to conventional rules and always allows human override. We adopt the same principle at small scale: a model proposes, but a separate checker and controller decide what runs, and a checked heuristic is the fallback.

**Our position.** Our planned study tests one bounded scheduling setting using matched underlying LLM and visible facts, comparing the combined grounding/checking/repair workflow with Plain. Agent has a larger bounded call budget, and this comparison does not isolate the causal effect of each component. We do not claim literature-wide novelty or that our architecture is best. The reviewed systems motivate the design; the study does not compare a range of alternative agent architectures.

## Notes for assembly

- **Length.** This is slightly over the 0.5-page budget, so trim the Grounded agents paragraph first if needed.
- **Novelty.** The source review is small and not systematic. Any stronger novelty claim needs a separate supported literature search before submission.
- **Corrected descriptions.** AssetOpsBench is an agent benchmark, not a knowledge graph; the typed-graph argument comes from [KG-Assets]. The public Resource Advisor material describes conversational data access, so don't say it links answers to evidence unless a source shows that.
- **Preprints.** [KG-Assets], [LC-Opt] and [AssetOpsBench] are cited as arXiv preprints. LC-Opt's arXiv page says it was submitted to NeurIPS 2025, which isn't confirmation of acceptance.
