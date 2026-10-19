"""Regression cases for actual L01 dispatch using synthetic HTTP, never inference."""

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.llm.plain import PlainLLMPolicy
from tests.llm.test_plain import propose, provider, state_and_context
from tests.llm.test_plain import server as server


@pytest.mark.parametrize("fault", ("stale_constraint_hash", "duplicate_context_jobs"))
def test_invalid_context_is_rejected_before_rendering_or_dispatch(server, fault):
    state, context = state_and_context()
    if fault == "stale_constraint_hash":
        content = context.content.model_copy(
            update={
                "constraints": tuple(
                    c.model_copy(update={"limit_value": 700})
                    if c.constraint_type == "capacity"
                    else c
                    for c in context.content.constraints
                )
            }
        )
        invalid = context.model_copy(update={"content": content})
    else:
        content = context.content.model_copy(
            update={"waiting_jobs": context.content.waiting_jobs * 2}
        )
        invalid = context.model_copy(
            update={"content": content, "content_hash": content.canonical_hash()}
        )
    # Prove the negative input violates F02, rather than changing its shared rules.
    with pytest.raises(ValueError):
        s.Context.model_validate(invalid.model_dump(mode="python", warnings="none"), strict=True)
    client = provider(server)
    with pytest.raises(ValueError):
        propose(PlainLLMPolicy(client), state, invalid)
    assert server.requests == []
    assert client.attempts == ()
