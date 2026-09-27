import pytest
from pydantic import ValidationError

from docfactory.entitymodels.application_overview import ApplicationOverview
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "application_name": "Test-App",
    "purpose": "Test purpose",
}

FULL = {
    "application_name": "Test-App",
    "purpose": "Test purpose",
    "business_overview": "Test business overview",
    "business_owner": "Test owner",
    "target_users": ["Test user group"],
    "key_capabilities": ["Test capability"],
    "out_of_scope": ["Test exclusion"],
    "business_criticality": "Test criticality",
    "lifecycle_status": "Test status",
    "go_live_date": "2000-01-01",
    "technology_summary": "Test technology",
    "related_systems": ["Test system"],
}


def test_minimal_payload_is_valid():
    ApplicationOverview.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ApplicationOverview.model_validate(FULL)
    assert ApplicationOverview.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["application_name", "purpose"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ApplicationOverview.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ApplicationOverview.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = ApplicationOverview.model_validate(MINIMAL)
    assert obj.business_overview == ''
    assert obj.business_owner == ''
    assert obj.target_users == []
    assert obj.key_capabilities == []
    assert obj.out_of_scope == []
    assert obj.business_criticality == ''
    assert obj.lifecycle_status == ''
    assert obj.go_live_date is None
    assert obj.technology_summary == ''
    assert obj.related_systems == []


@pytest.mark.parametrize("field", ["application_name", "purpose"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        ApplicationOverview.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["out_of_scope", "go_live_date"])
def test_not_applicable_is_accepted_where_allowed(field):
    ApplicationOverview.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["application_name", "purpose", "business_overview", "business_owner", "target_users", "key_capabilities", "business_criticality", "lifecycle_status", "technology_summary", "related_systems"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ApplicationOverview.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# ApplicationOverview has 12 scored fields, 2 of them mandatory (application_name, purpose).


def test_completeness_of_mandatory_only_payload():
    # answered 2 (mandatory) / total 12 -> 2 / 12 * 100
    obj = ApplicationOverview.model_validate(MINIMAL)
    assert field_counts(obj) == (2, 12)
    assert completeness(obj) == pytest.approx(2 / 12 * 100)


def test_completeness_of_fully_filled_payload_is_100():
    # all 12 fields differ from their defaults: 12 / 12 * 100
    obj = ApplicationOverview.model_validate(FULL)
    assert field_counts(obj) == (12, 12)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 2 of 12
    payload = {
        **MINIMAL,
        "business_overview": "",
        "business_owner": "",
        "target_users": [],
        "key_capabilities": [],
        "out_of_scope": [],
        "business_criticality": "",
        "lifecycle_status": "",
        "go_live_date": None,
        "technology_summary": "",
        "related_systems": [],
    }
    obj = ApplicationOverview.model_validate(payload)
    assert field_counts(obj) == (2, 12)


def test_legal_not_applicable_counts_as_answered():
    # 2 mandatory + out_of_scope N/A + go_live_date N/A = 4 answered / 12
    na = NotApplicable(reason="Not relevant for this test.")
    obj = ApplicationOverview.model_validate({**MINIMAL, "out_of_scope": na, "go_live_date": na})
    assert field_counts(obj) == (4, 12)
    assert completeness(obj) == pytest.approx(4 / 12 * 100)
