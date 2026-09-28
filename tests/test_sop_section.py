import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.sop_section import SopSection
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.sop_procedure import SopProcedure

MINIMAL = {}

FULL = {
    "procedures": [{"name": "Test procedures"}],
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    SopSection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = SopSection.model_validate(FULL)
    assert SopSection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SopSection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = SopSection.model_validate(MINIMAL)
    assert obj.procedures == []
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["procedures", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SopSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Mirror of the entity (hand-written) ---
from docfactory.entitymodels.sop import Sop  # noqa: E402


def test_section_mirrors_every_entity_field():
    assert list(SopSection.model_fields) == list(Sop.model_fields)
    for name, field in SopSection.model_fields.items():
        entity_field = Sop.model_fields[name]
        assert field.annotation == entity_field.annotation
        assert field.default == entity_field.default
        assert field.default_factory == entity_field.default_factory
        assert field.json_schema_extra["na_allowed"] == entity_field.json_schema_extra["na_allowed"]
        assert field.json_schema_extra["binding"] == f"Sop.{name}"


def test_list_of_item_fields_render_as_expected():
    tables = []
    for name, field in SopSection.model_fields.items():
        assert field.json_schema_extra["render_as"] == ("table" if name in tables else "list")
