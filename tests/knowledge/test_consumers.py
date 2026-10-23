"""Matty's K02 consumer checks; HTTP responses are synthetic, never a model.

These exercise actual retrieval, plain-policy and checker code. No passing
execution permit, live inference or completed A02/K01 acceptance is fabricated.
"""

import time

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.knowledge import retrieve
from dc_sustainability.llm.plain import PlainLLMPolicy, render_messages
from dc_sustainability.verification.checker import check_schedule
from tests.contracts import fixtures as f
from tests.llm.test_plain import provider
from tests.llm.test_plain import server as server  # noqa: F401


def test_k02_flat_context_enters_actual_plain_policy(server):
    snapshot = f.snapshot()
    state = f.visible_state(snapshot)
    retrieved = retrieve(state, snapshot)
    client = provider(server)
    decision = PlainLLMPolicy(client).propose(
        state, retrieved.context, seed=101, decision_deadline=time.monotonic() + 10
    )
    assert len(server.requests) == len(client.attempts) == 1
    assert server.requests[0]["messages"] == render_messages(retrieved.context)
    assert decision.context_hash == retrieved.context.content_hash
    assert set(retrieved.context.content.evidence_ids) == set(s.evidence_ids_for(state, snapshot))
    assert "CON-DL-J3" not in server.requests[0]["messages"][1]["content"]
    # The synthetic model response is retained; this is not an execution approval.
    assert decision.output.raw_response is not None and decision.attempt is not None


def test_k02_graph_presentation_is_not_accepted_as_plain_input(server):
    snapshot = f.snapshot()
    state = f.visible_state(snapshot)
    retrieved = retrieve(state, snapshot, representation="graph")
    client = provider(server)
    with pytest.raises(ValueError, match="flat context"):
        PlainLLMPolicy(client).propose(
            state, retrieved.context, seed=101, decision_deadline=time.monotonic() + 10
        )
    assert not server.requests and not client.attempts


@pytest.mark.parametrize("capacity,expected", [(100.0, "pass"), (70.0, "fail")])
def test_k02_capacity_value_reaches_real_fixed_checker(capacity, expected):
    snapshot = f.snapshot(capacity_kw=capacity)
    state = f.visible_state(snapshot)
    retrieved = retrieve(state, snapshot)
    row = next(c for c in retrieved.constraints if c["constraint_type"] == "capacity")
    assert row["limit_value"] == capacity
    assert (
        next(
            c.limit_value
            for c in retrieved.context.content.constraints
            if c.constraint_type == "capacity"
        )
        == capacity
    )
    plan = s.Plan(
        episode_id=state.episode_id,
        slot=state.current_slot,
        state_version=state.state_version,
        status="proposed",
        starts=(s.PlannedStart(job_id="J1", start_slot=0),),
    )
    result = check_schedule(plan, state, snapshot)
    assert next(c.outcome for c in result.performed if c.name == "capacity") == expected
    assert result.status != "pass"  # Unresolved shared rules still prevent approval.


def test_k02_missing_capacity_stays_missing_at_checker_boundary():
    snapshot = f.snapshot(include_capacity=False)
    state = f.visible_state(snapshot)
    retrieved = retrieve(state, snapshot)
    assert not any(c["constraint_type"] == "capacity" for c in retrieved.constraints)
    plan = s.Plan(episode_id=state.episode_id, slot=0, state_version=0, status="proposed")
    result = check_schedule(plan, state, snapshot)
    assert result.status == "error"
    assert next(c.outcome for c in result.performed if c.name == "capacity") == "error"
    with pytest.raises(ValueError):
        s.ApprovedActions.from_checked_plan(plan, result, state.state_version)


def test_k02_exposed_query_values_match_canonical_facts():
    snapshot = f.snapshot(pue=1.2)
    state = f.visible_state(snapshot)
    retrieved = retrieve(state, snapshot)
    assert {j["job_id"]: j for j in retrieved.eligible_jobs} == {
        j.job_id: j.model_dump(exclude={"record_type", "schema_version"})
        for j in state.waiting_jobs
    }
    assert retrieved.site == state.site.model_dump(exclude={"record_type", "schema_version"})
    by_id = {fact.fact_id: fact for fact in state.carbon_facts}
    for row in retrieved.forecasts:
        fact = by_id[row["fact_id"]]
        assert (row["value"], row["valid_slot"], row["source_id"], row["forecast_kind"]) == (
            fact.value,
            fact.valid_slot,
            fact.source_id,
            fact.forecast_kind,
        )
        assert row["issued_at_utc"] == fact.issued_at_utc.isoformat().replace("+00:00", "Z")
    # This checks exposed query fields, not a reconstruction of Context from RDF.
    assert retrieved.context.content_hash == s.Context.build(state, snapshot, "flat").content_hash
