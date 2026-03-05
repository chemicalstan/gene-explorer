import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.api.routes import create_app

@pytest.fixture
def client():
    mock_agent = MagicMock()
    mock_agent.run.return_value = (
        "I can help you explore cancer genomics data.",
        ["get_targets"],
    )
    mock_agent.provider_name = "rule_based/deterministic"
    app = create_app(agent=mock_agent)
    return TestClient(app)

def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert "provider" in resp.json()

def test_chat_returns_answer(client):
    resp = client.post("/chat", json={"message": "how can you help me?"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["answer"], str)
    assert len(body["answer"]) > 0

def test_chat_returns_tool_calls(client):
    resp = client.post("/chat",
                       json={"message": "what genes are in lung cancer?"})
    assert resp.status_code == 200
    assert "tool_calls_made" in resp.json()
    assert isinstance(resp.json()["tool_calls_made"], list)

def test_chat_invalid_body_returns_422(client):
    resp = client.post("/chat", json={})
    assert resp.status_code == 422

def test_health_provider_determines_mode(client):
    resp = client.get("/health")
    provider = resp.json()["provider"]
    assert "rule_based" in provider
