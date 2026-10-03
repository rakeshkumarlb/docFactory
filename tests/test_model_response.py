import pytest
from pydantic import ValidationError

from docfactory.models.model_response import ModelResponse
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.tool_call import ToolCall

MINIMAL = {}

FULL = {
    "text": "Test answer.",
    "tool_calls": [ToolCall(id="test-call-1", name="test_tool")],
}


def test_minimal_payload_is_valid():
    ModelResponse.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ModelResponse.model_validate(FULL)
    assert ModelResponse.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ModelResponse.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = ModelResponse.model_validate(MINIMAL)
    assert obj.text == ''
    assert obj.tool_calls == []


@pytest.mark.parametrize("field", ["text", "tool_calls"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ModelResponse.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
