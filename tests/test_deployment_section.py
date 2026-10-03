import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.deployment_section import DeploymentSection
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {}

FULL = {
    "release_process": "Test release process",
    "ci_cd_tooling": "Test ci cd tooling",
    "release_frequency": "Test release frequency",
    "rollback_procedure": "Test rollback procedure",
    "configuration_management": "Test configuration management",
}


def test_minimal_payload_is_valid():
    DeploymentSection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = DeploymentSection.model_validate(FULL)
    assert DeploymentSection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        DeploymentSection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = DeploymentSection.model_validate(MINIMAL)
    assert obj.release_process == ''
    assert obj.ci_cd_tooling == ''
    assert obj.release_frequency == ''
    assert obj.rollback_procedure == ''
    assert obj.configuration_management == ''


@pytest.mark.parametrize("field", ["release_process", "ci_cd_tooling", "release_frequency", "rollback_procedure", "configuration_management"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        DeploymentSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Mirror of the entity (hand-written) ---
from docfactory.entitymodels.facts.deployment import Deployment  # noqa: E402


def test_section_mirrors_every_entity_field():
    assert list(DeploymentSection.model_fields) == list(Deployment.model_fields)
    for name, field in DeploymentSection.model_fields.items():
        entity_field = Deployment.model_fields[name]
        assert field.annotation == entity_field.annotation
        assert field.default == entity_field.default
        assert field.default_factory == entity_field.default_factory
        assert field.json_schema_extra["na_allowed"] == entity_field.json_schema_extra["na_allowed"]
        assert field.json_schema_extra["binding"] == f"Deployment.{name}"


def test_list_of_item_fields_render_as_expected():
    tables = []
    for name, field in DeploymentSection.model_fields.items():
        assert field.json_schema_extra["render_as"] == ("table" if name in tables else "list")
