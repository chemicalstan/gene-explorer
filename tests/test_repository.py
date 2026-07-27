import pytest

from gene_explorer.domain import DataValidationError
from gene_explorer.repository import GeneRepository


def test_targets_for_returns_only_that_cancer(repo):
    assert set(repo.targets_for("breast")) == {"BRCA2", "TP53", "PIK3CA"}
    assert "EGFR" not in repo.targets_for("breast")


def test_expressions_use_the_cancer_specific_value(repo):
    # BRCA2 is 0.032 in breast, 0.112 in pancreatic. Must return the breast value.
    result = repo.expressions_for("breast", ["BRCA2", "TP53"])
    assert result == {"BRCA2": 0.032, "TP53": 0.233}


def test_expressions_do_not_leak_other_cancers(repo):
    # Asking breast for a gene that only exists under pancreatic returns nothing.
    assert repo.expressions_for("breast", ["EGFR"]) == {}


def test_expressions_unknown_gene_returns_empty(repo):
    assert repo.expressions_for("lung", ["NOPE"]) == {}


def test_cancer_types_derived_from_data(repo):
    assert repo.cancer_types == ("breast", "lung", "pancreatic")


def test_from_csv_rejects_missing_columns(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n1,2\n")
    with pytest.raises(DataValidationError):
        GeneRepository.from_csv(bad)


def test_from_csv_missing_file_raises(tmp_path):
    with pytest.raises(DataValidationError):
        GeneRepository.from_csv(tmp_path / "nope.csv")


def test_real_dataset_breast_values_are_pinned(real_repo):
    # Regression lock for the P0 bug. These are the true breast values.
    got = real_repo.expressions_for("breast", ["BRCA2", "BRCA1", "TP53", "CDH1", "PIK3CA"])
    assert got == {
        "BRCA2": 0.032,
        "BRCA1": 0.094,
        "TP53": 0.233,
        "CDH1": 0.561,
        "PIK3CA": 0.449,
    }
