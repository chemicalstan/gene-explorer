"""HTTP client for the Gene Explorer API.

Kept free of Streamlit imports so it can be tested without a running app.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

CONNECT_ERROR = "Cannot reach the service. Check that the backend is running."
TIMEOUT_ERROR = "The request took too long. Please try again."
AUTH_ERROR = "The API key was rejected. Check API_KEYS on the backend."
RATE_LIMIT_ERROR = "Too many requests. Please wait a moment and try again."
SERVER_ERROR = "The service reported an error. Please try again."
UNAVAILABLE_ERROR = "The model is unavailable right now. Please try again shortly."


@dataclass(frozen=True)
class Health:
    online: bool
    model: str | None = None


@dataclass(frozen=True)
class Reply:
    answer: str
    tool_calls: list[str] = field(default_factory=list)
    ok: bool = True


class GeneExplorerClient:
    """Talks to the versioned API and turns failures into readable messages."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {"X-API-Key": api_key} if api_key else {}
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )
        self._has_key = bool(api_key)

    @property
    def supports_sessions(self) -> bool:
        """Conversation history needs a caller identity, so it needs an API key."""
        return self._has_key

    def health(self) -> Health:
        try:
            response = self._client.get("/v1/health/ready", timeout=5.0)
            response.raise_for_status()
        except httpx.HTTPError:
            return Health(online=False)
        return Health(online=True, model=response.json().get("model"))

    def chat(self, message: str, *, session_id: str | None = None) -> Reply:
        payload: dict[str, object] = {"message": message}
        if session_id and self._has_key:
            payload["session_id"] = session_id
        try:
            response = self._client.post("/v1/chat", json=payload)
            response.raise_for_status()
        except httpx.ConnectError:
            return Reply(CONNECT_ERROR, ok=False)
        except httpx.TimeoutException:
            return Reply(TIMEOUT_ERROR, ok=False)
        except httpx.HTTPStatusError as exc:
            return Reply(_message_for_status(exc.response.status_code), ok=False)
        except httpx.HTTPError:
            return Reply(SERVER_ERROR, ok=False)

        body = response.json()
        return Reply(answer=body["answer"], tool_calls=body.get("tool_calls_made", []))

    def close(self) -> None:
        self._client.close()


def _message_for_status(status_code: int) -> str:
    if status_code == 401:
        return AUTH_ERROR
    if status_code == 429:
        return RATE_LIMIT_ERROR
    if status_code == 502:
        return UNAVAILABLE_ERROR
    return SERVER_ERROR
