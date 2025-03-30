# backend/app/assistant/tools/_base_tool.py
from abc import ABC, abstractmethod

class BaseTool(ABC):
    """Abstract Base Class for tools available to the assistant."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool (lowercase, snake_case recommended)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Clear description of what the tool does, its expected input format,
        and what it returns. This is crucial for the LLM to understand how
        and when to use the tool.
        """
        pass

    @abstractmethod
    def run(self, query: str) -> str:
        """
        Executes the tool with the given query string.
        Should handle potential errors and return a string result.
        """
        pass
