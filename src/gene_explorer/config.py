from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

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
    # NoDecode + validator: accept a plain comma-separated string in .env
    # (ALLOWED_ORIGINS=http://a,http://b) instead of requiring JSON.
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:8501"]
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
