import sqlite3
from contextlib import closing

import pytest

from docfactory import db


def _columns(path, table):
    with closing(sqlite3.connect(path)) as con:
        return {row[1]: (row[2], row[3], row[5]) for row in con.execute(f"PRAGMA table_info({table})")}


def test_db_path_uses_the_environment_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCFACTORY_DB", str(tmp_path / "x.sqlite"))
    assert db.db_path() == tmp_path / "x.sqlite"


def test_db_path_defaults_to_the_project_db_folder(monkeypatch):
    monkeypatch.delenv("DOCFACTORY_DB", raising=False)
    assert db.db_path() == db.PROJECT_ROOT / "db" / "docfactory.sqlite"
    assert (db.PROJECT_ROOT / "docfactory").is_dir()


def test_connect_creates_folder_file_and_schema(tmp_path, monkeypatch):
    path = tmp_path / "nested" / "folder" / "new.sqlite"
    monkeypatch.setenv("DOCFACTORY_DB", str(path))
    db.connect().close()
    assert path.is_file()
    facts = _columns(path, "KnowledgeFacts")
    assert facts["FactKey"][2] == 1  # primary key
    assert {"Value", "Hashcode", "AppID", "Completeness", "Version"} <= set(facts)
    assert facts["Value"][:2] == ("TEXT", 1) and facts["AppID"][:2] == ("TEXT", 0)
    assert facts["Completeness"][:2] == ("REAL", 1) and facts["Version"][:2] == ("INTEGER", 1)
    documents = _columns(path, "DocumentOutputs")
    assert documents["DocumentKey"][2] == 1
    # KnowledgeFacts has the same shape as DocumentOutputs plus the OKF columns (Phase 3)
    assert set(documents) - {"DocumentKey"} == set(facts) - {"FactKey"} - set(db.FACT_OKF_COLUMNS)


def test_init_schema_is_idempotent(tmp_db):
    db.write_row("KnowledgeFacts", "A.B", "{}", "h", "A", 10.0, 1)
    with closing(db.connect()) as con:
        db.init_schema(con)
        db.init_schema(con)
    assert db.get_row("KnowledgeFacts", "A.B")["Version"] == 1


@pytest.mark.parametrize("table,key", [("KnowledgeFacts", "KitchenHQ.Architecture"), ("DocumentOutputs", "KitchenHQ.Outputs.SMTD"), ("ConfiguredDocuments", "KitchenHQ.Configured.SMTD")])
def test_write_then_get_round_trips(tmp_db, table, key):
    db.write_row(table, key, '{"a":1}', "abc", "KitchenHQ", 12.5, 3)
    row = db.get_row(table, key)
    row = {name: row[name] for name in row if name not in db.FACT_OKF_COLUMNS}  # the OKF columns are tested in test_db_facts.py
    assert row == {
        db.TABLE_KEYS[table]: key,
        "Value": '{"a":1}',
        "Hashcode": "abc",
        "AppID": "KitchenHQ",
        "Completeness": 12.5,
        "Version": 3,
    }


def test_get_row_of_a_missing_key_is_none(tmp_db):
    assert db.get_row("KnowledgeFacts", "Nobody.Nothing") is None


def test_write_row_replaces_the_whole_row(tmp_db):
    db.write_row("KnowledgeFacts", "Shared.Kpis", "{}", "h1", None, 0.0, 1)
    db.write_row("KnowledgeFacts", "Shared.Kpis", '{"x":1}', "h2", None, 50.0, 2)
    row = db.get_row("KnowledgeFacts", "Shared.Kpis")
    assert (row["Value"], row["Hashcode"], row["AppID"], row["Completeness"], row["Version"]) == ('{"x":1}', "h2", None, 50.0, 2)
    assert len(db.list_rows("KnowledgeFacts")) == 1


def test_tables_are_separate(tmp_db):
    db.write_row("KnowledgeFacts", "A.B", "{}", "h", "A", 0.0, 1)
    assert db.get_row("DocumentOutputs", "A.B") is None
    assert db.list_rows("DocumentOutputs") == []


def test_list_rows_is_ordered_and_can_filter_by_application(tmp_db):
    db.write_row("KnowledgeFacts", "B.Two", "{}", "h", "B", 0.0, 1)
    db.write_row("KnowledgeFacts", "A.One", "{}", "h", "A", 0.0, 1)
    db.write_row("KnowledgeFacts", "Shared.Kpis", "{}", "h", None, 0.0, 1)
    assert [row["FactKey"] for row in db.list_rows("KnowledgeFacts")] == ["A.One", "B.Two", "Shared.Kpis"]
    assert [row["FactKey"] for row in db.list_rows("KnowledgeFacts", app_id="B")] == ["B.Two"]
    assert db.list_rows("KnowledgeFacts", app_id="Nobody") == []


def test_values_are_bound_as_parameters_not_pasted_into_sql(tmp_db):
    key = "A.B'; DROP TABLE KnowledgeFacts; --"
    db.write_row("KnowledgeFacts", key, "it's", "h", "A", 0.0, 1)
    assert db.get_row("KnowledgeFacts", key)["Value"] == "it's"
    assert db.list_rows("KnowledgeFacts", app_id="A' OR '1'='1") == []


@pytest.mark.parametrize("call", [
    lambda: db.get_row("Sqlite_master", "x"),
    lambda: db.write_row("Other; DROP TABLE x", "k", "{}", "h", None, 0.0, 1),
    lambda: db.list_rows("Other"),
])
def test_unknown_tables_are_refused(tmp_db, call):
    with pytest.raises(ValueError):
        call()


def test_the_fact_index_table_of_the_first_phase_4_build_is_dropped(tmp_db):
    import sqlite3
    with sqlite3.connect(tmp_db) as con:
        con.execute("CREATE TABLE FactIndex (FactKey TEXT PRIMARY KEY)")
    db.connect().close()
    with sqlite3.connect(tmp_db) as con:
        assert not con.execute("SELECT name FROM sqlite_master WHERE name = 'FactIndex'").fetchall()
