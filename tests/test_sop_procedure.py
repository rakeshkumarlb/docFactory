import pytest
from pydantic import ValidationError

from docfactory.models.sop_procedure import SopProcedure
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "name": "Test name",
}

FULL = {
    "name": "Test name",
    "purpose": "Test purpose",
    "trigger": "Test trigger",
    "frequency": "Test frequency",
    "roles": ["Test roles"],
    "prerequisites": ["Test prerequisites"],
    "steps": ["Test steps"],
    "verification": "Test verification",
    "escalation": "Test escalation",
}


def test_minimal_payload_is_valid():
    SopProcedure.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = SopProcedure.model_validate(FULL)
    assert SopProcedure.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["name"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        SopProcedure.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SopProcedure.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = SopProcedure.model_validate(MINIMAL)
    assert obj.purpose == ''
    assert obj.trigger == ''
    assert obj.frequency == ''
    assert obj.roles == []
    assert obj.prerequisites == []
    assert obj.steps == []
    assert obj.verification == ''
    assert obj.escalation == ''


@pytest.mark.parametrize("field", ["name"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        SopProcedure.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["name", "purpose", "trigger", "frequency", "roles", "prerequisites", "steps", "verification", "escalation"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SopProcedure.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# SopProcedure has 9 scored fields, 1 of them mandatory (name).


def test_completeness_of_mandatory_only_payload():
    # answered 1 (mandatory) / total 9 -> 1 / 9 * 100
    obj = SopProcedure.model_validate(MINIMAL)
    assert field_counts(obj) == (1, 9)
    assert completeness(obj) == pytest.approx(1 / 9 * 100)


def test_completeness_of_fully_filled_payload_is_100():
    # all 9 fields differ from their defaults: 9 / 9 * 100
    obj = SopProcedure.model_validate(FULL)
    assert field_counts(obj) == (9, 9)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 1 of 9
    defaults = {'purpose': '',
 'trigger': '',
 'frequency': '',
 'roles': [],
 'prerequisites': [],
 'steps': [],
 'verification': '',
 'escalation': ''}
    obj = SopProcedure.model_validate({**MINIMAL, **defaults})
    assert field_counts(obj) == (1, 9)


def test_steps_render_as_a_numbered_list_and_other_lists_as_bullets():
    extras = {name: field.json_schema_extra["render_as"] for name, field in SopProcedure.model_fields.items()}
    assert extras["steps"] == "numbered"
    assert extras["roles"] == extras["prerequisites"] == "list"
