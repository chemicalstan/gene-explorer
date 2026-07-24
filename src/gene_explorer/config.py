from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_DATA = Path(__file__).parent / "data" / "gene_dataset.csv"


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables and an optional .env."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    groq_api_key: SecretStr
    groq_base_url: str = "https://api.groq.com/openai/v1"
    model: str = "openai/gpt-oss-120b"
    temperature: float = 0.0
    reasoning_effort: str = "low"
    seed: int = 42
    max_turns: int = 6
    request_timeout_s: float = 30.0
    csv_path: Path = _DATA
    log_level: str = "INFO"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8501"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
