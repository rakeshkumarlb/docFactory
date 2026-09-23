#!/usr/bin/env python
"""SQLite registry + change log for docFactory. Import it, or use the CLI.

CLI:
  db.py init
  db.py status                      counts + pending work
  db.py pending-extraction          store documents not yet extracted (new or changed)
  db.py find [--app A] [--category C] [--like TEXT]
  db.py history [--limit N]         recent change log
  db.py next-id PREFIX              next document id, e.g. US -> US1, US2 ...
  db.py register-output DOC.md      record a generated document and its sources (from its Sources links)
  db.py stale-outputs               generated docs whose source documents changed since generation
"""
import argparse
import datetime
import json
import re
import sqlite3
import sys
from pathlib import Path

from common import DB_PATH, ROOT, parse_frontmatter, read_text, rel, sha256_file

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY, app TEXT NOT NULL, category TEXT NOT NULL, path TEXT NOT NULL UNIQUE,
  sha256 TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, size INTEGER,
  is_answer INTEGER NOT NULL DEFAULT 0, answer_ref TEXT, deleted INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, extracted_sha TEXT, extracted_at TEXT);
CREATE TABLE IF NOT EXISTS changes (
  id INTEGER PRIMARY KEY, ts TEXT NOT NULL, action TEXT NOT NULL, app TEXT, doc_path TEXT,
  old_sha TEXT, new_sha TEXT, version INTEGER, archived_to TEXT, note TEXT, actor TEXT);
CREATE TABLE IF NOT EXISTS proposals (
  id TEXT PRIMARY KEY, app TEXT NOT NULL, source_path TEXT, source_sha TEXT, path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, decided_at TEXT, decided_by TEXT,
  n_add INTEGER DEFAULT 0, n_confirm INTEGER DEFAULT 0, n_refine INTEGER DEFAULT 0,
  n_conflict INTEGER DEFAULT 0, n_obsolete INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS outputs (
  doc_id TEXT PRIMARY KEY, app TEXT, template TEXT, template_version TEXT, template_hash TEXT,
  title TEXT, path TEXT, completeness INTEGER, generated_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS output_sources (
  doc_id TEXT NOT NULL, store_path TEXT NOT NULL, sha256 TEXT, PRIMARY KEY (doc_id, store_path));
"""


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def log_change(con, action, app=None, doc_path=None, old_sha=None, new_sha=None, version=None,
               archived_to=None, note=None, actor="agent"):
    con.execute("INSERT INTO changes(ts,action,app,doc_path,old_sha,new_sha,version,archived_to,note,actor) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (now(), action, app, doc_path, old_sha, new_sha, version, archived_to, note, actor))


def next_counter(con, name):
    row = con.execute("SELECT value FROM counters WHERE name=?", (name,)).fetchone()
    val = (row["value"] if row else 0) + 1
    con.execute("INSERT INTO counters(name,value) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value",
                (name, val))
    return val


def pending_extraction(con):
    return con.execute("SELECT * FROM documents WHERE deleted=0 AND app NOT LIKE '\\_%' ESCAPE '\\' "
                       "AND (extracted_sha IS NULL OR extracted_sha != sha256) ORDER BY app, path").fetchall()


def cmd_status(con):
    docs = con.execute("SELECT app, COUNT(*) n FROM documents WHERE deleted=0 GROUP BY app").fetchall()
    print("Documents per app:", {r["app"]: r["n"] for r in docs} or "none")
    print("Pending extraction:", len(pending_extraction(con)))
    for st in ("pending", "applied", "rejected"):
        print(f"Proposals {st}:", con.execute("SELECT COUNT(*) FROM proposals WHERE status=?", (st,)).fetchone()[0])
    print("Generated outputs:", con.execute("SELECT COUNT(*) FROM outputs").fetchone()[0])
    print("Stale outputs:", len(stale_outputs(con)))


def stale_outputs(con):
    out = []
    for o in con.execute("SELECT * FROM outputs").fetchall():
        for s in con.execute("SELECT * FROM output_sources WHERE doc_id=?", (o["doc_id"],)).fetchall():
            d = con.execute("SELECT sha256, deleted FROM documents WHERE path=?", (s["store_path"],)).fetchone()
            if d is None or d["deleted"] or d["sha256"] != s["sha256"]:
                out.append((o["doc_id"], o["path"], s["store_path"], "removed" if d is None or d["deleted"] else "changed"))
    return out


LINK_RE = re.compile(r"\]\(([^)#\s]+)")


def cmd_register_output(con, doc):
    from completeness import analyze, summarize
    doc = Path(doc)
    text = read_text(doc)
    meta, body = parse_frontmatter(text)
    doc_id = meta.get("doc_id") or doc.stem
    pct = summarize(analyze(text)[1])["percent"]
    con.execute("""INSERT INTO outputs(doc_id,app,template,template_version,template_hash,title,path,completeness,generated_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(doc_id) DO UPDATE SET template_version=excluded.template_version,
                   template_hash=excluded.template_hash,title=excluded.title,path=excluded.path,
                   completeness=excluded.completeness,updated_at=excluded.updated_at""",
                (doc_id, meta.get("app"), meta.get("template"), meta.get("template_version"), meta.get("template_hash"),
                 meta.get("title"), rel(doc), pct, meta.get("generated", now()), now()))
    con.execute("DELETE FROM output_sources WHERE doc_id=?", (doc_id,))
    n = 0
    for link in set(LINK_RE.findall(body)):
        target = (doc.parent / link).resolve()
        if not target.exists():
            target = (ROOT / link).resolve()
        if target.exists() and (ROOT / "store").resolve() in target.parents:
            con.execute("INSERT OR REPLACE INTO output_sources VALUES(?,?,?)",
                        (doc_id, rel(target), sha256_file(target)))
            n += 1
    log_change(con, "OUTPUT", app=meta.get("app"), doc_path=rel(doc), note=f"{doc_id} completeness {pct}% sources {n}")
    print(json.dumps({"doc_id": doc_id, "completeness": pct, "sources": n}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("pending-extraction")
    sub.add_parser("stale-outputs")
    f = sub.add_parser("find")
    f.add_argument("--app"); f.add_argument("--category"); f.add_argument("--like")
    h = sub.add_parser("history")
    h.add_argument("--limit", type=int, default=20)
    n = sub.add_parser("next-id")
    n.add_argument("prefix")
    r = sub.add_parser("register-output")
    r.add_argument("doc")
    a = ap.parse_args()
    con = connect()
    try:
        if a.cmd == "init":
            print(f"initialised {rel(DB_PATH)}")
        elif a.cmd == "status":
            cmd_status(con)
        elif a.cmd == "pending-extraction":
            print(json.dumps([{"app": d["app"], "path": d["path"], "version": d["version"], "is_answer": d["is_answer"],
                               "answer_ref": d["answer_ref"]} for d in pending_extraction(con)], indent=2))
        elif a.cmd == "stale-outputs":
            print(json.dumps([{"doc_id": d, "path": p, "source": s, "why": w} for d, p, s, w in stale_outputs(con)], indent=2))
        elif a.cmd == "find":
            q, args = "SELECT app,category,path,version,deleted FROM documents WHERE 1=1", []
            for col, val in (("app", a.app), ("category", a.category)):
                if val:
                    q += f" AND {col}=?"; args.append(val)
            if a.like:
                q += " AND path LIKE ?"; args.append(f"%{a.like}%")
            print(json.dumps([dict(r) for r in con.execute(q + " ORDER BY path", args)], indent=2))
        elif a.cmd == "history":
            for r in con.execute("SELECT * FROM changes ORDER BY id DESC LIMIT ?", (a.limit,)):
                print(f"{r['ts']} {r['action']:9} {r['app'] or '-':12} {r['doc_path'] or ''} v{r['version'] or ''} {r['note'] or ''}")
        elif a.cmd == "next-id":
            print(f"{a.prefix}{next_counter(con, 'DOC:' + a.prefix)}")
        elif a.cmd == "register-output":
            cmd_register_output(con, a.doc)
        con.commit()
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
