# R01 — Data, synthetic workloads and simulator methods

Reconstructed by Matty on November 18 from published code/handoffs, without returning work to Reimo. Component ownership remains Reimo (D01-D05, S01/S02); this text is evidence-based report prose, not a personal attestation. Active delivery: [evidence-only activation](../decisions/NOV18_EVIDENCE_ONLY_ACTIVATION.md).

## Inputs and preprocessing

The historical development input was a pinned 8,760-row 2022 AZPS generation-mix intensity proxy distributed with SustainDC. Existing D01/D06 records establish byte identity, ordered hourly UTC labels and a numerically reproduced fixed-factor weighted mean. They do not establish the original EIA export history, physical interval convention, pollutant/lifecycle boundary or applicable exact-use/redistribution terms. B1-B3 remain unresolved and B4 provisional. The EIA and software license notices are not blanket permission for the derived CSV. See [D05 evidence](../../data/D05_SOURCE_EVIDENCE.md).

Existing preprocessing parses UTF-8, timestamps and finite numeric fields against a pinned hash without inventing missing values or changing time labels. Materialization binds recorded source indices and deterministic scenario seeds. Current documentation distinguishes numerical/structural checks from physical interpretation and source acceptance. No source read, re-export, new preprocessing or dataset replacement occurs in this handoff.

## Workload generation

Jobs and site operation are simulated, not measured real-center operating logs. The [D03 generator](../../data/D03_SYNTHETIC_SCENARIOS.md) uses explicit development assumptions: integer 10-40 kW job power, 1-4-slot duration and arrivals in slots 0-17. Normal/limited/spike/impossible variants vary workload and flexibility; selected impossible work has a deadline earlier than earliest completion. The generator does not filter every capacity-infeasible episode into a feasible one. Frontier-based empirical calibration has not been established. Scenario, seed, generator/distribution version and content hashes retain provenance.

The fixed development allocation has 40 episodes in historical blocked folds 16/12/12. Public receipts and the November 15 named-file check establish retained Matty v2 copy availability/hash integrity; no private values were parsed by that check. Historical Reimo and Matty copies are distinct. Do not regenerate or claim original 1,200 saved states were recovered. Held-out metadata receiving did not create the planned 30 research episodes or 300 study outputs. Those contents stay sealed/unmaterialized under the active scope.

## Simulator and impact boundary

[SchedulingSimulator](../../dc_sustainability/simulator/core.py) advances a single simulated site in one-hour steps, with 24 start-decision slots and six completion-only slots. It reveals only arrived jobs; no new starts are allowed in slots 24-29. Nonpreemptive jobs occupy their duration and nonflexible jobs start at arrival. The standard study assumptions are 100 kW IT capacity including 40 kW background and PUE 1.2, not facility-scale measurements or proof of megawatt scalability.

The simulator accepts controller-issued ApprovedActions, not arbitrary model plans. That typed capability is not cryptographic proof of approval; the trusted caller/controller must enforce latest-state checks and serialized transitions. Forecast issuance is explicit caller input; omitted forecasts remain missing evidence, never derived silently from private actuals. Initial, repair, fallback and actual execution are separate trace stages.

[Impact accounting](../../dc_sustainability/simulator/impact.py) uses explicit units: facility energy is PUE times IT power times hours; modeled mass is energy times intensity divided by 1000. The [equal-work comparison](../handoffs/E03_EQUAL_WORK_COMPARISON.md) blocks unsupported savings where paired inputs/completed work or replay consistency fail. Missing or blocked comparisons are not zero savings. Source ambiguity prevents claiming operational CO2e, marginal emissions or causal avoided emissions.

## Evidence and limits for final report/demo

Use the retained public EP-HAND1 examples with exact run identity, earlier failures, failed repairs and checked fallback reliance. They establish exercised technical behavior only. Historical development classification and pre-adjudication human reliability remain development evidence; no held-out superiority or real-site savings follows. The original source-dependent study is unexecuted and the research question unanswered in the activated delivery scope.

Retained sources: [D04 materialization](../handoffs/D04_DEVELOPMENT_MATERIALIZATION_112.md), [Matty-copy check](../handoffs/NOV15_MATTY_COPY_AVAILABILITY.md), [source status](../handoffs/REIMO_SOURCE_EVIDENCE_STATUS_DRAFT.md), [R04](../R04_DEVELOPMENT_EVIDENCE.md). Personal contribution confirmation, final release rights, report layout and authenticated submission remain separate; their absence is not filled with invented evidence.
