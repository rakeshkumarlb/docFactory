from types import SimpleNamespace

import pytest

from docfactory.agents.anthropic_model_client import AnthropicModelClient
from docfactory.models.message_role import MessageRole
from docfactory.models.model_message import ModelMessage


def _client_returning(stop_reason):
    block = SimpleNamespace(type="text", text="partial")
    response = SimpleNamespace(content=[block], stop_reason=stop_reason)
    stub = SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: response))
    return AnthropicModelClient(model="m", max_tokens=123, client=stub)


def test_cut_off_response_raises_a_clear_error():
    client = _client_returning("max_tokens")
    with pytest.raises(RuntimeError, match="max_tokens=123"):
        client.complete("SYS", [ModelMessage(role=MessageRole.USER, text="go")], [])


@pytest.mark.parametrize("stop_reason", ["end_turn", "tool_use", None])
def test_normal_stop_reasons_return_the_response(stop_reason):
    client = _client_returning(stop_reason)
    assert client.complete("SYS", [ModelMessage(role=MessageRole.USER, text="go")], []).text == "partial"


def test_sdk_retries_are_capped_by_max_retries(monkeypatch):
    import anthropic

    seen = {}

    def fake_ctor(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr(anthropic, "Anthropic", fake_ctor)
    AnthropicModelClient()
    assert seen == {"max_retries": 4}
    AnthropicModelClient(max_retries=1)
    assert seen == {"max_retries": 1}
