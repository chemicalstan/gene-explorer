import pytest
from pydantic import ValidationError

from gene_explorer.config import Settings


def test_defaults_apply(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    s = Settings(_env_file=None)
    assert s.model == "openai/gpt-oss-120b"
    assert s.groq_base_url == "https://api.groq.com/openai/v1"
    assert s.temperature == 0.0
    assert s.reasoning_effort == "low"
    assert s.seed == 42
    assert s.max_turns == 6


def test_model_is_overridable_from_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("MODEL", "openai/gpt-oss-20b")
    assert Settings(_env_file=None).model == "openai/gpt-oss-20b"


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_api_key_is_secret(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_secret")
    s = Settings(_env_file=None)
    assert "gsk_secret" not in repr(s)
    assert s.groq_api_key.get_secret_value() == "gsk_secret"
