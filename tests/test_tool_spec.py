import pytest
from pydantic import ValidationError

from docfactory.models.tool_spec import ToolSpec
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "name": "test_tool",
    "description": "Test tool description.",
    "input_schema_json": "{\"type\": \"object\"}",
}

FULL = {
    "name": "test_tool",
    "description": "Test tool description.",
    "input_schema_json": "{\"type\": \"object\"}",
}


def test_minimal_payload_is_valid():
    ToolSpec.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ToolSpec.model_validate(FULL)
    assert ToolSpec.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["name", "description", "input_schema_json"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ToolSpec.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ToolSpec.model_validate({**FULL, "not_a_field": "x"})


@pytest.mark.parametrize("field", ["name", "description", "input_schema_json"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        ToolSpec.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["name", "description", "input_schema_json"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ToolSpec.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("bad", ["not json", "[1, 2]", "\"text\"", "5", "null"])
def test_input_schema_json_must_be_a_json_object(bad):
    with pytest.raises(ValidationError, match="input_schema_json"):
        ToolSpec.model_validate({**MINIMAL, "input_schema_json": bad})
