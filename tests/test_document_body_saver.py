import pytest

from docfactory import db
from docfactory.documentsaver.document_body_saver import DocumentBodySaver

pytestmark = pytest.mark.usefixtures("tmp_db")

SAVER = DocumentBodySaver()
KEY = "TestApp.Outputs.SRS"
BODY = {"sections": [{"id": "overview", "title": "Overview", "fields": [
    {"binding": "ApplicationOverview.purpose", "label": "Purpose", "status": "answered", "value": '"Does one thing."'}]}]}


def test_the_body_is_stored_in_document_outputs_and_versioned():
    created = SAVER.save(KEY, BODY)
    assert created.ok and created.action == "CREATED" and created.version == 1
    assert db.get_row("DocumentOutputs", KEY)["AppID"] == "TestApp"
    assert db.get_row("KnowledgeFacts", KEY) is None
    assert SAVER.save(KEY, BODY).action == "UNCHANGED"
    changed = {"sections": [{**BODY["sections"][0], "title": "Changed"}]}
    updated = SAVER.save(KEY, changed)
    assert updated.action == "UPDATED" and updated.version == 2


def test_a_part_key_is_not_a_body_key():
    result = SAVER.save("TestApp.Outputs.SRS.DocumentControl", BODY)
    assert not result.ok and result.errors[0].error_type == "key_pattern_mismatch"
    assert db.list_rows("DocumentOutputs") == []
