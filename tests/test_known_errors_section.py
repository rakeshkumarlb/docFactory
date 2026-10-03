import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.known_errors_section import KnownErrorsSection
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.known_error import KnownError

MINIMAL = {}

FULL = {
    "known_errors": [{"title": "Test known errors"}],
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    KnownErrorsSection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = KnownErrorsSection.model_validate(FULL)
    assert KnownErrorsSection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        KnownErrorsSection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = KnownErrorsSection.model_validate(MINIMAL)
    assert obj.known_errors == []
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["known_errors", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        KnownErrorsSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Mirror of the entity (hand-written) ---
from docfactory.entitymodels.facts.known_errors import KnownErrors  # noqa: E402


def test_section_mirrors_every_entity_field():
    assert list(KnownErrorsSection.model_fields) == list(KnownErrors.model_fields)
    for name, field in KnownErrorsSection.model_fields.items():
        entity_field = KnownErrors.model_fields[name]
        assert field.annotation == entity_field.annotation
        assert field.default == entity_field.default
        assert field.default_factory == entity_field.default_factory
        assert field.json_schema_extra["na_allowed"] == entity_field.json_schema_extra["na_allowed"]
        assert field.json_schema_extra["binding"] == f"KnownErrors.{name}"


def test_list_of_item_fields_render_as_expected():
    tables = ['known_errors']
    for name, field in KnownErrorsSection.model_fields.items():
        assert field.json_schema_extra["render_as"] == ("table" if name in tables else "list")
