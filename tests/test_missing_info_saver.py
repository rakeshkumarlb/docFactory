import hashlib
import json
import os
import sqlite3

import pytest
from docfactory.documentmodels.missing_info import MissingInfo
from docfactory.documentsaver.missing_info_saver import MissingInfoSaver
from docfactory.documentmodels.document_gap import DocumentGap
from docfactory.documentmodels.document_need import DocumentNeed
from docfactory.documentmodels.needs_origin import NeedsOrigin

pytestmark = pytest.mark.usefixtures("tmp_db")

SAVER = MissingInfoSaver()
KEY = "TestApp.Outputs.TESTDOC.MissingInfo"
_FULL = {
    "gaps": [],
    "needs": [],
    "gaps_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "needs_origin": NeedsOrigin.LLM,
}
PAYLOAD = MissingInfo.model_validate(_FULL).model_dump(mode="json")
CHANGED = MissingInfo.model_validate({**_FULL, "gaps_hash": 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-changed'}).model_dump(mode="json")


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
    assert stored == MissingInfo.model_validate(PAYLOAD).model_dump(mode="json")
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
    payload = {k: v for k, v in PAYLOAD.items() if k != "gaps_hash"}
    result = SAVER.save(KEY, payload)
    assert result.action == "REJECTED" and _row(KEY) is None
    error = next(e for e in result.errors if "gaps_hash" in e.path)
    assert error.field_description and error.question


def test_key_pattern_is_the_fourth_output_row_of_a_document():
    assert MissingInfoSaver.key_patterns == ("{app}.Outputs.{doctype}.MissingInfo",)
    assert SAVER.save("TestApp.Outputs.SRS.MissingInfo", PAYLOAD).ok
    assert not SAVER.save("TestApp.Outputs.SRS.DocumentControl", PAYLOAD).ok
    assert not SAVER.save("TestApp.MissingInfo", PAYLOAD).ok


def test_gaps_hash_and_needs_origin_do_not_affect_completeness():
    a = SAVER.save("TestApp.Outputs.A.MissingInfo", PAYLOAD)
    other = {**PAYLOAD, "gaps_hash": "b" * 64, "needs_origin": NeedsOrigin.FALLBACK.value}
    b = SAVER.save("TestApp.Outputs.B.MissingInfo", other)
    assert a.completeness == b.completeness == 0.0


def test_completeness_counts_gap_and_need_fields_by_hand():
    gap = DocumentGap(number=1, field="a.b", question="Test question?", expected_source="Test.field")
    need = DocumentNeed(question="Test question?", gaps=[1])
    payload = {**PAYLOAD, "gaps": [gap.model_dump(mode="json")], "needs": [need.model_dump(mode="json")]}
    result = SAVER.save("TestApp.Outputs.C.MissingInfo", payload)
    # gap: 7 fields, 4 mandatory answered (missing_in, item_count, example_items unanswered); need: 3 fields, 2 answered (audience unanswered)
    assert result.completeness == pytest.approx(6 / 10 * 100)
