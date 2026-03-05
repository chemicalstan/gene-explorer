from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    tool_name: str
    arguments: dict[str, Any]
    call_id: str | None = None


@dataclass
class LLMResponse:
    content: str | None           # final answer
    tool_call: ToolCall | None    # tool invocation request
    raw: Any = None               # original provider response
    assistant_message: dict | None = None  # properly-formatted assistant msg for history


class BaseLLMAdapter(ABC):
    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
        response_format: dict | None = None,
    ) -> LLMResponse: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    def build_tool_result_message(
        self, call_id: str | None, result: str, tool_name: str | None = None
    ) -> dict:
        """Returns the message dict to append after executing a tool call.
        Default is Groq LLM format; override for providers with different formats."""
        return {"role": "tool", "tool_call_id": call_id, "content": result}
