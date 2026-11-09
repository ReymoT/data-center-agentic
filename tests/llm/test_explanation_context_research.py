"""Candidate schema research must leave runtime schema and plan bounds intact."""

import copy

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.llm.response_bounds import bounded_response_schema
from scripts.check_explanation_context import candidate_schema
from tests.contracts import fixtures as f


@pytest.mark.parametrize("model", [s.Plan, s.PolicyOutput, s.Explanation])
def test_candidate_changes_only_explanation_text_lengths(model):
    original, _ = bounded_response_schema(model, f.visible_state(), system="plain_llm")
    retained = copy.deepcopy(original)
    candidate = candidate_schema(original)
    assert original == retained
    assert candidate is not original
    if model is s.Plan:
        assert candidate == original
        return
    explanation = candidate if model is s.Explanation else candidate["$defs"]["Explanation"]
    assert explanation["properties"]["summary"]["maxLength"] == 256
    assert explanation["properties"]["limitations"]["items"]["maxLength"] == 256
    branches = candidate["$defs"]["Claim"]["anyOf"]
    assert [branch["properties"]["text"]["maxLength"] for branch in branches] == [256, 256]
    explanation["properties"]["summary"]["maxLength"] = 96
    explanation["properties"]["limitations"]["items"]["maxLength"] = 96
    for branch in branches:
        branch["properties"]["text"]["maxLength"] = 96
    assert candidate == original


def test_candidate_schema_still_reads_saved_single_object_claims():
    saved = {
        "title": "Explanation",
        "properties": {
            "summary": {"maxLength": 96},
            "limitations": {"items": {"maxLength": 96}},
        },
        "$defs": {"Claim": {"properties": {"text": {"maxLength": 96}}}},
    }
    candidate = candidate_schema(saved)
    assert candidate["$defs"]["Claim"]["properties"]["text"]["maxLength"] == 256
    assert saved["$defs"]["Claim"]["properties"]["text"]["maxLength"] == 96
