import pytest
from pydantic import ValidationError

from docfactory.entitymodels.backup_recovery import BackupRecovery
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
    BackupRecovery.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = BackupRecovery.model_validate(FULL)
    assert BackupRecovery.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        BackupRecovery.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = BackupRecovery.model_validate(MINIMAL)
    assert obj.backup_schedule is None
    assert obj.backup_retention is None
    assert obj.backup_location is None
    assert obj.restore_procedure is None
    assert obj.rpo == ''
    assert obj.rto == ''
    assert obj.disaster_recovery_plan == ''


@pytest.mark.parametrize("field", ["backup_schedule", "backup_retention", "backup_location", "restore_procedure"])
def test_not_applicable_is_accepted_where_allowed(field):
    BackupRecovery.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["rpo", "rto", "disaster_recovery_plan"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        BackupRecovery.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# BackupRecovery has 7 top-level scored fields, none mandatory.
# Full payload total: backup_schedule (1), backup_retention (1), backup_location (1), restore_procedure (1), rpo (1), rto (1), disaster_recovery_plan (1) = 7.
FULL_COMPLETE = {'backup_schedule': 'Test backup schedule',
 'backup_retention': 'Test backup retention',
 'backup_location': 'Test backup location',
 'restore_procedure': 'Test restore procedure',
 'rpo': 'Test rpo',
 'rto': 'Test rto',
 'disaster_recovery_plan': 'Test disaster recovery plan'}


def test_completeness_of_mandatory_only_payload():
    # an empty payload: every one of the 7 top-level fields is at its default (an empty list counts as one unanswered field)
    # -> answered 0 / total 7
    obj = BackupRecovery.model_validate(MINIMAL)
    assert field_counts(obj) == (0, 7)
    assert completeness(obj) == pytest.approx(0.0)


def test_completeness_of_fully_filled_payload_is_100():
    # every field filled, each list holding one fully filled item -> 7 / 7 * 100
    obj = BackupRecovery.model_validate(FULL_COMPLETE)
    assert field_counts(obj) == (7, 7)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 0 of 7
    defaults = {'backup_schedule': None,
 'backup_retention': None,
 'backup_location': None,
 'restore_procedure': None,
 'rpo': '',
 'rto': '',
 'disaster_recovery_plan': ''}
    obj = BackupRecovery.model_validate(defaults)
    assert field_counts(obj) == (0, 7)


def test_legal_not_applicable_on_backup_schedule_counts_as_answered():
    # backup_schedule N/A = 1 answered; the other 6 fields stay at their defaults -> 1 / 7
    obj = BackupRecovery.model_validate({"backup_schedule": NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (1, 7)
    assert completeness(obj) == pytest.approx(1 / 7 * 100)


def test_legal_not_applicable_on_backup_retention_counts_as_answered():
    # backup_retention N/A = 1 answered; the other 6 fields stay at their defaults -> 1 / 7
    obj = BackupRecovery.model_validate({"backup_retention": NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (1, 7)
    assert completeness(obj) == pytest.approx(1 / 7 * 100)


def test_legal_not_applicable_on_backup_location_counts_as_answered():
    # backup_location N/A = 1 answered; the other 6 fields stay at their defaults -> 1 / 7
    obj = BackupRecovery.model_validate({"backup_location": NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (1, 7)
    assert completeness(obj) == pytest.approx(1 / 7 * 100)


def test_legal_not_applicable_on_restore_procedure_counts_as_answered():
    # restore_procedure N/A = 1 answered; the other 6 fields stay at their defaults -> 1 / 7
    obj = BackupRecovery.model_validate({"restore_procedure": NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (1, 7)
    assert completeness(obj) == pytest.approx(1 / 7 * 100)


def test_all_not_applicable_fields_together_count_as_answered():
    # 4 N/A fields = 4 answered / 7
    obj = BackupRecovery.model_validate({"backup_schedule": NotApplicable(reason="Not relevant for this test."), "backup_retention": NotApplicable(reason="Not relevant for this test."), "backup_location": NotApplicable(reason="Not relevant for this test."), "restore_procedure": NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (4, 7)
