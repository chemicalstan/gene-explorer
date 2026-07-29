from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from typing import Any

from agents.memory.session import SessionABC

from gene_explorer.config import Settings

# Conversation history and grounded values are stored per (caller, session).
_ITEMS_SUFFIX = "items"
_GROUNDED_SUFFIX = "grounded"


def trim_history(items: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
    """Keep the most recent items, without orphaning a tool result.

    A purely positional cut can drop a `function_call` while keeping its
    `function_call_output`. The model rejects that history, which would wedge the
    conversation. Any leading tool result whose call was cut is dropped too.
    """
    window = items[-max_items:] if len(items) > max_items else list(items)
    seen_calls: set[str] = set()
    start = 0
    for index, item in enumerate(window):
        if item.get("type") == "function_call":
            call_id = item.get("call_id")
            if isinstance(call_id, str):
                seen_calls.add(call_id)
        elif item.get("type") == "function_call_output":
            call_id = item.get("call_id")
            if isinstance(call_id, str) and call_id not in seen_calls:
                start = index + 1  # its call was trimmed away; drop the orphan
    return window[start:]


def scope_key(session_id: str, caller_id: str) -> str:
    """Namespace a session by its caller.

    The session id comes from the client, so without a namespace one caller could
    read another caller's conversation by guessing an id. The caller id (the API
    key) is hashed, so the key itself never reaches the store or the logs.

    A caller id is required. There is no anonymous fallback: without a distinct
    caller every session would share one namespace, which is the failure this
    function exists to prevent.
    """
    if not caller_id:
        raise ValueError("scope_key requires a caller id")
    digest = hashlib.sha256(caller_id.encode("utf-8")).hexdigest()[:32]
    return f"{digest}:{session_id}"


class SessionStore(ABC):
    """Storage backend for conversation history and verified numeric values."""

    @abstractmethod
    async def get_items(self, key: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def add_items(self, key: str, items: list[dict[str, Any]]) -> None: ...

    @abstractmethod
    async def pop_item(self, key: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def clear(self, key: str) -> None: ...

    @abstractmethod
    async def get_grounded(self, key: str) -> set[float]: ...

    @abstractmethod
    async def add_grounded(self, key: str, values: set[float]) -> None: ...

    async def close(self) -> None:  # noqa: B027 - optional hook, not all backends need it
        """Release any backend resources."""


class InMemorySessionStore(SessionStore):
    """Process-local store. Suitable for development and tests, not for more than
    one instance, because each instance keeps its own copy."""

    def __init__(self, *, ttl_seconds: int, max_items: int, max_sessions: int = 10_000) -> None:
        self._ttl = ttl_seconds
        self._max_items = max_items
        self._max_sessions = max_sessions
        self._items: dict[str, list[dict[str, Any]]] = {}
        self._grounded: dict[str, set[float]] = {}
        self._expires_at: dict[str, float] = {}

    def _drop(self, key: str) -> None:
        self._items.pop(key, None)
        self._grounded.pop(key, None)
        self._expires_at.pop(key, None)

    def _evict_if_expired(self, key: str) -> None:
        expiry = self._expires_at.get(key)
        if expiry is not None and expiry <= time.monotonic():
            self._drop(key)

    def _sweep(self) -> None:
        """Drop every expired session, then cap the total.

        Lazy per-key eviction alone would retain abandoned sessions for the life
        of the process, because a key that is never touched again is never
        checked.
        """
        now = time.monotonic()
        for key in [k for k, exp in self._expires_at.items() if exp <= now]:
            self._drop(key)
        # Hard ceiling: if the store is still over budget, drop the oldest.
        overflow = len(self._expires_at) - self._max_sessions
        if overflow > 0:
            oldest = sorted(self._expires_at, key=lambda k: self._expires_at[k])
            for key in oldest[:overflow]:
                self._drop(key)

    def _touch(self, key: str) -> None:
        # Record the new expiry first, then sweep. The just-touched session has
        # the latest expiry, so the cap never evicts the session in use.
        self._expires_at[key] = time.monotonic() + self._ttl
        self._sweep()

    async def get_items(self, key: str) -> list[dict[str, Any]]:
        self._evict_if_expired(key)
        return list(self._items.get(key, []))

    async def add_items(self, key: str, items: list[dict[str, Any]]) -> None:
        self._evict_if_expired(key)
        history = self._items.setdefault(key, [])
        history.extend(items)
        # Bound the history so token cost per turn cannot grow without limit.
        self._items[key] = trim_history(history, self._max_items)
        self._touch(key)

    async def pop_item(self, key: str) -> dict[str, Any] | None:
        self._evict_if_expired(key)
        history = self._items.get(key)
        if not history:
            return None
        return history.pop()

    async def clear(self, key: str) -> None:
        self._items.pop(key, None)
        self._grounded.pop(key, None)
        self._expires_at.pop(key, None)

    async def get_grounded(self, key: str) -> set[float]:
        self._evict_if_expired(key)
        return set(self._grounded.get(key, set()))

    async def add_grounded(self, key: str, values: set[float]) -> None:
        self._evict_if_expired(key)
        # Replace, not accumulate. See AgentSession.record_grounded_values.
        self._grounded[key] = set(values)
        self._touch(key)


class RedisSessionStore(SessionStore):
    """Shared store. Many service instances see the same conversation."""

    def __init__(
        self,
        url: str,
        *,
        ttl_seconds: int,
        max_items: int,
        client: Any | None = None,
    ) -> None:
        if client is None:
            from redis.asyncio import from_url

            client = from_url(url, decode_responses=True)
        self._redis = client
        self._ttl = ttl_seconds
        self._max_items = max_items

    @staticmethod
    def _k(key: str, suffix: str) -> str:
        return f"gene-explorer:session:{key}:{suffix}"

    async def get_items(self, key: str) -> list[dict[str, Any]]:
        raw = await self._redis.lrange(self._k(key, _ITEMS_SUFFIX), 0, -1)
        # Trim on read as well, so a tool result whose call was cut is never
        # returned to the model.
        return trim_history([json.loads(item) for item in raw], self._max_items)

    async def add_items(self, key: str, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        name = self._k(key, _ITEMS_SUFFIX)
        pipe = self._redis.pipeline()
        pipe.rpush(name, *[json.dumps(item) for item in items])
        # Keep only the most recent max_items entries.
        pipe.ltrim(name, -self._max_items, -1)
        pipe.expire(name, self._ttl)
        pipe.expire(self._k(key, _GROUNDED_SUFFIX), self._ttl)
        await pipe.execute()

    async def pop_item(self, key: str) -> dict[str, Any] | None:
        raw = await self._redis.rpop(self._k(key, _ITEMS_SUFFIX))
        if not raw or isinstance(raw, list):
            return None
        return json.loads(raw)  # type: ignore[no-any-return]

    async def clear(self, key: str) -> None:
        await self._redis.delete(self._k(key, _ITEMS_SUFFIX), self._k(key, _GROUNDED_SUFFIX))

    async def get_grounded(self, key: str) -> set[float]:
        raw = await self._redis.smembers(self._k(key, _GROUNDED_SUFFIX))
        return {float(value) for value in raw}

    async def add_grounded(self, key: str, values: set[float]) -> None:
        if not values:
            return
        name = self._k(key, _GROUNDED_SUFFIX)
        pipe = self._redis.pipeline()
        # Replace, not accumulate. See AgentSession.record_grounded_values.
        pipe.delete(name)
        pipe.sadd(name, *[repr(value) for value in values])
        pipe.expire(name, self._ttl)
        await pipe.execute()

    async def close(self) -> None:
        await self._redis.aclose()


class AgentSession(SessionABC):
    """Adapts a SessionStore to the Agents SDK session protocol for one caller."""

    def __init__(self, store: SessionStore, session_id: str, caller_id: str) -> None:
        self.session_id = session_id
        self._store = store
        self._key = scope_key(session_id, caller_id)

    async def get_items(self, limit: int | None = None) -> list[Any]:
        items = await self._store.get_items(self._key)
        return items[-limit:] if limit is not None else items

    async def add_items(self, items: list[Any]) -> None:
        await self._store.add_items(self._key, list(items))

    async def pop_item(self) -> Any | None:
        return await self._store.pop_item(self._key)

    async def clear_session(self) -> None:
        await self._store.clear(self._key)

    async def grounded_values(self) -> set[float]:
        """Values verified in the previous turn of this conversation."""
        return await self._store.get_grounded(self._key)

    async def record_grounded_values(self, values: set[float]) -> None:
        """Store the values verified in this turn, replacing the previous turn's.

        Deliberately not cumulative. An ever-growing set would eventually contain
        most of the dataset and reduce the grounding guardrail to a no-op, and it
        would let a value verified for one cancer type validate a claim about a
        different one many turns later. Keeping only the previous turn supports a
        direct follow-up ("what was that value again?") with a much smaller window.
        """
        await self._store.add_grounded(self._key, values)


def build_session_store(settings: Settings) -> SessionStore:
    if settings.session_backend == "redis":
        return RedisSessionStore(
            settings.redis_url,
            ttl_seconds=settings.session_ttl_seconds,
            max_items=settings.session_max_items,
        )
    return InMemorySessionStore(
        ttl_seconds=settings.session_ttl_seconds,
        max_items=settings.session_max_items,
    )
