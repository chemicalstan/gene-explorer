from __future__ import annotations

import logging

from fastapi import FastAPI

from gene_explorer.agent import build_agent
from gene_explorer.api.app import create_app
from gene_explorer.config import Settings, get_settings
from gene_explorer.domain import CANCER_TYPES, DataValidationError
from gene_explorer.repository import GeneRepository

logger = logging.getLogger(__name__)


def build_app(settings: Settings | None = None) -> FastAPI:
    """Compose the application. Used by uvicorn via `--factory`, so there is no
    import-time side effect and tests can pass explicit settings."""
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    repo = GeneRepository.from_csv(settings.csv_path)
    if set(repo.cancer_types) != set(CANCER_TYPES):
        raise DataValidationError(
            f"Dataset cancers {repo.cancer_types} do not match "
            f"the code vocabulary {CANCER_TYPES}."
        )

    agent = build_agent(settings)
    logger.info("gene-explorer ready | model=%s", settings.model)
    return create_app(settings=settings, agent=agent, repo=repo)
