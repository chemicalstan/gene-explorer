from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, SecretStr
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_DATA = Path(__file__).parent / "data" / "gene_dataset.csv"


def _split_csv(value: object) -> object:
    """Accept a plain comma-separated string from .env instead of requiring JSON."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


# A list field that also accepts a comma-separated string from the environment.
CsvList = Annotated[list[str], NoDecode, BeforeValidator(_split_csv)]


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
    log_json: bool = True
    # Per-million-token prices for cost accounting. Defaults match gpt-oss-120b.
    input_price_per_1m: float = 0.15
    output_price_per_1m: float = 0.60

    allowed_origins: CsvList = Field(default_factory=lambda: ["http://localhost:8501"])
    # Comma-separated list of accepted API keys. Empty means authentication is
    # disabled, which is intended only for local development.
    api_keys: CsvList = Field(default_factory=list)
    rate_limit: str = "60/minute"
    rate_limit_storage_uri: str = "memory://"

    # Conversation memory. "memory" keeps history in the process, which suits one
    # instance. "redis" shares history across instances.
    session_backend: Literal["memory", "redis"] = "memory"
    redis_url: str = "redis://localhost:6379/0"
    session_ttl_seconds: int = 3600
    # Upper bound on stored history items, so the token cost per turn is bounded.
    session_max_items: int = 40


@lru_cache
def get_settings() -> Settings:
    return Settings()
