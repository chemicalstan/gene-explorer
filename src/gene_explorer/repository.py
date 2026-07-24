from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from gene_explorer.domain import DataValidationError

_REQUIRED_COLUMNS = {"cancer_indication", "gene", "median_value"}


class GeneRepository:
    """Read-only access to the gene dataset, keyed by (cancer_indication, gene)."""

    def __init__(self, df: pd.DataFrame) -> None:
        missing = _REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise DataValidationError(f"Dataset missing columns: {sorted(missing)}")
        self._df = df

    @classmethod
    def from_csv(cls, path: Path) -> GeneRepository:
        try:
            df = pd.read_csv(path)
        except FileNotFoundError as exc:
            raise DataValidationError(f"Dataset not found at {path}") from exc
        return cls(df)

    @property
    def cancer_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._df["cancer_indication"].unique()))

    def targets_for(self, cancer_name: str) -> list[str]:
        mask = self._df["cancer_indication"] == cancer_name
        return self._df.loc[mask, "gene"].tolist()

    def expressions_for(self, cancer_name: str, genes: Iterable[str]) -> dict[str, float]:
        # Filter on BOTH cancer and gene. Filtering on gene alone matches the same
        # gene under other cancers and silently returns the wrong value.
        wanted = list(genes)
        mask = (self._df["cancer_indication"] == cancer_name) & (self._df["gene"].isin(wanted))
        subset = self._df.loc[mask]
        return {
            str(g): float(v) for g, v in zip(subset["gene"], subset["median_value"], strict=True)
        }
