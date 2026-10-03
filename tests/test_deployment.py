import pytest
from pydantic import ValidationError

from docfactory.entitymodels.facts.deployment import Deployment
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
    Deployment.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Deployment.model_validate(FULL)
    assert Deployment.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Deployment.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Deployment.model_validate(MINIMAL)
    assert obj.release_process == ''
    assert obj.ci_cd_tooling == ''
    assert obj.release_frequency == ''
    assert obj.rollback_procedure == ''
    assert obj.configuration_management == ''


@pytest.mark.parametrize("field", ["release_process", "ci_cd_tooling", "release_frequency", "rollback_procedure", "configuration_management"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Deployment.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# Deployment has 5 top-level scored fields, none mandatory.
# Full payload total: release_process (1), ci_cd_tooling (1), release_frequency (1), rollback_procedure (1), configuration_management (1) = 5.
FULL_COMPLETE = {'release_process': 'Test release process',
 'ci_cd_tooling': 'Test ci cd tooling',
 'release_frequency': 'Test release frequency',
 'rollback_procedure': 'Test rollback procedure',
 'configuration_management': 'Test configuration management'}


def test_completeness_of_mandatory_only_payload():
    # an empty payload: every one of the 5 top-level fields is at its default (an empty list counts as one unanswered field)
    # -> answered 0 / total 5
    obj = Deployment.model_validate(MINIMAL)
    assert field_counts(obj) == (0, 5)
    assert completeness(obj) == pytest.approx(0.0)


def test_completeness_of_fully_filled_payload_is_100():
    # every field filled, each list holding one fully filled item -> 5 / 5 * 100
    obj = Deployment.model_validate(FULL_COMPLETE)
    assert field_counts(obj) == (5, 5)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 0 of 5
    defaults = {'release_process': '',
 'ci_cd_tooling': '',
 'release_frequency': '',
 'rollback_procedure': '',
 'configuration_management': ''}
    obj = Deployment.model_validate(defaults)
    assert field_counts(obj) == (0, 5)
