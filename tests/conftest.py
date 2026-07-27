from pathlib import Path

import pandas as pd
import pytest

from gene_explorer.repository import GeneRepository

# Deliberately includes a gene (BRCA2) shared across two cancers with DIFFERENT
# values — this is the exact shape that caused the original wrong-values bug.
_ROWS = [
    ("breast", "BRCA2", 0.032),
    ("breast", "TP53", 0.233),
    ("breast", "PIK3CA", 0.449),
    ("pancreatic", "BRCA2", 0.112),
    ("lung", "EGFR", 0.215),
    ("lung", "KRAS", 0.359),
]


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(_ROWS, columns=["cancer_indication", "gene", "median_value"])


@pytest.fixture
def repo(sample_df: pd.DataFrame) -> GeneRepository:
    return GeneRepository(sample_df)


@pytest.fixture
def real_repo() -> GeneRepository:
    root = Path(__file__).resolve().parents[1]
    return GeneRepository.from_csv(root / "src/gene_explorer/data/gene_dataset.csv")
