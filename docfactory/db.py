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
# OKF lives only in these columns; the content is the JSON in Value (there are no knowledge files). Tags and Sources are JSON lists.
# Rows written before Phase 3 get NULL / the defaults until they are saved again with metadata.
FACT_OKF_COLUMNS = {
    "FactType": "TEXT NULL",
    "Title": "TEXT NULL",
    "Description": "TEXT NULL",
    "Tags": "TEXT NOT NULL DEFAULT '[]'",
    "Sources": "TEXT NOT NULL DEFAULT '[]'",
    "YmlFrontmatter": "TEXT NULL",
    "GeneratedBy": "TEXT NULL",
    "GeneratedAt": "TEXT NULL",
    "Verified": "TEXT NOT NULL DEFAULT '[]'",
    "Status": "TEXT NOT NULL DEFAULT 'draft'",
    "StaleAfter": "TEXT NULL",
}
_FACT_OKF_SQL = ", ".join(f"{name} {definition}" for name, definition in FACT_OKF_COLUMNS.items())


_DROPPED_FACT_COLUMNS = ["FilePath"]  # the path of the removed bundles/ knowledge file


def _migrate_knowledge_facts(con: sqlite3.Connection) -> None:
    """Add the OKF columns to an older KnowledgeFacts table and drop the columns that no longer exist."""
    present = {row[1] for row in con.execute("PRAGMA table_info(KnowledgeFacts)")}
    for name, definition in FACT_OKF_COLUMNS.items():
        if name not in present:
            con.execute(f"ALTER TABLE KnowledgeFacts ADD COLUMN {name} {definition}")
    for name in _DROPPED_FACT_COLUMNS:
        if name in present:
            con.execute(f"ALTER TABLE KnowledgeFacts DROP COLUMN {name}")


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
        con.execute(  # the vector index of the facts (metadata + value) (Phase 4): derived and rebuildable, never truth
            "CREATE TABLE IF NOT EXISTS FactIndex (FactKey TEXT PRIMARY KEY, TextHash TEXT NOT NULL, "
            "EmbedModel TEXT NOT NULL, Dim INTEGER NOT NULL, Vector BLOB NOT NULL)"
        )
        con.execute(  # what each DocStore file contributed to a fact (Phase 3): the fact is the merge of its contributions
            "CREATE TABLE IF NOT EXISTS FactContributions (FactKey TEXT NOT NULL, Resource TEXT NOT NULL, Value TEXT NOT NULL, "
            "Hashcode TEXT NOT NULL, ChunksHash TEXT NULL, Description TEXT NULL, GeneratedBy TEXT NOT NULL, Timestamp TEXT NOT NULL, "
            "PRIMARY KEY (FactKey, Resource))"
        )
        con.execute(f"CREATE TABLE IF NOT EXISTS DocStore (FullPath TEXT PRIMARY KEY, {_DOCSTORE_COLUMNS})")
        con.execute(  # the chunked version of a stored original (Phase 2): derived from the file, rebuildable
            "CREATE TABLE IF NOT EXISTS DocChunks (FullPath TEXT NOT NULL, ChunkNo INTEGER NOT NULL, Heading TEXT NOT NULL, "
            "PageFrom INTEGER NULL, PageTo INTEGER NULL, Text TEXT NOT NULL, TextHash TEXT NOT NULL, PRIMARY KEY (FullPath, ChunkNo))"
        )
        con.execute(  # entity tags on chunks: the entity map of a stored original (rule or LLM-fallback tags)
            "CREATE TABLE IF NOT EXISTS DocChunkTags (FullPath TEXT NOT NULL, ChunkNo INTEGER NOT NULL, Entity TEXT NOT NULL, "
            "Origin TEXT NOT NULL, Score INTEGER NOT NULL, Evidence TEXT NOT NULL, PRIMARY KEY (FullPath, ChunkNo, Entity))"
        )
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


def write_contribution(key: str, resource: str, value: str, hashcode: str, chunks_hash: str | None, description: str | None,
                       generated_by: str, timestamp: str) -> None:
    """Insert or replace what `resource` contributes to the fact `key` (one transaction)."""
    with closing(connect()) as con, con:
        con.execute("INSERT OR REPLACE INTO FactContributions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (key, resource, value, hashcode, chunks_hash, description, generated_by, timestamp))


def delete_contribution(key: str, resource: str) -> None:
    """Remove what `resource` contributed to the fact `key`, if anything."""
    with closing(connect()) as con, con:
        con.execute("DELETE FROM FactContributions WHERE FactKey = ? AND Resource = ?", (key, resource))


def get_contribution(key: str, resource: str) -> dict | None:
    """The contribution of `resource` to the fact `key`, or None."""
    with closing(connect()) as con:
        row = con.execute("SELECT * FROM FactContributions WHERE FactKey = ? AND Resource = ?", (key, resource)).fetchone()
    return dict(row) if row else None


def list_contributions(key: str | None = None, resource: str | None = None) -> list[dict]:
    """Contributions ordered by fact key and resource; filtered by fact key and/or contributing resource."""
    clauses, params = [], []
    if key is not None:
        clauses.append("FactKey = ?")
        params.append(key)
    if resource is not None:
        clauses.append("Resource = ?")
        params.append(resource)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with closing(connect()) as con:
        rows = con.execute(f"SELECT * FROM FactContributions{where} ORDER BY FactKey, Resource", params).fetchall()
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


def list_index_rows() -> list[dict]:
    """All FactIndex rows ordered by key (the Vector column is raw float32 bytes)."""
    with closing(connect()) as con:
        rows = con.execute("SELECT * FROM FactIndex ORDER BY FactKey").fetchall()
    return [dict(row) for row in rows]


def replace_index(upserts: list[tuple[str, str, str, int, bytes]], delete_keys: list[str]) -> None:
    """Apply an index rebuild in one transaction: upsert (FactKey, TextHash, EmbedModel, Dim, Vector) rows, delete stale keys."""
    with closing(connect()) as con, con:
        con.executemany("INSERT OR REPLACE INTO FactIndex VALUES (?, ?, ?, ?, ?)", upserts)
        con.executemany("DELETE FROM FactIndex WHERE FactKey = ?", [(key,) for key in delete_keys])


def find_docstore_rows(file_name: str | None = None, hashcode: str | None = None) -> list[dict]:
    """DocStore rows whose file name (last path segment) is `file_name` and/or whose hash is `hashcode`, ordered by path."""
    clauses, params = [], []
    if file_name is not None:
        clauses.append("(FullPath = ? OR FullPath LIKE ? ESCAPE '!')")
        params += [file_name, "%/" + _like_escape(file_name)]
    if hashcode is not None:
        clauses.append("Hashcode = ?")
        params.append(hashcode)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with closing(connect()) as con:
        rows = con.execute(f"SELECT * FROM DocStore{where} ORDER BY FullPath", params).fetchall()
    return [dict(row) for row in rows if file_name is None or row["FullPath"].rsplit("/", 1)[-1] == file_name]


def list_doc_chunks(full_path: str) -> list[dict]:
    """The stored chunks of one original, in order."""
    with closing(connect()) as con:
        rows = con.execute("SELECT * FROM DocChunks WHERE FullPath = ? ORDER BY ChunkNo", (full_path,)).fetchall()
    return [dict(row) for row in rows]


def list_doc_chunk_tags(full_path: str) -> list[dict]:
    """The entity tags on one original's chunks, ordered by chunk then entity."""
    with closing(connect()) as con:
        rows = con.execute("SELECT * FROM DocChunkTags WHERE FullPath = ? ORDER BY ChunkNo, Entity", (full_path,)).fetchall()
    return [dict(row) for row in rows]


def commit_ingested(full_path: str, hashcode: str, timestamp: str, chunks: list[tuple], tags: list[tuple]) -> tuple[str, int, list[dict]]:
    """Record an ingested original in one transaction: the DocStore row (NEW / SAME / CHANGED as in write_docstore_row, history on
    CHANGED) and its chunks and tags, replacing any earlier ones. `chunks` are (ChunkNo, Heading, PageFrom, PageTo, Text, TextHash);
    `tags` are (ChunkNo, Entity, Origin, Score, Evidence). Returns (action, version, the chunks stored before, for change detection).
    """
    with closing(connect()) as con, con:
        before = [dict(row) for row in con.execute("SELECT * FROM DocChunks WHERE FullPath = ? ORDER BY ChunkNo", (full_path,))]
        row = con.execute("SELECT Hashcode, Version FROM DocStore WHERE FullPath = ?", (full_path,)).fetchone()
        if row is None:
            con.execute("INSERT INTO DocStore VALUES (?, ?, 1, ?)", (full_path, hashcode, timestamp))
            action, version = "NEW", 1
        elif row["Hashcode"] == hashcode:
            action, version = "SAME", row["Version"]
        else:
            version = row["Version"] + 1
            con.execute("UPDATE DocStore SET Hashcode = ?, Version = ?, Timestamp = ? WHERE FullPath = ?", (hashcode, version, timestamp, full_path))
            con.execute("INSERT INTO DocStoreHistory VALUES (?, ?, ?, ?)", (full_path, hashcode, version, timestamp))
            action = "CHANGED"
        con.execute("DELETE FROM DocChunks WHERE FullPath = ?", (full_path,))
        con.execute("DELETE FROM DocChunkTags WHERE FullPath = ?", (full_path,))
        con.executemany("INSERT INTO DocChunks VALUES (?, ?, ?, ?, ?, ?, ?)", [(full_path, *chunk) for chunk in chunks])
        con.executemany("INSERT INTO DocChunkTags VALUES (?, ?, ?, ?, ?, ?)", [(full_path, *tag) for tag in tags])
    return action, version, before
