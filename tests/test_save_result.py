import pytest
from pydantic import ValidationError

from docfactory.models.save_result import SaveResult
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.save_action import SaveAction
from docfactory.models.save_error import SaveError

MINIMAL = {
    "ok": True,
    "key": "TestApp.Thing",
    "action": SaveAction.CREATED,
}

FULL = {
    "ok": True,
    "key": "TestApp.Thing",
    "action": SaveAction.CREATED,
    "version": 1,
    "hashcode": "0" * 64,
    "completeness": 62.5,
    "errors": [SaveError(path="name", message="Field required", error_type="missing")],
}


def test_minimal_payload_is_valid():
    SaveResult.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = SaveResult.model_validate(FULL)
    assert SaveResult.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["ok", "key", "action"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        SaveResult.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SaveResult.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = SaveResult.model_validate(MINIMAL)
    assert obj.version is None
    assert obj.hashcode is None
    assert obj.completeness is None
    assert obj.errors == []


@pytest.mark.parametrize("field", ["key"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        SaveResult.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["ok", "key", "action", "version", "hashcode", "completeness", "errors"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SaveResult.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
