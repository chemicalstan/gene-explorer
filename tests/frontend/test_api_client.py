import httpx
import pytest
from api_client import (
    AUTH_ERROR,
    RATE_LIMIT_ERROR,
    SERVER_ERROR,
    TIMEOUT_ERROR,
    UNAVAILABLE_ERROR,
    GeneExplorerClient,
)


def _client(handler, **kwargs) -> GeneExplorerClient:
    return GeneExplorerClient(
        "http://backend:8000", transport=httpx.MockTransport(handler), **kwargs
    )


def test_chat_returns_answer_and_tools():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat"  # the versioned route
        return httpx.Response(
            200,
            json={
                "answer": "BRCA2: 0.032",
                "model": "openai/gpt-oss-120b",
                "tool_calls_made": ["get_targets", "get_expressions"],
            },
        )

    reply = _client(handler).chat("breast values?")
    assert reply.ok
    assert reply.answer == "BRCA2: 0.032"
    assert reply.tool_calls == ["get_targets", "get_expressions"]


def test_health_reads_the_versioned_ready_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/health/ready"
        return httpx.Response(200, json={"status": "ok", "model": "openai/gpt-oss-120b"})

    health = _client(handler).health()
    assert health.online
    assert health.model == "openai/gpt-oss-120b"


def test_health_reports_offline_when_unreachable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    health = _client(handler).health()
    assert not health.online
    assert health.model is None


def test_api_key_is_sent_as_a_header():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers.get("X-API-Key", "")
        return httpx.Response(200, json={"answer": "ok", "tool_calls_made": []})

    _client(handler, api_key="secret-key").chat("hi")
    assert seen["key"] == "secret-key"


def test_session_id_is_sent_when_a_key_is_present():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"answer": "ok", "tool_calls_made": []})

    _client(handler, api_key="secret-key").chat("hi", session_id="conv-1")
    assert seen["session_id"] == "conv-1"


def test_session_id_is_withheld_without_a_key():
    """The API refuses a session without a caller identity, so sending one would
    only produce a 400. Ask statelessly instead."""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"answer": "ok", "tool_calls_made": []})

    client = _client(handler)
    assert not client.supports_sessions
    client.chat("hi", session_id="conv-1")
    assert "session_id" not in seen


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, AUTH_ERROR),
        (429, RATE_LIMIT_ERROR),
        (502, UNAVAILABLE_ERROR),
        (500, SERVER_ERROR),
    ],
)
def test_error_statuses_become_readable_messages(status, expected):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"detail": "raw internal detail"})

    reply = _client(handler).chat("hi")
    assert not reply.ok
    assert reply.answer == expected
    assert "raw internal detail" not in reply.answer


def test_timeout_becomes_a_readable_message():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    reply = _client(handler).chat("hi")
    assert not reply.ok
    assert reply.answer == TIMEOUT_ERROR


def test_client_closes_cleanly():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"answer": "ok", "tool_calls_made": []})

    client = _client(handler)
    client.close()
