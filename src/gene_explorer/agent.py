from __future__ import annotations

from agents import (
    Agent,
    ModelSettings,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
)
from agents.items import ToolCallItem
from agents.run import Runner
from openai import AsyncOpenAI

from gene_explorer.config import Settings
from gene_explorer.domain import CANCER_TYPES, GeneContext, GeneExplorerError
from gene_explorer.prompts import build_system_prompt
from gene_explorer.repository import GeneRepository
from gene_explorer.tools import TOOLS

# Tracing otherwise uploads to OpenAI's servers and 401s against a Groq-only key.
set_tracing_disabled(True)


class AgentRunError(GeneExplorerError):
    """The agent failed to produce an answer."""


def build_agent(settings: Settings) -> Agent[GeneContext]:
    client = AsyncOpenAI(
        api_key=settings.groq_api_key.get_secret_value(),
        base_url=settings.groq_base_url,
        timeout=settings.request_timeout_s,
    )
    model = OpenAIChatCompletionsModel(model=settings.model, openai_client=client)
    return Agent[GeneContext](
        name="gene-explorer",
        instructions=build_system_prompt(CANCER_TYPES),
        model=model,
        tools=TOOLS,
        model_settings=ModelSettings(
            temperature=settings.temperature,
            extra_body={
                "seed": settings.seed,
                "reasoning_effort": settings.reasoning_effort,
            },
        ),
    )


async def run_agent(
    agent: Agent[GeneContext],
    repo: GeneRepository,
    message: str,
    *,
    max_turns: int,
) -> tuple[str, list[str]]:
    context = GeneContext(repo=repo)
    try:
        result = await Runner.run(agent, message, context=context, max_turns=max_turns)
    except Exception as exc:  # noqa: BLE001 - surfaced as a domain error to the API
        raise AgentRunError(str(exc)) from exc

    tools = context.tool_calls or [
        item.raw_item.name
        for item in getattr(result, "new_items", [])
        if isinstance(item, ToolCallItem)
    ]
    return str(result.final_output), tools
