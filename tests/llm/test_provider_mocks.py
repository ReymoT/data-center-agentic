"""Verify the fake's fault delivery and call evidence, not production LLM behavior."""

import socket
import urllib.request

import pytest

from tests.llm.mock_transport import ScriptedTransport


def test_mock_runs_without_credentials_or_network(monkeypatch):
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LANGSMITH_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    def network_forbidden(*args, **kwargs):
        raise AssertionError("Provider mock attempted network access")

    monkeypatch.setattr(socket.socket, "connect", network_forbidden)
    monkeypatch.setattr(socket, "create_connection", network_forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", network_forbidden)
    provider = ScriptedTransport(["synthetic response"])
    assert provider("synthetic request") == "synthetic response"
    provider.assert_consumed()


@pytest.mark.parametrize("raw", ["", "not JSON", '{"unfinished":', {"unexpected": [None]}])
def test_bad_outputs_reach_the_callers_parser_unchanged(raw):
    provider = ScriptedTransport([raw])
    assert provider("request") == raw
    assert provider.attempt_count == 1
    provider.assert_consumed()


@pytest.mark.parametrize("failure", [TimeoutError("synthetic timeout"), ConnectionError("offline")])
def test_failures_are_counted_without_hidden_retry(failure):
    provider = ScriptedTransport([failure, "only after an explicit second call"])
    with pytest.raises(type(failure), match=str(failure)):
        provider("first request")
    assert provider.attempt_count == 1
    assert provider.remaining_count == 1
    assert provider.calls[0].args == ("first request",)
    assert provider("explicit retry") == "only after an explicit second call"
    assert provider.attempt_count == 2
    provider.assert_consumed()


def test_one_call_plain_script_flags_an_unexpected_second_call():
    provider = ScriptedTransport(["raw plain response"])
    assert provider("flat facts") == "raw plain response"
    with pytest.raises(AssertionError, match="Unexpected provider call 2"):
        provider("unscripted corrective feedback")
    assert provider.attempt_count == 2
    assert provider.calls[-1].args == ("unscripted corrective feedback",)


def test_three_call_agent_script_preserves_a_failed_repair_attempt():
    provider = ScriptedTransport(
        ["raw proposal", TimeoutError("repair timed out"), "raw explanation"]
    )
    assert provider("proposal request") == "raw proposal"
    with pytest.raises(TimeoutError, match="repair timed out"):
        provider("repair request")
    assert provider("explanation request") == "raw explanation"
    assert [call.args[0] for call in provider.calls] == [
        "proposal request",
        "repair request",
        "explanation request",
    ]
    provider.assert_consumed()
    with pytest.raises(AssertionError, match="Unexpected provider call 4"):
        provider("unscripted extra repair")


def test_recorded_requests_survive_caller_mutation():
    request = {"messages": [{"content": "original synthetic facts"}]}
    provider = ScriptedTransport(["response"])
    provider(request, settings={"test_setting": [1]})
    request["messages"][0]["content"] = "changed after request"
    assert provider.calls[0].args[0] == {"messages": [{"content": "original synthetic facts"}]}
    obtained_log = provider.calls
    obtained_log[0].kwargs["settings"]["test_setting"].append(2)
    assert provider.calls[0].kwargs == {"settings": {"test_setting": [1]}}


def test_response_scripts_survive_mutation_between_calls():
    canned = {"synthetic": ["original"]}
    provider = ScriptedTransport([canned, canned])
    canned["synthetic"].append("changed after scripting")
    first = provider()
    first["synthetic"].append("changed by caller")
    assert provider() == {"synthetic": ["original"]}
    provider.assert_consumed()


def test_unexercised_script_stage_is_not_silent_success():
    provider = ScriptedTransport(["proposal", "explanation"])
    provider()
    with pytest.raises(AssertionError, match="1 scripted provider outcomes were not used"):
        provider.assert_consumed()


def test_empty_script_records_and_rejects_first_unexpected_attempt():
    provider = ScriptedTransport([])
    provider.assert_consumed()
    with pytest.raises(AssertionError, match="Unexpected provider call 1"):
        provider("unexpected request")
    assert provider.attempt_count == 1
    assert provider.remaining_count == 0
