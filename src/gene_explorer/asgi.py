from __future__ import annotations

from fastapi import FastAPI

from gene_explorer.agent import build_agent
from gene_explorer.api.app import create_app
from gene_explorer.config import Settings, get_settings
from gene_explorer.domain import DataValidationError
from gene_explorer.logging_config import configure_logging, get_logger
from gene_explorer.repository import GeneRepository

logger = get_logger("gene_explorer.startup")


def build_app(settings: Settings | None = None) -> FastAPI:
    """Compose the application. Used by uvicorn via `--factory`, so there is no
    import-time side effect and tests can pass explicit settings."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_logs=settings.log_json)

    repo = GeneRepository.from_csv(settings.csv_path)
    if not repo.cancer_types:
        raise DataValidationError(f"Dataset at {settings.csv_path} contains no rows.")

    agent = build_agent(settings, repo)
    logger.info("startup_ready", model=settings.model, cancer_types=len(repo.cancer_types))
    return create_app(settings=settings, agent=agent)
