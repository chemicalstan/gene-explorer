from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

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
from gene_explorer.sessions import SessionStore, build_session_store

_access_logger = get_logger("gene_explorer.access")


def _build_rate_limit_key(settings: Settings) -> Callable[[Request], str]:
    """Bucket by API key, but only by a key the service accepts.

    Bucketing on an arbitrary header would let a caller rotate the header on each
    request and get a fresh budget every time, which bypasses the limit.
    """
    allowed = set(settings.api_keys)

    def key_func(request: Request) -> str:
        candidate = request.headers.get("X-API-Key")
        if candidate and candidate in allowed:
            return candidate
        return get_remote_address(request)

    return key_func


async def _access_log(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.perf_counter()
    status_code = 500  # assume failure until proven otherwise
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        # Log even when the endpoint raised (status stays 500), so genuine
        # server failures remain visible and traceable by request id.
        # Health probes are frequent and low-value; do not log them.
        if not request.url.path.startswith("/v1/health"):
            _access_logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
            )


def create_app(
    *,
    settings: Settings,
    agent: Agent[ToolCallLog],
    session_store: SessionStore | None = None,
) -> FastAPI:
    store = session_store or build_session_store(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await store.close()

    app = FastAPI(
        title="Gene Explorer API",
        description="Conversational agent for querying a cancer gene expression dataset.",
        version="1.0.0",
        lifespan=lifespan,
    )

    limiter = Limiter(
        key_func=_build_rate_limit_key(settings),
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
    app.include_router(build_router(settings, agent, limiter, store))
    return app
