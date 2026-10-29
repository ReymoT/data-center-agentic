"""K01 ontology, unit mapping, and SHACL validation tests."""

import pytest
from rdflib import RDF, RDFS, XSD, Graph, Literal, Namespace

from dc_sustainability import schemas as s
from dc_sustainability.knowledge.graph import SCHED, build_graph
from dc_sustainability.knowledge.ontology import (
    BRICK,
    ONTOLOGY_IRI,
    ONTOLOGY_VERSION,
    QUDT_UNIT,
    UnitInfo,
    UnitMappingError,
    add_unit_metadata,
    load_ontology_graph,
    load_shapes_graph,
    map_unit,
    validate_graph,
)
from tests.contracts import fixtures as fx


def test_ontology_loads_offline():
    """The project ontology parses without network access."""
    graph = load_ontology_graph()
    assert isinstance(graph, Graph)
    assert len(graph) > 0
    assert (ONTOLOGY_IRI, RDF.type, Namespace("http://www.w3.org/2002/07/owl#").Ontology) in graph


def test_ontology_declares_version():
    """The ontology IRI carries the expected version literal."""
    graph = load_ontology_graph()
    version = graph.value(ONTOLOGY_IRI, Namespace("http://www.w3.org/2002/07/owl#").versionInfo)
    assert str(version) == ONTOLOGY_VERSION


def test_shapes_load_offline():
    """The SHACL shapes graph parses without network access."""
    graph = load_shapes_graph()
    assert isinstance(graph, Graph)
    assert len(graph) > 0


def test_map_unit_known_codes():
    """All F02 unit codes map to a UnitInfo with the expected QUDT or project unit."""
    assert map_unit("kW") == UnitInfo("kW", QUDT_UNIT.KiloW, "active electrical power")
    assert map_unit("kWh") == UnitInfo("kWh", QUDT_UNIT["KiloW-HR"], "electrical energy")
    assert map_unit("slot") == UnitInfo(
        "slot", None, "discrete scheduling slot index; dimensionless ordinal"
    )
    assert map_unit("h") == UnitInfo("h", QUDT_UNIT.HR, "duration in hours")
    assert map_unit("kg") == UnitInfo("kg", QUDT_UNIT.KiloGM, "mass")
    assert map_unit("1") == UnitInfo("1", None, "dimensionless ratio (PUE)")


def test_map_unit_g_per_kwh_uses_project_unit():
    """g/kWh maps to the project-defined dimensional unit."""
    info = map_unit("g/kWh")
    assert info.code == "g/kWh"
    assert info.qudt_unit == SCHED.GramPerKiloWattHour


def test_map_unit_rejects_unknown_and_miscased_codes():
    """Unknown or miscased unit codes raise UnitMappingError."""
    for bad in ("kw", "KWH", "kwh", "g/kwh", "gco2/kwh", "gCO2/kWh", "MW", "wh", "Wh", "ft"):
        with pytest.raises(UnitMappingError):
            map_unit(bad)


def test_add_unit_metadata_adds_qudt_link():
    """add_unit_metadata preserves the F02 unit literal and adds a QUDT link."""
    graph = Graph()
    subject = SCHED["test-subject"]
    info = add_unit_metadata(graph, subject, "kW")
    assert info.code == "kW"
    assert (subject, SCHED.unit, Literal("kW")) in graph
    assert (subject, SCHED.qudtUnit, QUDT_UNIT.KiloW) in graph
    assert (subject, RDFS.comment, Literal("active electrical power")) in graph


def test_add_unit_metadata_dimensionless_slot():
    """Dimensionless units get a comment but no QUDT link."""
    graph = Graph()
    subject = SCHED["test-subject"]
    add_unit_metadata(graph, subject, "slot")
    assert (subject, SCHED.unit, Literal("slot")) in graph
    assert (subject, SCHED.qudtUnit, None) not in graph
    assert (
        subject,
        RDFS.comment,
        Literal("discrete scheduling slot index; dimensionless ordinal"),
    ) in graph


def test_add_unit_metadata_unknown_unit_raises():
    """add_unit_metadata propagates UnitMappingError for unsupported units."""
    graph = Graph()
    with pytest.raises(UnitMappingError):
        add_unit_metadata(graph, SCHED["test-subject"], "MW")


def test_standard_fixture_graph_conforms():
    """The hand-example visible-state graph passes SHACL validation."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    report = validate_graph(graph)
    assert report.conforms, report.report_text


def test_validation_report_to_dict():
    """ValidationReport.to_dict returns JSON-friendly fields."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    report = validate_graph(graph)
    d = report.to_dict()
    assert d["conforms"] is True
    assert isinstance(d["report_text"], str)
    assert isinstance(d["report_triples"], int)


def test_graph_without_capacity_fails_validation():
    """A graph missing the site-wide capacity constraint fails SHACL validation."""
    snap = fx.snapshot(include_capacity=False)
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    report = validate_graph(graph)
    assert not report.conforms
    assert "capacity" in report.report_text.lower()


def test_graph_with_bad_forecast_source_fails():
    """A forecast referencing a non-existent source fails SHACL validation."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    # Replace the valid carbonSource with a dangling URI.
    fact = state.carbon_facts[0]
    fact_node = SCHED[fact.fact_id]
    graph.remove((fact_node, SCHED.carbonSource, None))
    graph.add((fact_node, SCHED.carbonSource, SCHED["MISSING-SOURCE"]))
    report = validate_graph(graph)
    assert not report.conforms


def test_graph_with_missing_unit_fails():
    """A constraint without a unit literal fails SHACL validation."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    cap = SCHED["CON-CAP-01"]
    graph.remove((cap, SCHED.unit, None))
    report = validate_graph(graph)
    assert not report.conforms


def test_datetime_literals_carry_xsd_datatype():
    """Carbon forecast issuedAtUtc is emitted as an xsd:dateTime literal."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    fact = state.carbon_facts[0]
    value = graph.value(SCHED[fact.fact_id], SCHED.issuedAtUtc)
    assert isinstance(value, Literal)
    assert value.datatype == XSD.dateTime


def test_forecast_uses_carbon_source_not_source():
    """Carbon forecasts use :carbonSource, avoiding RDFS inference to Constraint."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    fact = state.carbon_facts[0]
    fact_node = SCHED[fact.fact_id]
    assert (fact_node, SCHED.carbonSource, SCHED[fx.SOURCE_ID]) in graph
    assert (fact_node, SCHED.source, None) not in graph


def test_constraint_uses_source_not_carbon_source():
    """Constraints use :source, not :carbonSource."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    cap = SCHED["CON-CAP-01"]
    assert (cap, SCHED.source, SCHED[fx.SOURCE_ID]) in graph
    assert (cap, SCHED.carbonSource, None) not in graph


def test_site_is_typed_as_building():
    """Site nodes carry both :Site and brick:Building types."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    site = SCHED["SITE1"]
    assert (site, RDF.type, SCHED.Site) in graph
    assert (site, RDF.type, BRICK.Building) in graph


def test_job_is_typed_as_job():
    """Waiting jobs carry both :WaitingJob and :Job types."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    j1 = SCHED["J1"]
    assert (j1, RDF.type, SCHED.WaitingJob) in graph
    assert (j1, RDF.type, SCHED.Job) in graph


def test_validate_graph_accepts_external_shapes_and_ontology():
    """validate_graph can be called with caller-supplied shapes/ontology graphs."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    shapes = load_shapes_graph()
    ontology = load_ontology_graph()
    report = validate_graph(graph, shacl_graph=shapes, ont_graph=ontology, inference="rdfs")
    assert report.conforms


def test_validate_graph_without_inference_checks_explicit_types():
    """Without RDFS inference, the SiteShape requires the explicit brick:Building type."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    # build_graph explicitly adds brick:Building, so validation passes even without RDFS.
    report = validate_graph(graph, inference=None)
    assert report.conforms, report.report_text


def test_validate_graph_without_inference_fails_without_building_type():
    """Removing the explicit brick:Building type fails validation when RDFS inference is off."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    site = SCHED["SITE1"]
    graph.remove((site, RDF.type, BRICK.Building))
    report = validate_graph(graph, inference=None)
    assert not report.conforms
    assert "brick:Building" in report.report_text


def test_completed_job_graph_conforms():
    """A visible state with only completed jobs passes SHACL validation."""
    snap = fx.snapshot()
    state = s.VisibleState.from_snapshot(
        snap,
        episode_id="EP-COMPLETED",
        current_slot=3,
        state_version=3,
        waiting_jobs=(fx.jobs()["J2"],),
        completed_jobs=(s.CompletedJobView(job_id="J1", start_slot=0, end_slot=2),),
        carbon_facts=tuple(
            f for f in fx.forecasts() if 3 <= f.valid_slot < 3 + s.PROPOSED_DECISION_SLOTS
        ),
    )
    graph = build_graph(state, snap)
    report = validate_graph(graph)
    assert report.conforms, report.report_text


def test_duplicate_capacity_constraint_fails_validation():
    """Two capacity constraints for the same site are rejected as ambiguous."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    # Add a second capacity constraint for the same site.
    dup = SCHED["CON-CAP-DUP"]
    graph.add((dup, RDF.type, SCHED.Constraint))
    graph.add((dup, SCHED.constraintType, Literal("capacity")))
    graph.add((dup, SCHED.limitValue, Literal(50.0)))
    graph.add((dup, SCHED.unit, Literal("kW")))
    graph.add((dup, SCHED.source, SCHED[fx.SOURCE_ID]))
    graph.add((dup, SCHED.appliesToSite, SCHED["SITE1"]))
    report = validate_graph(graph)
    assert not report.conforms
    assert "more than one capacity" in report.report_text.lower()


def test_capacity_unit_must_be_kw():
    """A capacity constraint with a non-kW unit fails unit-consistency validation."""
    snap = fx.snapshot()
    state = fx.visible_state(snap)
    graph = build_graph(state, snap)
    cap = SCHED["CON-CAP-01"]
    graph.remove((cap, SCHED.unit, None))
    graph.add((cap, SCHED.unit, Literal("slot")))
    report = validate_graph(graph)
    assert not report.conforms
    assert "unit" in report.report_text.lower()
