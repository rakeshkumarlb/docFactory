import os
import sqlite3
from contextlib import closing
from pathlib import Path

ENV_VAR = "DOCFACTORY_DB"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# The only tables that exist and the name of each one's key column. Table names never come from callers.
TABLE_KEYS = {"KnowledgeFacts": "FactKey", "DocumentOutputs": "DocumentKey"}

_COLUMNS = (
    "Value TEXT NOT NULL, Hashcode TEXT NOT NULL, AppID TEXT NULL, "
    "Completeness REAL NOT NULL, Version INTEGER NOT NULL"
)


def db_path() -> Path:
    """The database file: env DOCFACTORY_DB, else db/docfactory.sqlite under the project root."""
    override = os.environ.get(ENV_VAR)
    return Path(override) if override else PROJECT_ROOT / "db" / "docfactory.sqlite"


_DOCSTORE_COLUMNS = "Hashcode TEXT NOT NULL, Version INTEGER NOT NULL, Timestamp TEXT NOT NULL"

# The OKF columns of KnowledgeFacts (Phase 3): column name -> SQL definition. All are derived by the saver, never hand-written.
# Rows written before Phase 3 get NULL / the defaults until they are saved again with metadata.
FACT_OKF_COLUMNS = {
    "FilePath": "TEXT NULL",
    "YmlFrontmatter": "TEXT NULL",
    "GeneratedBy": "TEXT NULL",
    "GeneratedAt": "TEXT NULL",
    "Verified": "TEXT NOT NULL DEFAULT '[]'",
    "Status": "TEXT NOT NULL DEFAULT 'draft'",
    "StaleAfter": "TEXT NULL",
}
_FACT_OKF_SQL = ", ".join(f"{name} {definition}" for name, definition in FACT_OKF_COLUMNS.items())


def _migrate_knowledge_facts(con: sqlite3.Connection) -> None:
    """Add the OKF columns to a KnowledgeFacts table created before Phase 3."""
    present = {row[1] for row in con.execute("PRAGMA table_info(KnowledgeFacts)")}
    for name, definition in FACT_OKF_COLUMNS.items():
        if name not in present:
            con.execute(f"ALTER TABLE KnowledgeFacts ADD COLUMN {name} {definition}")


def init_schema(con: sqlite3.Connection) -> None:
    """Create all tables if they do not exist and migrate older ones. Safe to call any number of times."""
    with con:
        for table, key_column in TABLE_KEYS.items():
            extra = f", {_FACT_OKF_SQL}" if table == "KnowledgeFacts" else ""
            con.execute(f"CREATE TABLE IF NOT EXISTS {table} ({key_column} TEXT PRIMARY KEY, {_COLUMNS}{extra})")
        _migrate_knowledge_facts(con)
        con.execute(
            "CREATE TABLE IF NOT EXISTS KnowledgeFactsHistory (FactKey TEXT NOT NULL, Hashcode TEXT NOT NULL, "
            "Version INTEGER NOT NULL, Timestamp TEXT NOT NULL, GeneratedBy TEXT NULL, PRIMARY KEY (FactKey, Version))"
        )
        con.execute(
            "CREATE TABLE IF NOT EXISTS KnowledgeFactSources (FactKey TEXT NOT NULL, Resource TEXT NOT NULL, "
            "PRIMARY KEY (FactKey, Resource))"
        )
        con.execute(f"CREATE TABLE IF NOT EXISTS DocStore (FullPath TEXT PRIMARY KEY, {_DOCSTORE_COLUMNS})")
        con.execute(
            f"CREATE TABLE IF NOT EXISTS DocStoreHistory (FullPath TEXT NOT NULL, {_DOCSTORE_COLUMNS}, "
            "PRIMARY KEY (FullPath, Version))"
        )


def connect() -> sqlite3.Connection:
    """Open the database (creating the file and folder) with the schema in place. Rows come back as sqlite3.Row."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    init_schema(con)
    return con


def _key_column(table: str) -> str:
    if table not in TABLE_KEYS:
        raise ValueError(f"unknown table {table!r}; expected one of {sorted(TABLE_KEYS)}")
    return TABLE_KEYS[table]


def get_row(table: str, key: str) -> dict | None:
    """The stored row for `key` as a dict, or None when there is none."""
    key_column = _key_column(table)
    with closing(connect()) as con:
        row = con.execute(f"SELECT * FROM {table} WHERE {key_column} = ?", (key,)).fetchone()
    return dict(row) if row else None


def write_row(table: str, key: str, value: str, hashcode: str, app_id: str | None, completeness: float, version: int) -> None:
    """Insert or replace the whole row for `key` in one transaction."""
    key_column = _key_column(table)
    with closing(connect()) as con, con:
        con.execute(
            f"INSERT OR REPLACE INTO {table} ({key_column}, Value, Hashcode, AppID, Completeness, Version) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (key, value, hashcode, app_id, completeness, version),
        )


def _check_okf_columns(okf: dict) -> None:
    unknown = set(okf) - set(FACT_OKF_COLUMNS)
    if unknown:
        raise ValueError(f"unknown KnowledgeFacts column(s) {sorted(unknown)}; expected {sorted(FACT_OKF_COLUMNS)}")


def _replace_sources(con: sqlite3.Connection, key: str, sources: list[str]) -> None:
    con.execute("DELETE FROM KnowledgeFactSources WHERE FactKey = ?", (key,))
    con.executemany("INSERT OR IGNORE INTO KnowledgeFactSources VALUES (?, ?)", [(key, resource) for resource in sources])


def write_fact_row(key: str, value: str, hashcode: str, app_id: str | None, completeness: float, version: int,
                   okf: dict, sources: list[str], history: bool) -> None:
    """Insert or replace a whole KnowledgeFacts row with its OKF columns and source index in one transaction.

    `okf` maps OKF column names to values (columns it omits get their defaults). With `history`, the new state is also added
    to KnowledgeFactsHistory (Timestamp = GeneratedAt).
    """
    _check_okf_columns(okf)
    columns = ["FactKey", "Value", "Hashcode", "AppID", "Completeness", "Version", *okf]
    values = [key, value, hashcode, app_id, completeness, version, *okf.values()]
    with closing(connect()) as con, con:
        con.execute(
            f"INSERT OR REPLACE INTO KnowledgeFacts ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})", values
        )
        _replace_sources(con, key, sources)
        if history:
            con.execute("INSERT INTO KnowledgeFactsHistory VALUES (?, ?, ?, ?, ?)",
                        (key, hashcode, version, okf.get("GeneratedAt") or "", okf.get("GeneratedBy")))


def update_fact_metadata(key: str, okf: dict, sources: list[str]) -> None:
    """Refresh OKF columns and the source index of an existing fact in place. Value, Hashcode and Version are untouched."""
    _check_okf_columns(okf)
    assignments = ", ".join(f"{name} = ?" for name in okf)
    with closing(connect()) as con, con:
        if okf:
            con.execute(f"UPDATE KnowledgeFacts SET {assignments} WHERE FactKey = ?", [*okf.values(), key])
        _replace_sources(con, key, sources)


def list_fact_keys_by_source(resource: str) -> list[str]:
    """Keys of the facts whose sources name `resource` (a DocStore path), ordered."""
    with closing(connect()) as con:
        rows = con.execute("SELECT FactKey FROM KnowledgeFactSources WHERE Resource = ? ORDER BY FactKey", (resource,)).fetchall()
    return [row[0] for row in rows]


def list_fact_history(key: str) -> list[dict]:
    """The change history of one fact, oldest first."""
    with closing(connect()) as con:
        rows = con.execute("SELECT * FROM KnowledgeFactsHistory WHERE FactKey = ? ORDER BY Version", (key,)).fetchall()
    return [dict(row) for row in rows]


def list_rows(table: str, app_id: str | None = None) -> list[dict]:
    """All stored rows ordered by key; with `app_id`, only that application's rows."""
    key_column = _key_column(table)
    with closing(connect()) as con:
        if app_id is None:
            rows = con.execute(f"SELECT * FROM {table} ORDER BY {key_column}").fetchall()
        else:
            rows = con.execute(f"SELECT * FROM {table} WHERE AppID = ? ORDER BY {key_column}", (app_id,)).fetchall()
    return [dict(row) for row in rows]


def get_docstore_row(full_path: str) -> dict | None:
    """The DocStore row for `full_path` (forward slashes, relative to DocStore/) as a dict, or None."""
    with closing(connect()) as con:
        row = con.execute("SELECT * FROM DocStore WHERE FullPath = ?", (full_path,)).fetchone()
    return dict(row) if row else None


def _like_escape(text: str) -> str:
    """Escape LIKE wildcards so `text` matches literally under ESCAPE '!'."""
    return text.replace("!", "!!").replace("%", "!%").replace("_", "!_")


def list_docstore_rows(folder: str | None = None, name_contains: str | None = None) -> list[dict]:
    """DocStore rows ordered by path. `folder` keeps rows at or below that folder; `name_contains` is a case-insensitive path match."""
    clauses, params = [], []
    if folder:
        folder = folder.strip("/")
        clauses.append("(FullPath = ? OR FullPath LIKE ? ESCAPE '!')")
        params += [folder, _like_escape(folder) + "/%"]
    if name_contains:
        clauses.append("lower(FullPath) LIKE ? ESCAPE '!'")
        params.append("%" + _like_escape(name_contains.lower()) + "%")
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with closing(connect()) as con:
        rows = con.execute(f"SELECT * FROM DocStore{where} ORDER BY FullPath", params).fetchall()
    return [dict(row) for row in rows]


def write_docstore_row(full_path: str, hashcode: str, timestamp: str) -> tuple[str, int]:
    """Record a stored file in one transaction. Returns (action, version).

    No row: NEW, version 1. Same hash: SAME, nothing written. Different hash: CHANGED, version + 1, and the new state is
    also added to DocStoreHistory.
    """
    with closing(connect()) as con, con:
        row = con.execute("SELECT Hashcode, Version FROM DocStore WHERE FullPath = ?", (full_path,)).fetchone()
        if row is None:
            con.execute("INSERT INTO DocStore VALUES (?, ?, 1, ?)", (full_path, hashcode, timestamp))
            return "NEW", 1
        if row["Hashcode"] == hashcode:
            return "SAME", row["Version"]
        version = row["Version"] + 1
        con.execute("UPDATE DocStore SET Hashcode = ?, Version = ?, Timestamp = ? WHERE FullPath = ?",
                    (hashcode, version, timestamp, full_path))
        con.execute("INSERT INTO DocStoreHistory VALUES (?, ?, ?, ?)", (full_path, hashcode, version, timestamp))
        return "CHANGED", version


def list_docstore_history(full_path: str) -> list[dict]:
    """The change history of one file, oldest first."""
    with closing(connect()) as con:
        rows = con.execute("SELECT * FROM DocStoreHistory WHERE FullPath = ? ORDER BY Version", (full_path,)).fetchall()
    return [dict(row) for row in rows]
