import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.slo_section import SloSection
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.slo_objective import SloObjective

MINIMAL = {}

FULL = {
    "objectives": [{"name": "Test objectives"}],
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    SloSection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = SloSection.model_validate(FULL)
    assert SloSection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SloSection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = SloSection.model_validate(MINIMAL)
    assert obj.objectives == []
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["objectives", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SloSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Mirror of the entity (hand-written) ---
from docfactory.entitymodels.slo import Slo  # noqa: E402


def test_section_mirrors_every_entity_field():
    assert list(SloSection.model_fields) == list(Slo.model_fields)
    for name, field in SloSection.model_fields.items():
        entity_field = Slo.model_fields[name]
        assert field.annotation == entity_field.annotation
        assert field.default == entity_field.default
        assert field.default_factory == entity_field.default_factory
        assert field.json_schema_extra["na_allowed"] == entity_field.json_schema_extra["na_allowed"]
        assert field.json_schema_extra["binding"] == f"Slo.{name}"


def test_list_of_item_fields_render_as_expected():
    tables = ['objectives']
    for name, field in SloSection.model_fields.items():
        assert field.json_schema_extra["render_as"] == ("table" if name in tables else "list")
