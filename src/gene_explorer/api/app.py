from __future__ import annotations

from agents import Agent
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from gene_explorer.api.routes import build_router
from gene_explorer.config import Settings
from gene_explorer.domain import ToolCallLog


def _rate_limit_key(request: Request) -> str:
    # Rate limit per API key when present, otherwise per client address.
    return request.headers.get("X-API-Key") or get_remote_address(request)


def create_app(*, settings: Settings, agent: Agent[ToolCallLog]) -> FastAPI:
    app = FastAPI(
        title="Gene Explorer API",
        description="Conversational agent for querying a cancer gene expression dataset.",
        version="1.0.0",
    )

    limiter = Limiter(
        key_func=_rate_limit_key,
        storage_uri=settings.rate_limit_storage_uri,
    )
    app.state.limiter = limiter
    # slowapi's handler is typed for RateLimitExceeded specifically, which is
    # narrower than Starlette's (Request, Exception) handler signature.
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(build_router(settings, agent, limiter))
    return app
