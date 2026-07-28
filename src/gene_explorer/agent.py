from __future__ import annotations

from typing import Any

from agents import (
    Agent,
    InputGuardrailTripwireTriggered,
    ModelSettings,
    OpenAIChatCompletionsModel,
    OutputGuardrailTripwireTriggered,
    set_tracing_disabled,
)
from agents.run import Runner
from openai import AsyncOpenAI

from gene_explorer.config import Settings
from gene_explorer.domain import AgentResult, GeneExplorerError, RunUsage, ToolCallLog
from gene_explorer.guardrails import (
    INPUT_BLOCKED_MESSAGE,
    OUTPUT_UNGROUNDED_MESSAGE,
    grounding_guardrail,
    injection_guardrail,
)
from gene_explorer.logging_config import get_logger
from gene_explorer.prompts import build_system_prompt
from gene_explorer.repository import GeneRepository
from gene_explorer.tools import build_tools

logger = get_logger("gene_explorer.agent")


def _to_run_usage(usage: Any) -> RunUsage:
    return RunUsage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        requests=usage.requests,
    )


def _usage_from_exception(exc: Any) -> RunUsage:
    # A guardrail that trips after the model runs still cost tokens. The SDK
    # attaches the accumulated usage to the exception's run_data.
    run_data = getattr(exc, "run_data", None)
    if run_data is None:
        return RunUsage()
    return _to_run_usage(run_data.context_wrapper.usage)


# Tracing otherwise uploads to OpenAI's servers and 401s against a Groq-only key.
set_tracing_disabled(True)


class AgentRunError(GeneExplorerError):
    """The agent failed to produce an answer."""


def build_agent(settings: Settings, repo: GeneRepository) -> Agent[ToolCallLog]:
    """Build the agent for a given data layer. The prompt and the tools both take
    their cancer vocabulary from the repository, so the agent adapts to whatever
    data the repository serves."""
    client = AsyncOpenAI(
        api_key=settings.groq_api_key.get_secret_value(),
        base_url=settings.groq_base_url,
        timeout=settings.request_timeout_s,
    )
    model = OpenAIChatCompletionsModel(model=settings.model, openai_client=client)
    return Agent[ToolCallLog](
        name="gene-explorer",
        instructions=build_system_prompt(repo.cancer_types),
        model=model,
        tools=build_tools(repo),
        input_guardrails=[injection_guardrail],
        output_guardrails=[grounding_guardrail],
        model_settings=ModelSettings(
            temperature=settings.temperature,
            extra_body={
                "seed": settings.seed,
                "reasoning_effort": settings.reasoning_effort,
            },
        ),
    )


async def run_agent(agent: Agent[ToolCallLog], message: str, *, max_turns: int) -> AgentResult:
    log = ToolCallLog()
    try:
        result = await Runner.run(agent, message, context=log, max_turns=max_turns)
    except InputGuardrailTripwireTriggered as exc:
        logger.warning("input_guardrail_blocked")
        return AgentResult(INPUT_BLOCKED_MESSAGE, list(log.tool_calls), _usage_from_exception(exc))
    except OutputGuardrailTripwireTriggered as exc:
        logger.warning("output_grounding_withheld")
        return AgentResult(
            OUTPUT_UNGROUNDED_MESSAGE, list(log.tool_calls), _usage_from_exception(exc)
        )
    except Exception as exc:  # noqa: BLE001 - surfaced as a domain error to the API
        raise AgentRunError(str(exc)) from exc

    # Each tool appends its own name to the log, giving the exact call order.
    return AgentResult(
        answer=str(result.final_output),
        tool_calls=list(log.tool_calls),
        usage=_to_run_usage(result.context_wrapper.usage),
    )
