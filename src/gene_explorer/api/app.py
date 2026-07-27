from __future__ import annotations

from agents import Agent
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gene_explorer.api.routes import build_router
from gene_explorer.config import Settings
from gene_explorer.domain import ToolCallLog


def create_app(*, settings: Settings, agent: Agent[ToolCallLog]) -> FastAPI:
    app = FastAPI(
        title="Gene Explorer API",
        description="Conversational agent for querying a cancer gene expression dataset.",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(build_router(settings, agent))
    return app
