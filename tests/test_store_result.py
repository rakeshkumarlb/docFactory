import pytest
from pydantic import ValidationError

from docfactory.models.store_result import StoreResult
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.file_action import FileAction

MINIMAL = {
    "ok": True,
    "target_path": "Test-Scope/test-file.txt",
}

FULL = {
    "ok": True,
    "target_path": "Test-Scope/test-file.txt",
    "action": FileAction.NEW,
    "version": 1,
    "sidecar_path": "Test-Scope/test-file.txt.md",
    "error": "test error",
}


def test_minimal_payload_is_valid():
    StoreResult.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = StoreResult.model_validate(FULL)
    assert StoreResult.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["ok", "target_path"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        StoreResult.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        StoreResult.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = StoreResult.model_validate(MINIMAL)
    assert obj.action is None
    assert obj.version is None
    assert obj.sidecar_path is None
    assert obj.error is None


@pytest.mark.parametrize("field", ["target_path"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        StoreResult.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["ok", "target_path", "action", "version", "sidecar_path", "error"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        StoreResult.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
