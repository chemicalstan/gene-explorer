import pandas as pd

from backend.tools.base import BaseTool


class GetExpressionsTool(BaseTool):
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    @property
    def name(self) -> str:
        return "get_expressions"

    @property
    def description(self) -> str:
        return (
            "Returns the median expression values for a list of genes. "
            "Use this after get_targets to retrieve expression data for the returned genes."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "genes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of gene names to retrieve median expression values for.",
                }
            },
            "required": ["genes"],
        }

    def run(self, **kwargs) -> dict:
        genes = kwargs["genes"]
        subset = self._df[self._df["gene"].isin(genes)]
        return dict(zip(subset["gene"], subset["median_value"]))
