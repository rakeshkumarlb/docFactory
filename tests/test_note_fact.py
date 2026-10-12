import pytest

from docfactory.entitymodels.facts.note import Note
from docfactory.bundle.bundle_store import BundleStore
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.save_action import SaveAction
from docfactory.entitymodels.items.note_entry import NoteEntry

pytestmark = pytest.mark.usefixtures("tmp_bundle")

KEY = "TestApp.Note"
_FULL = {
    "overview": "Test overview.",
    "notes": [],
}
PAYLOAD = Note.model_validate(_FULL).model_dump(mode="json")
CHANGED = Note.model_validate({**_FULL, "overview": 'Test overview.-changed'}).model_dump(mode="json")


def test_created_is_a_concept_file_with_canonical_json_hash_and_version_1():
    result = BundleStore().write_fact(KEY, PAYLOAD)
    assert result.ok and result.action == SaveAction.CREATED and result.version == 1
    record = BundleStore().read_fact(KEY)
    assert record.value == canonical_json(Note.model_validate(PAYLOAD).model_dump(mode="json"))
    assert record.hashcode == sha256_hex(record.value) == result.hashcode
    assert record.app_id == 'TestApp'
    assert record.version == 1 and 0 <= record.completeness <= 100


def test_same_payload_is_unchanged_and_touches_nothing():
    BundleStore().write_fact(KEY, PAYLOAD)
    before = BundleStore().read_fact(KEY)
    result = BundleStore().write_fact(KEY, PAYLOAD)
    assert result.ok and result.action == SaveAction.UNCHANGED and result.version == 1
    assert BundleStore().read_fact(KEY) == before


def test_changed_payload_updates_and_changing_back_is_a_new_version():
    first = BundleStore().write_fact(KEY, PAYLOAD)
    second = BundleStore().write_fact(KEY, CHANGED)
    assert second.action == SaveAction.UPDATED and second.version == 2 and second.hashcode != first.hashcode
    third = BundleStore().write_fact(KEY, PAYLOAD)
    assert third.action == SaveAction.UPDATED and third.version == 3 and third.hashcode == first.hashcode


def test_invalid_payload_is_rejected_and_nothing_is_written():
    result = BundleStore().write_fact(KEY, {**PAYLOAD, "not_a_field": "x"})
    assert not result.ok and result.action == SaveAction.REJECTED
    assert result.errors and all(e.path and e.message and e.error_type for e in result.errors)
    assert BundleStore().read_fact(KEY) is None


def test_component_key_stores_the_application_as_app_id():
    result = BundleStore().write_fact("TestApp.Components.testcomponent.Note", PAYLOAD)
    assert result.ok and result.action == SaveAction.CREATED
    assert BundleStore().read_fact("TestApp.Components.testcomponent.Note").app_id == 'TestApp'
