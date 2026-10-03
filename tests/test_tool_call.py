import pytest
from pydantic import ValidationError

from docfactory.models.tool_call import ToolCall
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "id": "test-call-1",
    "name": "test_tool",
}

FULL = {
    "id": "test-call-1",
    "name": "test_tool",
    "arguments_json": "{\"x\": 1}",
}


def test_minimal_payload_is_valid():
    ToolCall.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ToolCall.model_validate(FULL)
    assert ToolCall.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["id", "name"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ToolCall.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ToolCall.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = ToolCall.model_validate(MINIMAL)
    assert obj.arguments_json == '{}'


@pytest.mark.parametrize("field", ["id", "name"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        ToolCall.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["id", "name", "arguments_json"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ToolCall.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("bad", ["not json", "[1, 2]", "\"text\"", "5", "null", ""])
def test_arguments_json_must_be_a_json_object(bad):
    with pytest.raises(ValidationError, match="arguments_json"):
        ToolCall.model_validate({**FULL, "arguments_json": bad})
