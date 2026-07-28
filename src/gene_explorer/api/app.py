from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from agents import Agent
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from gene_explorer.api.routes import build_router
from gene_explorer.config import Settings
from gene_explorer.domain import ToolCallLog
from gene_explorer.logging_config import get_logger

_access_logger = get_logger("gene_explorer.access")


def _rate_limit_key(request: Request) -> str:
    # Rate limit per API key when present, otherwise per client address.
    return request.headers.get("X-API-Key") or get_remote_address(request)


async def _access_log(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    # Health probes are frequent and low-value; do not log them.
    if not request.url.path.startswith("/v1/health"):
        _access_logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
    return response


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

    # Middleware added later wraps earlier ones. Order (outer to inner):
    # CORS -> CorrelationId (sets request_id) -> access log (reads request_id).
    app.add_middleware(BaseHTTPMiddleware, dispatch=_access_log)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(build_router(settings, agent, limiter))
    return app
