import pytest
import pandas as pd
from backend.tools.get_targets import GetTargetsTool

@pytest.fixture
def mock_df():
    return pd.DataFrame({
        "cancer_indication": ["lung", "lung", "breast", "esophageal"],
        "gene": ["EGFR", "KRAS", "BRCA1", "TP53"],
        "median_value": [1.2, 3.4, 2.1, 0.9],
    })

def test_returns_correct_genes(mock_df):
    tool = GetTargetsTool(mock_df)
    result = tool.run(cancer_name="lung")
    assert "EGFR" in result
    assert "KRAS" in result
    assert "BRCA1" not in result

def test_returns_empty_for_unknown(mock_df):
    tool = GetTargetsTool(mock_df)
    assert tool.run(cancer_name="unknown") == []

def test_schema_has_required_fields(mock_df):
    tool = GetTargetsTool(mock_df)
    schema = tool.to_llm_schema()
    assert schema["name"] == "get_targets"
    assert "cancer_name" in schema["input_schema"]["properties"]
