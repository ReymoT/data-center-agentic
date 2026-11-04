# Introduction and problem statement (R05 draft)

Owner: Nisha; Reimo co-owns the problem statement. **Status: draft.** Sections B and C of the [report outline](README.md), about 0.75 and 0.5 pages. Bracketed items wait for evidence and aren't claims. Citation keys match [the reference list](REFERENCES.md).

## I. Introduction

Data centers can run some compute work at different times, and the carbon intensity of electricity changes from hour to hour. Moving flexible work toward cleaner hours can therefore lower emissions without changing the energy the work needs. Language models are a natural interface for this kind of decision support, because they can read operating facts and explain a recommendation. But a sustainability recommendation that sounds reasonable can still be wrong. It can overload a site, miss a deadline, or claim savings that the evidence doesn't support, and fluent text gives an operator no way to tell.

Recent work points toward ways of containing that risk. Benchmarks now evaluate language-model agents on industrial operations [AssetOpsBench], and typed knowledge graphs can supply such agents with exact facts [KG-Assets]. Simulation tests decisions before they are applied [SustainDC], [LC-Opt], and constraint checks with fallbacks protect execution in autonomous cooling [DeepMind]. These systems motivated our design, but we aren't aware of work that measures how much such safeguards change an LLM's recommendations when it is compared with the same model without them.

We ask: *does an ontology-grounded, tool-verified agent improve the accuracy, faithfulness and safety of data-center sustainability recommendations compared with a plain LLM?* We study this in one bounded setting: scheduling flexible jobs at a single simulated site. Scheduling is the test setting rather than the goal, because it gives each recommendation a checkable outcome.

Both LLM systems use the same local model and receive equivalent visible facts. The agent reads them from a knowledge graph, has each plan checked, may repair it once, and falls back to a checked greedy plan. The plain LLM makes one call and its output is kept uncorrected. Two greedy heuristics, a decision tree and a random forest give classical reference points. All six systems run through the same execution gate, and an evaluator that is independent of the production checker replays what actually ran.

Our contributions are:

1. A paired six-system comparison in which the agent and the plain LLM differ in grounding, checking and repair, not in the model or the facts it sees.
2. An execution design in which no model output can run without passing a checker and a controller, with every stage and request saved.
3. An evaluation that separates schedule accuracy, safety and explanation faithfulness, using independent replay and blinded human claim review with a reported inter-rater reliability.
4. [Held-out findings, added after the frozen runs.]

Our conclusions are limited to the scenarios we evaluate. [State here whether the frozen forecast allows conclusions about carbon-aware timing; see §G.]

## II. Problem statement

**Site and jobs.** We model one site with one resource pool and hourly slots. IT capacity is 100 kW, which includes 40 kW of background load. Each job has an arrival slot, a duration of 1–4 slots, a constant power of 10–40 kW and a deadline. A job can't pause once started. Some jobs are flexible; a nonflexible job must start at its arrival slot. Jobs are provisional synthetic draws and aren't calibrated to a real job trace.

**Episodes.** An episode has 24 decision slots followed by 6 completion slots. New jobs may start only in slots 0–23, and the completion slots let running work finish. At each decision slot, a system sees only arrived jobs, running work, constraints and the forecasts visible at that time. It never sees future arrivals or realized carbon.

**Decision.** At each slot with waiting work, a system proposes a plan that starts, defers or abstains from each waiting job. Only starts for the current slot can execute, and only after the plan passes the checks against the latest state.

**Impact.** Energy per slot is PUE × IT power × one hour, and emissions are energy × carbon intensity ÷ 1,000 kg. We use a PUE of 1.2 as a design assumption. For the same completed work, timing changes emissions but not energy. Savings are therefore reported only between schedules that completed the same work under the same inputs.

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
