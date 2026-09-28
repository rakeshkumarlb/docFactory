import pytest
from pydantic import ValidationError

from docfactory.models.known_error import KnownError
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "title": "Test title",
}

FULL = {
    "title": "Test title",
    "error_id": "Test error id",
    "symptoms": "Test symptoms",
    "cause": "Test cause",
    "workaround": "Test workaround",
    "permanent_fix": "Test permanent fix",
    "severity": "Test severity",
    "status": "Test status",
    "related_ticket": "Test related ticket",
}


def test_minimal_payload_is_valid():
    KnownError.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = KnownError.model_validate(FULL)
    assert KnownError.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["title"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        KnownError.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        KnownError.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = KnownError.model_validate(MINIMAL)
    assert obj.error_id == ''
    assert obj.symptoms == ''
    assert obj.cause == ''
    assert obj.workaround == ''
    assert obj.permanent_fix is None
    assert obj.severity == ''
    assert obj.status == ''
    assert obj.related_ticket is None


@pytest.mark.parametrize("field", ["title"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        KnownError.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["permanent_fix", "related_ticket"])
def test_not_applicable_is_accepted_where_allowed(field):
    KnownError.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["title", "error_id", "symptoms", "cause", "workaround", "severity", "status"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        KnownError.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# KnownError has 9 scored fields, 1 of them mandatory (title).


def test_completeness_of_mandatory_only_payload():
    # answered 1 (mandatory) / total 9 -> 1 / 9 * 100
    obj = KnownError.model_validate(MINIMAL)
    assert field_counts(obj) == (1, 9)
    assert completeness(obj) == pytest.approx(1 / 9 * 100)


def test_completeness_of_fully_filled_payload_is_100():
    # all 9 fields differ from their defaults: 9 / 9 * 100
    obj = KnownError.model_validate(FULL)
    assert field_counts(obj) == (9, 9)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 1 of 9
    defaults = {'error_id': '',
 'symptoms': '',
 'cause': '',
 'workaround': '',
 'permanent_fix': None,
 'severity': '',
 'status': '',
 'related_ticket': None}
    obj = KnownError.model_validate({**MINIMAL, **defaults})
    assert field_counts(obj) == (1, 9)


def test_legal_not_applicable_on_permanent_fix_counts_as_answered():
    # 1 mandatory + permanent_fix N/A = 2 answered / 9
    obj = KnownError.model_validate({**MINIMAL, "permanent_fix": NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (2, 9)
    assert completeness(obj) == pytest.approx(2 / 9 * 100)


def test_legal_not_applicable_on_related_ticket_counts_as_answered():
    # 1 mandatory + related_ticket N/A = 2 answered / 9
    obj = KnownError.model_validate({**MINIMAL, "related_ticket": NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (2, 9)
    assert completeness(obj) == pytest.approx(2 / 9 * 100)
