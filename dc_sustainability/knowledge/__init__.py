"""K01/K02: RDF graph construction, SPARQL retrieval, and flat-context projection.

Owner: Ved. Provides controlled graph retrieval and equivalent flat-context
projection for all policy systems. Full Brick/PROV-O/QUDT mapping and SHACL
shapes are K01's scope; this module implements the K02 retrieval layer on
top of F02 policy-visible records.
"""

from dc_sustainability.knowledge.graph import SCHED, build_graph
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
    "RetrievalResult",
    "build_graph",
    "get_context",
    "query_constraints",
    "query_eligible_jobs",
    "query_forecasts",
    "query_missing_carbon_slots",
    "query_running_jobs",
    "query_site",
    "retrieve",
]
