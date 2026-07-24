import json

from agents.tool_context import ToolContext
from agents.usage import Usage

from gene_explorer.domain import ToolCallLog
from gene_explorer.tools import build_tools


def _ctx() -> ToolContext[ToolCallLog]:
    return ToolContext(
        context=ToolCallLog(),
        usage=Usage(),
        tool_name="test",
        tool_call_id="call_test",
        tool_arguments="",
    )


def _tools(repo):
    tools = {t.name: t for t in build_tools(repo)}
    return tools["get_targets"], tools["get_expressions"]


async def test_get_targets_returns_json_list(repo):
    get_targets, _ = _tools(repo)
    ctx = _ctx()
    out = await get_targets.on_invoke_tool(ctx, json.dumps({"cancer_name": "breast"}))
    assert set(json.loads(out)) == {"BRCA2", "TP53", "PIK3CA"}
    assert ctx.context.tool_calls == ["get_targets"]


async def test_get_expressions_scopes_to_cancer(repo):
    _, get_expressions = _tools(repo)
    ctx = _ctx()
    payload = json.dumps({"cancer_name": "breast", "genes": ["BRCA2"]})
    out = await get_expressions.on_invoke_tool(ctx, payload)
    assert json.loads(out) == {"BRCA2": 0.032}  # not pancreatic 0.112
    assert ctx.context.tool_calls == ["get_expressions"]


def test_cancer_enum_is_derived_from_the_repository(repo):
    # The schema's enum must come from the data, not a hardcoded list.
    get_targets, _ = _tools(repo)
    prop = get_targets.params_json_schema["properties"]["cancer_name"]
    assert set(prop["enum"]) == set(repo.cancer_types)
    assert get_targets.strict_json_schema is True


def test_enum_changes_with_the_data(sample_df):
    # A different dataset yields a different constraint, with no code change.
    # (A single-value Literal serialises to JSON Schema `const`, many to `enum`.)
    from gene_explorer.repository import GeneRepository

    smaller = GeneRepository(sample_df[sample_df["cancer_indication"] == "lung"])
    get_targets = build_tools(smaller)[0]
    prop = get_targets.params_json_schema["properties"]["cancer_name"]
    allowed = prop.get("enum") or [prop["const"]]
    assert allowed == ["lung"]
