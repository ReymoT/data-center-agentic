"""K02: Controlled SPARQL retrieval and equivalent flat-context projection.

Provides SPARQL queries for eligible jobs, running work, visible forecasts,
applicable constraints, and missing links. The ``get_context`` function
builds an F02 ``Context`` record from a ``VisibleState`` and
``ConstraintSnapshot``, producing the same ``content_hash`` whether the
data was read from the RDF graph or directly from the F02 records.

Policies receive only visibility-filtered access. Arbitrary SPARQL queries
against hidden episode facts are not supported; the graph is built from
policy-visible records only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from rdflib import Graph, Literal, URIRef

from dc_sustainability import schemas as s
from dc_sustainability.knowledge.graph import _id, build_graph

# --------------------------------------------------------------------------- SPARQL queries

SPARQL_ELIGIBLE_JOBS = """
PREFIX sched: <https://data-center-agentic.example.org/sched#>
SELECT ?job ?arrivalSlot ?durationSlots ?powerKw ?deadlineSlot ?flexible
WHERE {
    ?job a sched:WaitingJob ;
         sched:arrivalSlot ?arrivalSlot ;
         sched:durationSlots ?durationSlots ;
         sched:powerKw ?powerKw ;
         sched:deadlineSlot ?deadlineSlot ;
         sched:flexible ?flexible .
}
ORDER BY ?job
"""

SPARQL_RUNNING_JOBS = """
PREFIX sched: <https://data-center-agentic.example.org/sched#>
SELECT ?job ?startSlot ?powerKw ?durationSlots
WHERE {
    ?job a sched:RunningJob ;
         sched:startSlot ?startSlot ;
         sched:powerKw ?powerKw ;
         sched:durationSlots ?durationSlots .
}
ORDER BY ?job
"""

SPARQL_FORECASTS = """
PREFIX sched: <https://data-center-agentic.example.org/sched#>
SELECT ?fact ?value ?validSlot ?src ?issuedAt ?forecastKind
WHERE {
    ?fact a sched:CarbonForecast ;
          sched:carbonValue ?value ;
          sched:validSlot ?validSlot ;
          sched:carbonSource ?src ;
          sched:issuedAtUtc ?issuedAt ;
          sched:forecastKind ?forecastKind .
}
ORDER BY ?fact
"""

SPARQL_CONSTRAINTS = """
PREFIX sched: <https://data-center-agentic.example.org/sched#>
SELECT ?con ?type ?limit ?unit ?src ?site ?job
WHERE {
    ?con a sched:Constraint ;
         sched:constraintType ?type ;
         sched:limitValue ?limit ;
         sched:unit ?unit ;
         sched:source ?src .
    OPTIONAL { ?con sched:appliesToSite ?site }
    OPTIONAL { ?con sched:appliesToJob ?job }
}
ORDER BY ?con ?job
"""

SPARQL_MISSING_LINKS = """
PREFIX sched: <https://data-center-agentic.example.org/sched#>
SELECT ?slot
WHERE {
    ?ep a sched:Episode ;
        sched:missingCarbonSlot ?slot .
}
ORDER BY ?slot
"""

SPARQL_SITE = """
PREFIX sched: <https://data-center-agentic.example.org/sched#>
SELECT ?site ?backgroundKw ?pue ?slotHours
WHERE {
    ?site a sched:Site ;
          sched:backgroundKw ?backgroundKw ;
          sched:pue ?pue ;
          sched:slotHours ?slotHours .
}
"""


# --------------------------------------------------------------------------- query helpers


def _val(row: Any, idx: int) -> Any:
    """Extract a Python value from an rdflib result row cell."""
    cell = row[idx]
    if cell is None:
        return None
    if isinstance(cell, Literal):
        value = cell.toPython()
        # Preserve XSD dateTime strings as ISO 8601 with Z suffix, matching F02.
        if (
            cell.datatype
            and str(cell.datatype).endswith("dateTime")
            and isinstance(value, datetime)
        ):
            return value.isoformat().replace("+00:00", "Z")
        return value
    if isinstance(cell, URIRef):
        return _id(cell)
    return str(cell)


def query_eligible_jobs(graph: Graph) -> list[dict[str, Any]]:
    """Return waiting (eligible) jobs as flat dicts via SPARQL."""
    results = []
    for row in graph.query(SPARQL_ELIGIBLE_JOBS):
        results.append(
            {
                "job_id": _val(row, 0),
                "arrival_slot": int(_val(row, 1)),
                "duration_slots": int(_val(row, 2)),
                "power_kw": float(_val(row, 3)),
                "deadline_slot": int(_val(row, 4)),
                "flexible": bool(_val(row, 5)),
            }
        )
    return results


def query_running_jobs(graph: Graph) -> list[dict[str, Any]]:
    """Return running job views as flat dicts via SPARQL."""
    results = []
    for row in graph.query(SPARQL_RUNNING_JOBS):
        results.append(
            {
                "job_id": _val(row, 0),
                "start_slot": int(_val(row, 1)),
                "power_kw": float(_val(row, 2)),
                "duration_slots": int(_val(row, 3)),
            }
        )
    return results


def query_forecasts(graph: Graph) -> list[dict[str, Any]]:
    """Return visible carbon forecasts as flat dicts via SPARQL."""
    results = []
    for row in graph.query(SPARQL_FORECASTS):
        results.append(
            {
                "fact_id": _val(row, 0),
                "value": float(_val(row, 1)),
                "valid_slot": int(_val(row, 2)),
                "source_id": _val(row, 3),
                "issued_at_utc": _val(row, 4),
                "forecast_kind": _val(row, 5),
            }
        )
    return results


def query_constraints(graph: Graph) -> list[dict[str, Any]]:
    """Return visible constraints as flat dicts via SPARQL."""
    results = []
    for row in graph.query(SPARQL_CONSTRAINTS):
        results.append(
            {
                "constraint_id": _val(row, 0),
                "constraint_type": _val(row, 1),
                "limit_value": float(_val(row, 2)),
                "unit": _val(row, 3),
                "source_id": _val(row, 4),
                "applies_to_site": _val(row, 5),
                "applies_to_jobs": _val(row, 6),
            }
        )
    return results


def query_missing_carbon_slots(graph: Graph) -> list[int]:
    """Return explicit missing-forecast slots via SPARQL."""
    return [int(_val(row, 0)) for row in graph.query(SPARQL_MISSING_LINKS)]


def query_site(graph: Graph) -> dict[str, Any]:
    """Return site config as a flat dict via SPARQL."""
    row = next(iter(graph.query(SPARQL_SITE)))
    return {
        "site_id": _val(row, 0),
        "background_kw": float(_val(row, 1)),
        "pue": float(_val(row, 2)),
        "slot_hours": float(_val(row, 3)),
    }


# --------------------------------------------------------------------------- context builder


def get_context(
    state: s.VisibleState,
    snapshot: s.ConstraintSnapshot,
    *,
    representation: str = "flat",
    presentation_sha256: str | None = None,
) -> s.Context:
    """Build an F02 ``Context`` from a visible state and authoritative snapshot.

    This is the K02 retrieval entry point. It delegates to
    ``Context.build`` which performs the visibility projection, evidence-ID
    derivation, source resolution, and canonical hashing. The resulting
    ``content_hash`` is representation-independent: a graph-representation
    context and a flat-representation context built from the same state
    and snapshot carry the same ``content_hash``.

    Parameters
    ----------
    state:
        Policy-visible state from the simulator.
    snapshot:
        Authoritative constraint snapshot (full, not projected).
    representation:
        ``"flat"`` or ``"graph"``. The content is identical; only the
        presentation label differs.
    presentation_sha256:
        Optional hash of any rendered text, for traceability.
    """
    return s.Context.build(
        state,
        snapshot,
        representation=representation,  # type: ignore[arg-type]
        presentation_sha256=presentation_sha256,
    )


@dataclass(frozen=True)
class RetrievalResult:
    """Bundle of SPARQL query results for one visible state.

    Provides the flat projection that policies consume. The ``context``
    field carries the F02 ``Context`` record with its canonical hash so
    Nisha can verify equivalent information across systems.
    """

    context: s.Context
    eligible_jobs: tuple[dict[str, Any], ...]
    running_jobs: tuple[dict[str, Any], ...]
    forecasts: tuple[dict[str, Any], ...]
    constraints: tuple[dict[str, Any], ...]
    missing_carbon_slots: tuple[int, ...]
    site: dict[str, Any]


def retrieve(
    state: s.VisibleState,
    snapshot: s.ConstraintSnapshot,
    *,
    representation: str = "flat",
) -> RetrievalResult:
    """Build the RDF graph, run SPARQL queries, and assemble the flat projection.

    This is the full K02 retrieval pipeline:
    1. Build the controlled RDF graph from policy-visible records.
    2. Run SPARQL queries for each fact category.
    3. Build the F02 ``Context`` with canonical hash.
    4. Return a ``RetrievalResult`` bundling the context and flat query results.

    The SPARQL results are a development convenience for inspection and
    testing. The authoritative policy input is the ``Context`` record,
    whose ``content_hash`` proves graph/flat equivalence.
    """
    graph = build_graph(state, snapshot)
    context = get_context(state, snapshot, representation=representation)
    return RetrievalResult(
        context=context,
        eligible_jobs=tuple(query_eligible_jobs(graph)),
        running_jobs=tuple(query_running_jobs(graph)),
        forecasts=tuple(query_forecasts(graph)),
        constraints=tuple(query_constraints(graph)),
        missing_carbon_slots=tuple(query_missing_carbon_slots(graph)),
        site=query_site(graph),
    )
