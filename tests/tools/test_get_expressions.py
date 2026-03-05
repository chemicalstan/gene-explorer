import pytest
import pandas as pd
from backend.tools.get_expressions import GetExpressionsTool

@pytest.fixture
def mock_df():
    return pd.DataFrame({
        'cancer_indication': ['lung', 'lung', 'breast'],
        'gene': ['EGFR', 'KRAS', 'BRCA1'],
        'median_value': [0.215, 0.359, 0.094],
    })

def test_returns_correct_values(mock_df):
    tool = GetExpressionsTool(mock_df)
    result = tool.run(genes=['EGFR', 'KRAS'])
    assert result['EGFR'] == pytest.approx(0.215)
    assert result['KRAS'] == pytest.approx(0.359)

def test_unknown_gene_returns_empty(mock_df):
    tool = GetExpressionsTool(mock_df)
    result = tool.run(genes=['NONEXISTENT'])
    assert result == {}

def test_only_requested_genes_returned(mock_df):
    tool = GetExpressionsTool(mock_df)
    result = tool.run(genes=['EGFR'])
    assert 'KRAS' not in result
    assert 'BRCA1' not in result

def test_schema_has_required_fields(mock_df):
    tool = GetExpressionsTool(mock_df)
    schema = tool.to_llm_schema()
    assert schema['name'] == 'get_expressions'
    assert 'genes' in schema['input_schema']['properties']
