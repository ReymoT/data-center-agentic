"""Real synthetic sockets: drain ordering and rejection of incomplete HTTP bodies."""

import select
import socket
import time

import pytest

from dc_sustainability.llm.provider import CallBlocked
from tests.llm.test_ollama_provider import generate, provider
from tests.llm.test_ollama_provider import server as server  # noqa: F401


def read_body(connection, expected):
    wire = bytearray()
    while b"\r\n\r\n" not in wire or len(wire.partition(b"\r\n\r\n")[2]) < len(expected):
        block = connection.recv(65536)
        assert block, "server closed before the complete synthetic response"
        wire.extend(block)
    assert wire.partition(b"\r\n\r\n")[2] == expected


def connect(server):
    connection = socket.create_connection(("127.0.0.1", server.server_port), timeout=2)
    connection.sendall(b"POST /api/chat HTTP/1.0\r\nHost: localhost\r\nContent-Length: 2\r\n\r\n{}")
    return connection


def test_fixture_does_not_dispose_handle_before_peer_finishes(server):
    server.body = b'{"x":' * 4000 + b"0" + b"}" * 4000
    with connect(server) as connection:
        read_body(connection, server.body)
        assert server.shutdown_started.wait(1)
        assert not server.shutdown_outcomes
        assert not select.select([connection], [], [], 0)[0]  # no early server FIN
        # The client has all 24,001 unchanged bytes, but has not yet closed.
    assert server.wait_for_shutdowns(1, 1)
    assert server.shutdown_outcomes[0]["outcome"] == "peer_eof"


def test_fixture_drain_has_a_total_bound_and_does_not_claim_peer_eof(server):
    server.drain_timeout = 0.1
    server.body = b"synthetic"
    started = time.monotonic()
    with connect(server) as connection:
        read_body(connection, server.body)
        assert server.wait_for_shutdowns(1, 1)
        assert server.shutdown_outcomes[0]["outcome"] == "timeout"
    assert time.monotonic() - started < 2


@pytest.mark.parametrize("protocol", ["HTTP/1.0", "HTTP/1.1"])
def test_incomplete_body_stays_uncertain_spent_and_byte_preserved(server, monkeypatch, protocol):
    original = server.RequestHandlerClass.respond
    raw = b"partial-synthetic-body"
    monkeypatch.setattr(server.RequestHandlerClass, "protocol_version", protocol)

    def truncated(handler, body, status=200):
        if handler.path != "/api/chat":
            return original(handler, body, status)
        handler.send_response(200)
        handler.send_header("Content-Length", str(len(raw) + 641))
        handler.send_header("X-Request-ID", "synthetic-truncated")
        handler.end_headers()
        handler.wfile.write(raw)
        handler.connection.shutdown(socket.SHUT_WR)  # deliberate real truncation/EOF
        handler.close_connection = True

    monkeypatch.setattr(server.RequestHandlerClass, "respond", truncated)
    client = provider(server)
    attempt = generate(client, system="plain_llm")
    assert attempt.error == "incomplete response body"
    assert attempt.raw_response == raw and attempt.http_status == 200
    assert attempt.provider_request_id == "synthetic-truncated"
    assert attempt.output is None and attempt.uncertain_outcome
    assert attempt.prompt_tokens is attempt.completion_tokens is None
    assert client.attempts == (attempt,) and len(server.requests) == 1
    with pytest.raises(CallBlocked, match="per-decision attempt cap"):
        generate(client, system="plain_llm")
    assert client.attempts == (attempt,) and len(server.requests) == 1
