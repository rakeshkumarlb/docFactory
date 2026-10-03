import json
import os

from docfactory.agents.model_client import ModelClient
from docfactory.models.message_role import MessageRole
from docfactory.models.model_message import ModelMessage
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall
from docfactory.models.tool_spec import ToolSpec

MODEL_ENV = "DOCFACTORY_MODEL"
DEFAULT_MODEL = "claude-sonnet-5-5"


class AnthropicModelClient(ModelClient):
    """ModelClient over the Anthropic Messages API. Translates neutral messages and tools to the provider format and back."""

    def __init__(self, model: str | None = None, max_tokens: int = 4096, max_retries: int = 4, client=None) -> None:
        self.model = model or os.environ.get(MODEL_ENV) or DEFAULT_MODEL
        self.max_tokens = max_tokens
        if client is None:
            import anthropic  # reads ANTHROPIC_API_KEY from the environment

            # The SDK retries rate limits (429), server errors (5xx), timeouts and connection errors with backoff, up to max_retries.
            client = anthropic.Anthropic(max_retries=max_retries)
        self._client = client

    def complete(self, system: str, messages: list[ModelMessage], tools: list[ToolSpec]) -> ModelResponse:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=self._to_provider_messages(messages),
            tools=[{"name": t.name, "description": t.description, "input_schema": json.loads(t.input_schema_json)} for t in tools],
        )
        if getattr(response, "stop_reason", None) == "max_tokens":
            raise RuntimeError(f"model response was cut off at max_tokens={self.max_tokens}; raise max_tokens or shorten the task")
        text = "".join(block.text for block in response.content if block.type == "text")
        calls = [ToolCall(id=b.id, name=b.name, arguments_json=json.dumps(b.input)) for b in response.content if b.type == "tool_use"]
        return ModelResponse(text=text, tool_calls=calls)

    @staticmethod
    def _to_provider_messages(messages: list[ModelMessage]) -> list[dict]:
        out: list[dict] = []
        for message in messages:
            if message.role == MessageRole.TOOL:
                block = {"type": "tool_result", "tool_use_id": message.tool_call_id, "content": message.text}
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(block)  # results of one assistant turn go in one user message
                else:
                    out.append({"role": "user", "content": [block]})
            elif message.role == MessageRole.ASSISTANT:
                content = [{"type": "text", "text": message.text}] if message.text else []
                content += [{"type": "tool_use", "id": c.id, "name": c.name, "input": json.loads(c.arguments_json)} for c in message.tool_calls]
                out.append({"role": "assistant", "content": content})
            else:
                out.append({"role": "user", "content": message.text})
        return out
