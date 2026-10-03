import json
import os
import time
import urllib.error
import urllib.request

from docfactory.agents.model_client import ModelClient
from docfactory.models.message_role import MessageRole
from docfactory.models.model_message import ModelMessage
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall
from docfactory.models.tool_spec import ToolSpec

MODEL_ENV = "DOCFACTORY_MODEL"
HOST_ENV = "OLLAMA_HOST"
API_KEY_ENV = "OLLAMA_API_KEY"
NUM_CTX_ENV = "DOCFACTORY_NUM_CTX"
DEFAULT_NUM_CTX = 16384
CLOUD_HOST = "https://ollama.com"
DEFAULT_MODEL = "llama3.2"
DEFAULT_HOST = "http://localhost:11434"


class OllamaModelClient(ModelClient):
    """ModelClient over a local Ollama server (/api/chat, no streaming). The model must support tool calling (e.g. llama3.2, gemma4).

    Local by default. For Ollama Cloud set OLLAMA_HOST=https://ollama.com and OLLAMA_API_KEY (sent as a bearer token), and pick a
    cloud model with DOCFACTORY_MODEL (e.g. gpt-oss:120b). Through a signed-in local server, a '<model>:cloud' name also works.
    Uses only the standard library. Connection errors are retried up to `max_retries` times with a growing pause.
    """

    def __init__(self, model: str | None = None, host: str | None = None, api_key: str | None = None, num_ctx: int | None = None, max_retries: int = 5,
                 timeout: float = 600.0, sleep=time.sleep) -> None:
        self.model = model or os.environ.get(MODEL_ENV) or DEFAULT_MODEL
        self.host = (host or os.environ.get(HOST_ENV) or DEFAULT_HOST).rstrip("/")
        self.api_key = api_key or os.environ.get(API_KEY_ENV)
        if not self.host.startswith("http"):  # OLLAMA_HOST is often given as host:port; never send a key over plain http
            self.host = ("https://" if self.api_key else "http://") + self.host
        self.num_ctx = num_ctx or int(os.environ.get(NUM_CTX_ENV) or DEFAULT_NUM_CTX)  # the extraction agent's 14 tool schemas alone need ~18k tokens
        self.max_retries = max_retries
        self.timeout = timeout
        self._sleep = sleep

    def complete(self, system: str, messages: list[ModelMessage], tools: list[ToolSpec]) -> ModelResponse:
        body = {
            "model": self.model,
            "stream": False,
            "options": {"num_ctx": self.num_ctx, "temperature": 0},
            "messages": [{"role": "system", "content": system}] + self._to_provider_messages(messages),
            "tools": [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": json.loads(t.input_schema_json)}} for t in tools],
        }
        data = self._post("/api/chat", body)
        if data.get("done_reason") == "length":
            raise RuntimeError(f"model response was cut off (context or output limit, num_ctx={self.num_ctx}); raise num_ctx or shorten the task")
        message = data.get("message", {})
        calls = [
            ToolCall(id=f"call_{index}_{call['function']['name']}", name=call["function"]["name"],
                     arguments_json=json.dumps(call["function"].get("arguments") or {}))
            for index, call in enumerate(message.get("tool_calls") or [])
        ]
        return ModelResponse(text=message.get("content") or "", tool_calls=calls)

    def _post(self, path: str, body: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(self.host + path, data=json.dumps(body).encode("utf-8"), headers=headers)
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:  # the server answered: a 4xx is our mistake, not worth retrying
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code < 500:
                    raise RuntimeError(f"Ollama rejected the request ({exc.code}): {detail}") from exc
                error = RuntimeError(f"Ollama server error ({exc.code}): {detail}")
            except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
                error = RuntimeError(f"cannot reach Ollama at {self.host}: {exc}")
            if attempt == self.max_retries:
                raise error
            self._sleep(2 ** attempt)
        raise AssertionError("unreachable")

    @staticmethod
    def _to_provider_messages(messages: list[ModelMessage]) -> list[dict]:
        names: dict[str, str] = {}
        out: list[dict] = []
        for message in messages:
            if message.role == MessageRole.ASSISTANT:
                entry: dict = {"role": "assistant", "content": message.text}
                if message.tool_calls:
                    for call in message.tool_calls:
                        names[call.id] = call.name
                    entry["tool_calls"] = [{"function": {"name": c.name, "arguments": json.loads(c.arguments_json)}} for c in message.tool_calls]
                out.append(entry)
            elif message.role == MessageRole.TOOL:
                out.append({"role": "tool", "tool_name": names.get(message.tool_call_id, ""), "content": message.text})
            else:
                out.append({"role": "user", "content": message.text})
        return out
