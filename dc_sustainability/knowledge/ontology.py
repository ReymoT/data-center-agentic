"""K01: ontology loading, unit mapping, and SHACL validation.

Owner: Ved. This module provides the semantic foundation for the knowledge graph:

* load the versioned project ontology and SHACL shapes from package resources;
* map F02 unit codes to explicit QUDT/unit IRIs (or project-defined dimensional units);
* validate an RDFLib graph against the SHACL shapes and return a structured report.

All ontology files are loaded offline from the installed package. No network calls are
made during import, graph construction, or validation.
"""

from __future__ import annotations

import dataclasses
import importlib.resources
from pathlib import Path
from typing import Any, ClassVar, Mapping

from pyshacl import validate
from rdflib import RDFS, Graph, Literal, Namespace, URIRef

SCHED = Namespace("https://data-center-agentic.example.org/sched#")

# Standard prefixes used in the ontology files.
BRICK = Namespace("https://brickschema.org/schema/Brick#")
PROV = Namespace("http://www.w3.org/ns/prov#")
QUDT = Namespace("http://qudt.org/schema/qudt/")
QUDT_UNIT = Namespace("http://qudt.org/vocab/unit/")
SH = Namespace("http://www.w3.org/ns/shacl#")

ONTOLOGY_VERSION = "1.0.0"
ONTOLOGY_IRI = URIRef("https://data-center-agentic.example.org/sched")


class UnitMappingError(ValueError):
    """Raised when a unit code is unknown or unsupported."""


@dataclasses.dataclass(frozen=True)
class UnitInfo:
    """Semantic description of an F02 unit code."""

    code: str
    qudt_unit: URIRef | None
    dimensional_note: str | None = None


# Explicit mapping from every F02 Unit value to a QUDT unit IRI or a project-defined
# dimensional class. Values are never converted; the mapping only supplies a semantic
# reference for the already-stated unit code.
#
# Canonical IRIs are verified against the pinned pyqudt 1.1.1 unit vocabulary
# (.venv/lib64/python3.12/site-packages/qudt/ontology/resources/unit.rdf), which
# uses the namespace http://qudt.org/vocab/unit# and local names:
#   Kilowatt, Kilowatthour, Hour, Kilogram, Unitless, Gram.
UNIT_MAP: Mapping[str, UnitInfo] = {
    "kW": UnitInfo("kW", URIRef("http://qudt.org/vocab/unit#Kilowatt"), "active electrical power"),
    "kWh": UnitInfo("kWh", URIRef("http://qudt.org/vocab/unit#Kilowatthour"), "electrical energy"),
    "slot": UnitInfo("slot", None, "discrete scheduling slot index; dimensionless ordinal"),
    "h": UnitInfo("h", URIRef("http://qudt.org/vocab/unit#Hour"), "duration in hours"),
    "g/kWh": UnitInfo(
        "g/kWh",
        SCHED.GramPerKiloWattHour,
        "project dimensional unit for carbon intensity; pollutant basis recorded separately",
    ),
    "kg": UnitInfo("kg", URIRef("http://qudt.org/vocab/unit#Kilogram"), "mass"),
    "1": UnitInfo("1", URIRef("http://qudt.org/vocab/unit#Unitless"), "dimensionless ratio (PUE)"),
}

# Aliases that F02 does not accept but may appear in raw data; reject them explicitly.
UNKNOWN_UNIT_CODES: ClassVar[frozenset[str]] = frozenset(
    {
        "kw",
        "KWH",
        "kwh",
        "g/kwh",
        "gco2/kwh",
        "gCO2/kWh",
        "MW",
        "wh",
        "Wh",
    }
)


def map_unit(code: str) -> UnitInfo:
    """Return the semantic unit info for an F02 unit code.

    Parameters
    ----------
    code:
        Unit literal from an F02 record (e.g. ``"kW"``, ``"g/kWh"``).

    Raises
    ------
    UnitMappingError
        If ``code`` is not one of the supported F02 unit codes.
    """
    if code in UNKNOWN_UNIT_CODES:
        raise UnitMappingError(f"unit code {code!r} is not an accepted F02 unit")
    try:
        return UNIT_MAP[code]
    except KeyError as exc:
        raise UnitMappingError(f"unknown unit code {code!r}") from exc


def _package_ttl(name: str) -> str:
    """Read a Turtle file bundled with the ``dc_sustainability`` package."""
    package = "dc_sustainability"
    try:
        ref = importlib.resources.files(package).joinpath(f"../ontology/{name}")
        return ref.read_text(encoding="utf-8")
    except (AttributeError, OSError):
        # Fallback for older importlib.resources APIs.
        with importlib.resources.path(package, "") as base:
            return (Path(base).parent / "ontology" / name).read_text(encoding="utf-8")


def load_ontology_graph() -> Graph:
    """Load the project ontology from the bundled Turtle file.

    The ontology is parsed offline; no network requests are made.
    """
    graph = Graph()
    graph.bind("sched", SCHED)
    graph.bind("brick", BRICK)
    graph.bind("prov", PROV)
    graph.bind("qudt", QUDT)
    graph.bind("unit", QUDT_UNIT)
    graph.parse(data=_package_ttl("dc-sustainability.ttl"), format="turtle")
    return graph


def load_shapes_graph() -> Graph:
    """Load the SHACL shapes graph from the bundled Turtle file.

    The shapes are parsed offline; no network requests are made.
    """
    graph = Graph()
    graph.bind("sched", SCHED)
    graph.bind("sh", SH)
    graph.parse(data=_package_ttl("shapes.ttl"), format="turtle")
    return graph


@dataclasses.dataclass(frozen=True)
class ValidationReport:
    """Structured result from SHACL validation."""

    conforms: bool
    report_graph: Graph
    report_text: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly summary of the validation result."""
        return {
            "conforms": self.conforms,
            "report_text": self.report_text,
            "report_triples": len(self.report_graph),
        }


def validate_graph(
    data_graph: Graph,
    *,
    shacl_graph: Graph | None = None,
    ont_graph: Graph | None = None,
    inference: str | None = "rdfs",
) -> ValidationReport:
    """Validate ``data_graph`` against the project SHACL shapes.

    Parameters
    ----------
    data_graph:
        RDFLib graph to validate (typically from ``build_graph``).
    shacl_graph:
        Optional SHACL shapes graph. If ``None``, the bundled shapes are loaded.
    ont_graph:
        Optional ontology graph for RDFS inference. If ``None``, the bundled ontology
        is loaded.
    inference:
        Inference level passed to pySHACL. ``"rdfs"`` expands class hierarchies so
        subclass targets (e.g. ``:WaitingJob`` as ``:Job``) are validated.

    Returns
    -------
    ValidationReport
        A structured report with ``conforms``, the report graph, and report text.
    """
    shapes = shacl_graph if shacl_graph is not None else load_shapes_graph()
    ontology = ont_graph if ont_graph is not None else load_ontology_graph()
    # Issue #71: completed-job nodes are typed only as :CompletedJob in the
    # policy-visible graph. pySHACL with RDFS inference expands
    # sh:targetClass :WaitingJob/:RunningJob to the superclass :Job and then
    # validates any :CompletedJob (also a subclass of :Job) against :JobShape,
    # causing false missing-property violations. We therefore validate without
    # RDFS inference; build_graph already emits explicit types such as
    # brick:Building where required.
    conforms, report_graph, report_text = validate(
        data_graph,
        shacl_graph=shapes,
        ont_graph=ontology,
        inference=None,
        abort_on_first=False,
        meta_shacl=False,
        debug=False,
    )
    return ValidationReport(
        conforms=bool(conforms),
        report_graph=report_graph,
        report_text=report_text,
    )


def add_unit_metadata(graph: Graph, subject: URIRef, unit_code: str) -> UnitInfo:
    """Add semantic unit metadata for ``subject`` to ``graph``.

    The original F02 ``unit`` literal is preserved, and a ``sched:qudtUnit`` link is
    added when a QUDT or project unit IRI is available. Unknown unit codes raise
    ``UnitMappingError`` so they cannot silently pass validation.
    """
    info = map_unit(unit_code)
    graph.add((subject, SCHED.unit, Literal(info.code)))
    if info.qudt_unit is not None:
        graph.add((subject, SCHED.qudtUnit, info.qudt_unit))
    if info.dimensional_note:
        graph.add((subject, RDFS.comment, Literal(info.dimensional_note)))
    return info
