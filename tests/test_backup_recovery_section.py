import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.backup_recovery_section import BackupRecoverySection
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {}

FULL = {
    "backup_schedule": "Test backup schedule",
    "backup_retention": "Test backup retention",
    "backup_location": "Test backup location",
    "restore_procedure": "Test restore procedure",
    "rpo": "Test rpo",
    "rto": "Test rto",
    "disaster_recovery_plan": "Test disaster recovery plan",
}


def test_minimal_payload_is_valid():
    BackupRecoverySection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = BackupRecoverySection.model_validate(FULL)
    assert BackupRecoverySection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        BackupRecoverySection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = BackupRecoverySection.model_validate(MINIMAL)
    assert obj.backup_schedule is None
    assert obj.backup_retention is None
    assert obj.backup_location is None
    assert obj.restore_procedure is None
    assert obj.rpo == ''
    assert obj.rto == ''
    assert obj.disaster_recovery_plan == ''


@pytest.mark.parametrize("field", ["backup_schedule", "backup_retention", "backup_location", "restore_procedure"])
def test_not_applicable_is_accepted_where_allowed(field):
    BackupRecoverySection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["rpo", "rto", "disaster_recovery_plan"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        BackupRecoverySection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Mirror of the entity (hand-written) ---
from docfactory.entitymodels.backup_recovery import BackupRecovery  # noqa: E402


def test_section_mirrors_every_entity_field():
    assert list(BackupRecoverySection.model_fields) == list(BackupRecovery.model_fields)
    for name, field in BackupRecoverySection.model_fields.items():
        entity_field = BackupRecovery.model_fields[name]
        assert field.annotation == entity_field.annotation
        assert field.default == entity_field.default
        assert field.default_factory == entity_field.default_factory
        assert field.json_schema_extra["na_allowed"] == entity_field.json_schema_extra["na_allowed"]
        assert field.json_schema_extra["binding"] == f"BackupRecovery.{name}"


def test_list_of_item_fields_render_as_expected():
    tables = []
    for name, field in BackupRecoverySection.model_fields.items():
        assert field.json_schema_extra["render_as"] == ("table" if name in tables else "list")
