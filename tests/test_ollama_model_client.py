import io
import json
import urllib.error

import pytest

from docfactory.agents import ollama_model_client as module
from docfactory.agents.model_client_factory import default_client
from docfactory.agents.ollama_model_client import OllamaModelClient
from docfactory.models.message_role import MessageRole
from docfactory.models.model_message import ModelMessage
from docfactory.models.tool_call import ToolCall
from docfactory.models.tool_spec import ToolSpec


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def server(monkeypatch):
    """Replaces urlopen; `server.replies` is a list of dicts (returned) or exceptions (raised); `server.requests` records what was sent."""
    state = type("S", (), {"replies": [], "requests": []})()

    def urlopen(request, timeout=None):
        state.requests.append(request)
        reply = state.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return _Response(json.dumps(reply).encode("utf-8"))

    monkeypatch.setattr(module.urllib.request, "urlopen", urlopen)
    for var in ("OLLAMA_HOST", "OLLAMA_API_KEY", "DOCFACTORY_MODEL", "DOCFACTORY_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    return state


SPEC = ToolSpec(name="list_incoming", description="d", input_schema_json='{"type": "object", "properties": {}}')
USER = ModelMessage(role=MessageRole.USER, text="go")


def test_request_and_response_translation(server):
    server.replies.append({"done_reason": "stop", "message": {"content": "hi", "tool_calls": [
        {"function": {"name": "list_incoming", "arguments": {}}}, {"function": {"name": "store_file", "arguments": {"a": 1}}}]}})
    messages = [USER,
                ModelMessage(role=MessageRole.ASSISTANT, tool_calls=[ToolCall(id="c1", name="list_incoming")]),
                ModelMessage(role=MessageRole.TOOL, tool_call_id="c1", text="[]")]
    response = OllamaModelClient(model="m").complete("SYS", messages, [SPEC])
    sent = json.loads(server.requests[0].data)
    assert server.requests[0].full_url == "http://localhost:11434/api/chat"
    assert sent["model"] == "m" and sent["stream"] is False and sent["options"]["temperature"] == 0
    assert sent["messages"][0] == {"role": "system", "content": "SYS"}
    assert sent["messages"][2]["tool_calls"] == [{"function": {"name": "list_incoming", "arguments": {}}}]
    assert sent["messages"][3] == {"role": "tool", "tool_name": "list_incoming", "content": "[]"}
    assert sent["tools"][0]["function"]["parameters"] == {"type": "object", "properties": {}}
    assert response.text == "hi"
    assert [(c.name, json.loads(c.arguments_json)) for c in response.tool_calls] == [("list_incoming", {}), ("store_file", {"a": 1})]
    assert len({c.id for c in response.tool_calls}) == 2


def test_cloud_host_and_api_key(server, monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "ollama.com")
    monkeypatch.setenv("OLLAMA_API_KEY", "secret")
    server.replies.append({"message": {"content": "ok"}})
    OllamaModelClient().complete("S", [USER], [])
    request = server.requests[0]
    assert request.full_url == "https://ollama.com/api/chat"  # a key forces https for a bare host
    assert request.get_header("Authorization") == "Bearer secret"


def test_https_cloud_host_is_kept(server):
    server.replies.append({"message": {"content": "ok"}})
    OllamaModelClient(host="https://ollama.com", api_key="k").complete("S", [USER], [])
    assert server.requests[0].full_url == "https://ollama.com/api/chat"


def test_no_key_means_no_auth_header(server):
    server.replies.append({"message": {"content": "ok"}})
    OllamaModelClient().complete("S", [USER], [])
    assert server.requests[0].get_header("Authorization") is None


def test_cut_off_raises(server):
    server.replies.append({"done_reason": "length", "message": {"content": "par"}})
    with pytest.raises(RuntimeError, match="cut off"):
        OllamaModelClient().complete("S", [USER], [])


def test_connection_errors_are_retried_then_raised(server):
    sleeps = []
    server.replies += [urllib.error.URLError("down"), urllib.error.URLError("down"), {"message": {"content": "ok"}}]
    assert OllamaModelClient(sleep=sleeps.append).complete("S", [USER], []).text == "ok"
    assert sleeps == [1, 2]
    server.replies += [urllib.error.URLError("down")] * 3
    with pytest.raises(RuntimeError, match="cannot reach Ollama"):
        OllamaModelClient(max_retries=2, sleep=lambda s: None).complete("S", [USER], [])


def test_client_errors_are_not_retried(server):
    err = urllib.error.HTTPError("u", 401, "unauthorized", {}, io.BytesIO(b'{"error":"bad key"}'))
    server.replies.append(err)
    with pytest.raises(RuntimeError, match="401"):
        OllamaModelClient(sleep=lambda s: None).complete("S", [USER], [])
    assert len(server.requests) == 1


def test_default_client_is_ollama_and_provider_is_switchable(server, monkeypatch):
    assert isinstance(default_client(), OllamaModelClient)
    monkeypatch.setenv("DOCFACTORY_PROVIDER", "nope")
    with pytest.raises(ValueError):
        default_client()


def test_num_ctx_defaults_to_16384_and_can_be_set_by_argument_or_environment(monkeypatch):
    from docfactory.agents.ollama_model_client import OllamaModelClient

    monkeypatch.delenv("DOCFACTORY_NUM_CTX", raising=False)
    assert OllamaModelClient().num_ctx == 16384
    monkeypatch.setenv("DOCFACTORY_NUM_CTX", "65536")
    assert OllamaModelClient().num_ctx == 65536
    assert OllamaModelClient(num_ctx=32768).num_ctx == 32768
