from gene_explorer.domain import DataValidationError, GeneExplorerError, ToolCallLog


def test_tool_call_log_defaults_to_empty():
    assert ToolCallLog().tool_calls == []


def test_tool_call_log_records_order():
    log = ToolCallLog()
    log.tool_calls.append("get_targets")
    log.tool_calls.append("get_expressions")
    assert log.tool_calls == ["get_targets", "get_expressions"]


def test_data_validation_error_is_a_domain_error():
    assert issubclass(DataValidationError, GeneExplorerError)
