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


def test_record_targets_accumulates_genes():
    log = ToolCallLog()
    log.record_targets(["BRCA1", "TP53"])
    assert log.grounded_genes == {"BRCA1", "TP53"}


def test_record_expressions_accumulates_genes_and_values():
    log = ToolCallLog()
    log.record_expressions({"BRCA1": 0.094, "TP53": 0.233})
    assert log.grounded_genes == {"BRCA1", "TP53"}
    assert log.grounded_values == {0.094, 0.233}
