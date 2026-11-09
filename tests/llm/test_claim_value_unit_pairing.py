"""Paired claim value/unit rule in the request-local schema (offline; synthetic HTTP only).

RUN-bc420d3e8d72 stopped because a generated Agent explanation carried claims with a
unit and a null value.  F02 rejected it correctly; the request schema allowed it.
These tests check the request schema separately from F02, using a small checker for
exactly the JSON-schema keywords the pinned converter reads.  They are not native
grammar or model evidence; that remains a live-validation check.
"""

import json
import math
import re

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.llm.response_bounds import bounded_response_schema
from tests.contracts import fixtures as f
from tests.llm.test_ollama_provider import deployment, generate
from tests.llm.test_ollama_provider import server as _server_fixture

server = _server_fixture

# The pinned converter (llama.cpp b11669, used by Ollama 0.40.5) does not read these.
IGNORED_BY_CONVERTER = {
    "if",
    "then",
    "else",
    "not",
    "dependentRequired",
    "dependentSchemas",
    "oneOf",
    "allOf",
}
MISSING = object()
EVIDENCE = ["FACT-CI-s03"]
PROFILES = [96, 256]
SYSTEMS = [(s.Explanation, "agent"), (s.PolicyOutput, "plain_llm")]


def _resolve(node, root):
    while "$ref" in node:
        node = root["$defs"][node["$ref"].rsplit("/", 1)[-1]]
    return node


def accepts(instance, node, root):
    """Decide one instance against the request schema subset; no F02 code is used."""
    node = _resolve(node, root)
    if "anyOf" in node:
        return any(accepts(instance, branch, root) for branch in node["anyOf"])
    if "const" in node and instance != node["const"]:
        return False
    if "enum" in node and instance not in node["enum"]:
        return False
    kind = node.get("type")
    if kind == "null":
        return instance is None
    if kind == "number":
        return (
            isinstance(instance, (int, float))
            and not isinstance(instance, bool)
            and math.isfinite(instance)
        )
    if kind == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if kind == "string":
        if not isinstance(instance, str):
            return False
        if len(instance) < node.get("minLength", 0):
            return False
        if "maxLength" in node and len(instance) > node["maxLength"]:
            return False
        return "pattern" not in node or re.search(node["pattern"], instance) is not None
    if kind == "array":
        if not isinstance(instance, list) or len(instance) > node.get("maxItems", len(instance)):
            return False
        return all(accepts(item, node.get("items", {}), root) for item in instance)
    if kind == "object" or "properties" in node:
        if not isinstance(instance, dict):
            return False
        properties = node.get("properties", {})
        if node.get("additionalProperties") is False and set(instance) - set(properties):
            return False
        if set(node.get("required", ())) - set(instance):
            return False
        return all(accepts(instance[k], properties[k], root) for k in instance if k in properties)
    return True


def claim(value=MISSING, unit=MISSING, evidence=EVIDENCE, **extra):
    record = {"claim_id": "C1", "text": "Slot 3 is forecast at 250 g/kWh."}
    if evidence is not MISSING:
        record["evidence_ids"] = list(evidence)
    if value is not MISSING:
        record["value"] = value
    if unit is not MISSING:
        record["unit"] = unit
    record.update(extra)
    return record


def f02_accepts(record):
    try:
        s.Claim.from_json(json.dumps(record))
    except (ValueError, TypeError):
        return False
    return True


def wrap(claims, model):
    explanation = {"source": "llm", "summary": "Start J1 at slot 2.", "claims": claims}
    if model is s.Explanation:
        return explanation
    output = json.loads(
        s.PolicyOutput(system="plain_llm", output_status="ok", plan=f.plan()).to_json()
    )
    output["plan"]["evidence_ids"] = []  # the fixture plan cites more IDs than a request allows
    output["explanation"] = explanation
    return output


# (case, claim, request schema accepts, F02 accepts)
CASES = [
    ("observed null value with g/kWh", claim(None, "g/kWh"), False, False),
    ("observed null value with slot", claim(None, "slot"), False, False),
    ("omitted value with unit", claim(unit="kg"), False, False),
    ("number with null unit", claim(250.0, None), False, False),
    ("number with omitted unit", claim(250.0), False, False),
    ("number and allowed unit", claim(250.0, "g/kWh"), True, True),
    ("zero and unit", claim(0.0, "kg"), True, True),
    ("negative per existing F02", claim(-8.5, "kg"), True, True),
    ("JSON integer and unit", claim(4, "slot"), True, True),
    ("both null", claim(None, None), True, True),
    ("both null, no evidence", claim(None, None, evidence=[]), True, True),
    # Generation requires explicit keys; the stored F02 contract still allows omission.
    ("both omitted", claim(), False, True),
    ("numeric with omitted evidence list", claim(1.0, "kg", evidence=MISSING), False, True),
    ("boolean value", claim(True, "kg"), False, False),
    ("string value", claim("250", "g/kWh"), False, False),
    ("unsupported unit", claim(250.0, "MWh"), False, False),
    ("extra key", claim(None, None, note="x"), False, False),
]


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("model,system", SYSTEMS)
@pytest.mark.parametrize("case,record,request_ok,f02_ok", CASES, ids=[c[0] for c in CASES])
def test_request_schema_enforces_pairing_separately_from_f02(
    profile, model, system, case, record, request_ok, f02_ok
):
    schema, _ = bounded_response_schema(
        model, f.visible_state(), system=system, explanation_characters=profile
    )
    assert accepts(wrap([record], model), schema, schema) is request_ok
    assert f02_accepts(record) is f02_ok
    # Anything the request schema permits must also pass the final F02 gate.
    assert not request_ok or f02_ok


def test_nonfinite_values_remain_f02_failures():
    for value in (float("nan"), float("inf"), -float("inf")):
        with pytest.raises(ValueError):
            s.Claim(claim_id="C1", text="Synthetic.", value=value, unit="kg")


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("model,system", SYSTEMS)
def test_counts_lengths_and_evidence_limits_are_unchanged(profile, model, system):
    schema, _ = bounded_response_schema(
        model, f.visible_state(), system=system, explanation_characters=profile
    )
    numeric = claim(22.0, "kg")
    four = [dict(numeric, claim_id=f"C{i}") for i in range(1, 5)]
    assert accepts(wrap([], model), schema, schema)
    assert accepts(wrap(four, model), schema, schema)
    assert not accepts(wrap(four + [dict(numeric, claim_id="C5")], model), schema, schema)
    too_many = ["FACT-CI-s01", "FACT-CI-s02", "FACT-CI-s03"]
    assert not accepts(wrap([claim(1.0, "kg", evidence=too_many)], model), schema, schema)
    assert not accepts(wrap([claim(1.0, "kg", evidence=["FACT-CI-s99"])], model), schema, schema)
    assert accepts(wrap([dict(numeric, text="x" * profile)], model), schema, schema)
    assert not accepts(wrap([dict(numeric, text="x" * (profile + 1))], model), schema, schema)
    assert not accepts(wrap([dict(numeric, claim_id="C" * 17)], model), schema, schema)


@pytest.mark.parametrize("profile", PROFILES)
def test_plain_and_agent_carry_the_same_claim_rule_with_supported_keywords(profile):
    state = f.visible_state()
    agent, _ = bounded_response_schema(
        s.Explanation, state, system="agent", explanation_characters=profile
    )
    plain, _ = bounded_response_schema(
        s.PolicyOutput, state, system="plain_llm", explanation_characters=profile
    )
    assert agent["$defs"]["Claim"] == plain["$defs"]["Claim"]
    branches = agent["$defs"]["Claim"]["anyOf"]
    keys = ["claim_id", "text", "evidence_ids", "value", "unit"]
    assert [list(b["properties"]) for b in branches] == [keys, keys]
    assert [b["required"] for b in branches] == [keys, keys]
    assert branches[0]["properties"]["value"] == branches[0]["properties"]["unit"]
    assert branches[0]["properties"]["unit"] == {"type": "null"}
    assert branches[1]["properties"]["value"] == {"type": "number"}
    assert branches[1]["properties"]["unit"]["enum"] == ["kW", "kWh", "slot", "h", "g/kWh", "kg"]

    def keywords(node):
        if isinstance(node, dict):
            yield from node
            for value in node.values():
                yield from keywords(value)
        elif isinstance(node, list):
            for value in node:
                yield from keywords(value)

    for schema in (agent, plain):
        assert not IGNORED_BY_CONVERTER & set(keywords(schema))


@pytest.mark.parametrize("profile", PROFILES)
def test_plan_requests_carry_no_claim_and_f02_schema_is_unchanged(profile):
    before = json.dumps(s.Claim.model_json_schema(), sort_keys=True)
    schema, _ = bounded_response_schema(
        s.Plan, f.visible_state(), system="agent", explanation_characters=profile
    )
    assert "Claim" not in json.dumps(schema)
    assert json.dumps(s.Claim.model_json_schema(), sort_keys=True) == before
    f02_claim = s.Claim.model_json_schema()["properties"]
    assert {"type": "null"} in f02_claim["value"]["anyOf"]
    assert {"type": "null"} in f02_claim["unit"]["anyOf"]


def _reply(server, model, claims):
    server.body["message"]["content"] = json.dumps(wrap(claims, model))


@pytest.mark.parametrize("profile,tokens,prompt", [(96, 1536, 1000), (256, 4096, 1000)])
@pytest.mark.parametrize("model,system", SYSTEMS)
def test_entry_point_sends_paired_claims_and_keeps_contract_failures(
    server, profile, tokens, prompt, model, system
):
    from dc_sustainability.llm.provider import OllamaProvider

    config = deployment(
        server,
        output_tokens=tokens,
        explanation_characters=profile,
        max_prompt_tokens=prompt,
    )
    client = OllamaProvider(config, count_prompt_tokens=lambda request: 20)
    bad = [claim(None, "g/kWh"), dict(claim(None, "slot"), claim_id="C2")]
    _reply(server, model, bad)
    sent = server.body["message"]["content"]
    attempt = generate(client, system=system, response_model=model)

    request = server.requests[0]
    expected, _ = bounded_response_schema(
        model, f.visible_state(), system=system, explanation_characters=profile
    )
    assert request["format"] == expected
    assert len(request["format"]["$defs"]["Claim"]["anyOf"]) == 2
    # The rejected response is a spent, retained attempt: no retry, no rewrite.
    assert attempt.output is None
    assert attempt.error.startswith("invalid response:")
    assert "value and unit" in attempt.error
    assert json.loads(attempt.raw_response)["message"]["content"] == sent
    assert len(server.requests) == 1 and len(client.attempts) == 1

    _reply(server, model, [claim(250.0, "g/kWh"), dict(claim(None, None), claim_id="C2")])
    fresh = OllamaProvider(config, count_prompt_tokens=lambda request: 20)
    good = generate(fresh, system=system, response_model=model)
    assert good.error is None
    explanation = good.output if model is s.Explanation else good.output.explanation
    assert [(c.value, c.unit) for c in explanation.claims] == [(250.0, "g/kWh"), (None, None)]
