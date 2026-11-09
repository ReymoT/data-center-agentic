"""Opt-in response settings through real transport code and synthetic HTTP only."""

import json

import pytest

from dc_sustainability import schemas as s
from dc_sustainability.experiments import models
from dc_sustainability.experiments.config import ModelSettings
from dc_sustainability.llm.provider import CallBlocked, OllamaProvider
from tests.contracts import fixtures as f
from tests.llm.test_ollama_provider import deployment, generate
from tests.llm.test_ollama_provider import server as _server_fixture

server = _server_fixture


@pytest.mark.parametrize(
    "system,model", [("agent", s.Plan), ("agent", s.Explanation), ("plain_llm", s.PolicyOutput)]
)
def test_candidate_reaches_normal_request_entry_point(server, system, model):
    config = deployment(
        server, output_tokens=4096, explanation_characters=256, max_prompt_tokens=12288
    )
    explanation = s.Explanation(source="llm", summary="Synthetic profile test.")
    value = {
        s.Plan: f.plan(),
        s.Explanation: explanation,
        s.PolicyOutput: s.PolicyOutput(
            system="plain_llm", output_status="ok", plan=f.plan(), explanation=explanation
        ),
    }[model]
    server.body["message"]["content"] = value.to_json()
    client = OllamaProvider(config, count_prompt_tokens=lambda request: 20)
    result = generate(client, system=system, response_model=model)
    assert result.output == value
    request = server.requests[0]
    assert request["options"]["num_predict"] == 4096
    schema = request["format"]
    if model is not s.Plan:
        definition = schema if model is s.Explanation else schema["$defs"]["Explanation"]
        assert definition["properties"]["summary"]["maxLength"] == 256
        claim_branches = schema["$defs"]["Claim"]["anyOf"]
        assert [b["properties"]["text"]["maxLength"] for b in claim_branches] == [256, 256]
    if model is not s.Explanation:
        detail = schema["$defs"]["Deferral"]["properties"]["detail"]
        assert next(x for x in detail["anyOf"] if x.get("type") == "string")["maxLength"] == 96


def test_candidate_prompt_budget_blocks_before_dispatch(server):
    config = deployment(
        server, output_tokens=4096, explanation_characters=256, max_prompt_tokens=12288
    )
    client = OllamaProvider(config, count_prompt_tokens=lambda request: 12289)
    with pytest.raises(CallBlocked, match="context budget"):
        generate(client)
    assert not server.requests and not client.attempts
    with pytest.raises(ValueError, match="leave room"):
        deployment(server, output_tokens=4096, explanation_characters=256, max_prompt_tokens=12289)
    with pytest.raises(ValueError, match="explicit 256/4096"):
        deployment(server, output_tokens=1536, explanation_characters=256)


def test_legacy_pins_and_configuration_identity_remain_compatible(server):
    legacy = deployment(server)
    pins = models.deployment_pins(legacy)
    assert "output_tokens" not in pins and "explanation_characters" not in pins
    frozen = json.loads(json.dumps(pins))
    settings = ModelSettings(
        seeds=((0, 7),), decision_seconds=3, max_total_attempts=24, deployment=frozen
    )
    identity = settings.identity()
    inputs = models.ModelInputs(
        provider_factory=lambda: OllamaProvider(legacy, count_prompt_tokens=lambda request: 20)
    )
    assert models.new_provider(settings, inputs).deployment == legacy
    assert settings.identity() == identity
    candidate = deployment(
        server, output_tokens=4096, explanation_characters=256, max_prompt_tokens=12288
    )
    candidate_pins = models.deployment_pins(candidate)
    assert candidate_pins["output_tokens"] == 4096
    assert candidate_pins["explanation_characters"] == 256


def test_launcher_uses_explicit_candidate_without_changing_envelope():
    from dataclasses import replace

    from dc_sustainability.llm.provider import Deployment
    from scripts.run_i01_public_receiving import MODEL_DIGEST, candidate_deployment

    config = Deployment(
        base_url="http://127.0.0.1:11439",
        runtime_version="0.40.5",
        model_digest=MODEL_DIGEST,
        max_run_attempts=18,
        max_response_bytes=2 * 1024 * 1024,
        max_prompt_tokens=12288,
        context_policy_ref="offline-candidate-not-native-validated",
        request_timeout_seconds=150,
        output_tokens=4096,
        explanation_characters=256,
    )
    identity = {"model": {"deployment": models.deployment_pins(config)}}
    assert candidate_deployment(identity, 11439) == config
    identity["model"]["deployment"] = models.deployment_pins(replace(config, max_run_attempts=19))
    with pytest.raises(ValueError, match="fixed receiving envelope"):
        candidate_deployment(identity, 11439)
