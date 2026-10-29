# K01 Ontology, Units, and SHACL Validation

Owner: Ved.

This directory documents the semantic layer for the data-center sustainability project. The ontology, SHACL shapes, and validation API live under `dc_sustainability/knowledge/` and `ontology/`.

## Files

| File | Purpose |
|------|---------|
| `ontology/dc-sustainability.ttl` | Versioned OWL ontology (classes, properties, unit definitions) |
| `ontology/shapes.ttl` | SHACL shapes for structural validation of policy-visible graphs |
| `dc_sustainability/knowledge/ontology.py` | Python API: load ontology, map units, run SHACL validation |
| `dc_sustainability/knowledge/graph.py` | K02 graph builder; emits K01 unit/ontology metadata |
| `dc_sustainability/knowledge/retrieval.py` | K02 SPARQL retrieval; queries the graph built above |

## Namespace

```turtle
@prefix sched: <https://data-center-agentic.example.org/sched#> .
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix prov:  <http://www.w3.org/ns/prov#> .
@prefix qudt:  <http://qudt.org/schema/qudt/> .
@prefix unit:  <http://qudt.org/vocab/unit/> .
@prefix sh:    <http://www.w3.org/ns/shacl#> .
```

## Classes

| Class | Parent / Equivalent | Meaning |
|-------|---------------------|---------|
| `sched:Episode` | `owl:Class` | A single scheduling episode at a decision or completion slot |
| `sched:Site` | `brick:Building` | Data-center site configuration |
| `sched:Job` | `owl:Class` | Constant-power non-preemptive workload |
| `sched:WaitingJob` | `sched:Job` | Job that has arrived and is eligible to start |
| `sched:RunningJob` | `sched:Job` | Job currently executing |
| `sched:CompletedJob` | `sched:Job` | Job that has finished |
| `sched:Slot` | `owl:Class` | Discrete scheduling slot index |
| `sched:CarbonFact` | `owl:Class` | Abstract carbon intensity fact |
| `sched:CarbonObservation` | `sched:CarbonFact` | Realized (private) carbon observation |
| `sched:CarbonForecast` | `sched:CarbonFact` | Policy-visible carbon forecast |
| `sched:Constraint` | `owl:Class` | Operational constraint on the episode |
| `sched:Source` | `prov:Entity` | Provenance record for a data source |
| `sched:Decision` | `prov:Activity` | Scheduling decision activity |
| `sched:Check` | `prov:Activity` | Validation check activity |

## Key Properties

### Episode

- `sched:currentSlot` — current decision slot
- `sched:stateVersion` — version of the visible state
- `sched:snapshotId` — constraint snapshot identifier
- `sched:missedJob` — links a missed job IRI to the episode
- `sched:missingCarbonSlot` — slot with no forecast available

### Site

- `sched:backgroundKw` — background power draw
- `sched:pue` — power usage effectiveness (dimensionless)
- `sched:slotHours` — duration of one slot in hours

### Job

- `sched:arrivalSlot`, `sched:durationSlots`, `sched:deadlineSlot`, `sched:startSlot`, `sched:endSlot`
- `sched:powerKw` — constant power while running
- `sched:flexible` — whether the job is deferrable

### Carbon forecast

- `sched:carbonValue` — forecast value
- `sched:validSlot` — slot the value applies to
- `sched:carbonSource` — provenance source (separate from `sched:source` on constraints)
- `sched:issuedAtUtc`, `sched:validFromUtc`, `sched:validToUtc`
- `sched:forecastKind`, `sched:qualityStatus`
- `sched:pollutantBasis`, `sched:intervalConvention`, `sched:emissionsFactorType`, `sched:slotMappingStatus`

### Constraint

- `sched:constraintType` — one of `capacity`, `arrival`, `deadline`, `nonflexible`, `freshness`
- `sched:limitValue` — numeric limit
- `sched:unit` — F02 unit code literal
- `sched:source` — provenance source
- `sched:appliesToSite`, `sched:appliesToJob`
- `sched:sourceVersion`

### Source

- `sched:path` — file or origin path
- `sched:redistributionStatus` — e.g. `permitted`
- `sched:commit`, `sched:sha256`

## Unit Mapping

F02 unit codes are mapped to explicit QUDT or project-defined units by `map_unit()` in `dc_sustainability/knowledge/ontology.py`. Values are **never converted**; the mapping only supplies a semantic reference.

| F02 code | QUDT / project unit | Note |
|----------|---------------------|------|
| `kW` | `http://qudt.org/vocab/unit#Kilowatt` | active electrical power |
| `kWh` | `http://qudt.org/vocab/unit#Kilowatthour` | electrical energy |
| `slot` | — | discrete scheduling slot index; dimensionless ordinal |
| `h` | `http://qudt.org/vocab/unit#Hour` | duration in hours |
| `g/kWh` | `https://data-center-agentic.example.org/sched#GramPerKiloWattHour` | project-defined dimensional unit for carbon intensity |
| `kg` | `http://qudt.org/vocab/unit#Kilogram` | mass |
| `1` | `http://qudt.org/vocab/unit#Unitless` | **internal-only** dimensionless ratio used for the site PUE property; not an accepted F02 `Unit` value |

The canonical IRIs above are verified against the pinned `pyqudt` 1.1.1 unit vocabulary (`qudt/ontology/resources/unit.rdf`).
Unknown or miscased codes (e.g. `kw`, `KWH`, `MW`, `gco2/kwh`) raise `UnitMappingError`.

## SHACL Validation

```python
from dc_sustainability.knowledge.ontology import validate_graph
from dc_sustainability.knowledge.graph import build_graph

graph = build_graph(state, snapshot)
report = validate_graph(graph)
assert report.conforms
print(report.report_text)
```

`validate_graph` loads the bundled ontology and shapes offline, runs `pyshacl`, and returns a `ValidationReport`. Validation intentionally uses explicit types only (`inference=None`). Other inference values are rejected rather than silently ignored because pySHACL's RDFS expansion applies waiting/running job requirements to completed-job views that do not contain those private fields.

### Shape highlights

- `SiteShape` — exactly one background, PUE, slot-hours; PUE ≥ 1; site typed as `brick:Building`
- `JobShape` — targets `:WaitingJob` and `:RunningJob`; requires arrival, duration, power, deadline, and flexibility
- `WaitingJobShape` / `RunningJobShape` / `CompletedJobShape` — type-specific required slots, power, and flexibility
- `CarbonForecastShape` — required value, slot, source, issued time, forecast kind, quality status, semantics
- `ConstraintShape` — required type, limit, unit, source; type must be in the allowed set
- `SourceShape` — path and redistribution status required
- `EpisodeShape` — current slot, state version, snapshot ID
- `CapacityEvidenceShape` — every site must have exactly one `capacity` constraint; missing or duplicate capacity evidence is not accepted as a valid scheduling limit
- `UnitConsistencyShape` — every `limitValue` and `carbonValue` must carry a `sched:unit` literal
- `ConstraintSourceReferenceShape` / `ForecastSourceReferenceShape` — source IRIs must exist in the graph

### Completed jobs

Completed jobs are emitted as `:CompletedJob` nodes carrying only their completion interval (`startSlot`, `endSlot`) and label. They are **not** typed as `:Job`, `:WaitingJob`, or `:RunningJob`, and they do **not** receive fabricated arrival, duration, power, deadline, or flexibility properties. This prevents the waiting/running job shape from being applied to completed jobs while still allowing `:CompletedJobShape` to validate their actual properties.

### Capacity evidence

A site must have exactly one visible `capacity` constraint. SHACL rejects:

- a site with no capacity constraint (`CapacityEvidenceShape` missing-capacity SPARQL constraint);
- a site with more than one capacity constraint (`CapacityEvidenceShape` duplicate-capacity SPARQL constraint);
- a capacity constraint whose unit is not `kW` (`UnitConsistencyShape`).

Missing or ambiguous capacity evidence is never replaced by an invented default. Downstream consumers such as the scheduler and context builder fail closed (`MissingEvidenceError` / `ContractError`) when capacity is absent or multiple.

## Layer Separation

- **Static ontology** — `ontology/dc-sustainability.ttl` and `ontology/shapes.ttl` are versioned and read-only at runtime.
- **Episode graph** — `build_graph` creates a fresh graph per episode from policy-visible F02 records only. It does not include private observations, future arrivals, or fixture metadata.
- **Trace / provenance** — `Source`, `Decision`, and `Check` classes are declared for future provenance tracking; the current graph builder only emits `Source` nodes for visible sources.

## Known Limitations

- The ontology does not yet model QUDT quantity kinds or full Brick equipment classes; it only links unit codes to QUDT/unit IRIs.
- Provenance activities (`Decision`, `Check`) are declared but not yet emitted by `build_graph`.
- SHACL shapes validate structure and consistency, not scheduling feasibility (deadline satisfiability, capacity sufficiency, etc.). Passing SHACL is therefore not a certification of scientific validity or operational emissions accuracy.
- Missing or ambiguous capacity evidence is rejected by SHACL and by the F02 `ConstraintSnapshot.capacity_kw` property, but a production gate must still ensure that any context used for scheduling was derived from an authoritative snapshot whose hash matches the expected value.
