from __future__ import annotations

from dataclasses import dataclass, field


class GeneExplorerError(Exception):
    """Base class for domain errors."""


class DataValidationError(GeneExplorerError):
    """The dataset does not match the code's expectations."""


@dataclass
class ToolCallLog:
    """Per-request state passed to tools through the Agents SDK run context.

    It records the tools invoked during one agent run and, for grounding, the
    exact values and gene names the tools returned. The output guardrail checks
    the final answer against these grounded sets. The data layer is injected into
    the tools themselves (see tools.build_tools), so it is not part of this object.
    """

    tool_calls: list[str] = field(default_factory=list)
    grounded_values: set[float] = field(default_factory=set)
    grounded_genes: set[str] = field(default_factory=set)

    def record_targets(self, genes: list[str]) -> None:
        self.grounded_genes.update(genes)

    def record_expressions(self, expressions: dict[str, float]) -> None:
        self.grounded_genes.update(expressions.keys())
        self.grounded_values.update(expressions.values())
