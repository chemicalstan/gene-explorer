import ast
import re

from backend.adapters.base import BaseLLMAdapter, LLMResponse, ToolCall
from backend.utils.constants import CANCER_TYPES

_SUPPORTED = ", ".join(CANCER_TYPES)

_CAPABILITIES = (
    "I can help you explore cancer genomics data. You can ask me:\n"
    f"- What genes are associated with a specific cancer ({_SUPPORTED})\n"
    "- The median expression values of genes in a given cancer type\n"
    "- To chain both lookups together for a full summary"
)

_CATCHALL = (
    "I can answer questions about cancer gene targets and expression values. "
    f"Supported cancer types: {_SUPPORTED}. "
    "Try asking: 'What genes are involved in lung cancer?' or "
    "'What is the median expression of genes in breast cancer?'"
)

# Queries that need both get_targets → get_expressions chained
_MEDIAN_PATTERN = re.compile(r"median|expression", re.IGNORECASE)
_HELP_PATTERN = re.compile(r"how can you help|what can you do", re.IGNORECASE)


def _tool_results(messages: list[dict]) -> list[dict]:
    """Return all tool result messages in order: {role, tool_call_id, content}."""
    return [m for m in messages if m.get("role") == "tool"]


def _parse_gene_list(raw: str) -> list[str] | None:
    """Try to parse a Python list literal of gene names from a tool result string."""
    try:
        value = ast.literal_eval(raw.strip())
        if isinstance(value, list):
            return value
    except Exception:
        pass
    return None


def _format_expressions(raw: str) -> str:
    """Turn a dict-repr expression result into a readable string."""
    try:
        data: dict = ast.literal_eval(raw.strip())
        if isinstance(data, dict):
            lines = [f"  {gene}: {value:.3f}" for gene, value in data.items()]
            return "Median expression values:\n" + "\n".join(lines)
    except Exception:
        pass
    return f"Based on the dataset: {raw}"


class RuleBasedAdapter(BaseLLMAdapter):
    def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
        response_format: dict | None = None,
    ) -> LLMResponse:
        try:
            tool_results = _tool_results(messages)

            if tool_results:
                first_result = tool_results[0]["content"]

                # Determine if the original query needs expression values
                user_messages = [m for m in messages if m.get("role") == "user"]
                original_query = user_messages[0].get("content", "") if user_messages else ""
                needs_expressions = bool(_MEDIAN_PATTERN.search(original_query))

                # Detect chain state by parsing result content:
                # get_targets  -> returns a list  -> parse as gene list
                # get_expressions -> returns a dict -> parse as expression map
                first_as_list = _parse_gene_list(first_result)
                if (
                    needs_expressions
                    and len(tool_results) == 1
                    and first_as_list is not None
                ):
                    # Have gene list, still need expressions, chain to get_expressions
                    return LLMResponse(
                        content=None,
                        tool_call=ToolCall("get_expressions", {"genes": first_as_list}),
                    )

                # We have the final result, use the last tool result
                last_result = tool_results[-1]["content"]
                return LLMResponse(content=_format_expressions(last_result), tool_call=None)

            user_messages = [m for m in messages if m.get("role") == "user"]
            if not user_messages:
                return LLMResponse(content=_CATCHALL, tool_call=None)

            text = user_messages[-1].get("content", "").lower()

            if _HELP_PATTERN.search(text):
                return LLMResponse(content=_CAPABILITIES, tool_call=None)

            for cancer in CANCER_TYPES:
                if cancer in text:
                    return LLMResponse(
                        content=None,
                        tool_call=ToolCall("get_targets", {"cancer_name": cancer}),
                    )

            return LLMResponse(content=_CATCHALL, tool_call=None)
        except Exception:
            return LLMResponse(content=_CATCHALL, tool_call=None)

    @property
    def provider_name(self) -> str:
        return "rule_based/deterministic"
