"""K01/K02: RDF graph construction, SPARQL retrieval, and flat-context projection.

Owner: Ved. Provides controlled graph retrieval and equivalent flat-context
projection for all policy systems. Full Brick/PROV-O/QUDT mapping and SHACL
shapes are K01's scope; this module exposes both the K01 ontology/validation
helpers and the K02 retrieval layer on top of F02 policy-visible records.
"""

from dc_sustainability.knowledge.graph import SCHED, build_graph
from dc_sustainability.knowledge.ontology import (
    ONTOLOGY_IRI,
    ONTOLOGY_VERSION,
    UnitInfo,
    UnitMappingError,
    ValidationReport,
    load_ontology_graph,
    load_shapes_graph,
    map_unit,
    validate_graph,
)
from dc_sustainability.knowledge.ontology import (
    SCHED as ONTOLOGY_SCHED,
)
from dc_sustainability.knowledge.retrieval import (
    RetrievalResult,
    get_context,
    query_constraints,
    query_eligible_jobs,
    query_forecasts,
    query_missing_carbon_slots,
    query_running_jobs,
    query_site,
    retrieve,
)

__all__ = [
    "SCHED",
    "ONTOLOGY_IRI",
    "ONTOLOGY_VERSION",
    "ONTOLOGY_SCHED",
    "RetrievalResult",
    "UnitInfo",
    "UnitMappingError",
    "ValidationReport",
    "build_graph",
    "get_context",
    "load_ontology_graph",
    "load_shapes_graph",
    "map_unit",
    "query_constraints",
    "query_eligible_jobs",
    "query_forecasts",
    "query_missing_carbon_slots",
    "query_running_jobs",
    "query_site",
    "retrieve",
    "validate_graph",
]
