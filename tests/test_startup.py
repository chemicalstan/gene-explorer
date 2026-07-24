import pytest

from gene_explorer.asgi import build_app
from gene_explorer.config import Settings
from gene_explorer.domain import DataValidationError


def test_build_app_succeeds_with_real_data(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    app = build_app(Settings(_env_file=None))
    assert app.title == "Gene Explorer API"


def test_startup_rejects_data_drift(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    csv = tmp_path / "drift.csv"
    csv.write_text("cancer_indication,gene,median_value\nzzz,GENE,0.1\n")
    with pytest.raises(DataValidationError):
        build_app(Settings(_env_file=None, csv_path=csv))
