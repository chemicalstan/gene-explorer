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
                },
                "cancer_name": {
                    "type": "string",
                    "enum": [
                        "lung", "breast", "prostate", "gastric",
                        "glioblastoma", "colorectal", "melanoma",
                        "ovarian", "pancreatic", "renal"
                    ],
                    "description": "The cancer type to look up gene targets for.",
                }
            },
            "required": ["genes", "cancer_name"],
        }

    def run(self, **kwargs) -> dict:
        genes = kwargs["genes"]
        cancer_name = kwargs["cancer_name"]
        
        subset = self._df[self._df["gene"].isin(genes) & (self._df['cancer_indication'] == cancer_name)]
        return dict(zip(subset["gene"], subset["median_value"]))
