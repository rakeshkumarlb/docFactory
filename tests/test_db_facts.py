"""KnowledgeFacts OKF columns, migration, KnowledgeFactsHistory and the source index (Phase 3a)."""
import sqlite3

import pytest

from docfactory import db

OKF = {
    "FactType": "Architecture",
    "Title": "KitchenHQ architecture",
    "Description": "Three services.",
    "Tags": '["architecture"]',
    "Sources": '[{"resource":"KitchenHQ/srs.pdf"}]',
    "YmlFrontmatter": "type: Architecture\n",
    "GeneratedBy": "seed",
    "GeneratedAt": "2026-10-03T10:00:00Z",
    "Verified": "[]",
    "Status": "draft",
    "StaleAfter": None,
}
KEY = "KitchenHQ.Architecture"


def _write(version=1, history=False, okf=OKF, sources=()):
    db.write_fact_row(KEY, '{"a":1}', f"hash{version}", "KitchenHQ", 50.0, version, okf, list(sources), history)


def test_a_fact_row_holds_the_okf_columns(tmp_db):
    _write()
    row = db.get_row("KnowledgeFacts", KEY)
    assert {name: row[name] for name in OKF} == OKF
    assert row["Version"] == 1 and row["Value"] == '{"a":1}'


def test_okf_columns_default_for_a_plain_write(tmp_db):
    db.write_row("KnowledgeFacts", KEY, "{}", "h", "KitchenHQ", 0.0, 1)
    row = db.get_row("KnowledgeFacts", KEY)
    assert row["Verified"] == "[]" and row["Status"] == "draft"
    assert row["Tags"] == "[]" and row["Sources"] == "[]" and "FilePath" not in row
    assert row["FactType"] is None and row["Title"] is None and row["YmlFrontmatter"] is None and row["GeneratedBy"] is None


def test_document_outputs_has_no_okf_columns(tmp_db):
    db.write_row("DocumentOutputs", "KitchenHQ.Outputs.SMTD", "{}", "h", "KitchenHQ", 0.0, 1)
    assert not set(db.FACT_OKF_COLUMNS) & set(db.get_row("DocumentOutputs", "KitchenHQ.Outputs.SMTD"))


def test_unknown_okf_columns_are_refused(tmp_db):
    with pytest.raises(ValueError, match="unknown KnowledgeFacts column"):
        _write(okf={"Value; DROP TABLE KnowledgeFacts": "x"})
    with pytest.raises(ValueError, match="unknown KnowledgeFacts column"):
        db.update_fact_metadata(KEY, {"Version": 9}, [])


def test_history_is_written_only_when_asked_and_records_who_and_when(tmp_db):
    _write(version=1)
    assert db.list_fact_history(KEY) == []
    _write(version=2, history=True, okf={**OKF, "GeneratedBy": "okf-extraction-agent/m", "GeneratedAt": "2026-10-04T08:00:00Z"})
    _write(version=3, history=True)
    assert db.list_fact_history(KEY) == [
        {"FactKey": KEY, "Hashcode": "hash2", "Version": 2, "Timestamp": "2026-10-04T08:00:00Z", "GeneratedBy": "okf-extraction-agent/m"},
        {"FactKey": KEY, "Hashcode": "hash3", "Version": 3, "Timestamp": "2026-10-03T10:00:00Z", "GeneratedBy": "seed"},
    ]


def test_update_fact_metadata_leaves_value_hash_and_version_alone(tmp_db):
    _write(version=4)
    db.update_fact_metadata(KEY, {"YmlFrontmatter": "type: New\n", "StaleAfter": "2027-01-01T00:00:00Z"}, ["a/b.pdf"])
    row = db.get_row("KnowledgeFacts", KEY)
    assert (row["Value"], row["Hashcode"], row["Version"]) == ('{"a":1}', "hash4", 4)
    assert row["YmlFrontmatter"] == "type: New\n" and row["StaleAfter"] == "2027-01-01T00:00:00Z"
    assert row["GeneratedBy"] == "seed"  # not named, so not touched
    assert db.list_fact_history(KEY) == []


def test_sources_find_the_facts_derived_from_a_file_and_are_replaced_on_save(tmp_db):
    db.write_fact_row("KitchenHQ.Architecture", "{}", "h", "KitchenHQ", 0.0, 1, OKF, ["KitchenHQ/srs.pdf", "KitchenHQ/arch.docx"], False)
    db.write_fact_row("KitchenHQ.Environments", "{}", "h", "KitchenHQ", 0.0, 1, OKF, ["KitchenHQ/srs.pdf"], False)
    assert db.list_fact_keys_by_source("KitchenHQ/srs.pdf") == ["KitchenHQ.Architecture", "KitchenHQ.Environments"]
    assert db.list_fact_keys_by_source("KitchenHQ/arch.docx") == ["KitchenHQ.Architecture"]
    assert db.list_fact_keys_by_source("nothing.pdf") == []
    db.update_fact_metadata("KitchenHQ.Architecture", {}, ["KitchenHQ/arch.docx"])
    assert db.list_fact_keys_by_source("KitchenHQ/srs.pdf") == ["KitchenHQ.Environments"]


def test_a_database_created_before_phase_3_is_migrated_and_keeps_its_rows(tmp_path, monkeypatch):
    path = tmp_path / "old.sqlite"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE KnowledgeFacts (FactKey TEXT PRIMARY KEY, Value TEXT NOT NULL, Hashcode TEXT NOT NULL, "
                "AppID TEXT NULL, Completeness REAL NOT NULL, Version INTEGER NOT NULL)")
    con.execute("INSERT INTO KnowledgeFacts VALUES ('KitchenHQ.Architecture', '{}', 'h', 'KitchenHQ', 10.0, 2)")
    con.commit()
    con.close()
    monkeypatch.setenv(db.ENV_VAR, str(path))
    row = db.get_row("KnowledgeFacts", KEY)
    assert row["Version"] == 2 and row["Completeness"] == 10.0
    assert row["Status"] == "draft" and row["Verified"] == "[]" and row["Tags"] == "[]" and row["Title"] is None
    db.connect().close()  # migrating twice is harmless


def test_the_file_path_column_of_the_removed_knowledge_files_is_dropped(tmp_path, monkeypatch):
    path = tmp_path / "phase3.sqlite"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE KnowledgeFacts (FactKey TEXT PRIMARY KEY, Value TEXT NOT NULL, Hashcode TEXT NOT NULL, "
                "AppID TEXT NULL, Completeness REAL NOT NULL, Version INTEGER NOT NULL, FilePath TEXT NULL, YmlFrontmatter TEXT NULL)")
    con.execute("INSERT INTO KnowledgeFacts VALUES ('KitchenHQ.Architecture', '{}', 'h', 'KitchenHQ', 10.0, 2, 'bundles/x.md', 'type: A')")
    con.commit()
    con.close()
    monkeypatch.setenv(db.ENV_VAR, str(path))
    row = db.get_row("KnowledgeFacts", KEY)
    assert "FilePath" not in row and row["YmlFrontmatter"] == "type: A" and row["Version"] == 2
