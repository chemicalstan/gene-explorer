import pytest

from gene_explorer.asgi import build_app
from gene_explorer.config import Settings
from gene_explorer.domain import DataValidationError


def test_build_app_succeeds_with_real_data(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    app = build_app(Settings(_env_file=None))
    assert app.title == "Gene Explorer API"


def test_startup_logs_ready_event(monkeypatch, capsys):
    import json

    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    build_app(Settings(_env_file=None))
    records = [
        json.loads(line)
        for line in capsys.readouterr().out.splitlines()
        if line.strip().startswith("{")
    ]
    ready = [r for r in records if r.get("event") == "startup_ready"]
    assert ready
    assert ready[-1]["model"] == "openai/gpt-oss-120b"
    assert ready[-1]["cancer_types"] == 10


def test_startup_rejects_empty_dataset(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    csv = tmp_path / "empty.csv"
    csv.write_text("cancer_indication,gene,median_value\n")
    with pytest.raises(DataValidationError):
        build_app(Settings(_env_file=None, csv_path=csv))


def test_startup_rejects_missing_dataset(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    with pytest.raises(DataValidationError):
        build_app(Settings(_env_file=None, csv_path=tmp_path / "nope.csv"))
