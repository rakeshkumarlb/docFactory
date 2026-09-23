#!/usr/bin/env python
"""Move a file from incoming/ into the document store with dedupe, versioning, archive and logging.

  store_file.py --src incoming/X.md --app kitchenhq --category docs --name repo/agents/README.md
  store_file.py --src incoming/A.md --app kitchenhq --category answers --name A.md --answer-ref US123
  store_file.py --delete --app kitchenhq --category docs --name old.md --note "removed per call 12 Sep"
  store_file.py --src incoming/X.md --app _unclassified --category unsorted   (park a file for a human)

Result is one JSON line: {"action": "ADD|UPDATE|DUPLICATE|DELETE", "path": ..., "version": ..., ...}
  ADD        new path
  UPDATE     same path, different content: old version archived to store/_archive/, version + 1
  DUPLICATE  identical content already at that path: incoming copy discarded
  DELETE     archived and marked deleted (never physically lost)
"""
import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

import db
from common import ROOT, STORE, rel, sha256_file


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def archive(target, app, category, name, version):
    dest = STORE / "_archive" / app / category / f"{name}.v{version}.{stamp()}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(target), str(dest))
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src")
    ap.add_argument("--app", required=True)
    ap.add_argument("--category", required=True)
    ap.add_argument("--name")
    ap.add_argument("--answer-ref")
    ap.add_argument("--delete", action="store_true")
    ap.add_argument("--note")
    ap.add_argument("--actor", default="ingestion-agent")
    a = ap.parse_args()

    if not a.delete and not a.src:
        ap.error("--src required unless --delete")
    src = Path(a.src) if a.src else None
    if src and not src.is_absolute():
        src = ROOT / src
    name = (a.name or (src.name if src else None) or "").replace("\\", "/").strip("/")
    if not name or ".." in name.split("/"):
        ap.error("--name required and must not contain '..'")
    target = STORE / a.app / a.category / name
    tpath = rel(target)

    con = db.connect()
    try:
        row = con.execute("SELECT * FROM documents WHERE path=?", (tpath,)).fetchone()
        if a.delete:
            if not target.exists() or not row or row["deleted"]:
                print(json.dumps({"action": "ERROR", "error": f"not in store: {tpath}"}))
                return 1
            arch = archive(target, a.app, a.category, name, row["version"])
            con.execute("UPDATE documents SET deleted=1, updated_at=? WHERE path=?", (db.now(), tpath))
            db.log_change(con, "DELETE", a.app, tpath, row["sha256"], None, row["version"], rel(arch), a.note, a.actor)
            con.commit()
            print(json.dumps({"action": "DELETE", "path": tpath, "archived_to": rel(arch)}))
            return 0

        if not src.exists():
            print(json.dumps({"action": "ERROR", "error": f"source not found: {a.src}"}))
            return 1
        sha = sha256_file(src)
        size = src.stat().st_size
        is_ans = 1 if a.answer_ref else 0
        twin = con.execute("SELECT path FROM documents WHERE sha256=? AND deleted=0 AND path!=?", (sha, tpath)).fetchone()
        notes = a.note or ""
        if twin:
            notes = (notes + f" identical content also stored at {twin['path']}").strip()

        if row and not row["deleted"] and target.exists():
            if row["sha256"] == sha:
                src.unlink()
                db.log_change(con, "DUPLICATE", a.app, tpath, sha, sha, row["version"], None, notes, a.actor)
                con.commit()
                print(json.dumps({"action": "DUPLICATE", "path": tpath, "version": row["version"]}))
                return 0
            arch = archive(target, a.app, a.category, name, row["version"])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(target))
            ver = row["version"] + 1
            con.execute("UPDATE documents SET sha256=?, version=?, size=?, updated_at=?, is_answer=?, answer_ref=? WHERE path=?",
                        (sha, ver, size, db.now(), is_ans, a.answer_ref, tpath))
            db.log_change(con, "UPDATE", a.app, tpath, row["sha256"], sha, ver, rel(arch), notes, a.actor)
            action, extra = "UPDATE", {"archived_to": rel(arch)}
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(target))
            ver = (row["version"] + 1) if row else 1  # re-adding a deleted path continues its version count
            if row:
                con.execute("UPDATE documents SET sha256=?, version=?, size=?, deleted=0, updated_at=?, is_answer=?, answer_ref=?, "
                            "extracted_sha=NULL WHERE path=?", (sha, ver, size, db.now(), is_ans, a.answer_ref, tpath))
            else:
                con.execute("INSERT INTO documents(app,category,path,sha256,version,size,is_answer,answer_ref,created_at,updated_at) "
                            "VALUES(?,?,?,?,?,?,?,?,?,?)", (a.app, a.category, tpath, sha, ver, size, is_ans, a.answer_ref, db.now(), db.now()))
            db.log_change(con, "ADD", a.app, tpath, None, sha, ver, None, notes, a.actor)
            action, extra = "ADD", {}
        con.commit()
        print(json.dumps({"action": action, "path": tpath, "version": ver, **extra, **({"note": notes} if notes else {})}))
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
