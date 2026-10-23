"""K01/K02: RDF graph construction from F02 policy-visible records.

Builds a controlled RDF graph from a ``VisibleState`` and ``ConstraintSnapshot``.
Only policy-visible data is included: no private fixture fields, no future
arrivals, no realized carbon observations. The graph is a development
representation for SPARQL retrieval (K02); full Brick/PROV-O/QUDT mapping
is K01's scope and is not applied here.
"""

from rdflib import RDF, Graph, Literal, Namespace, URIRef

from dc_sustainability import schemas as s

SCHED = Namespace("https://data-center-agentic.example.org/sched#")


def _iri(entity_id: str) -> URIRef:
    """Map an F02 entity ID to its scheduling-namespace IRI."""
    return SCHED[entity_id]


def _id(iri: URIRef) -> str:
    """Extract the F02 entity ID from a scheduling-namespace IRI."""
    return str(iri).removeprefix(str(SCHED))


def _add_job_triples(graph: Graph, job: s.Job, rdf_type: URIRef) -> None:
    """Add common job property triples for a visible job."""
    node = _iri(job.job_id)
    graph.add((node, RDF.type, rdf_type))
    graph.add((node, SCHED.arrivalSlot, Literal(job.arrival_slot)))
    graph.add((node, SCHED.durationSlots, Literal(job.duration_slots)))
    graph.add((node, SCHED.powerKw, Literal(job.power_kw)))
    graph.add((node, SCHED.deadlineSlot, Literal(job.deadline_slot)))
    graph.add((node, SCHED.flexible, Literal(job.flexible)))


def _add_constraint_triples(graph: Graph, constraint: s.Constraint) -> None:
    """Add constraint property triples."""
    node = _iri(constraint.constraint_id)
    graph.add((node, RDF.type, SCHED.Constraint))
    graph.add((node, SCHED.constraintType, Literal(constraint.constraint_type)))
    graph.add((node, SCHED.limitValue, Literal(constraint.limit_value)))
    graph.add((node, SCHED.unit, Literal(constraint.unit)))
    graph.add((node, SCHED.source, _iri(constraint.source_id)))
    if constraint.applies_to_site is not None:
        graph.add((node, SCHED.appliesToSite, _iri(constraint.applies_to_site)))
    for job_id in constraint.applies_to_jobs:
        graph.add((node, SCHED.appliesToJob, _iri(job_id)))
    if constraint.source_version is not None:
        graph.add((node, SCHED.sourceVersion, Literal(constraint.source_version)))


def _add_source_triples(graph: Graph, source: s.SourceRef) -> None:
    """Add source provenance triples."""
    node = _iri(source.source_id)
    graph.add((node, RDF.type, SCHED.Source))
    graph.add((node, SCHED.path, Literal(source.path)))
    graph.add((node, SCHED.redistributionStatus, Literal(source.redistribution_status)))
    if source.commit is not None:
        graph.add((node, SCHED.commit, Literal(source.commit)))
    if source.sha256 is not None:
        graph.add((node, SCHED.sha256, Literal(source.sha256)))


def _add_forecast_triples(graph: Graph, fact: s.CarbonForecast) -> None:
    """Add carbon forecast property triples including nested semantics."""
    node = _iri(fact.fact_id)
    graph.add((node, RDF.type, SCHED.CarbonForecast))
    graph.add((node, SCHED.carbonValue, Literal(fact.value)))
    graph.add((node, SCHED.validSlot, Literal(fact.valid_slot)))
    graph.add((node, SCHED.unit, Literal(fact.unit)))
    graph.add((node, SCHED.source, _iri(fact.source_id)))
    graph.add(
        (
            node,
            SCHED.issuedAtUtc,
            Literal(fact.issued_at_utc.isoformat().replace("+00:00", "Z")),
        )
    )
    graph.add((node, SCHED.forecastKind, Literal(fact.forecast_kind)))
    graph.add((node, SCHED.qualityStatus, Literal(fact.quality_status)))
    sem = fact.semantics
    graph.add((node, SCHED.pollutantBasis, Literal(sem.pollutant_basis)))
    graph.add((node, SCHED.intervalConvention, Literal(sem.interval_convention)))
    graph.add((node, SCHED.emissionsFactorType, Literal(sem.emissions_factor_type)))
    graph.add((node, SCHED.slotMappingStatus, Literal(sem.slot_mapping_status)))
    if fact.valid_from_utc is not None:
        graph.add(
            (
                node,
                SCHED.validFromUtc,
                Literal(fact.valid_from_utc.isoformat().replace("+00:00", "Z")),
            )
        )
    if fact.valid_to_utc is not None:
        graph.add(
            (
                node,
                SCHED.validToUtc,
                Literal(fact.valid_to_utc.isoformat().replace("+00:00", "Z")),
            )
        )
    if fact.source_sha256 is not None:
        graph.add((node, SCHED.sourceSha256, Literal(fact.source_sha256)))


def build_graph(state: s.VisibleState, snapshot: s.ConstraintSnapshot) -> Graph:
    """Build a controlled RDF graph from policy-visible F02 records.

    Only visible data is included. The constraint and source sets are
    projected through ``visible_constraints_for`` so that not-yet-arrived
    jobs cannot leak through constraint IDs or ``applies_to_jobs`` lists.
    """
    graph = Graph()
    graph.bind("sched", SCHED)

    # Episode metadata
    ep = _iri(state.episode_id)
    graph.add((ep, RDF.type, SCHED.Episode))
    graph.add((ep, SCHED.currentSlot, Literal(state.current_slot)))
    graph.add((ep, SCHED.stateVersion, Literal(state.state_version)))
    graph.add((ep, SCHED.snapshotId, Literal(snapshot.snapshot_id)))

    # Site config
    site_node = _iri(state.site.site_id)
    graph.add((site_node, RDF.type, SCHED.Site))
    graph.add((site_node, SCHED.backgroundKw, Literal(state.site.background_kw)))
    graph.add((site_node, SCHED.pue, Literal(state.site.pue)))
    graph.add((site_node, SCHED.slotHours, Literal(state.site.slot_hours)))

    # Waiting jobs
    for job in state.waiting_jobs:
        _add_job_triples(graph, job, SCHED.WaitingJob)

    # Running jobs
    for view in state.running_jobs:
        _add_job_triples(graph, view.job, SCHED.RunningJob)
        graph.add((_iri(view.job.job_id), SCHED.startSlot, Literal(view.start_slot)))

    # Completed jobs
    for view in state.completed_jobs:
        node = _iri(view.job_id)
        graph.add((node, RDF.type, SCHED.CompletedJob))
        graph.add((node, SCHED.startSlot, Literal(view.start_slot)))
        graph.add((node, SCHED.endSlot, Literal(view.end_slot)))

    # Missed jobs
    for job_id in state.missed_job_ids:
        graph.add((ep, SCHED.missedJob, _iri(job_id)))

    # Carbon forecasts
    for fact in state.carbon_facts:
        _add_forecast_triples(graph, fact)

    # Missing carbon slots
    for slot in state.missing_carbon_slots:
        graph.add((ep, SCHED.missingCarbonSlot, Literal(slot)))

    # Visible constraints only (same projection as Context.build)
    visible_constraints = s.visible_constraints_for(state, snapshot)
    for constraint in visible_constraints:
        _add_constraint_triples(graph, constraint)

    # Visible sources only
    visible_source_ids = {c.source_id for c in visible_constraints}
    visible_source_ids |= {f.source_id for f in state.carbon_facts}
    for source in snapshot.sources:
        if source.source_id in visible_source_ids:
            _add_source_triples(graph, source)

    return graph
