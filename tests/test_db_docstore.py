from docfactory import db


def test_tables_exist_with_expected_columns(tmp_db):
    with db.connect() as con:
        for table in ("DocStore", "DocStoreHistory"):
            cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
            assert cols == ["FullPath", "Hashcode", "Version", "Timestamp"]


def test_new_same_changed_and_history(tmp_db):
    assert db.write_docstore_row("App/a.pdf", "h1", "t1") == ("NEW", 1)
    assert db.write_docstore_row("App/a.pdf", "h1", "t2") == ("SAME", 1)
    assert db.get_docstore_row("App/a.pdf")["Timestamp"] == "t1"
    assert db.list_docstore_history("App/a.pdf") == []
    assert db.write_docstore_row("App/a.pdf", "h2", "t3") == ("CHANGED", 2)
    row = db.get_docstore_row("App/a.pdf")
    assert (row["Hashcode"], row["Version"], row["Timestamp"]) == ("h2", 2, "t3")
    assert [(h["Version"], h["Hashcode"]) for h in db.list_docstore_history("App/a.pdf")] == [(2, "h2")]


def test_missing_row_is_none(tmp_db):
    assert db.get_docstore_row("nope") is None


def test_list_filters_by_folder_and_name(tmp_db):
    for path in ("App/SRS.pdf", "App/sub/Runbook.html", "Application2/x.pdf", "shared/Standards.pdf"):
        db.write_docstore_row(path, "h", "t")
    assert [r["FullPath"] for r in db.list_docstore_rows()] == sorted(
        ["App/SRS.pdf", "App/sub/Runbook.html", "Application2/x.pdf", "shared/Standards.pdf"])
    assert [r["FullPath"] for r in db.list_docstore_rows(folder="App")] == ["App/SRS.pdf", "App/sub/Runbook.html"]
    assert [r["FullPath"] for r in db.list_docstore_rows(name_contains="run")] == ["App/sub/Runbook.html"]
    assert [r["FullPath"] for r in db.list_docstore_rows(folder="App", name_contains="srs")] == ["App/SRS.pdf"]
    assert db.list_docstore_rows(name_contains="%") == []
