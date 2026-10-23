"""Real synthetic HTTP; decoder controls cover both platform-dependent branches."""

import json

import pytest

from dc_sustainability.llm.provider import CallBlocked
from tests.llm.test_ollama_provider import generate, provider
from tests.llm.test_ollama_provider import server as transport_server


@pytest.fixture
def pin_server():
    yield from transport_server.__wrapped__()


@pytest.mark.parametrize("path", ["/api/version", "/api/tags"])
@pytest.mark.parametrize("branch", ["reject_nesting", "decode_outer_list", "ordinary_list"])
def test_invalid_pin_metadata_preserves_exact_cause_and_never_spends_attempt(
    pin_server, monkeypatch, path, branch
):
    server = pin_server
    # These are explicit test-only decoder faults, not measured macOS execution.
    raw = b"[]" if branch == "ordinary_list" else b"[" * 4000 + b"0" + b"]" * 4000
    old_get, old_loads = server.RequestHandlerClass.do_GET, json.loads
    requested = []
    injected = RecursionError("synthetic decoder nesting rejection")

    def get(handler):
        requested.append(handler.path)
        if handler.path == path:
            handler.respond(raw)
        else:
            old_get(handler)

    def decode(data, *args, **kwargs):
        if data == raw and branch != "ordinary_list":
            if branch == "reject_nesting":
                raise injected
            return []  # Correct outer type of the nested array; not a fake model output.
        return old_loads(data, *args, **kwargs)

    monkeypatch.setattr(server.RequestHandlerClass, "do_GET", get)
    monkeypatch.setattr(json, "loads", decode)
    client = provider(server)
    with pytest.raises(CallBlocked, match="pre-dispatch verification failed") as caught:
        generate(client)
    if branch == "reject_nesting":
        assert caught.value.__cause__ is injected
    else:
        assert type(caught.value.__cause__) is AttributeError
        assert "get" in str(caught.value.__cause__)
    assert requested == (["/api/version"] if path == "/api/version" else ["/api/version", path])
    assert client.attempts == () and server.requests == [] and client._counts == {}
