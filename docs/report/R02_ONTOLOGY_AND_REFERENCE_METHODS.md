# R02 — Ontology, retrieval and reference methods

Owner: Ved Patil. Report material for #223, reviewed against main
`e503c21bee8494fb1684eaf630a8d94145e724e4`. Ved's full technical investigation is
[preserved separately](R02_TECHNICAL_AUDIT_NOV18.md), including its stated local
observations and limitations. This concise section describes implemented methods;
it is not final report acceptance, a new research result or personal attestation
of tests the reviewer did not run.

## Typed knowledge and visible context

The [ontology resources](../../ontology/README.md),
[ontology helpers](../../dc_sustainability/knowledge/ontology.py) and
[graph builder](../../dc_sustainability/knowledge/graph.py) represent policy-visible
jobs, site facts, forecasts and constraints using project vocabulary with selected
Brick, PROV and QUDT references. SHACL validates graph structure in the development
checks. This is partial semantic alignment, not complete external-ontology
conformance, numerical source validation or a runtime plan-verification gate.

[Retrieval](../../dc_sustainability/knowledge/retrieval.py) builds the visible graph,
runs fixed SPARQL queries and separately constructs the canonical F02 Context from
state/snapshot records. Query results support inspection/testing; they are not
silently substituted for that Context. Graph and flat presentations preserve the
same canonical facts. Do not claim that a different presentation changes factual
content or that the current policy decisions are derived from SPARQL results.
Unknown future arrivals, private realized future values and offline references
must remain outside policy inputs. That design boundary still needs actual
end-to-end evidence for any empirical comparison.

## Independent layers of validation

Pydantic record validation, SHACL graph validation, the deterministic
[production checker](../../dc_sustainability/verification/checker.py), latest-state
execution recheck and simulator guards perform different jobs. The runtime checker
uses shared constraints for timing, job status, forecast coverage and per-slot
joint capacity; a missing authoritative capacity is not unlimited capacity. The
simulator re-enforces physical execution rules. SHACL does not certify schedules,
and passing a production check is not the independent evaluation verdict.

## Visible reference optimization and development labels

The [visible-state MILP](../../dc_sustainability/reference/solver.py) schedules arrived
waiting jobs over legal starts, respecting occupied slots and capacity. Its legacy
objective is weighted modeled impact, conditional on supplied forecasts, slot
length and PUE. Without established source semantics this is not measured real-site
emissions or causal avoided carbon. Statuses distinguish certified optimal,
certified infeasible, unresolved and insufficient evidence. Missing/stale forecasts
and timeouts must not be relabeled as physical infeasibility.

Stable candidate order does not establish a unique global optimum or a scientific
secondary tie-break. The [reference review](../handoffs/VED_REFERENCE_MANAGER_REVIEW.md)
records the limitations. [Labels](../../dc_sustainability/reference/labels.py) encode
membership in one certified returned schedule, not membership in every optimum.
The [cache](../../dc_sustainability/reference/cache.py) binds context, candidates,
trusted time and configuration; cached reference information is not policy input.

The retained [development-label audit](../handoffs/LEGACY_LABEL_AUDIT_2026-11-04.md)
records 6,046 labels associated with 570 cached results: 1,411 positives and 4,635
negatives across 40 development episodes. These are historical published audit
counts, not new runs or held-out findings; alternate-optimum multiplicity and
excluded-candidate totals are not established. The
[hindsight exporter](../../dc_sustainability/reference/hindsight.py) uses a distinct
offline artifact boundary and cannot be substituted into visible-state context.
No restricted artifact was opened for this prose review.

## Current focused-study scope and limitations

The [accepted specification](../decisions/NOV20_RULE01_SPECIFICATION_ACCEPTANCE.md)
uses independently authored artificial inputs, explicit rules and separate bounded
safety/progress checking. The legacy MILP, ontology prototype and historical
Agent/Plain evidence remain methods/background, not results of that new study.
RULE-02 implementation is under separate review in PR #257; independent verifier,
case and accounting checker implementations are available, but their fixture tests
are not frozen-scheduler verification or unseen generalization evidence.

The original Agent-versus-Plain held-out question remains unanswered. O04 held-out
references, original source permissions/semantics, final reproduction and actual
new-study results are not supplied by this section. Report artificial score units,
actual sample counts, counterexamples and bounded assumptions when those accepted
artifacts arrive. Avoid ontology-grounding, unique-optimum, source-rights or
successful-study claims that exceed the linked evidence.

Contribution: Ved supplied shared contracts, ontology/retrieval/constraint work,
reference and label/cache/hindsight methods and the technical investigation.
Matty organized this concise handoff and preserved the investigation as an appendix;
the final assembled contribution table must remain evidence-linked.
