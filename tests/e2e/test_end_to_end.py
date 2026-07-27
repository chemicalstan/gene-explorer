import os

import pytest
from fastapi.testclient import TestClient

from gene_explorer.asgi import build_app
from gene_explorer.config import Settings


def _live_client() -> TestClient:
    # Reads the real GROQ_API_KEY from the environment, not any cached settings.
    return TestClient(build_app(Settings(_env_file=None)))


@pytest.mark.skipif(not os.getenv("GROQ_LIVE_TEST"), reason="set GROQ_LIVE_TEST=1 for live e2e")
def test_breast_query_returns_grounded_values():
    r = _live_client().post(
        "/v1/chat",
        json={"message": "What is the median expression of BRCA2 in breast cancer?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "0.032" in body["answer"]
    assert "get_expressions" in body["tool_calls_made"]


@pytest.mark.skipif(not os.getenv("GROQ_LIVE_TEST"), reason="set GROQ_LIVE_TEST=1 for live e2e")
def test_unknown_cancer_is_refused():
    r = _live_client().post("/v1/chat", json={"message": "genes in esophageal cancer?"})
    assert r.status_code == 200
    assert "don't have data" in r.json()["answer"].lower()
    assert r.json()["tool_calls_made"] == []
