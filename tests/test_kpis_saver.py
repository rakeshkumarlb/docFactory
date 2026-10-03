import hashlib
import json
import os
import sqlite3

import pytest
from docfactory.entitymodels.facts.kpis import Kpis
from docfactory.entitysaver.kpis_saver import KpisSaver
from docfactory.entitymodels.items.kpi import Kpi

pytestmark = pytest.mark.usefixtures("tmp_db")

SAVER = KpisSaver()
KEY = "Shared.Kpis"
_FULL = {
    "kpis": [{"name": "Test KPI", "definition": "Test definition"}],
    "notes": "Test notes",
}
PAYLOAD = Kpis.model_validate(_FULL).model_dump(mode="json")
CHANGED = Kpis.model_validate({**_FULL, "notes": "Test notes-changed"}).model_dump(mode="json")


def _row(key):
    con = sqlite3.connect(os.environ["DOCFACTORY_DB"])
    con.row_factory = sqlite3.Row
    try:
        return con.execute("SELECT * FROM KnowledgeFacts WHERE FactKey = ?", (key,)).fetchone()
    finally:
        con.close()


def test_created_stores_canonical_json_hash_app_id_and_version_1():
    result = SAVER.save(KEY, PAYLOAD)
    assert result.ok and result.action == "CREATED" and result.version == 1
    row = _row(KEY)
    stored = json.loads(row["Value"])
    assert stored == Kpis.model_validate(PAYLOAD).model_dump(mode="json")
    assert row["Value"] == json.dumps(stored, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert row["Hashcode"] == hashlib.sha256(row["Value"].encode("utf-8")).hexdigest()
    assert row["AppID"] == None
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
