import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.environments_section import EnvironmentsSection
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.environment import Environment

MINIMAL = {}

FULL = {
    "environments": [{"name": "Test environments"}],
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    EnvironmentsSection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = EnvironmentsSection.model_validate(FULL)
    assert EnvironmentsSection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        EnvironmentsSection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = EnvironmentsSection.model_validate(MINIMAL)
    assert obj.environments == []
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["environments", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        EnvironmentsSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Mirror of the entity (hand-written) ---
from docfactory.entitymodels.environments import Environments  # noqa: E402


def test_section_mirrors_every_entity_field():
    assert list(EnvironmentsSection.model_fields) == list(Environments.model_fields)
    for name, field in EnvironmentsSection.model_fields.items():
        entity_field = Environments.model_fields[name]
        assert field.annotation == entity_field.annotation
        assert field.default == entity_field.default
        assert field.default_factory == entity_field.default_factory
        assert field.json_schema_extra["na_allowed"] == entity_field.json_schema_extra["na_allowed"]
        assert field.json_schema_extra["binding"] == f"Environments.{name}"


def test_list_of_item_fields_render_as_expected():
    tables = ['environments']
    for name, field in EnvironmentsSection.model_fields.items():
        assert field.json_schema_extra["render_as"] == ("table" if name in tables else "list")
