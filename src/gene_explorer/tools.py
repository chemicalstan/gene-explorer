from __future__ import annotations

import json
from typing import Annotated

from agents import RunContextWrapper, Tool, function_tool
from pydantic import Field

from gene_explorer.domain import CancerName, GeneContext


@function_tool(strict_mode=True)
def get_targets(ctx: RunContextWrapper[GeneContext], cancer_name: CancerName) -> str:
    """Return the JSON list of gene targets for one cancer type."""
    ctx.context.tool_calls.append("get_targets")
    return json.dumps(ctx.context.repo.targets_for(cancer_name))


@function_tool(strict_mode=True)
def get_expressions(
    ctx: RunContextWrapper[GeneContext],
    cancer_name: CancerName,
    genes: Annotated[list[str], Field(min_length=1, max_length=64)],
) -> str:
    """Return JSON median expression values for genes within one cancer type."""
    ctx.context.tool_calls.append("get_expressions")
    return json.dumps(ctx.context.repo.expressions_for(cancer_name, genes))


TOOLS: list[Tool] = [get_targets, get_expressions]
