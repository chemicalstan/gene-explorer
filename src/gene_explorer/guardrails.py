from __future__ import annotations

import re
from collections.abc import Iterable

from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    TResponseInputItem,
    input_guardrail,
    output_guardrail,
)

from gene_explorer.domain import ToolCallLog

# A decimal literal, e.g. 0.032. Integers are ignored on purpose: expression
# values are decimals, and counts such as "10 genes" are legitimate.
_DECIMAL = re.compile(r"\d+\.\d+")

# First-line prompt-injection patterns. This is a cheap deterministic filter, not
# a complete defence; the strict tool schema and the output guardrail carry the
# real safety guarantees.
_INJECTION = re.compile(
    r"ignore\s+(?:all\s+|your\s+|the\s+)?(?:previous|prior|above)\s+instructions"
    r"|disregard\s+(?:the\s+|your\s+)?(?:rules|instructions|system)"
    r"|system\s+prompt"
    r"|you\s+are\s+now\b"
    r"|reveal\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions)",
    re.IGNORECASE,
)


def ungrounded_numbers(answer: str, allowed: Iterable[float], *, tol: float = 1e-9) -> list[str]:
    """Return the decimal literals in the answer that are not among the allowed
    values. The allowed set is what the tools actually returned this turn."""
    allowed_list = list(allowed)
    result: list[str] = []
    for token in _DECIMAL.findall(answer):
        value = float(token)
        if not any(abs(value - a) <= tol for a in allowed_list):
            result.append(token)
    return result


def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION.search(text))


def _input_text(user_input: str | list[TResponseInputItem]) -> str:
    if isinstance(user_input, str):
        return user_input
    parts: list[str] = []
    for item in user_input:
        content = item.get("content") if isinstance(item, dict) else None
        if isinstance(content, str):
            parts.append(content)
    return " ".join(parts)


@input_guardrail
async def injection_guardrail(
    ctx: RunContextWrapper[ToolCallLog],
    agent: Agent[ToolCallLog],
    user_input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """Block obvious prompt-injection attempts before the model runs."""
    blocked = looks_like_injection(_input_text(user_input))
    return GuardrailFunctionOutput(output_info={"blocked": blocked}, tripwire_triggered=blocked)


@output_guardrail
async def grounding_guardrail(
    ctx: RunContextWrapper[ToolCallLog],
    agent: Agent[ToolCallLog],
    output: str,
) -> GuardrailFunctionOutput:
    """Fail closed: every decimal in the answer must be a value the tools returned
    this turn. Any other decimal is treated as ungrounded and trips the wire."""
    answer = output if isinstance(output, str) else str(output)
    ungrounded = ungrounded_numbers(answer, ctx.context.grounded_values)
    return GuardrailFunctionOutput(
        output_info={"ungrounded_numbers": ungrounded},
        tripwire_triggered=bool(ungrounded),
    )
