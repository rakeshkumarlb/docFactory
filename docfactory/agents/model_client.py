from abc import ABC, abstractmethod

from docfactory.models.model_message import ModelMessage
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_spec import ToolSpec


class ModelClient(ABC):
    """Provider-neutral interface to an LLM: one call takes the conversation and the tools on offer and returns one response."""

    @abstractmethod
    def complete(self, system: str, messages: list[ModelMessage], tools: list[ToolSpec]) -> ModelResponse:
        """Send `system`, the conversation so far and the available tools; return the model's text and any tool calls."""
