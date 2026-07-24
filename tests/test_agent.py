import os

import pytest
from agents.run import Runner

from gene_explorer.agent import AgentRunError, build_agent, run_agent
from gene_explorer.config import Settings


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    return Settings(_env_file=None)


def test_build_agent_wires_tools_and_model(settings, repo):
    agent = build_agent(settings, repo)
    assert {t.name for t in agent.tools} == {"get_targets", "get_expressions"}
    assert agent.model.model == settings.model  # type: ignore[union-attr]


def test_agent_prompt_lists_repository_cancers(settings, repo):
    agent = build_agent(settings, repo)
    for cancer in repo.cancer_types:
        assert cancer in agent.instructions  # type: ignore[operator]


async def test_run_agent_reports_answer_and_tools(settings, repo, monkeypatch):
    class _Result:
        final_output = "BRCA2: 0.032"

    async def _fake_run(agent, message, *, context, max_turns):
        context.tool_calls.extend(["get_targets", "get_expressions"])
        return _Result()

    monkeypatch.setattr(Runner, "run", staticmethod(_fake_run))
    agent = build_agent(settings, repo)
    answer, tools = await run_agent(agent, "breast values?", max_turns=6)
    assert answer == "BRCA2: 0.032"
    assert tools == ["get_targets", "get_expressions"]


async def test_run_agent_wraps_failures(settings, repo, monkeypatch):
    async def _boom(agent, message, *, context, max_turns):
        raise RuntimeError("groq exploded")

    monkeypatch.setattr(Runner, "run", staticmethod(_boom))
    agent = build_agent(settings, repo)
    with pytest.raises(AgentRunError):
        await run_agent(agent, "x", max_turns=6)


@pytest.mark.skipif(
    not os.getenv("GROQ_LIVE_TEST"), reason="set GROQ_LIVE_TEST=1 for live e2e"
)
async def test_live_breast_query_grounded(real_repo):
    # Reads the real GROQ_API_KEY from the environment, not the fake-key fixture.
    live_settings = Settings(_env_file=None)
    agent = build_agent(live_settings, real_repo)
    answer, tools = await run_agent(
        agent, "Median expression of BRCA2 in breast cancer?", max_turns=6
    )
    assert "0.032" in answer
    assert "get_expressions" in tools
