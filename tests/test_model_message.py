import pytest
from pydantic import ValidationError

from docfactory.models.model_message import ModelMessage
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.message_role import MessageRole
from docfactory.models.tool_call import ToolCall

MINIMAL = {
    "role": MessageRole.USER,
}

FULL = {
    "role": MessageRole.ASSISTANT,
    "text": "Test message.",
    "tool_calls": [ToolCall(id="test-call-1", name="test_tool")],
    "tool_call_id": None,
}


def test_minimal_payload_is_valid():
    ModelMessage.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ModelMessage.model_validate(FULL)
    assert ModelMessage.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["role"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ModelMessage.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ModelMessage.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = ModelMessage.model_validate(MINIMAL)
    assert obj.text == ''
    assert obj.tool_calls == []
    assert obj.tool_call_id is None


@pytest.mark.parametrize("field", ["role", "text", "tool_calls", "tool_call_id"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ModelMessage.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


CALL = ToolCall(id="test-call-1", name="test_tool")


@pytest.mark.parametrize("role", [MessageRole.USER, MessageRole.TOOL])
def test_tool_calls_rejected_unless_assistant(role):
    extra = {"tool_call_id": "test-call-1"} if role == MessageRole.TOOL else {}
    with pytest.raises(ValidationError, match="tool_calls are allowed only"):
        ModelMessage.model_validate({"role": role, "tool_calls": [CALL], **extra})


def test_tool_message_requires_tool_call_id():
    with pytest.raises(ValidationError, match="tool_call_id is required"):
        ModelMessage.model_validate({"role": MessageRole.TOOL, "text": "result"})


def test_tool_message_with_tool_call_id_is_valid():
    ModelMessage.model_validate({"role": MessageRole.TOOL, "text": "result", "tool_call_id": "test-call-1"})


@pytest.mark.parametrize("role", [MessageRole.USER, MessageRole.ASSISTANT])
def test_tool_call_id_forbidden_unless_tool(role):
    with pytest.raises(ValidationError, match="tool_call_id is allowed only"):
        ModelMessage.model_validate({"role": role, "tool_call_id": "test-call-1"})
