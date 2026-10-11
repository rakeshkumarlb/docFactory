"""Validation errors as feedback (path, description, question) and the key patterns, on a test-only model.

These rules came from BaseSaver's tests; BundleStore, DocumentStateStore and the extraction tool all report errors this way.
"""
from enum import StrEnum

import pytest
from pydantic import ValidationError

from docfactory.completeness import completeness
from docfactory.key_patterns import pattern_matches
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable
from docfactory.validation_errors import validation_errors


class _Level(StrEnum):
    LOW = "low"
    HIGH = "high"


class _Contact(DocFactoryModel):
    """Test-only nested item: a contact of a thing."""

    name: str = doc_field(description="Name of the contact, e.g. test-contact.", question="What is the contact's name?")
    phone: str | None = doc_field(default=None, description="Phone of the contact, e.g. 000.")


class _Thing(DocFactoryModel):
    """Test-only object validated by these tests."""

    name: str = doc_field(description="Name of the thing, e.g. test-thing.", question="What is the name of the thing?", min_length=1)
    size: int | None = doc_field(default=None, description="Size of the thing, e.g. 3.")
    level: _Level = doc_field(default=_Level.LOW, description="Level of the thing, e.g. low or high.")
    contacts: list[_Contact] = doc_field(default_factory=list, description="Contacts of the thing, e.g. one.")
    url: str | NotApplicable | None = doc_field(default=None, description="Url of the thing, e.g. x.", na_allowed=True)


PAYLOAD = {"name": "thing", "contacts": [{"name": "a", "phone": "1"}, {"name": "b"}]}


def _errors(payload):
    with pytest.raises(ValidationError) as caught:
        _Thing.model_validate(payload)
    return validation_errors(_Thing, caught.value)


def test_missing_mandatory_field_carries_description_and_question():
    (error,) = _errors({k: v for k, v in PAYLOAD.items() if k != "name"})
    assert error.path == "name" and error.error_type == "missing" and error.message
    assert error.field_description == "Name of the thing, e.g. test-thing."
    assert error.question == "What is the name of the thing?"
    assert error.received is None and error.expected


def test_wrong_type_carries_description_and_the_description_stands_in_for_a_missing_question():
    (error,) = _errors({**PAYLOAD, "size": "big"})
    assert error.path == "size" and error.error_type == "int_parsing" and error.received == '"big"'
    assert error.field_description == error.question == "Size of the thing, e.g. 3."


def test_bad_enum_value_says_what_is_expected():
    (error,) = _errors({**PAYLOAD, "level": "extreme"})
    assert error.path == "level" and error.error_type == "enum"
    assert "low" in error.expected and "high" in error.expected and error.field_description and error.question


def test_extra_field_says_which_fields_exist():
    (error,) = _errors({**PAYLOAD, "bogus": 1})
    assert error.path == "bogus" and error.error_type == "extra_forbidden"
    assert error.field_description == "Test-only object validated by these tests."
    assert "bogus" in error.question and "contacts" in error.question


def test_error_inside_a_list_item_has_the_full_path_and_the_items_field_metadata():
    (error,) = _errors({"name": "x", "contacts": [{"name": "a"}, {"phone": "1"}]})
    assert error.path == "contacts.1.name" and error.error_type == "missing"
    assert error.field_description == "Name of the contact, e.g. test-contact."
    assert error.question == "What is the contact's name?"


def test_extra_field_inside_a_list_item_names_the_item_model():
    (error,) = _errors({"name": "x", "contacts": [{"name": "a", "bogus": 1}]})
    assert error.path == "contacts.0.bogus" and "_Contact" in error.question and "phone" in error.question


def test_not_applicable_is_rejected_where_not_allowed():
    (error,) = _errors({"name": {"reason": "n/a"}})
    assert error.path.startswith("name")


def test_not_applicable_with_an_empty_reason_is_rejected():
    errors = _errors({"name": "x", "url": {"reason": ""}})
    assert errors and all(e.path.startswith("url") and e.field_description and e.question for e in errors)
    reason = next(e for e in errors if e.path.endswith("reason"))
    assert reason.field_description.startswith("Why the question does not apply") and reason.question == "Why is this not applicable?"


def test_all_errors_are_reported_together():
    assert {e.path for e in _errors({"size": "big", "bogus": 1})} == {"name", "size", "bogus"}


@pytest.mark.parametrize("payload", ["not an object", 5, None, ["name"]])
def test_a_payload_that_is_not_an_object_is_one_error_not_an_exception(payload):
    (error,) = _errors(payload)
    assert error.path == "payload"


def test_completeness_counts_answered_fields_and_not_explicit_defaults():
    assert completeness(_Thing.model_validate({"name": "x"})) == 20.0  # name answered; size, level, url default; contacts empty
    assert completeness(_Thing.model_validate({"name": "x", "size": 3})) == 40.0
    assert completeness(_Thing.model_validate({"name": "x", "size": None, "level": "low", "contacts": [], "url": None})) == 20.0
    assert completeness(_Thing.model_validate({"name": "x", "url": {"reason": "It has no URL."}})) == 40.0  # N/A counts as answered
    assert completeness(_Thing.model_validate(PAYLOAD)) == 50.0  # 4 of 8: contacts count item by item


@pytest.mark.parametrize("pattern,key", [
    ("{app}.Thing", "TestApp.Thing"), ("{app}.Components.{component}.Thing", "TestApp.Components.dbmcp.Thing"),
    ("Shared.Thing", "Shared.Thing"), ("{app}.Outputs.{doctype}", "TestApp.Outputs.SMTD"),
])
def test_a_key_matches_its_pattern(pattern, key):
    assert pattern_matches(pattern, key)


@pytest.mark.parametrize("pattern,key", [
    ("{app}.Thing", "TestApp.Other"), ("{app}.Thing", "TestApp.Thing.Extra"), ("{app}.Thing", "Thing"), ("{app}.Thing", ".Thing"),
    ("{app}.Components.{component}.Thing", "TestApp.Components.Thing"), ("{app}.Components.{component}.Thing", "TestApp.Components..Thing"),
    ("{app}.Thing", "Shared.Thing"),  # Shared is not an application
    ("Shared.Thing", "TestApp.Thing"), ("Shared.Thing", "shared.Thing"),  # case-sensitive
    ("{app}.Outputs.{doctype}", "TestApp.outputs.SMTD"),
])
def test_a_key_that_does_not_match_its_pattern(pattern, key):
    assert not pattern_matches(pattern, key)
