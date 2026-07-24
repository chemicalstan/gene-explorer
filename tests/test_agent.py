import os

import pytest
from agents.run import Runner

from gene_explorer.agent import build_agent, run_agent
from gene_explorer.config import Settings


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    return Settings(_env_file=None)


def test_build_agent_wires_tools_and_model(settings):
    agent = build_agent(settings)
    assert {t.name for t in agent.tools} == {"get_targets", "get_expressions"}
    assert agent.model.model == settings.model  # type: ignore[union-attr]


async def test_run_agent_reports_answer_and_tools(settings, repo, monkeypatch):
    class _Result:
        final_output = "BRCA2: 0.032"
        new_items: list[object] = []

    async def _fake_run(agent, message, *, context, max_turns):
        context.tool_calls.extend(["get_targets", "get_expressions"])
        return _Result()

    monkeypatch.setattr(Runner, "run", staticmethod(_fake_run))
    agent = build_agent(settings)
    answer, tools = await run_agent(agent, repo, "breast values?", max_turns=6)
    assert answer == "BRCA2: 0.032"
    assert tools == ["get_targets", "get_expressions"]


async def test_run_agent_wraps_failures(settings, repo, monkeypatch):
    from gene_explorer.agent import AgentRunError

    async def _boom(agent, message, *, context, max_turns):
        raise RuntimeError("groq exploded")

    monkeypatch.setattr(Runner, "run", staticmethod(_boom))
    agent = build_agent(settings)
    with pytest.raises(AgentRunError):
        await run_agent(agent, repo, "x", max_turns=6)


@pytest.mark.skipif(not os.getenv("GROQ_LIVE_TEST"), reason="set GROQ_LIVE_TEST=1 for live e2e")
async def test_live_breast_query_grounded(real_repo):
    # Reads the real GROQ_API_KEY from the environment, not the fake-key fixture.
    live_settings = Settings(_env_file=None)
    agent = build_agent(live_settings)
    answer, tools = await run_agent(
        agent, real_repo, "Median expression of BRCA2 in breast cancer?", max_turns=6
    )
    assert "0.032" in answer
    assert "get_expressions" in tools
