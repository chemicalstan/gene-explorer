from __future__ import annotations

from dataclasses import dataclass, field


class GeneExplorerError(Exception):
    """Base class for domain errors."""


class DataValidationError(GeneExplorerError):
    """The dataset does not match the code's expectations."""


@dataclass
class ToolCallLog:
    """Per-request state passed to tools through the Agents SDK run context.

    Holds the ordered names of the tools invoked during one agent run. The data
    layer is injected into the tools themselves (see tools.build_tools), so it is
    deliberately not part of this per-request object.
    """

    tool_calls: list[str] = field(default_factory=list)
