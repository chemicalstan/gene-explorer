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
    """Exactly one of content or tool_call will be set — never both, required for agent loop branching."""
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
        """Formats a tool result for the message history.
        Override this for providers that expect a different format."""
        return {"role": "tool", "tool_call_id": call_id, "content": result}
