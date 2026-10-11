"""DocumentStateStore: the stored parts of a generated document as validated JSON state files (Step 5 of the OKF bundle redesign)."""
import json

import pytest

from docfactory.bundle.bundle_error import BundleError
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.documentmodels.document_control import DocumentControl
from docfactory.generation.document_parts import BODY, CONTROL, HISTORY, NEEDS, part_key
from docfactory.generation.document_state_store import DocumentStateStore
from docfactory.models.save_action import SaveAction

APP, DOC = "TestApp", "SRS"
CONTROL_PAYLOAD = {"document_id": "TestApp-SRS", "title": "TestApp SRS", "document_version": "0.1", "status": "Draft"}
HISTORY_PAYLOAD = {"revisions": [{"version": "0.1", "date": "2026-10-11", "summary": "Created.", "author": "docFactory"}]}


@pytest.fixture
def store(tmp_bundle):
    return DocumentStateStore()


def test_keys_keep_the_old_shape():
    assert [part_key(APP, DOC, part) for part in (BODY, CONTROL, HISTORY, NEEDS)] == [
        "TestApp.Outputs.SRS", "TestApp.Outputs.SRS.DocumentControl", "TestApp.Outputs.SRS.RevisionHistory", "TestApp.Outputs.SRS.MissingInfo"]


def test_a_part_is_created_as_a_state_file_with_key_version_hash_completeness_and_value(store):
    result = store.save(APP, DOC, CONTROL, CONTROL_PAYLOAD)
    assert (result.ok, result.action, result.version, result.key) == (True, SaveAction.CREATED, 1, "TestApp.Outputs.SRS.DocumentControl")
    path = store.root / APP / "state" / "SRS.control.json"
    assert store.path(APP, DOC, CONTROL) == path.resolve() and path.is_file()
    state = json.loads(path.read_text(encoding="utf-8"))
    assert set(state) == {"key", "version", "hashcode", "completeness", "value"} and state["version"] == 1
    assert state["hashcode"] == sha256_hex(canonical_json(state["value"])) == result.hashcode
    assert state["value"]["document_id"] == "TestApp-SRS" and state["completeness"] == result.completeness


def test_same_value_is_unchanged_and_writes_nothing_a_new_value_updates_and_changing_back_is_a_new_version(store):
    store.save(APP, DOC, CONTROL, CONTROL_PAYLOAD)
    path = store.path(APP, DOC, CONTROL)
    before = path.read_bytes()
    assert store.save(APP, DOC, CONTROL, CONTROL_PAYLOAD).action == SaveAction.UNCHANGED and path.read_bytes() == before
    changed = {**CONTROL_PAYLOAD, "status": "Approved"}
    assert (store.save(APP, DOC, CONTROL, changed).action, store.read(APP, DOC, CONTROL).version) == (SaveAction.UPDATED, 2)
    assert store.save(APP, DOC, CONTROL, CONTROL_PAYLOAD).version == 3


def test_a_model_instance_and_a_dict_give_the_same_part(store):
    from_dict = store.save(APP, DOC, CONTROL, CONTROL_PAYLOAD)
    again = store.save(APP, DOC, CONTROL, DocumentControl.model_validate(CONTROL_PAYLOAD))
    assert again.action == SaveAction.UNCHANGED and again.hashcode == from_dict.hashcode
    assert store.model(APP, DOC, CONTROL) == DocumentControl.model_validate(CONTROL_PAYLOAD)


def test_an_invalid_part_is_rejected_with_feedback_and_nothing_is_written(store):
    result = store.save(APP, DOC, CONTROL, {"document_id": "x", "bogus": 1})
    assert result.action == SaveAction.REJECTED and not result.ok
    assert {e.error_type for e in result.errors} >= {"extra_forbidden", "missing"} and any(e.question for e in result.errors)
    assert not store.root.exists() and store.read(APP, DOC, CONTROL) is None and store.model(APP, DOC, CONTROL) is None


def test_the_record_carries_canonical_json_hash_version_and_application(store):
    store.save(APP, DOC, HISTORY, HISTORY_PAYLOAD)
    record = store.read(APP, DOC, HISTORY)
    assert record.key == "TestApp.Outputs.SRS.RevisionHistory" and record.app_id == APP and record.version == 1
    assert record.value == canonical_json(json.loads(record.value)) and record.hashcode == sha256_hex(record.value)


def test_list_is_ordered_and_can_filter_by_application(store):
    store.save(APP, DOC, CONTROL, CONTROL_PAYLOAD)
    store.save(APP, DOC, HISTORY, HISTORY_PAYLOAD)
    store.save("Other", "SMTD", CONTROL, {**CONTROL_PAYLOAD, "document_id": "Other-SMTD"})
    assert [r.key for r in store.list()] == ["Other.Outputs.SMTD.DocumentControl", "TestApp.Outputs.SRS.DocumentControl", "TestApp.Outputs.SRS.RevisionHistory"]
    assert [r.key for r in store.list(APP)] == ["TestApp.Outputs.SRS.DocumentControl", "TestApp.Outputs.SRS.RevisionHistory"]
    assert DocumentStateStore(store.root / "nowhere").list() == []


def test_a_state_file_edited_outside_the_system_is_refused(store):
    store.save(APP, DOC, CONTROL, CONTROL_PAYLOAD)
    path = store.path(APP, DOC, CONTROL)
    path.write_text(path.read_text(encoding="utf-8").replace("Draft", "Approved"), encoding="utf-8")
    with pytest.raises(BundleError, match="edited outside the system"):
        store.read(APP, DOC, CONTROL)
    with pytest.raises(BundleError):
        store.list()


def test_a_file_that_is_not_a_state_file_is_refused(store):
    store.path(APP, DOC, CONTROL).parent.mkdir(parents=True)
    store.path(APP, DOC, CONTROL).write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(BundleError, match="not a readable document state"):
        store.read(APP, DOC, CONTROL)


@pytest.mark.parametrize("app,doc", [("..", "SRS"), ("TestApp", "../../x"), ("a/../..", "SRS")])
def test_names_that_would_leave_the_output_folder_are_refused(store, app, doc):
    with pytest.raises(ValueError):
        store.path(app, doc, CONTROL)


def test_the_state_folder_sits_beside_the_rendered_documents(store):
    store.save(APP, DOC, BODY, {"sections": []})
    (store.root / APP / "SRS.md").write_text("# view", encoding="utf-8")
    assert sorted(p.relative_to(store.root).as_posix() for p in store.root.rglob("*") if p.is_file()) == ["TestApp/SRS.md", "TestApp/state/SRS.body.json"]
