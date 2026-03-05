import logging

from backend.adapters.base import BaseLLMAdapter
from backend.tools.registry import ToolRegistry
from backend.utils.constants import MAX_ITERATIONS
from backend.utils.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, llm: BaseLLMAdapter, registry: ToolRegistry) -> None:
        self._llm = llm
        self._registry = registry

    @property
    def provider_name(self) -> str:
        return self._llm.provider_name

    def run(self, user_message: str) -> tuple[str, list[str]]:
        messages = [{"role": "user", "content": user_message}]
        tool_schemas = self._registry.all_schemas()
        tool_calls_made: list[str] = []

        for iteration in range(MAX_ITERATIONS):
            logger.info("[%s] Agent iteration %s", self._llm.provider_name, iteration)

            response = self._llm.complete(
                system_prompt=SYSTEM_PROMPT,
                messages=messages,
                tools=tool_schemas,
            )

            if response.tool_call is not None:
                tool_call = response.tool_call
                tool = self._registry.get(tool_call.tool_name)
                result = tool.run(**tool_call.arguments)
                tool_calls_made.append(tool_call.tool_name)
                logger.info("Tool call: %s(%s)", tool_call.tool_name, tool_call.arguments)
                messages.append(
                    response.assistant_message
                    or {"role": "assistant", "content": None}
                )
                messages.append(
                    self._llm.build_tool_result_message(tool_call.call_id, str(result), tool_call.tool_name)
                )
                continue

            if response.content is not None:
                return response.content, tool_calls_made

        return (
            "I was unable to complete your request within the allowed reasoning steps. "
            "Please rephrase your question.",
            tool_calls_made,
        )
