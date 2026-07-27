import json
from typing import Annotated, Literal

from agents import RunContextWrapper, Tool, function_tool
from pydantic import Field

from gene_explorer.domain import ToolCallLog
from gene_explorer.repository import GeneRepository

# NOTE: this module intentionally does NOT use `from __future__ import annotations`.
# The cancer enum is a Literal built at runtime from the repository, and it must be
# the real annotation object (captured by closure) rather than a string the SDK
# would fail to re-resolve.


def build_tools(repo: GeneRepository) -> list[Tool]:
    """Build the tool set bound to a repository.

    The cancer vocabulary comes from the repository (the data layer), so nothing
    about the domain is hardcoded. Swapping the CSV-backed repository for a
    database-backed one changes the accepted values with no code change here.
    """
    cancer_type = Literal[tuple(repo.cancer_types)]  # type: ignore[valid-type]

    @function_tool(strict_mode=True)
    def get_targets(
        ctx: RunContextWrapper[ToolCallLog],
        cancer_name: cancer_type,  # type: ignore[valid-type]
    ) -> str:
        """Return the JSON list of gene targets for one cancer type."""
        ctx.context.tool_calls.append("get_targets")
        return json.dumps(repo.targets_for(cancer_name))

    @function_tool(strict_mode=True)
    def get_expressions(
        ctx: RunContextWrapper[ToolCallLog],
        cancer_name: cancer_type,  # type: ignore[valid-type]
        genes: Annotated[list[str], Field(min_length=1, max_length=64)],
    ) -> str:
        """Return JSON median expression values for genes within one cancer type."""
        ctx.context.tool_calls.append("get_expressions")
        return json.dumps(repo.expressions_for(cancer_name, genes))

    return [get_targets, get_expressions]
