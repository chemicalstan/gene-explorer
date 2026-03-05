import pandas as pd

from backend.tools.base import BaseTool


class GetTargetsTool(BaseTool):
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    @property
    def name(self) -> str:
        return "get_targets"

    @property
    def description(self) -> str:
        return (
            "Returns the list of gene targets associated with a given cancer type. "
            "Use this when asked what genes are involved in a specific cancer."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
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
            "required": ["cancer_name"],
        }

    def run(self, **kwargs) -> list:
        cancer_name = kwargs["cancer_name"]
        return self._df[self._df["cancer_indication"] == cancer_name]["gene"].tolist()
