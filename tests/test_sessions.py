import pytest

from gene_explorer.config import Settings
from gene_explorer.sessions import (
    AgentSession,
    InMemorySessionStore,
    RedisSessionStore,
    build_session_store,
    scope_key,
)


@pytest.fixture
def store():
    return InMemorySessionStore(ttl_seconds=3600, max_items=6)


def _msg(text):
    return {"role": "user", "content": text}


async def test_history_round_trips(store):
    session = AgentSession(store, "s1", "caller-a")
    await session.add_items([_msg("first"), _msg("second")])
    assert [i["content"] for i in await session.get_items()] == ["first", "second"]


async def test_history_is_bounded(store):
    session = AgentSession(store, "s1", "caller-a")
    await session.add_items([_msg(str(n)) for n in range(10)])
    items = await session.get_items()
    # max_items=6, so only the most recent six survive.
    assert len(items) == 6
    assert [i["content"] for i in items] == ["4", "5", "6", "7", "8", "9"]


async def test_get_items_respects_limit(store):
    session = AgentSession(store, "s1", "caller-a")
    await session.add_items([_msg("a"), _msg("b"), _msg("c")])
    assert [i["content"] for i in await session.get_items(limit=2)] == ["b", "c"]


async def test_pop_and_clear(store):
    session = AgentSession(store, "s1", "caller-a")
    await session.add_items([_msg("a"), _msg("b")])
    assert (await session.pop_item())["content"] == "b"
    await session.clear_session()
    assert await session.get_items() == []
    assert await session.pop_item() is None


async def test_sessions_are_isolated_between_callers(store):
    """Security: the same session id under a different API key is a different
    conversation, so a guessed id cannot expose another caller's history."""
    mine = AgentSession(store, "shared-id", "caller-a")
    theirs = AgentSession(store, "shared-id", "caller-b")
    await mine.add_items([_msg("my private question")])
    assert await theirs.get_items() == []
    await mine.record_grounded_values({0.032})
    assert await theirs.grounded_values() == set()


def test_scope_key_hashes_the_caller():
    key = scope_key("s1", "super-secret-api-key")
    assert "super-secret-api-key" not in key
    assert key.endswith(":s1")
    assert scope_key("s1", "a") != scope_key("s1", "b")


def test_scope_key_requires_a_caller():
    # There is no anonymous fallback: without a caller every session would share
    # one namespace, which is exactly the leak this guards against.
    for missing in ("", None):
        with pytest.raises(ValueError):
            scope_key("s1", missing)


async def test_grounded_values_replace_rather_than_accumulate(store):
    session = AgentSession(store, "s1", "caller-a")
    await session.record_grounded_values({0.032})
    await session.record_grounded_values({0.094})
    # Only the previous turn's values remain, so the allowed set cannot grow to
    # cover the whole dataset and neutralise the guardrail.
    assert await session.grounded_values() == {0.094}


def test_trim_history_drops_orphaned_tool_output():
    from gene_explorer.sessions import trim_history

    items = [
        {"type": "function_call", "call_id": "c1"},
        {"type": "function_call_output", "call_id": "c1"},
        {"role": "assistant", "content": "answer"},
    ]
    # A positional cut of 2 would keep the output without its call, which the
    # model rejects and which would wedge the conversation.
    kept = trim_history(items, 2)
    assert all(i.get("type") != "function_call_output" for i in kept)


def test_trim_history_keeps_intact_pairs():
    from gene_explorer.sessions import trim_history

    items = [
        {"role": "user", "content": "q"},
        {"type": "function_call", "call_id": "c1"},
        {"type": "function_call_output", "call_id": "c1"},
    ]
    assert len(trim_history(items, 3)) == 3


async def test_expired_sessions_are_swept_not_just_evicted_on_access():
    swept = InMemorySessionStore(ttl_seconds=0, max_items=10)
    abandoned = AgentSession(swept, "abandoned", "caller-a")
    await abandoned.add_items([_msg("old")])
    # Touching a DIFFERENT session must clear the abandoned one, otherwise the
    # process retains every session it has ever seen.
    other = AgentSession(swept, "other", "caller-b")
    await other.add_items([_msg("new")])
    assert swept._items.get(scope_key("abandoned", "caller-a")) is None


async def test_session_count_is_capped():
    capped = InMemorySessionStore(ttl_seconds=3600, max_items=10, max_sessions=3)
    for n in range(6):
        await AgentSession(capped, f"s{n}", "caller-a").add_items([_msg(str(n))])
    assert len(capped._items) <= 3


async def test_expired_session_is_dropped():
    expired = InMemorySessionStore(ttl_seconds=0, max_items=10)
    session = AgentSession(expired, "s1", "caller-a")
    await session.add_items([_msg("old")])
    assert await session.get_items() == []


def test_build_session_store_selects_backend(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    memory = build_session_store(Settings(_env_file=None))
    assert isinstance(memory, InMemorySessionStore)


def test_build_session_store_selects_redis(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    store = build_session_store(Settings(_env_file=None, session_backend="redis"))
    assert isinstance(store, RedisSessionStore)


# ---------------------------------------------------------------------------
# The Redis backend, exercised against an in-process Redis server (fakeredis).
# ---------------------------------------------------------------------------


@pytest.fixture
def redis_store():
    import fakeredis.aioredis

    return RedisSessionStore(
        "redis://unused",
        ttl_seconds=60,
        max_items=4,
        client=fakeredis.aioredis.FakeRedis(decode_responses=True),
    )


async def test_redis_history_round_trips_and_is_bounded(redis_store):
    session = AgentSession(redis_store, "s1", "caller-a")
    await session.add_items([_msg(str(n)) for n in range(6)])
    items = [i["content"] for i in await session.get_items()]
    assert items == ["2", "3", "4", "5"]  # bounded to max_items=4


async def test_redis_isolates_callers(redis_store):
    mine = AgentSession(redis_store, "shared", "caller-a")
    theirs = AgentSession(redis_store, "shared", "caller-b")
    await mine.add_items([_msg("private")])
    await mine.record_grounded_values({0.032})
    assert await theirs.get_items() == []
    assert await theirs.grounded_values() == set()


async def test_redis_grounded_values_round_trip(redis_store):
    session = AgentSession(redis_store, "s1", "caller-a")
    await session.record_grounded_values({0.032, 0.094})
    assert await session.grounded_values() == {0.032, 0.094}


async def test_redis_pop_and_clear(redis_store):
    session = AgentSession(redis_store, "s1", "caller-a")
    await session.add_items([_msg("a"), _msg("b")])
    assert (await session.pop_item())["content"] == "b"
    await session.clear_session()
    assert await session.get_items() == []
    assert await session.pop_item() is None


async def test_redis_empty_writes_are_noops(redis_store):
    session = AgentSession(redis_store, "s1", "caller-a")
    await session.add_items([])
    await session.record_grounded_values(set())
    assert await session.get_items() == []
    assert await session.grounded_values() == set()


async def test_redis_close_is_safe(redis_store):
    await redis_store.close()
