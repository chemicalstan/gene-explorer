import json

from agents.tool_context import ToolContext
from agents.usage import Usage

from gene_explorer.domain import GeneContext
from gene_explorer.tools import TOOLS, get_expressions, get_targets


def _ctx(repo) -> ToolContext[GeneContext]:
    return ToolContext(
        context=GeneContext(repo=repo),
        usage=Usage(),
        tool_name="test",
        tool_call_id="call_test",
        tool_arguments="",
    )


async def test_get_targets_returns_json_list(repo):
    ctx = _ctx(repo)
    out = await get_targets.on_invoke_tool(ctx, json.dumps({"cancer_name": "breast"}))
    assert set(json.loads(out)) == {"BRCA2", "TP53", "PIK3CA"}
    assert ctx.context.tool_calls == ["get_targets"]


async def test_get_expressions_scopes_to_cancer(repo):
    ctx = _ctx(repo)
    payload = json.dumps({"cancer_name": "breast", "genes": ["BRCA2"]})
    out = await get_expressions.on_invoke_tool(ctx, payload)
    assert json.loads(out) == {"BRCA2": 0.032}  # not pancreatic 0.112
    assert ctx.context.tool_calls == ["get_expressions"]


def test_tool_schema_pins_cancer_enum():
    schema = get_targets.params_json_schema
    prop = schema["properties"]["cancer_name"]
    assert "breast" in prop["enum"]
    assert get_targets.strict_json_schema is True


def test_tools_list_has_both():
    names = {t.name for t in TOOLS}
    assert names == {"get_targets", "get_expressions"}
