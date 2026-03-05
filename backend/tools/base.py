from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Contract every tool must fulfil to work with the agent."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier the LLM uses to call this tool."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Tells the LLM what this tool does."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict:
        """Defines what arguments the LLM should pass."""
        ...

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """The actual tool logic."""
        ...

    def to_llm_schema(self) -> dict:
        """Packages name, description, and schema into the format the LLM expects."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }