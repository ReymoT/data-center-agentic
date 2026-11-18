# R02 — Ontology, retrieval and reference methods

Owner: Ved Patil (`vedp3705`). Matty repaired the empty file merged by #234 through a separate factual handoff review against main `6ae3018355ad5fb778e30365bf23b23ec424c5e6`.
Status: methods and retained development evidence for #223. This is not an O04 held-out reference, completed I03 reproduction, source acceptance or scientific freeze. This reconstructed prose is based on implemented code and published handoffs; it is not an invented personal attestation by Ved.

## Ontology and policy-visible graph (K01/K02)

The project vocabulary and shapes are versioned in [ontology](../../ontology/README.md). The [ontology helpers](../../dc_sustainability/knowledge/ontology.py) load RDF/SHACL resources offline, map supported F02 unit codes to explicit semantic identifiers and return structured graph-validation reports. Mapping a unit code does not convert values or establish the source's pollutant basis. Brick, PROV and QUDT terms supply semantic references; this is not a claim of complete external-ontology conformance or source validation.

[Graph construction](../../dc_sustainability/knowledge/graph.py) builds RDF from policy-visible state/context records. [Controlled retrieval](../../dc_sustainability/knowledge/retrieval.py) queries waiting and running jobs, forecasts, applicable constraints, site facts and missing carbon slots through fixed SPARQL queries. Private future arrivals, realized future carbon and offline reference artifacts do not enter policy views. There is no arbitrary query access to a hidden full episode.

`get_context` produces graph and flat F02 representations with equivalent canonical content hashes for matching input state/snapshot. The Agent receives graph-grounded context and Plain equivalent flat facts. This preserves the matched-information design; it does not prove equivalence of model attention, cost or every possible retrieval route. The authoritative production checker/controller consume the F02 inputs. SHACL graph validation and graph-driven validation are separate mechanisms, not substitutes for latest-state execution checks. See [interfaces](../INTERFACES.md) and [architecture](../ARCHITECTURE.md).

## Visible-state reference formulation (O01/O02)

The [visible-state solver](../../dc_sustainability/reference/solver.py) uses `scipy.optimize.milp` with binary variables for feasible arrived-job/start-slot pairs. Each arrived waiting job must start exactly once, within its arrival/deadline/start window; nonflexible jobs start at arrival. Per-slot capacity includes background, running work and proposed starts. The objective sums job power times slot duration times PUE times forecast intensity divided by 1000. This is modeled carbon-proxy arithmetic, not established real-site CO2e or causal avoided emissions while #60 source semantics remain unresolved.

Explicit statuses distinguish `certified_optimal`, `certified_infeasible`, `unresolved` and `insufficient_evidence`. Missing/stale forecasts or missing capacity cannot be treated as proof of physical infeasibility. Certification is conditional on the encoded problem, trusted supplied time and solver/backend settings; it does not establish the input source's scientific validity or deployment safety. A visible reference does not use future arrivals.

Stable candidate ordering is implemented. A scientific secondary tie optimization or a unique optimal schedule is not established. The manager [reference review](../handoffs/VED_REFERENCE_MANAGER_REVIEW.md) rejected a proposed secondary optimization that could tolerate a more expensive schedule. Preserve the recorded gap/bound/tolerance/status evidence and unresolved tie/matching decisions rather than calling backend selection a proved lexical optimum.

## Labels, cache and hindsight boundaries

[Development labels](../../dc_sustainability/reference/labels.py) attach definite positives/negatives only to certified optimal visible-state results. A positive means membership in the one returned schedule, not membership in every optimal solution. Other statuses remain unavailable/excluded. The [cache](../../dc_sustainability/reference/cache.py) binds complete state/context/candidate/configuration and trusted-time identity, detects content corruption and refuses incompatible result kinds. Cached labels are not policy-visible oracle information.

The retained [legacy-label audit](../handoffs/LEGACY_LABEL_AUDIT_2026-11-04.md) matched all 6,046 saved development labels to 570 cached results: 1,411 positive and 4,635 negative across 40 episodes. Original excluded-candidate counts and alternate global-optimum multiplicity are unavailable. Flat persistence forecasts make carbon features constant within each job-decision; this does not prove that all candidate choices are jointly feasible optima. No cache, model or source file was reopened for this documentation repair.

[Hindsight infrastructure](../../dc_sustainability/reference/hindsight.py) is offline-only and uses private realized information under a distinct artifact boundary. Its [handoff and manager corrections](../handoffs/O03_HINDSIGHT_EXPORT.md) retain explicit matching-work IDs, actual timing, immutable artifact identities and separate export/manifest files. It is not interchangeable with a visible-state label source or final held-out reference. Windows private-directory ACLs are a caller prerequisite; POSIX chmod is not proof of Windows custody.

## Contributions and pending acceptance

Retained responsibility/code records attribute F02 contracts, ontology/graph/retrieval and validation work, visible-state reference/label/cache methods and offline hindsight infrastructure to Ved (F02, K01-K03, O01-O03). Original teammate work and later manager integration corrections remain distinguishable; see the [responsibility checklist](../team/03_RESPONSIBILITY_CHECKLIST.md) and [manager review](../handoffs/VED_REFERENCE_MANAGER_REVIEW.md). This supplies evidence-based R02 prose, not sole-authorship or final-task certification.

O04 held-out labels follow accepted I02 and frozen inference; final I03 reproduction follows accepted final evaluation artifacts. Development infrastructure, passing tests and this handoff do not complete those tasks. Source B1-B3 remain unresolved and B4 provisional; exact permitted inputs, operational custody, compatibility, shared-protocol acceptance and fresh execution approval remain separate. No new solver/model/training/source/held-out operation or private artifact publication is authorized by this document.
