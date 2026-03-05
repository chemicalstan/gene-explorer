import pytest
from backend.adapters.rule_based_adapter import RuleBasedAdapter

@pytest.fixture
def adapter():
    return RuleBasedAdapter()

def test_help_returns_content(adapter):
    resp = adapter.complete(
        "", [{"role": "user", "content": "how can you help me?"}], []
    )
    assert resp.content is not None
    assert resp.tool_call is None

def test_lung_returns_tool_call(adapter):
    resp = adapter.complete(
        "", [{"role": "user", "content": "median expression lung cancer"}], []
    )
    assert resp.tool_call is not None
    assert resp.tool_call.tool_name == "get_targets"
    assert resp.tool_call.arguments["cancer_name"] == "lung"

def test_unknown_query_returns_content(adapter):
    resp = adapter.complete(
        "", [{"role": "user", "content": "xyzzy 12345 unknown"}], []
    )
    assert resp.content is not None

def test_complete_never_raises(adapter):
    resp = adapter.complete("", [], [])
    assert resp.content is not None
