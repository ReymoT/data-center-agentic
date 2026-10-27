"""K03: Graph-driven capacity checks and fail-closed evidence handling.

These tests prove that the RDF graph projection (K01/K02) is the source of truth
for the production schedule checker (A03).  They exercise:

* building the graph from a visible state + constraint snapshot;
* validating the graph with SHACL;
* retrieving the capacity constraint via SPARQL;
* feeding the retrieved constraint record into ``check_schedule``;
* fail-closed behavior when capacity evidence is missing or malformed.

All fixtures reuse the hand-calculated F02 example from ``tests.contracts.fixtures``
so the results are stable and independent of simulator randomness.
"""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.knowledge.graph import SCHED, build_graph
from dc_sustainability.knowledge.ontology import validate_graph
from dc_sustainability.knowledge.retrieval import query_constraints, retrieve
from dc_sustainability.verification.checker import check_schedule
from tests.contracts import fixtures as fx


def _single_job_state_and_snapshot(capacity_kw: float = 100.0, include_capacity: bool = True):
    """Return a minimal visible state and snapshot for J1 only."""
    snap = fx.snapshot(capacity_kw=capacity_kw, include_capacity=include_capacity)
    state = s.VisibleState.from_snapshot(
        snap,
        episode_id=fx.EPISODE_ID,
        current_slot=0,
        state_version=0,
        waiting_jobs=(fx.jobs()["J1"],),
        carbon_facts=tuple(fact for fact in fx.forecasts() if 0 <= fact.valid_slot < 24),
    )
    return state, snap


def _plan_for(state: s.VisibleState) -> s.Plan:
    """Return a plan that starts J1 in the current slot."""
    evidence_ids = ["FACT-JOB-J1"]
    if state.constraint_ids:
        evidence_ids.insert(0, state.constraint_ids[0])
    return s.Plan(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        starts=(s.PlannedStart(job_id="J1", start_slot=state.current_slot),),
        evidence_ids=tuple(evidence_ids),
        status="proposed",
    )


def test_graph_conforms_for_single_job_state():
    """The K01 graph for a single waiting job and capacity evidence passes SHACL."""
    state, snap = _single_job_state_and_snapshot()
    graph = build_graph(state, snap)
    report = validate_graph(graph)
    assert report.conforms, report.report_text


def test_sparql_retrieves_capacity_constraint():
    """K02 SPARQL returns the site-wide capacity constraint with the correct value."""
    state, snap = _single_job_state_and_snapshot(capacity_kw=100.0)
    graph = build_graph(state, snap)
    constraints = query_constraints(graph)
    cap = next(c for c in constraints if c["constraint_type"] == "capacity")
    assert cap["constraint_id"] == "CON-CAP-01"
    assert cap["limit_value"] == 100.0
    assert cap["unit"] == "kW"
    assert cap["applies_to_site"] == "SITE1"
    assert cap["applies_to_jobs"] is None


def test_capacity_100_kw_allows_single_job():
    """A 100 kW capacity lets the 40 kW J1 start now; the checker passes."""
    state, snap = _single_job_state_and_snapshot(capacity_kw=100.0)
    plan = _plan_for(state)
    result = check_schedule(plan, state, snap)
    assert result.status == "pass"
    assert all(c.outcome == "pass" for c in result.performed)
    cap_check = next(c for c in result.performed if c.name == "capacity")
    assert cap_check.constraint_ids == ("CON-CAP-01",)


def test_capacity_70_kw_blocks_single_job():
    """A 70 kW capacity is below the 80 kW total IT load, so the checker fails."""
    state, snap = _single_job_state_and_snapshot(capacity_kw=70.0)
    plan = _plan_for(state)
    result = check_schedule(plan, state, snap)
    assert result.status == "fail"
    cap_check = next(c for c in result.performed if c.name == "capacity")
    assert cap_check.outcome == "fail"
    violations = [v for v in result.violations if v.violation_type == "capacity"]
    assert violations
    assert all("70" in v.message for v in violations)
    assert all(v.constraint_ids == ("CON-CAP-01",) for v in violations)


def test_retrieved_capacity_drives_checker_result():
    """The same SPARQL-retrieved capacity value that the graph exposes is what the checker uses."""
    for capacity, expected in ((100.0, "pass"), (70.0, "fail")):
        state, snap = _single_job_state_and_snapshot(capacity_kw=capacity)
        graph = build_graph(state, snap)
        retrieved = query_constraints(graph)
        cap = next(c for c in retrieved if c["constraint_type"] == "capacity")
        assert cap["limit_value"] == capacity
        result = check_schedule(_plan_for(state), state, snap)
        assert result.status == expected


def test_missing_capacity_fails_closed():
    """When no capacity constraint is in the snapshot, SHACL and the checker both fail closed."""
    state, snap = _single_job_state_and_snapshot(include_capacity=False)
    graph = build_graph(state, snap)
    report = validate_graph(graph)
    assert not report.conforms
    assert "capacity" in report.report_text.lower()

    constraints = query_constraints(graph)
    assert not any(c["constraint_type"] == "capacity" for c in constraints)

    plan = _plan_for(state)
    result = check_schedule(plan, state, snap)
    assert result.status == "error"
    cap_check = next(c for c in result.performed if c.name == "capacity")
    assert cap_check.outcome == "error"
    assert any("capacity" in e.lower() for e in result.errors)


def test_wrong_capacity_unit_fails_shacl():
    """A capacity constraint with the wrong unit is rejected by the K01 unit-consistency shape."""
    state, snap = _single_job_state_and_snapshot(capacity_kw=100.0)
    graph = build_graph(state, snap)
    cap_node = SCHED["CON-CAP-01"]
    from rdflib import Literal

    graph.remove((cap_node, SCHED.unit, None))
    graph.add((cap_node, SCHED.unit, Literal("MW")))
    report = validate_graph(graph)
    assert not report.conforms
    assert "unit" in report.report_text.lower()


def test_dangling_capacity_source_fails_shacl():
    """A capacity constraint referencing a missing source is rejected by the source-reference shape."""
    state, snap = _single_job_state_and_snapshot(capacity_kw=100.0)
    graph = build_graph(state, snap)
    cap_node = SCHED["CON-CAP-01"]
    graph.remove((cap_node, SCHED.source, None))
    graph.add((cap_node, SCHED.source, SCHED["SRC-MISSING"]))
    report = validate_graph(graph)
    assert not report.conforms
    assert "source" in report.report_text.lower()


def test_retrieve_bundles_capacity_context_and_constraints():
    """The K02 retrieve pipeline bundles the capacity constraint with the context hash."""
    state, snap = _single_job_state_and_snapshot(capacity_kw=100.0)
    result = retrieve(state, snap)
    cap = next(c for c in result.constraints if c["constraint_type"] == "capacity")
    assert cap["limit_value"] == 100.0
    context_cap = next(
        c for c in result.context.content.constraints if c.constraint_type == "capacity"
    )
    assert context_cap.limit_value == 100.0
    assert result.context.content_hash == s.Context.build(state, snap, "flat").content_hash


def test_capacity_change_changes_retrieved_context_hash():
    """Changing only the capacity limit changes the retrieved context hash."""
    state_100, snap_100 = _single_job_state_and_snapshot(capacity_kw=100.0)
    state_70, snap_70 = _single_job_state_and_snapshot(capacity_kw=70.0)
    result_100 = retrieve(state_100, snap_100)
    result_70 = retrieve(state_70, snap_70)
    assert result_100.context.content_hash != result_70.context.content_hash


def test_schema_rejects_duplicate_capacity_constraints():
    """The F02 schema itself rejects multiple capacity constraints before they reach the graph."""
    duplicate_capacity_constraints = (
        s.Constraint(
            constraint_id="CON-CAP-01",
            constraint_type="capacity",
            limit_value=100.0,
            unit="kW",
            applies_to_site="SITE1",
            source_id=fx.SOURCE_ID,
        ),
        s.Constraint(
            constraint_id="CON-CAP-02",
            constraint_type="capacity",
            limit_value=70.0,
            unit="kW",
            applies_to_site="SITE1",
            source_id=fx.SOURCE_ID,
        ),
    )
    with pytest.raises(ValueError, match="at most one capacity"):
        s.ConstraintSnapshot(
            snapshot_id="SNAP-DUP",
            site=fx.site(),
            constraints=duplicate_capacity_constraints,
            sources=(fx.source(),),
        )
