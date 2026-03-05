import os
import logging
from backend.adapters.base import BaseLLMAdapter
from backend.adapters.groq_adapter import GroqAdapter
from backend.utils.constants import GROQ_MODEL

logger = logging.getLogger(__name__)

def get_llm_adapter() -> BaseLLMAdapter:
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            try:
                adapter = GroqAdapter(GROQ_MODEL)
                logger.info("Using provider: %s", adapter.provider_name)
                return adapter
            except Exception as e:
                logger.warning("GroqAdapter failed: %s. Falling back.", e)

    logger.warning("No LLM provider available. Using rule-based fallback.")