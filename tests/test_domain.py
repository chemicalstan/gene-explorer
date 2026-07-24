from typing import get_args

from gene_explorer.domain import CANCER_TYPES, CancerName, GeneContext


def test_cancer_types_are_sorted_and_unique():
    assert list(CANCER_TYPES) == sorted(CANCER_TYPES)
    assert len(set(CANCER_TYPES)) == len(CANCER_TYPES)


def test_cancer_name_literal_matches_tuple():
    assert set(get_args(CancerName)) == set(CANCER_TYPES)


def test_context_defaults_to_empty_tool_calls():
    ctx = GeneContext(repo=object())  # type: ignore[arg-type]
    assert ctx.tool_calls == []
