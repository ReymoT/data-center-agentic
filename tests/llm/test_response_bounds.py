"""Offline A01 request-local response-bound tests; no provider or model calls."""

from copy import deepcopy

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.llm.response_bounds import (
    ResponseBounds,
    bounded_response_schema,
    response_bounds,
)
from tests.contracts import fixtures as f


def state_with_waiting(count: int) -> s.VisibleState:
    base = f.visible_state(current_slot=0)
    jobs = tuple(
        s.Job(
            job_id=f"J{index:02d}",
            arrival_slot=0,
            duration_slots=1,
            power_kw=10,
            deadline_slot=24,
            flexible=True,
        )
        for index in range(1, count + 1)
    )
    return base.model_copy(update={"waiting_jobs": jobs})


def definition(schema: dict, name: str) -> dict:
    return schema if schema.get("title") == name else schema["$defs"][name]


@pytest.mark.parametrize("count", [1, 3, 20])
@pytest.mark.parametrize("record", [s.Plan, s.PolicyOutput])
def test_plan_bound_always_allows_every_waiting_job(count, record):
    state = state_with_waiting(count)
    schema, limits = bounded_response_schema(record, state, system="plain_llm")
    plan = definition(schema, "Plan")
    assert limits.plan_entries == count
    assert all(
        plan["properties"][name]["maxItems"] == count
        for name in ("starts", "deferrals", "abstentions")
    )
    assert definition(schema, "PlannedStart")["properties"]["job_id"]["enum"] == [
        job.job_id for job in state.waiting_jobs
    ]
    assert plan["properties"]["episode_id"]["const"] == state.episode_id
    assert plan["properties"]["slot"]["const"] == state.current_slot
    assert plan["properties"]["state_version"]["const"] == state.state_version
    assert plan["properties"]["status"]["const"] == "proposed"
    assert {"record_type", "schema_version"} <= set(plan["required"])
    assert definition(schema, "PlannedStart")["properties"]["start_slot"]["maximum"] == 29


def test_plain_and_agent_explanation_bounds_are_identical():
    state = state_with_waiting(20)
    plain, plain_limits = bounded_response_schema(s.PolicyOutput, state, system="plain_llm")
    agent, agent_limits = bounded_response_schema(s.Explanation, state, system="agent")
    assert plain_limits == agent_limits == ResponseBounds(plan_entries=20)
    for schema in (plain, agent):
        explanation = definition(schema, "Explanation")
        claim = definition(schema, "Claim")
        assert explanation["properties"]["claims"]["maxItems"] == 4
        assert explanation["properties"]["limitations"]["maxItems"] == 4
        assert explanation["properties"]["summary"]["maxLength"] == 96
        assert explanation["properties"]["limitations"]["items"]["maxLength"] == 96
        assert claim["properties"]["text"]["maxLength"] == 96
        assert claim["properties"]["claim_id"]["maxLength"] == 16
        assert claim["properties"]["evidence_ids"]["maxItems"] == 2


def test_policy_output_is_one_valid_uncorrected_plain_shape():
    schema, _ = bounded_response_schema(s.PolicyOutput, state_with_waiting(3), system="plain_llm")
    assert schema["properties"]["system"] == {"const": "plain_llm", "type": "string"}
    assert schema["properties"]["output_status"] == {"const": "ok", "type": "string"}
    assert schema["properties"]["raw_response"] == {"const": None, "type": "null"}
    assert {"record_type", "schema_version"} <= set(schema["required"])


def test_bounds_do_not_mutate_f02_schema():
    original = deepcopy(s.PolicyOutput.model_json_schema())
    bounded_response_schema(s.PolicyOutput, state_with_waiting(3), system="plain_llm")
    assert s.PolicyOutput.model_json_schema() == original


def test_empty_queue_schema_has_zero_plan_entries_while_policy_remains_no_call():
    state = f.visible_state(current_slot=0).model_copy(update={"waiting_jobs": ()})
    assert response_bounds(state).plan_entries == 0
    schema, _ = bounded_response_schema(s.Plan, state, system="agent")
    assert all(
        schema["properties"][name]["maxItems"] == 0
        for name in ("starts", "deferrals", "abstentions")
    )
