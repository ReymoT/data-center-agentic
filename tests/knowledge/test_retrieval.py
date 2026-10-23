"""K02 retrieval tests: SPARQL queries, context equivalence, and visibility."""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.knowledge.graph import build_graph
from dc_sustainability.knowledge.retrieval import (
    get_context,
    query_constraints,
    query_eligible_jobs,
    query_forecasts,
    query_missing_carbon_slots,
    query_running_jobs,
    query_site,
    retrieve,
)
from tests.contracts import fixtures as fx


def _state_and_snapshot(**snap_kw):
    snap = fx.snapshot(**snap_kw)
    state = fx.visible_state(snap)
    return state, snap


# ---------------------------------------------------------------- SPARQL queries


def test_query_eligible_jobs():
    """Verify SPARQL returns the two waiting jobs with correct fields."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    jobs = query_eligible_jobs(graph)
    assert len(jobs) == 2
    by_id = {j["job_id"]: j for j in jobs}
    assert by_id["J1"]["power_kw"] == 40.0
    assert by_id["J1"]["duration_slots"] == 2
    assert by_id["J2"]["power_kw"] == 30.0


def test_query_running_jobs_empty():
    """Verify no running jobs at slot 0."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    assert query_running_jobs(graph) == []


def test_query_forecasts():
    """Verify SPARQL returns all visible forecasts with correct values."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    forecasts = query_forecasts(graph)
    assert len(forecasts) == 7
    by_slot = {f["valid_slot"]: f for f in forecasts}
    assert by_slot[0]["value"] == 500.0
    assert by_slot[6]["value"] == 520.0


def test_query_constraints():
    """Verify SPARQL returns only visible constraints (not J3's deadline)."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    constraints = query_constraints(graph)
    ids = {c["constraint_id"] for c in constraints}
    assert "CON-CAP-01" in ids
    assert "CON-DL-J1" in ids
    assert "CON-DL-J3" not in ids


def test_query_missing_carbon_slots():
    """Verify missing carbon slots are returned when present."""
    snap = fx.snapshot()
    state = s.VisibleState.from_snapshot(
        snap,
        episode_id="EP-HAND1",
        current_slot=0,
        state_version=0,
        waiting_jobs=(fx.jobs()["J1"],),
        carbon_facts=(),
        missing_carbon_slots=(0, 1, 2),
    )
    graph = build_graph(state, snap)
    assert query_missing_carbon_slots(graph) == [0, 1, 2]


def test_query_site():
    """Verify site config is returned with correct values."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    site = query_site(graph)
    assert site["site_id"] == "SITE1"
    assert site["background_kw"] == 40.0
    assert site["pue"] == 1.0


# ---------------------------------------------------------------- context equivalence


def test_context_hash_matches_flat_build():
    """Verify get_context produces the same hash as Context.build with flat representation."""
    state, snap = _state_and_snapshot()
    ctx = get_context(state, snap, representation="flat")
    expected = s.Context.build(state, snap, representation="flat")
    assert ctx.content_hash == expected.content_hash


def test_graph_and_flat_context_same_hash():
    """Verify graph and flat representations carry the same content hash."""
    state, snap = _state_and_snapshot()
    ctx_flat = get_context(state, snap, representation="flat")
    ctx_graph = get_context(state, snap, representation="graph")
    assert ctx_flat.content_hash == ctx_graph.content_hash
    assert ctx_flat.representation == "flat"
    assert ctx_graph.representation == "graph"


def test_context_evidence_ids_match():
    """Verify context evidence IDs match the expected visible records."""
    state, snap = _state_and_snapshot()
    ctx = get_context(state, snap)
    expected = s.evidence_ids_for(state, snap)
    assert set(ctx.content.evidence_ids) == set(expected)


def test_context_no_private_keys():
    """Verify context content has no private fixture keys."""
    state, snap = _state_and_snapshot()
    ctx = get_context(state, snap)
    data = ctx.content.to_jsonable()
    s.assert_no_private_keys(data)


# ---------------------------------------------------------------- retrieve pipeline


def test_retrieve_returns_full_result():
    """Verify retrieve() returns a RetrievalResult with all fields populated."""
    state, snap = _state_and_snapshot()
    result = retrieve(state, snap)
    assert (
        result.context.content_hash
        == s.Context.build(state, snap, representation="flat").content_hash
    )
    assert len(result.eligible_jobs) == 2
    assert len(result.forecasts) == 7
    assert result.site["site_id"] == "SITE1"


def test_retrieve_constraints_match_context():
    """Verify SPARQL constraint IDs match the context's constraint IDs."""
    state, snap = _state_and_snapshot()
    result = retrieve(state, snap)
    sparql_ids = {c["constraint_id"] for c in result.constraints}
    context_ids = {c.constraint_id for c in result.context.content.constraints}
    assert sparql_ids == context_ids


def test_retrieve_eligible_jobs_match_context():
    """Verify SPARQL eligible job IDs match the context's waiting job IDs."""
    state, snap = _state_and_snapshot()
    result = retrieve(state, snap)
    sparql_ids = {j["job_id"] for j in result.eligible_jobs}
    context_ids = {j.job_id for j in result.context.content.waiting_jobs}
    assert sparql_ids == context_ids


def test_retrieve_forecasts_match_context():
    """Verify SPARQL forecast fact IDs match the context's carbon fact IDs."""
    state, snap = _state_and_snapshot()
    result = retrieve(state, snap)
    sparql_ids = {f["fact_id"] for f in result.forecasts}
    context_ids = {f.fact_id for f in result.context.content.carbon_facts}
    assert sparql_ids == context_ids


# ---------------------------------------------------------------- visibility


def test_future_job_not_leaked():
    """Verify J3 (arrives slot 4) is not in the graph or context at slot 0."""
    state, snap = _state_and_snapshot()
    result = retrieve(state, snap)
    all_job_ids = {j["job_id"] for j in result.eligible_jobs}
    all_job_ids |= {j["job_id"] for j in result.running_jobs}
    assert "J3" not in all_job_ids
    constraint_ids = {c["constraint_id"] for c in result.constraints}
    assert "CON-DL-J3" not in constraint_ids


def test_capacity_change_changes_context():
    """Verify changing capacity from 100 to 70 kW changes the context hash."""
    state_100, snap_100 = _state_and_snapshot(capacity_kw=100.0)
    state_70, snap_70 = _state_and_snapshot(capacity_kw=70.0)
    ctx_100 = get_context(state_100, snap_100)
    ctx_70 = get_context(state_70, snap_70)
    assert ctx_100.content_hash != ctx_70.content_hash
    cap_100 = [c for c in ctx_100.content.constraints if c.constraint_type == "capacity"][0]
    cap_70 = [c for c in ctx_70.content.constraints if c.constraint_type == "capacity"][0]
    assert cap_100.limit_value == 100.0
    assert cap_70.limit_value == 70.0


def test_missing_capacity_raises_in_snapshot():
    """Verify a snapshot without capacity raises MissingEvidenceError on capacity_kw."""
    _, snap = _state_and_snapshot(include_capacity=False)
    with pytest.raises(s.MissingEvidenceError):
        _ = snap.capacity_kw
