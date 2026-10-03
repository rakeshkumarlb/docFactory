import hashlib
import json
import os
import sqlite3
from contextlib import closing
from enum import StrEnum

import pytest

from docfactory import db
from docfactory.base_saver import BaseSaver
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.save_action import SaveAction
from docfactory.models.save_result import SaveResult

pytestmark = pytest.mark.usefixtures("tmp_db")


class _Level(StrEnum):
    LOW = "low"
    HIGH = "high"


class _Contact(DocFactoryModel):
    """Test-only nested item: a contact of a thing."""

    name: str = doc_field(description="Name of the contact, e.g. test-contact.", question="What is the contact's name?")
    phone: str | None = doc_field(default=None, description="Phone of the contact, e.g. 000.")


class _Thing(DocFactoryModel):
    """Test-only object saved by the test savers."""

    name: str = doc_field(description="Name of the thing, e.g. test-thing.", question="What is the name of the thing?", min_length=1)
    size: int | None = doc_field(default=None, description="Size of the thing, e.g. 3.")
    level: _Level = doc_field(default=_Level.LOW, description="Level of the thing, e.g. low or high.")
    contacts: list[_Contact] = doc_field(default_factory=list, description="Contacts of the thing, e.g. one.")
    url: str | NotApplicable | None = doc_field(default=None, description="Url of the thing, e.g. x.", na_allowed=True)


# A concrete saver declares only `model` and `key_patterns`; everything else is inherited.
class _AppThingSaver(BaseSaver[_Thing]):
    model = _Thing
    key_patterns = ("{app}.Thing", "{app}.Components.{component}.Thing")


class _SharedThingSaver(BaseSaver[_Thing]):
    model = _Thing
    key_patterns = ("Shared.Thing",)


class _DocThingSaver(BaseSaver[_Thing]):
    __module__ = "docfactory.documentsaver.test"
    model = _Thing
    key_patterns = ("{app}.Outputs.{doctype}",)


FACTS, DOCUMENTS = "KnowledgeFacts", "DocumentOutputs"
CASES = [
    pytest.param(_AppThingSaver(), "TestApp.Thing", "TestApp", FACTS, id="app-fact"),
    pytest.param(_AppThingSaver(), "TestApp.Components.dbmcp.Thing", "TestApp", FACTS, id="component-fact"),
    pytest.param(_SharedThingSaver(), "Shared.Thing", None, FACTS, id="shared-fact"),
    pytest.param(_DocThingSaver(), "TestApp.Outputs.TESTDOC", "TestApp", DOCUMENTS, id="document"),
]
SAVER, KEY = _AppThingSaver(), "TestApp.Thing"

PAYLOAD = {"name": "thing", "contacts": [{"name": "a", "phone": "1"}, {"name": "b"}]}
CHANGED = {**PAYLOAD, "name": "thing-changed"}
STORED = {
    "name": "thing",
    "size": None,
    "level": "low",
    "contacts": [{"name": "a", "phone": "1"}, {"name": "b", "phone": None}],
    "url": None,
}


def _row(table, key):
    column = db.TABLE_KEYS[table]
    with closing(sqlite3.connect(os.environ["DOCFACTORY_DB"])) as con:
        con.row_factory = sqlite3.Row
        row = con.execute(f"SELECT * FROM {table} WHERE {column} = ?", (key,)).fetchone()
    return dict(row) if row else None


def _nothing_written():
    return db.list_rows(FACTS) == [] and db.list_rows(DOCUMENTS) == []


@pytest.mark.parametrize("saver,key,app_id,table", CASES)
def test_created_stores_canonical_json_hash_app_id_completeness_and_version_1(saver, key, app_id, table):
    result = saver.save(key, PAYLOAD)
    assert isinstance(result, SaveResult)
    assert result.ok and result.action == SaveAction.CREATED and result.version == 1 and result.errors == []
    row = _row(table, key)
    assert json.loads(row["Value"]) == STORED
    assert row["Value"] == json.dumps(STORED, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert row["Hashcode"] == hashlib.sha256(row["Value"].encode("utf-8")).hexdigest() == result.hashcode
    assert row["AppID"] == app_id
    assert row["Version"] == 1
    # name answered (1 of 1); size, level, url at their defaults (0 of 3);
    # contacts: item one 2 of 2, item two 1 of 2 = 3 of 4. Together 4 of 8 = 50.
    assert row["Completeness"] == 50.0 == result.completeness
    other = DOCUMENTS if table == FACTS else FACTS
    assert _row(other, key) is None


@pytest.mark.parametrize("saver,key,app_id,table", CASES)
def test_same_payload_is_unchanged_and_touches_nothing(saver, key, app_id, table):
    first = saver.save(key, PAYLOAD)
    before = _row(table, key)
    again = saver.save(key, PAYLOAD)
    assert again.ok and again.action == SaveAction.UNCHANGED and again.version == 1
    assert again.hashcode == first.hashcode and again.completeness == before["Completeness"]
    assert _row(table, key) == before


@pytest.mark.parametrize("saver,key,app_id,table", CASES)
def test_changed_payload_updates_and_changing_back_is_a_new_version(saver, key, app_id, table):
    first = saver.save(key, PAYLOAD)
    second = saver.save(key, CHANGED)
    assert second.action == SaveAction.UPDATED and second.version == 2 and second.hashcode != first.hashcode
    assert json.loads(_row(table, key)["Value"])["name"] == "thing-changed"
    third = saver.save(key, PAYLOAD)
    assert third.action == SaveAction.UPDATED and third.version == 3 and third.hashcode == first.hashcode
    assert _row(table, key)["Version"] == 3


def test_update_recomputes_completeness():
    first = SAVER.save(KEY, {"name": "x"})
    # name answered; size, level, url default; contacts empty (one unanswered): 1 of 5 = 20.
    assert first.completeness == 20.0
    second = SAVER.save(KEY, {"name": "x", "size": 3})
    # name and size answered: 2 of 5 = 40.
    assert second.action == SaveAction.UPDATED and second.completeness == 40.0
    assert _row(FACTS, KEY)["Completeness"] == 40.0


def test_defaults_passed_explicitly_do_not_raise_completeness():
    result = SAVER.save(KEY, {"name": "x", "size": None, "level": "low", "contacts": [], "url": None})
    assert result.completeness == 20.0
    assert result.action == SaveAction.CREATED


def test_key_order_does_not_change_the_hash():
    reordered = {"contacts": [{"phone": "1", "name": "a"}, {"name": "b"}], "name": "thing"}
    first = SAVER.save(KEY, PAYLOAD)
    second = SAVER.save(KEY, reordered)
    assert second.action == SaveAction.UNCHANGED and second.hashcode == first.hashcode


def test_component_key_validates_with_the_same_model_and_stores_the_application():
    component_key = "TestApp.Components.dbmcp.Thing"
    assert SAVER.save(component_key, {"name": "x"}).ok
    assert _row(FACTS, component_key)["AppID"] == "TestApp"
    result = SAVER.save(component_key, {"level": "low"})
    assert result.action == SaveAction.REJECTED and result.errors[0].path == "name"


def test_not_applicable_is_accepted_where_allowed_and_counts_as_answered():
    result = SAVER.save(KEY, {"name": "x", "url": {"reason": "It has no URL."}})
    assert result.ok
    # name and url (N/A) answered; size, level default; contacts empty: 2 of 5 = 40.
    assert result.completeness == 40.0
    assert json.loads(_row(FACTS, KEY)["Value"])["url"] == {"reason": "It has no URL."}


# ---- rejected payloads: nothing is written, errors carry path, description and question ----

def _errors(payload):
    result = SAVER.save(KEY, payload)
    assert not result.ok and result.action == SaveAction.REJECTED
    assert result.version is None and result.hashcode is None and result.completeness is None
    assert _nothing_written()
    return result.errors


def test_missing_mandatory_field_is_rejected_with_description_and_question():
    (error,) = _errors({k: v for k, v in PAYLOAD.items() if k != "name"})
    assert error.path == "name" and error.error_type == "missing" and error.message
    assert error.field_description == "Name of the thing, e.g. test-thing."
    assert error.question == "What is the name of the thing?"
    assert error.received is None and error.expected


def test_wrong_type_is_rejected_with_description_and_question():
    (error,) = _errors({**PAYLOAD, "size": "big"})
    assert error.path == "size" and error.error_type == "int_parsing"
    assert error.received == '"big"'
    assert error.field_description == "Size of the thing, e.g. 3."
    assert error.question == "Size of the thing, e.g. 3."  # no question declared: falls back to the description


def test_bad_enum_value_is_rejected_and_says_what_is_expected():
    (error,) = _errors({**PAYLOAD, "level": "extreme"})
    assert error.path == "level" and error.error_type == "enum"
    assert "low" in error.expected and "high" in error.expected
    assert error.field_description and error.question


def test_extra_field_is_rejected_and_says_which_fields_exist():
    (error,) = _errors({**PAYLOAD, "bogus": 1})
    assert error.path == "bogus" and error.error_type == "extra_forbidden"
    assert error.field_description == "Test-only object saved by the test savers."
    assert "bogus" in error.question and "contacts" in error.question


def test_error_inside_a_list_item_has_the_full_path_and_the_items_field_metadata():
    (error,) = _errors({"name": "x", "contacts": [{"name": "a"}, {"phone": "1"}]})
    assert error.path == "contacts.1.name" and error.error_type == "missing"
    assert error.field_description == "Name of the contact, e.g. test-contact."
    assert error.question == "What is the contact's name?"


def test_extra_field_inside_a_list_item_names_the_item_model():
    (error,) = _errors({"name": "x", "contacts": [{"name": "a", "bogus": 1}]})
    assert error.path == "contacts.0.bogus"
    assert "_Contact" in error.question and "phone" in error.question


def test_not_applicable_is_rejected_where_not_allowed():
    (error,) = _errors({"name": {"reason": "n/a"}})
    assert error.path.startswith("name")


def test_not_applicable_with_an_empty_reason_is_rejected():
    errors = _errors({"name": "x", "url": {"reason": ""}})
    assert errors and all(e.path.startswith("url") for e in errors)
    assert all(e.field_description and e.question for e in errors)
    reason = next(e for e in errors if e.path.endswith("reason"))
    assert reason.field_description.startswith("Why the question does not apply")
    assert reason.question == "Why is this not applicable?"


def test_empty_mandatory_text_is_rejected():
    (error,) = _errors({"name": ""})
    assert error.path == "name"


def test_all_errors_are_reported_together():
    errors = _errors({"size": "big", "bogus": 1})
    assert {e.path for e in errors} == {"name", "size", "bogus"}


@pytest.mark.parametrize("payload", ["not an object", 5, None, ["name"]])
def test_a_payload_that_is_not_an_object_is_rejected_not_raised(payload):
    (error,) = _errors(payload)
    assert error.path == "payload"


# ---- keys and application ids ----

@pytest.mark.parametrize(
    "saver,key",
    [
        (_AppThingSaver(), "TestApp.Other"),
        (_AppThingSaver(), "TestApp.Thing.Extra"),
        (_AppThingSaver(), "Thing"),
        (_AppThingSaver(), "TestApp.Components.Thing"),
        (_AppThingSaver(), "TestApp.Components..Thing"),
        (_AppThingSaver(), ".Thing"),
        (_AppThingSaver(), "Shared.Thing"),  # Shared is not an application
        (_SharedThingSaver(), "TestApp.Thing"),
        (_SharedThingSaver(), "shared.Thing"),  # case-sensitive
        (_DocThingSaver(), "TestApp.Thing"),
        (_DocThingSaver(), "TestApp.outputs.SMTD"),
        (_AppThingSaver(), ""),
        (_AppThingSaver(), None),
        (_AppThingSaver(), 42),
    ],
)
def test_a_key_matching_none_of_the_savers_patterns_is_rejected(saver, key):
    result = saver.save(key, PAYLOAD)
    assert not result.ok and result.action == SaveAction.REJECTED
    (error,) = result.errors
    assert error.path == "key" and error.error_type == "key_pattern_mismatch"
    assert error.field_description and error.question and error.expected
    assert _nothing_written()


def test_key_is_checked_before_the_payload():
    result = SAVER.save("Nope", {"bogus": 1})
    assert [e.path for e in result.errors] == ["key"]


def test_shared_key_stores_a_null_app_id():
    assert _SharedThingSaver().save("Shared.Thing", PAYLOAD).ok
    assert _row(FACTS, "Shared.Thing")["AppID"] is None


def test_an_app_key_with_a_mismatching_app_id_is_rejected():
    result = SAVER.save(KEY, PAYLOAD, app_id="Other")
    assert result.action == SaveAction.REJECTED
    (error,) = result.errors
    assert error.path == "app_id" and error.error_type == "app_id_mismatch"
    assert _nothing_written()


def test_app_id_is_case_sensitive():
    assert SAVER.save(KEY, PAYLOAD, app_id="testapp").action == SaveAction.REJECTED
    assert SAVER.save("testapp.Thing", PAYLOAD, app_id="TestApp").action == SaveAction.REJECTED
    assert _nothing_written()


def test_a_matching_app_id_is_accepted():
    assert SAVER.save(KEY, PAYLOAD, app_id="TestApp").action == SaveAction.CREATED


def test_a_shared_key_with_an_app_id_is_rejected():
    result = _SharedThingSaver().save("Shared.Thing", PAYLOAD, app_id="TestApp")
    assert result.action == SaveAction.REJECTED and result.errors[0].path == "app_id"
    assert _nothing_written()


# ---- table choice ----

def test_entity_savers_write_knowledge_facts_and_document_savers_write_document_outputs():
    SAVER.save(KEY, PAYLOAD)
    _DocThingSaver().save("TestApp.Outputs.TESTDOC", PAYLOAD)
    assert [r["FactKey"] for r in db.list_rows(FACTS)] == [KEY]
    assert [r["DocumentKey"] for r in db.list_rows(DOCUMENTS)] == ["TestApp.Outputs.TESTDOC"]
