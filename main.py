import logging
import os

import pandas as pd

from backend.agent.agent import Agent
from backend.api.routes import create_app
from backend.config import get_llm_adapter
from backend.tools.get_expressions import GetExpressionsTool
from backend.tools.get_targets import GetTargetsTool
from backend.tools.registry import ToolRegistry

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

_csv_path = os.getenv("CSV_PATH", "backend/data/gene_dataset.csv")
_df = pd.read_csv(_csv_path)

_registry = ToolRegistry()
_registry.register(GetTargetsTool(_df))
_registry.register(GetExpressionsTool(_df))

_adapter = get_llm_adapter()
_agent = Agent(llm=_adapter, registry=_registry)

app = create_app(agent=_agent)