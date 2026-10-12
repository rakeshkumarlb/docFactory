import pytest
from pydantic import ValidationError

from docfactory.models.scope_resolution import ScopeResolution
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.resolution_group import ResolutionGroup

MINIMAL = {
    "scope": "TestApp",
    "hashcode": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "generated_by": "test-agent/1",
    "timestamp": "2026-01-01T00:00:00+00:00",
}

FULL = {
    "scope": "TestApp",
    "groups": [],
    "asked": ["Component=abc"],
    "hashcode": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "generated_by": "test-agent/1",
    "timestamp": "2026-01-01T00:00:00+00:00",
}


def test_minimal_payload_is_valid():
    ScopeResolution.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ScopeResolution.model_validate(FULL)
    assert ScopeResolution.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["scope", "hashcode", "generated_by", "timestamp"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ScopeResolution.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ScopeResolution.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = ScopeResolution.model_validate(MINIMAL)
    assert obj.groups == []
    assert obj.asked == []


@pytest.mark.parametrize("field", ["scope", "generated_by", "timestamp"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        ScopeResolution.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["hashcode"])
def test_text_not_matching_the_pattern_is_rejected(field):
    with pytest.raises(ValidationError):
        ScopeResolution.model_validate({**FULL, field: "not matching the pattern"})


@pytest.mark.parametrize("field", ["scope", "groups", "asked", "hashcode", "generated_by", "timestamp"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ScopeResolution.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
