import pytest
from fastapi.testclient import TestClient

from gene_explorer.api.app import create_app
from gene_explorer.config import Settings


class _StubAgent:
    pass


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    settings = Settings(_env_file=None)

    async def _fake_run_agent(agent, message, *, max_turns):
        return ("BRCA2: 0.032", ["get_targets", "get_expressions"])

    monkeypatch.setattr("gene_explorer.api.routes.run_agent", _fake_run_agent)
    app = create_app(settings=settings, agent=_StubAgent())
    return TestClient(app)


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
