from __future__ import annotations

import hmac
import logging
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from gene_explorer.config import Settings

logger = logging.getLogger(__name__)

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _is_valid(candidate: str, allowed: list[str]) -> bool:
    # Constant-time comparison against every key, so a wrong key cannot be found
    # faster than a right one. Compare bytes: Starlette decodes headers as
    # latin-1, and compare_digest rejects str with characters above U+007F.
    candidate_bytes = candidate.encode("utf-8", errors="ignore")
    return any(hmac.compare_digest(candidate_bytes, key.encode("utf-8")) for key in allowed)


def build_api_key_dependency(
    settings: Settings,
) -> Callable[[str | None], Awaitable[None]]:
    """Return a FastAPI dependency that enforces the X-API-Key header.

    When no keys are configured, authentication is disabled and every request is
    allowed. This is intended only for local development.
    """
    if not settings.api_keys:
        logger.warning("no API_KEYS configured — authentication is disabled")

    async def require_api_key(
        key: str | None = Security(_API_KEY_HEADER),
    ) -> None:
        if not settings.api_keys:
            return
        if key is None or not _is_valid(key, settings.api_keys):
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    return require_api_key
