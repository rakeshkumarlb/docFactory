import hashlib
import json
import os
import sqlite3

import pytest
from docfactory.entitymodels.facts.backup_recovery import BackupRecovery
from docfactory.entitysaver.backup_recovery_saver import BackupRecoverySaver

pytestmark = pytest.mark.usefixtures("tmp_db")

SAVER = BackupRecoverySaver()
KEY = "TestApp.BackupRecovery"
_FULL = {
    "backup_schedule": "Test backup schedule",
    "backup_retention": "Test backup retention",
    "backup_location": "Test backup location",
    "restore_procedure": "Test restore procedure",
    "rpo": "Test rpo",
    "rto": "Test rto",
    "disaster_recovery_plan": "Test disaster recovery plan",
}
PAYLOAD = BackupRecovery.model_validate(_FULL).model_dump(mode="json")
CHANGED = BackupRecovery.model_validate({**_FULL, "backup_schedule": 'Test backup schedule-changed'}).model_dump(mode="json")


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
    assert stored == BackupRecovery.model_validate(PAYLOAD).model_dump(mode="json")
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


def test_component_key_stores_the_application_as_app_id():
    result = SAVER.save("TestApp.Components.testcomponent.BackupRecovery", PAYLOAD)
    assert result.ok and result.action == "CREATED"
    assert _row("TestApp.Components.testcomponent.BackupRecovery")["AppID"] == 'TestApp'
