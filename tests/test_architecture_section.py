import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.architecture_section import ArchitectureSection
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.component import Component
from docfactory.entitymodels.items.data_store import DataStore
from docfactory.entitymodels.items.integration import Integration

MINIMAL = {}

FULL = {
    "architecture_style": "Test architecture style",
    "technology_stack": ["Test technology stack"],
    "components": [{"name": "Test components"}],
    "data_stores": [{"name": "Test data stores"}],
    "integrations": [{"name": "Test integrations"}],
    "diagram_reference": "Test diagram reference",
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    ArchitectureSection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ArchitectureSection.model_validate(FULL)
    assert ArchitectureSection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ArchitectureSection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = ArchitectureSection.model_validate(MINIMAL)
    assert obj.architecture_style == ''
    assert obj.technology_stack == []
    assert obj.components == []
    assert obj.data_stores == []
    assert obj.integrations == []
    assert obj.diagram_reference is None
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["diagram_reference"])
def test_not_applicable_is_accepted_where_allowed(field):
    ArchitectureSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["architecture_style", "technology_stack", "components", "data_stores", "integrations", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ArchitectureSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Mirror of the entity (hand-written) ---
from docfactory.entitymodels.facts.architecture import Architecture  # noqa: E402


def test_section_mirrors_every_entity_field():
    assert list(ArchitectureSection.model_fields) == list(Architecture.model_fields)
    for name, field in ArchitectureSection.model_fields.items():
        entity_field = Architecture.model_fields[name]
        assert field.annotation == entity_field.annotation
        assert field.default == entity_field.default
        assert field.default_factory == entity_field.default_factory
        assert field.json_schema_extra["na_allowed"] == entity_field.json_schema_extra["na_allowed"]
        assert field.json_schema_extra["binding"] == f"Architecture.{name}"


def test_list_of_item_fields_render_as_expected():
    tables = ['components', 'data_stores', 'integrations']
    for name, field in ArchitectureSection.model_fields.items():
        assert field.json_schema_extra["render_as"] == ("table" if name in tables else "list")
