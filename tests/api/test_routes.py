import pytest
from fastapi.testclient import TestClient

from gene_explorer.api.app import create_app
from gene_explorer.config import Settings


class _StubAgent:
    pass


async def _fake_run_agent(agent, message, *, max_turns):
    return ("BRCA2: 0.032", ["get_targets", "get_expressions"])


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


def test_chat_is_rate_limited(monkeypatch):
    client = _client(monkeypatch, rate_limit="2/minute")
    assert client.post("/v1/chat", json={"message": "a"}).status_code == 200
    assert client.post("/v1/chat", json={"message": "b"}).status_code == 200
    assert client.post("/v1/chat", json={"message": "c"}).status_code == 429
