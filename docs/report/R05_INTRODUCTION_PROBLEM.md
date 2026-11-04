# Introduction and problem statement (R05 draft)

Owner: Nisha; Reimo co-owns the problem statement. **Status: draft.** Sections B and C of the [report outline](README.md), about 0.75 and 0.5 pages. Bracketed items wait for evidence and aren't claims. Citation keys match [the source review](../SOURCE_REVIEW.md); full references are pending.

## I. Introduction

Flexible compute work can be scheduled at different times. In our fixed-power, fixed-PUE simulation, moving the same work to a slot with lower carbon intensity can reduce modeled emissions without changing that work's energy. Language models offer an interface for reading operating facts and explaining recommendations. But a sustainability recommendation that sounds reasonable can still overload a site, miss a deadline, or claim savings that the evidence does not support. Fluency alone does not establish correctness.

The source review identifies ideas that motivate our architecture: typed relationships and retrieval [AssetOpsBench], simulation before application [LC-Opt], checks and fallbacks [DeepMind], and evidence-linked sustainability decision support [Resource Advisor]. We use these ideas to design a controlled comparison with the same underlying LLM. This review motivates design choices; it is not an audit of deployed systems or evidence of our agent's superiority.

We ask: *does an ontology-grounded, tool-verified agent improve the accuracy, faithfulness and safety of data-center sustainability recommendations compared with a plain LLM?* We study this in one bounded setting: scheduling flexible jobs at a single simulated site. Scheduling is the test setting rather than the goal, because it gives each recommendation a checkable outcome.

Both LLM systems use the same local model and receive equivalent visible facts. The agent reads them from a knowledge graph, has each plan checked, may repair it once, and may use a checked greedy fallback or abstain. The plain LLM makes one call per required decision and its output is kept uncorrected; deterministic empty-queue no-ops make no call. Two greedy heuristics, a decision tree and a random forest give classical reference points. All six systems use the same execution gate, and an evaluator implemented separately from the production checker replays saved executions. These paths have development receiving evidence; the frozen comparative study is not complete.

Our implemented infrastructure and planned study provide:

1. A design for a paired six-system comparison in which the agent and the plain LLM differ in grounding, checking and repair, with matched underlying model and visible facts. The agent may use more calls within its recorded budget.
2. An execution design in which no model output can run without passing a checker and a controller, with every stage and request saved.
3. Evaluation tooling that separates schedule accuracy, safety and explanation faithfulness, with independent replay and retained development annotation/reliability records. Frozen held-out review and its reliability report remain pending.
4. [Held-out findings, added after the frozen runs.]

Our conclusions are limited to the scenarios we evaluate. [State here whether the frozen forecast allows conclusions about carbon-aware timing; see §G.]

## II. Problem statement

**Site and jobs.** We model one site with one resource pool and hourly slots. IT capacity is 100 kW, which includes 40 kW of background load. Each job has an arrival slot, a duration of 1–4 slots, a constant power of 10–40 kW and a deadline. A job can't pause once started. Some jobs are flexible; a nonflexible job must start at its arrival slot. Jobs are provisional synthetic draws and aren't calibrated to a real job trace.

**Episodes.** An episode has 24 decision slots followed by 6 completion slots. New jobs may start only in slots 0–23, and the completion slots let running work finish. At each decision slot, a system sees only arrived jobs, running work, constraints and the forecasts visible at that time. It never sees future arrivals or realized carbon.

**Decision.** At each slot with waiting work, a system proposes a plan that starts, defers or abstains from each waiting job. Only starts for the current slot can execute, and only after the plan passes the checks against the latest state.

**Impact.** Energy per slot is PUE × IT power × one hour. With energy in kWh and carbon intensity in g/kWh, modeled emissions in kg are energy × carbon intensity ÷ 1,000. We use PUE 1.2 as a design assumption. Under these fixed-power/PUE assumptions, timing can change emissions for the same completed work without changing its energy. Savings are reported only between schedules that completed the same work under the same inputs, and remain development proxy arithmetic until source acceptance.

**Feasible schedules.** A schedule must respect arrivals, deadlines, the nonflexible rule, the 100 kW capacity limit in every slot and the start window. Each waiting job must be started, deferred or abstained from. Abstention is credited only when a job is verifiably infeasible or required evidence is unavailable.

**Scenarios.** Episodes come from four scenarios: normal, limited flexibility, an arrival spike and one with an intentionally impossible job. A further variant withholds forecasts from a normal episode.

**Objectives.** We measure three things. *Accuracy* covers valid decisions, completed work, deadline misses and emissions against reference schedules. *Safety* covers rule-breaking proposals, abstention and reliance on fallback. *Faithfulness* is whether explanations are supported by the evidence. These are reported separately, because a safe schedule can have an unfaithful explanation.

## Notes for assembly

- **Numbers.** Site, job, episode and impact values come from [the shared rules](../team/01_SHARED_RULES.md) and `dc_sustainability/data/scenarios.py`.
- **Motivation.** No statistics on data-center energy or emissions are stated yet, because none has a verified source in the repository. Add one only with a citation.
- **Forecast sentence.** Update the bracket at the end of §I once the study forecast is decided (#60, #168).
- **Carbon wording.** Pollutant basis and interval meaning remain open in #60, so this draft says "carbon intensity" and doesn't claim verified CO2e or site-specific emissions.
- **Frontier.** The job table was proposed for calibration but never acquired or accepted (D02), so it isn't cited as a data source.
- **"Independent."** The evaluator is separate from the production checker, but it isn't an outside review, so don't say more than that.
