import hashlib
import json
import os
import sqlite3

import pytest
from docfactory.documentmodels.documents.srs_document import SrsDocument
from docfactory.documentsaver.documents.srs_document_saver import SrsDocumentSaver
from docfactory.documentmodels.entitybound.application_summary_section import ApplicationSummarySection
from docfactory.documentmodels.entitybound.functional_requirements_section import FunctionalRequirementsSection
from docfactory.documentmodels.entitybound.non_functional_requirements_section import NonFunctionalRequirementsSection
from docfactory.documentmodels.entitybound.slo_section import SloSection

pytestmark = pytest.mark.usefixtures("tmp_db")

SAVER = SrsDocumentSaver()
KEY = "TestApp.Outputs.SRS"
_FULL = {
    "application_summary": {"application_name": "Test-App", "purpose": "Test purpose statement."},
    "functional_requirements": {"summary": "Test summary"},
    "non_functional_requirements": {"summary": "Test summary"},
    "service_levels": {"notes": "Test notes."},
}
PAYLOAD = SrsDocument.model_validate(_FULL).model_dump(mode="json")
CHANGED = SrsDocument.model_validate({**_FULL, "application_summary": {'application_name': 'Test-App-changed', 'purpose': 'Test purpose statement.'}}).model_dump(mode="json")


def _row(key):
    con = sqlite3.connect(os.environ["DOCFACTORY_DB"])
    con.row_factory = sqlite3.Row
    try:
        return con.execute("SELECT * FROM DocumentOutputs WHERE DocumentKey = ?", (key,)).fetchone()
    finally:
        con.close()


def test_created_stores_canonical_json_hash_app_id_and_version_1():
    result = SAVER.save(KEY, PAYLOAD)
    assert result.ok and result.action == "CREATED" and result.version == 1
    row = _row(KEY)
    stored = json.loads(row["Value"])
    assert stored == SrsDocument.model_validate(PAYLOAD).model_dump(mode="json")
    assert row["Value"] == json.dumps(stored, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert row["Hashcode"] == hashlib.sha256(row["Value"].encode("utf-8")).hexdigest()
    assert row["AppID"] == 'TestApp'
    assert row["Version"] == 1 and 0 <= row["Completeness"] <= 100


def test_same_payload_is_unchanged_and_touches_nothing():
    SAVER.save(KEY, PAYLOAD)
    before = dict(_row(KEY))
    result = SAVER.save(KEY, PAYLOAD)
    assert result.ok and result.action == "UNCHANGED" and result.version == 1
    assert dict(_row(KEY)) == before


def test_changed_payload_updates_and_changing_back_is_a_new_version():
    first = SAVER.save(KEY, PAYLOAD)
    second = SAVER.save(KEY, CHANGED)
    assert second.action == "UPDATED" and second.version == 2 and second.hashcode != first.hashcode
    third = SAVER.save(KEY, PAYLOAD)
    assert third.action == "UPDATED" and third.version == 3 and third.hashcode == first.hashcode


def test_invalid_payload_is_rejected_and_nothing_is_written():
    result = SAVER.save(KEY, {**PAYLOAD, "not_a_field": "x"})
    assert not result.ok and result.action == "REJECTED"
    assert result.errors and all(e.path and e.message and e.error_type for e in result.errors)
    assert _row(KEY) is None


def test_missing_mandatory_field_error_carries_description_and_question():
    payload = {k: v for k, v in PAYLOAD.items() if k != "application_summary"}
    result = SAVER.save(KEY, payload)
    assert result.action == "REJECTED" and _row(KEY) is None
    error = next(e for e in result.errors if "application_summary" in e.path)
    assert error.field_description and error.question
