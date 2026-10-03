import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.support_section import SupportSection
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.support_contact import SupportContact

MINIMAL = {}

FULL = {
    "support_model": "Test support model",
    "contacts": [{"role": "Test contacts"}],
    "escalation_path": "Test escalation path",
    "incident_process": "Test incident process",
    "runbooks": ["Test runbooks"],
}


def test_minimal_payload_is_valid():
    SupportSection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = SupportSection.model_validate(FULL)
    assert SupportSection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SupportSection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = SupportSection.model_validate(MINIMAL)
    assert obj.support_model == ''
    assert obj.contacts == []
    assert obj.escalation_path == ''
    assert obj.incident_process == ''
    assert obj.runbooks == []


@pytest.mark.parametrize("field", ["support_model", "contacts", "escalation_path", "incident_process", "runbooks"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SupportSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Mirror of the entity (hand-written) ---
from docfactory.entitymodels.facts.support import Support  # noqa: E402


def test_section_mirrors_every_entity_field():
    assert list(SupportSection.model_fields) == list(Support.model_fields)
    for name, field in SupportSection.model_fields.items():
        entity_field = Support.model_fields[name]
        assert field.annotation == entity_field.annotation
        assert field.default == entity_field.default
        assert field.default_factory == entity_field.default_factory
        assert field.json_schema_extra["na_allowed"] == entity_field.json_schema_extra["na_allowed"]
        assert field.json_schema_extra["binding"] == f"Support.{name}"


def test_list_of_item_fields_render_as_expected():
    tables = ['contacts']
    for name, field in SupportSection.model_fields.items():
        assert field.json_schema_extra["render_as"] == ("table" if name in tables else "list")
