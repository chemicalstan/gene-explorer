import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from gene_explorer.api.app import create_app
from gene_explorer.config import Settings
from gene_explorer.domain import AgentResult, RunUsage


class _StubAgent:
    pass


async def _fake_run_agent(agent, message, *, max_turns, session=None):
    return AgentResult(
        answer="BRCA2: 0.032",
        tool_calls=["get_targets", "get_expressions"],
        usage=RunUsage(input_tokens=100, output_tokens=20, total_tokens=120, requests=2),
    )


def _client(monkeypatch, **overrides) -> TestClient:
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    settings = Settings(_env_file=None, **overrides)
    monkeypatch.setattr("gene_explorer.api.routes.run_agent", _fake_run_agent)
    return TestClient(create_app(settings=settings, agent=_StubAgent()))


@pytest.fixture
def client(monkeypatch):
    # No API keys configured: authentication is disabled.
    return _client(monkeypatch)


def test_chat_returns_answer_and_tools(client):
    r = client.post("/v1/chat", json={"message": "breast values?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "BRCA2: 0.032"
    assert body["tool_calls_made"] == ["get_targets", "get_expressions"]
    assert body["model"] == "openai/gpt-oss-120b"


def test_chat_rejects_empty_message(client):
    assert client.post("/v1/chat", json={"message": ""}).status_code == 422


def test_chat_rejects_oversized_message(client):
    assert client.post("/v1/chat", json={"message": "x" * 5000}).status_code == 422


def test_liveness_is_ok(client):
    r = client.get("/v1/health/live")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_readiness_reports_model(client):
    r = client.get("/v1/health/ready")
    assert r.status_code == 200
    assert r.json()["model"] == "openai/gpt-oss-120b"


def test_chat_requires_api_key_when_configured(monkeypatch):
    client = _client(monkeypatch, api_keys=["secret-key"])
    # Missing key.
    assert client.post("/v1/chat", json={"message": "hi"}).status_code == 401
    # Wrong key.
    r = client.post("/v1/chat", json={"message": "hi"}, headers={"X-API-Key": "nope"})
    assert r.status_code == 401
    # Correct key.
    r = client.post("/v1/chat", json={"message": "hi"}, headers={"X-API-Key": "secret-key"})
    assert r.status_code == 200


def test_health_does_not_require_api_key(monkeypatch):
    client = _client(monkeypatch, api_keys=["secret-key"])
    assert client.get("/v1/health/live").status_code == 200
    assert client.get("/v1/health/ready").status_code == 200


def test_response_has_request_id_header(client):
    r = client.post("/v1/chat", json={"message": "hi"})
    assert r.headers.get("X-Request-ID")


def test_valid_upstream_request_id_is_echoed(client):
    # asgi-correlation-id validates the incoming id as a UUID, which prevents
    # log-injection via the header. A valid upstream id is preserved.
    upstream = "123e4567-e89b-42d3-a456-426614174000"
    r = client.post("/v1/chat", json={"message": "hi"}, headers={"X-Request-ID": upstream})
    assert r.headers["X-Request-ID"] == upstream


def test_invalid_request_id_is_replaced(client):
    # A non-UUID (potentially malicious) id is rejected and replaced.
    r = client.post(
        "/v1/chat",
        json={"message": "hi"},
        headers={"X-Request-ID": "evil\ninjection"},
    )
    assert r.headers["X-Request-ID"] != "evil\ninjection"
    assert "\n" not in r.headers["X-Request-ID"]


def test_logs_never_contain_message_content_or_api_key(monkeypatch, capsys):
    from gene_explorer.logging_config import configure_logging

    configure_logging("INFO", json_logs=True)
    client = _client(monkeypatch, api_keys=["super-secret-key"])
    secret_message = "PATIENT-SSN-123-45-6789"
    r = client.post(
        "/v1/chat",
        json={"message": secret_message},
        headers={"X-API-Key": "super-secret-key"},
    )
    assert r.status_code == 200
    logs = capsys.readouterr().out
    assert "chat_completed" in logs  # the metrics line was emitted
    assert secret_message not in logs  # but not the message content
    assert "super-secret-key" not in logs  # and never the API key


def test_chat_is_rate_limited(monkeypatch):
    client = _client(monkeypatch, rate_limit="2/minute")
    assert client.post("/v1/chat", json={"message": "a"}).status_code == 200
    assert client.post("/v1/chat", json={"message": "b"}).status_code == 200
    assert client.post("/v1/chat", json={"message": "c"}).status_code == 429


def _json_lines(text):
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return lines


def test_access_log_and_correlation(monkeypatch, capsys):
    from gene_explorer.logging_config import configure_logging

    configure_logging("INFO", json_logs=True)
    client = _client(monkeypatch)
    client.post("/v1/chat", json={"message": "hi"})
    records = _json_lines(capsys.readouterr().out)

    access = [r for r in records if r.get("event") == "request"]
    chat = [r for r in records if r.get("event") == "chat_completed"]
    assert access and chat
    assert access[-1]["path"] == "/v1/chat"
    assert access[-1]["status_code"] == 200
    assert "duration_ms" in access[-1]
    # The access log and the chat metrics line share the same request id.
    assert access[-1]["request_id"] == chat[-1]["request_id"]


def test_502_path_logs_no_message_content(monkeypatch, capsys):
    from gene_explorer.agent import AgentRunError
    from gene_explorer.logging_config import configure_logging

    # Console mode is where the traceback-locals leak used to happen.
    configure_logging("INFO", json_logs=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    settings = Settings(_env_file=None, log_json=False)
    secret = "patient-MRN-00998877"

    async def _raises(agent, message, *, max_turns, session=None):
        # `message` (the secret) is a live frame local here.
        raise AgentRunError("upstream failure") from TimeoutError("groq timeout")

    monkeypatch.setattr("gene_explorer.api.routes.run_agent", _raises)
    client = TestClient(create_app(settings=settings, agent=_StubAgent()))
    r = client.post("/v1/chat", json={"message": secret})
    assert r.status_code == 502
    logs = capsys.readouterr().out + capsys.readouterr().err
    assert secret not in logs  # message content must never reach the logs


def test_session_id_is_echoed(client):
    r = client.post("/v1/chat", json={"message": "hi", "session_id": "abc-1"})
    assert r.status_code == 200
    assert r.json()["session_id"] == "abc-1"


def test_session_id_absent_by_default(client):
    assert client.post("/v1/chat", json={"message": "hi"}).json()["session_id"] is None


def test_malformed_session_id_is_rejected(client):
    # The pattern blocks path/# separators and whitespace.
    for bad in ["../etc", "a b", "x" * 200, ""]:
        r = client.post("/v1/chat", json={"message": "hi", "session_id": bad})
        assert r.status_code == 422, bad


def test_session_is_scoped_to_the_caller(monkeypatch):
    """Two callers using the same session id must not share a conversation."""
    from gene_explorer.sessions import InMemorySessionStore

    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    settings = Settings(_env_file=None, api_keys=["key-a", "key-b"])
    store = InMemorySessionStore(ttl_seconds=3600, max_items=10)
    captured: list[object] = []

    async def _capture(agent, message, *, max_turns, session=None):
        captured.append(session)
        await session.add_items([{"role": "user", "content": message}])
        return AgentResult("ok", [], RunUsage())

    monkeypatch.setattr("gene_explorer.api.routes.run_agent", _capture)
    client = TestClient(create_app(settings=settings, agent=_StubAgent(), session_store=store))
    client.post(
        "/v1/chat",
        json={"message": "caller a secret", "session_id": "same"},
        headers={"X-API-Key": "key-a"},
    )
    client.post(
        "/v1/chat",
        json={"message": "caller b", "session_id": "same"},
        headers={"X-API-Key": "key-b"},
    )

    session_a, session_b = captured
    history_a = [i["content"] for i in asyncio.run(session_a.get_items())]
    history_b = [i["content"] for i in asyncio.run(session_b.get_items())]
    assert history_a == ["caller a secret"]
    # Caller B must not see caller A's message despite the identical session id.
    assert history_b == ["caller b"]


def test_unhandled_error_is_access_logged(monkeypatch, capsys):
    from gene_explorer.logging_config import configure_logging

    configure_logging("INFO", json_logs=True)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    settings = Settings(_env_file=None)

    async def _boom(agent, message, *, max_turns, session=None):
        raise ValueError("unexpected")  # not AgentRunError -> unhandled -> 500

    monkeypatch.setattr("gene_explorer.api.routes.run_agent", _boom)
    client = TestClient(
        create_app(settings=settings, agent=_StubAgent()), raise_server_exceptions=False
    )
    r = client.post("/v1/chat", json={"message": "hi"})
    assert r.status_code == 500
    access = [x for x in _json_lines(capsys.readouterr().out) if x.get("event") == "request"]
    assert access and access[-1]["status_code"] == 500
