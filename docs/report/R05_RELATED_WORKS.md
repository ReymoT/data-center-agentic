# Related works (R05 draft)

Owners: Matty and Nisha. **Status: draft of section D**, about 0.5 pages. Citation keys match [the reference list](REFERENCES.md). Every description below was checked against its source on November 4, 2026.

## III. Related works

**Carbon-aware scheduling.** Moving flexible work to cleaner hours is an established idea. Wiesner et al. [Wiesner] use simulation to study how much temporal workload shifting can reduce emissions, and how time constraints, scheduling strategy and forecast accuracy affect the result. Radovanovic et al. [Radovanovic] describe a production system at Google that delays temporally flexible workloads using day-ahead capacity limits. Carbon Explorer [CarbonExplorer] studies carbon-aware datacenter design more broadly. This work optimizes schedules directly. Our question is different: whether safeguards change the quality of recommendations made by a language model.

**Learned control and simulation benchmarks.** SustainDC [SustainDC] provides environments for multi-agent reinforcement learning across workload scheduling, cooling and battery control, and we use the Arizona carbon-intensity file from its repository. LC-Opt [LC-Opt] benchmarks reinforcement learning and agentic AI for liquid cooling, using a simulation of a supercomputer's cooling system. Both show the value of testing decisions in simulation before applying them. Our simulator is far smaller and covers only job scheduling at one site, but it lets us check every decision and replay it independently.

**Grounded language-model agents.** ReAct [ReAct] interleaves reasoning with actions, and retrieval-augmented generation [RAG] conditions a model on retrieved text. AssetOpsBench [AssetOpsBench] evaluates agents on industrial asset operations and maintenance. Mandarapu and Kunkunuru [KG-Assets] argue that for such tasks the structure of the data behind an agent's tools matters more than how the agent is orchestrated, and they use a typed knowledge graph to supply it. We likewise give the agent typed facts with stable identifiers, and we give the plain LLM the same facts in flat form, so the comparison isolates grounding, checking and repair rather than access to information. Commercial assistants such as EcoStruxure Resource Advisor Copilot [ResourceAdvisor] show demand for conversational access to sustainability data, and we study how far such recommendations can be trusted.

**Safe autonomous control.** DeepMind's data-centre cooling system [DeepMind] screens actions by confidence, verifies operator-defined constraints twice, can fall back to conventional rules and always allows human override. We adopt the same principle at small scale: a model proposes, but a separate checker and controller decide what runs, and a checked heuristic is the fallback.

**Our position.** To our knowledge, these works don't provide a paired test of the same model with and without grounding, checking and repair on one scheduling task, scored for accuracy, safety and explanation faithfulness together. [Confirm this claim with a final literature search before submission.] We don't claim that our architecture is the best one: the reviewed systems motivated our design, and no experiment here compares architectures.

## Notes for assembly

- **Length.** This is slightly over the 0.5-page budget, so trim the Grounded agents paragraph first if needed.
- **The "our position" claim** is the riskiest sentence here. It rests on a small source review, not a systematic search, so keep "to our knowledge" and do the final search.
- **Corrected descriptions.** AssetOpsBench is an agent benchmark, not a knowledge graph; the typed-graph argument comes from [KG-Assets]. The public Resource Advisor material describes conversational data access, so don't say it links answers to evidence unless a source shows that.
- **Preprints.** [KG-Assets], [LC-Opt] and [AssetOpsBench] are cited as arXiv preprints. LC-Opt's arXiv page says it was submitted to NeurIPS 2025, which isn't confirmation of acceptance.
