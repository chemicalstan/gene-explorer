import json
import logging
import os

from backend.utils.constants import GROQ_MODEL_MAX_TOKEN, GROQ_MODEL_TEMPERATURE
import groq
from groq import Groq

from backend.adapters.base import BaseLLMAdapter, LLMResponse, ToolCall

logger = logging.getLogger(__name__)


def _to_openai_tool_schema(tool: dict) -> dict:
    """Translate BaseTool.to_llm_schema() format into OpenAI function-calling format."""
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


class GroqAdapter(BaseLLMAdapter):
    def __init__(self, model: str) -> None:
        self._model = model
        # Pass api_key explicitly so the SDK doesn't raise if the env var is absent.
        # The key is only used when complete() makes an actual network call.
        self._client = Groq(api_key=os.getenv("GROQ_API_KEY", "placeholder"))

    def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
        response_format: dict | None = None,
    ) -> LLMResponse:
        translated_tools = [_to_openai_tool_schema(t) for t in tools]

        kwargs: dict = {
            "model": self._model,
            "max_tokens": GROQ_MODEL_MAX_TOKEN,
            "temperature": GROQ_MODEL_TEMPERATURE,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
        }
        if translated_tools:
            kwargs["tools"] = translated_tools
            kwargs["tool_choice"] = "auto"
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = self._call_with_retry(kwargs)
        except groq.BadRequestError as exc:
            code = (exc.body or {}).get("error", {}).get("code", "") if isinstance(exc.body, dict) else ""
            if code == "tool_use_failed":
                logger.error("Groq tool_use_failed after retry — returning graceful fallback")
                return LLMResponse(
                    content="I wasn't able to process that query. Please rephrase your question.",
                    tool_call=None,
                    raw=None,
                )
            raise

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            tool = tool_calls[0]
            assistant_message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tool.id,
                        "type": "function",
                        "function": {
                            "name": tool.function.name,
                            "arguments": tool.function.arguments,
                        },
                    }
                ],
            }
            return LLMResponse(
                content=None,
                tool_call=ToolCall(
                    tool_name=tool.function.name,
                    arguments=json.loads(tool.function.arguments),
                    call_id=tool.id,
                ),
                raw=response,
                assistant_message=assistant_message,
            )

        return LLMResponse(
            content=response.choices[0].message.content,
            tool_call=None,
            raw=response,
        )

    def _call_with_retry(self, kwargs: dict):
        """Groq/llama models occasionally emit Hermes-format tool calls instead of
        Structured JSON, causing a 400 tool_use_failed. Retry once — the error is intermittent.
        Other providers with schema enforcement never reach this path. See Readme referece for details"""
        for attempt in range(2):
            try:
                return self._client.chat.completions.create(**kwargs)
            except groq.BadRequestError as exc:
                code = (exc.body or {}).get("error", {}).get("code", "") if isinstance(exc.body, dict) else ""
                if code == "tool_use_failed" and attempt == 0:
                    logger.warning("Groq tool_use_failed on attempt 1 — retrying once")
                    continue
                raise

    def build_tool_result_message(
        self, call_id: str | None, result: str, tool_name: str | None = None
    ) -> dict:
        """Groq requires a 'name' field in tool result messages."""
        msg: dict = {"role": "tool", "tool_call_id": call_id, "content": result}
        if tool_name:
            msg["name"] = tool_name
        return msg

    @property
    def provider_name(self) -> str:
        return f"groq/{self._model}"
