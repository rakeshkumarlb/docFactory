from docfactory.agents.model_client import ModelClient
from docfactory.models.model_message import ModelMessage
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_spec import ToolSpec


class FakeModelClient(ModelClient):
    """Scripted ModelClient for tests: returns the prepared responses in order and records every request it received."""

    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[tuple[str, list[ModelMessage], list[ToolSpec]]] = []

    def complete(self, system: str, messages: list[ModelMessage], tools: list[ToolSpec]) -> ModelResponse:
        self.requests.append((system, list(messages), list(tools)))
        if not self._responses:
            raise AssertionError("FakeModelClient has no more scripted responses")
        return self._responses.pop(0)
