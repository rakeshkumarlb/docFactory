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


def init_schema(con: sqlite3.Connection) -> None:
    """Create both tables if they do not exist. Safe to call any number of times."""
    with con:
        for table, key_column in TABLE_KEYS.items():
            con.execute(f"CREATE TABLE IF NOT EXISTS {table} ({key_column} TEXT PRIMARY KEY, {_COLUMNS})")


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


def list_rows(table: str, app_id: str | None = None) -> list[dict]:
    """All stored rows ordered by key; with `app_id`, only that application's rows."""
    key_column = _key_column(table)
    with closing(connect()) as con:
        if app_id is None:
            rows = con.execute(f"SELECT * FROM {table} ORDER BY {key_column}").fetchall()
        else:
            rows = con.execute(f"SELECT * FROM {table} WHERE AppID = ? ORDER BY {key_column}", (app_id,)).fetchall()
    return [dict(row) for row in rows]
