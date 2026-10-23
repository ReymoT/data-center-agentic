"""K02 graph construction tests: RDF triples, visibility, and no private leakage."""

from rdflib import RDF, Graph, Literal

from dc_sustainability import schemas as s
from dc_sustainability.knowledge.graph import SCHED, build_graph
from tests.contracts import fixtures as fx


def _state_and_snapshot(**snap_kw):
    """Build a default hand-example state and snapshot pair."""
    snap = fx.snapshot(**snap_kw)
    state = fx.visible_state(snap)
    return state, snap


def test_graph_is_rdflib_graph():
    """Verify build_graph returns an rdflib Graph with the sched namespace bound."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    assert isinstance(graph, Graph)
    assert len(graph) > 0


def test_episode_triples_present():
    """Verify the episode node carries current slot, state version, and snapshot ID."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    ep = SCHED[state.episode_id]
    assert (ep, RDF.type, SCHED.Episode) in graph
    assert (ep, SCHED.currentSlot, Literal(0)) in graph
    assert (ep, SCHED.stateVersion, Literal(0)) in graph


def test_site_triples_present():
    """Verify site config is represented with background, PUE, and slot hours."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    site = SCHED["SITE1"]
    assert (site, RDF.type, SCHED.Site) in graph
    assert (site, SCHED.backgroundKw, Literal(40.0)) in graph
    assert (site, SCHED.pue, Literal(1.0)) in graph
    assert (site, SCHED.slotHours, Literal(1.0)) in graph


def test_waiting_jobs_present():
    """Verify waiting jobs J1 and J2 are in the graph with correct properties."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    j1 = SCHED["J1"]
    assert (j1, RDF.type, SCHED.WaitingJob) in graph
    assert (j1, SCHED.arrivalSlot, Literal(0)) in graph
    assert (j1, SCHED.durationSlots, Literal(2)) in graph
    assert (j1, SCHED.powerKw, Literal(40.0)) in graph
    assert (j1, SCHED.deadlineSlot, Literal(6)) in graph
    assert (j1, SCHED.flexible, Literal(True)) in graph
    j2 = SCHED["J2"]
    assert (j2, RDF.type, SCHED.WaitingJob) in graph
    assert (j2, SCHED.powerKw, Literal(30.0)) in graph


def test_infeasible_job_j3_not_in_graph():
    """Verify J3 (not yet arrived at slot 0) is absent from the graph."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    j3 = SCHED["J3"]
    assert (j3, RDF.type, SCHED.WaitingJob) not in graph
    assert (j3, RDF.type, SCHED.RunningJob) not in graph
    assert (j3, RDF.type, SCHED.CompletedJob) not in graph


def test_forecasts_present():
    """Verify carbon forecasts are in the graph with correct values."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    f0 = SCHED["FACT-CI-s00"]
    assert (f0, RDF.type, SCHED.CarbonForecast) in graph
    assert (f0, SCHED.carbonValue, Literal(500.0)) in graph
    assert (f0, SCHED.validSlot, Literal(0)) in graph


def test_constraints_projected():
    """Verify only visible constraints appear (site-wide + visible-job constraints)."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    # CON-CAP-01 is site-wide, always visible
    cap = SCHED["CON-CAP-01"]
    assert (cap, RDF.type, SCHED.Constraint) in graph
    # CON-DL-J1 applies to J1 which is visible
    dl_j1 = SCHED["CON-DL-J1"]
    assert (dl_j1, RDF.type, SCHED.Constraint) in graph
    # CON-DL-J3 applies to J3 which is NOT visible at slot 0
    dl_j3 = SCHED["CON-DL-J3"]
    assert (dl_j3, RDF.type, SCHED.Constraint) not in graph


def test_missing_capacity_not_in_graph():
    """Verify a snapshot without capacity constraint produces no capacity triple."""
    state, snap = _state_and_snapshot(include_capacity=False)
    graph = build_graph(state, snap)
    cap = SCHED["CON-CAP-01"]
    assert (cap, RDF.type, SCHED.Constraint) not in graph


def test_no_private_keys_in_graph():
    """Verify no private fixture data (scenario, split, seed) appears in the graph."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    for _, _, obj in graph.triples((None, None, None)):
        text = str(obj)
        for private in ("scenario", "split", "seed", "synthetic", "oracle", "heldout"):
            assert private not in text.lower(), f"private token {private!r} found in graph"


def test_running_job_triples():
    """Verify running jobs carry start slot and job properties."""
    snap = fx.snapshot()
    j1 = fx.jobs()["J1"]
    state = s.VisibleState.from_snapshot(
        snap,
        episode_id="EP-HAND1",
        current_slot=1,
        state_version=1,
        waiting_jobs=(fx.jobs()["J2"],),
        running_jobs=(s.RunningJobView(job=j1, start_slot=0),),
        carbon_facts=tuple(
            f for f in fx.forecasts() if 1 <= f.valid_slot < 1 + s.PROPOSED_DECISION_SLOTS
        ),
    )
    graph = build_graph(state, snap)
    j1_node = SCHED["J1"]
    assert (j1_node, RDF.type, SCHED.RunningJob) in graph
    assert (j1_node, SCHED.startSlot, Literal(0)) in graph


def test_completed_job_triples():
    """Verify completed jobs carry start and end slots."""
    snap = fx.snapshot()
    state = s.VisibleState.from_snapshot(
        snap,
        episode_id="EP-HAND1",
        current_slot=3,
        state_version=3,
        waiting_jobs=(fx.jobs()["J2"],),
        completed_jobs=(s.CompletedJobView(job_id="J1", start_slot=0, end_slot=2),),
        carbon_facts=tuple(
            f for f in fx.forecasts() if 3 <= f.valid_slot < 3 + s.PROPOSED_DECISION_SLOTS
        ),
    )
    graph = build_graph(state, snap)
    j1_node = SCHED["J1"]
    assert (j1_node, RDF.type, SCHED.CompletedJob) in graph
    assert (j1_node, SCHED.startSlot, Literal(0)) in graph
    assert (j1_node, SCHED.endSlot, Literal(2)) in graph


def test_missing_carbon_slots_in_graph():
    """Verify explicit missing-forecast slots are recorded on the episode node."""
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
    ep = SCHED["EP-HAND1"]
    assert (ep, SCHED.missingCarbonSlot, Literal(0)) in graph
    assert (ep, SCHED.missingCarbonSlot, Literal(1)) in graph
    assert (ep, SCHED.missingCarbonSlot, Literal(2)) in graph


def test_source_triples_present():
    """Verify source provenance records are in the graph."""
    state, snap = _state_and_snapshot()
    graph = build_graph(state, snap)
    src = SCHED["SRC-HAND"]
    assert (src, RDF.type, SCHED.Source) in graph
    assert (src, SCHED.redistributionStatus, Literal("permitted")) in graph
