#!/usr/bin/env python
"""Knowledge-base tool. The extraction agent PROPOSES; this script APPLIES, and only after human approval.

  kb.py submit review/<app>/<id>.json        validate + register a proposal, print it for review
  kb.py show <id>                            print a proposal
  kb.py apply <id> --approved-by NAME        apply an approved proposal (refuses stale/unapproved ones)
  kb.py reject <id> --by NAME [--note ..]    discard a proposal (source document is marked processed)
  kb.py resolve C-0001 --app A --keep new|existing --by NAME
  kb.py facts APP [--grep TEXT] [--all]      list facts with ids and files
  kb.py stats APP                            size per file, split suggestions
  kb.py reindex APP                          regenerate the file map in knowledge/APP/_index.md
  kb.py new-app APP

Proposal JSON:
  {"app": "kitchenhq", "source": "store/kitchenhq/docs/README.md", "summary": "...",
   "ops": [
     {"op": "add",      "file": "components/dbmcp/functional", "section": "Behaviour", "text": "...", "quote": "evidence"},
     {"op": "confirm",  "fact": "F-0007"},
     {"op": "refine",   "fact": "F-0007", "text": "full replacement text"},
     {"op": "conflict", "fact": "F-0007", "new_text": "...", "note": "why they disagree"},
     {"op": "obsolete", "fact": "F-0007", "reason": "..."} ]}

Knowledge layout: knowledge/<app>/_index.md, conflicts.md, history.md, <topic>.md and, for multi-component
apps, components/<component>/<topic>.md. A fact is one bullet:  - [F-0042] text — src: path; path
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import db
from common import KNOWLEDGE, REVIEW, ROOT, dump_frontmatter, parse_frontmatter, read_text, rel, write_text

APP_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
FACT_RE = re.compile(r"^- (?P<tilde>~~)?\[(?P<id>F-\d+)\] (?P<text>.*?)(?P<tail>~~ \(obsolete.*\)| — src: .*)?$")
SRC_SEP = " — src: "
MAX_LINES, MAX_FACTS = 300, 60
RESERVED = ("_index.md", "conflicts.md", "history.md")
OPS = {"add": ("file", "section", "text"), "confirm": ("fact",), "refine": ("fact", "text"),
       "conflict": ("fact", "new_text"), "obsolete": ("fact", "reason")}


def today():
    return datetime.date.today().isoformat()


def kb_dir(app):
    if not APP_RE.match(app):
        sys.exit(f"invalid app name {app!r} (use lowercase letters, digits, - _)")
    return KNOWLEDGE / app


def kb_files(app):
    return [p for p in sorted(kb_dir(app).rglob("*.md")) if p.name not in RESERVED]


def scan_facts(app):
    """{fact_id: (path, line_no, active, text, srcs)}"""
    out = {}
    for p in kb_files(app):
        for i, line in enumerate(read_text(p).splitlines()):
            m = FACT_RE.match(line)
            if m:
                srcs = []
                if m.group("tail") and m.group("tail").startswith(SRC_SEP):
                    srcs = [s.strip() for s in m.group("tail")[len(SRC_SEP):].split(";")]
                out[m.group("id")] = (p, i, not m.group("tilde"), m.group("text"), srcs)
    return out


class Files:
    def __init__(self):
        self.cache, self.touched = {}, set()

    def lines(self, path):
        if path not in self.cache:
            self.cache[path] = read_text(path).splitlines() if path.exists() else []
        return self.cache[path]

    def touch(self, path):
        self.touched.add(path)

    def save(self):
        for p in self.touched:
            lines = self.cache[p]
            text = "\n".join(lines) + "\n"
            if p.name not in RESERVED or p.name == "_index.md":
                meta, body = parse_frontmatter(text)
                if meta:
                    meta["updated"] = today()
                    text = dump_frontmatter(meta) + body
            write_text(p, text)


def new_topic_file(app, path):
    topic = path.stem
    title = topic.replace("-", " ").replace("_", " ").title()
    return ["---", f"app: {app}", f"topic: {topic}", "summary: ", f"updated: {today()}", "---", "", f"# {title}", ""]


def insert_fact(lines, section, fact_line):
    head = f"## {section}"
    idx = next((i for i, l in enumerate(lines) if l.strip().lower() == head.lower()), None)
    if idx is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines += [head, "", fact_line]
        return
    end = len(lines)
    for j in range(idx + 1, len(lines)):
        if re.match(r"^#{1,2}\s", lines[j]):
            end = j
            break
    k = end
    while k > idx + 1 and not lines[k - 1].strip():
        k -= 1
    lines.insert(k, fact_line)
    if k == idx + 1:
        lines.insert(k, "")


def fact_line(fid, text, srcs, tilde=False, tail=None):
    if tilde:
        return f"- ~~[{fid}] {text}~~ {tail}"
    return f"- [{fid}] {text}{SRC_SEP}{'; '.join(srcs)}" if srcs else f"- [{fid}] {text}"


# ---------------------------------------------------------------- proposals
def load_proposal(con, pid):
    row = con.execute("SELECT * FROM proposals WHERE id=?", (pid,)).fetchone()
    if not row:
        sys.exit(f"unknown proposal {pid}")
    return row, json.loads(read_text(ROOT / row["path"]))


def validate(prop):
    errs = []
    app = prop.get("app", "")
    if not APP_RE.match(app):
        errs.append(f"invalid app {app!r}")
        return errs
    if not prop.get("source"):
        errs.append("missing source")
    facts = scan_facts(app) if kb_dir(app).exists() else {}
    for n, op in enumerate(prop.get("ops", []), 1):
        kind = op.get("op")
        if kind not in OPS:
            errs.append(f"op {n}: unknown op {kind!r}")
            continue
        for k in OPS[kind]:
            if not str(op.get(k, "")).strip():
                errs.append(f"op {n} ({kind}): missing {k}")
        if kind == "add":
            f = op.get("file", "")
            if ".." in f or f.startswith("/") or f.endswith(RESERVED):
                errs.append(f"op {n}: bad file {f!r}")
        else:
            fid = op.get("fact")
            if fid and fid not in facts:
                errs.append(f"op {n} ({kind}): unknown fact {fid}")
            elif fid and not facts[fid][2]:
                errs.append(f"op {n} ({kind}): fact {fid} is already obsolete")
    return errs


def render(prop, pid, status="pending"):
    app = prop["app"]
    facts = scan_facts(app) if kb_dir(app).exists() else {}
    out = [f"# Proposal {pid}  [{status}]", "", f"App: {app}", f"Source: {prop['source']}",
           f"Summary: {prop.get('summary', '')}", "", f"{len(prop.get('ops', []))} operation(s):", ""]
    for n, op in enumerate(prop.get("ops", []), 1):
        k = op["op"]
        ex = facts.get(op.get("fact", ""))
        if k == "add":
            out.append(f"{n}. ADD to `{op['file']}` > {op['section']}\n   + {op['text']}" + (f"\n   evidence: \"{op['quote']}\"" if op.get("quote") else ""))
        elif k == "confirm":
            out.append(f"{n}. CONFIRM {op['fact']}: {ex[3] if ex else '?'}")
        elif k == "refine":
            out.append(f"{n}. REFINE {op['fact']}\n   - {ex[3] if ex else '?'}\n   + {op['text']}")
        elif k == "conflict":
            out.append(f"{n}. CONFLICT with {op['fact']} (NOT applied; goes to conflicts.md)\n   existing: {ex[3] if ex else '?'}\n   new:      {op['new_text']}\n   note: {op.get('note', '')}")
        elif k == "obsolete":
            out.append(f"{n}. OBSOLETE {op['fact']}: {ex[3] if ex else '?'}\n   reason: {op['reason']}")
    return "\n".join(out) + "\n"


def cmd_submit(con, path):
    p = Path(path)
    p = p if p.is_absolute() else ROOT / p
    prop = json.loads(read_text(p))
    errs = validate(prop)
    doc = con.execute("SELECT sha256 FROM documents WHERE path=? AND deleted=0", (prop.get("source"),)).fetchone()
    if not doc:
        errs.append(f"source {prop.get('source')!r} is not in the document store")
    if errs:
        print("PROPOSAL INVALID:\n  " + "\n  ".join(errs))
        sys.exit(1)
    pid = p.stem
    prop["id"], prop["source_sha"] = pid, doc["sha256"]
    write_text(p, json.dumps(prop, indent=2, ensure_ascii=False) + "\n")
    counts = {k: sum(1 for o in prop["ops"] if o["op"] == k) for k in OPS}
    con.execute("INSERT OR REPLACE INTO proposals(id,app,source_path,source_sha,path,status,created_at,n_add,n_confirm,n_refine,n_conflict,n_obsolete) "
                "VALUES(?,?,?,?,?,'pending',?,?,?,?,?,?)",
                (pid, prop["app"], prop["source"], doc["sha256"], rel(p), db.now(), counts["add"], counts["confirm"],
                 counts["refine"], counts["conflict"], counts["obsolete"]))
    text = render(prop, pid)
    write_text(p.with_suffix(".md"), text)
    print(text)
    print(f"Awaiting approval. To apply: kb.py apply {pid} --approved-by <name>")


def cmd_apply(con, pid, who):
    row, prop = load_proposal(con, pid)
    if row["status"] != "pending":
        sys.exit(f"proposal {pid} is {row['status']}, not pending")
    doc = con.execute("SELECT sha256 FROM documents WHERE path=?", (row["source_path"],)).fetchone()
    if not doc or doc["sha256"] != row["source_sha"]:
        sys.exit("source document changed since this proposal was made; re-run extraction (proposal is stale)")
    errs = validate(prop)
    if errs:
        sys.exit("proposal no longer valid:\n  " + "\n  ".join(errs))
    app, src = prop["app"], prop["source"]
    base = kb_dir(app)
    ensure_app(app)
    files, facts = Files(), scan_facts(app)
    hist = [f"- {today()} [{pid}] approved by {who}; source {src}"]
    counts = {k: 0 for k in OPS}

    def path_of(fid):
        return facts[fid][0]

    def edit(fid, transform):
        p = path_of(fid)
        lines = files.lines(p)
        i = next(i for i, l in enumerate(lines) if f"[{fid}]" in l and FACT_RE.match(l))
        lines[i] = transform(FACT_RE.match(lines[i]))
        files.touch(p)

    for op in prop["ops"]:
        kind = op["op"]
        counts[kind] += 1
        if kind == "add":
            fid = f"F-{db.next_counter(con, 'F:' + app):04d}"
            p = base / (op["file"] if op["file"].endswith(".md") else op["file"] + ".md")
            lines = files.lines(p)
            if not lines:
                lines.extend(new_topic_file(app, p))
            insert_fact(lines, op["section"], fact_line(fid, op["text"].strip(), [src]))
            files.touch(p)
            hist.append(f"  - added {fid} in {rel(p)}")
        elif kind in ("confirm", "refine"):
            fid = op["fact"]

            def tr(m, op=op, fid=fid):
                srcs = [s.strip() for s in (m.group("tail") or "")[len(SRC_SEP):].split(";") if s.strip()]
                if src not in srcs:
                    srcs.append(src)
                return fact_line(fid, op["text"].strip() if kind == "refine" else m.group("text"), srcs)
            if kind == "refine":
                hist.append(f"  - refined {fid}; was: {facts[fid][3]}")
            edit(fid, tr)
        elif kind == "conflict":
            cid = f"C-{db.next_counter(con, 'C:' + app):04d}"
            p = base / "conflicts.md"
            lines = files.lines(p)
            lines += ["", f"## {cid} (open)", f"- Existing-fact: {op['fact']} ({rel(facts[op['fact']][0])}): {facts[op['fact']][3]}",
                      f"- New-text: {op['new_text'].strip()}", f"- New-source: {src}", f"- Note: {op.get('note', '')}",
                      f"- Proposal: {pid}", f"- Resolve with: kb.py resolve {cid} --app {app} --keep new|existing --by <name>"]
            files.touch(p)
            hist.append(f"  - conflict {cid} against {op['fact']} (existing fact untouched)")
        elif kind == "obsolete":
            fid = op["fact"]
            edit(fid, lambda m, op=op: f"- ~~[{fid}] {m.group('text')}~~ (obsolete {today()}: {op['reason']}; src: {src})")
            hist.append(f"  - obsoleted {fid}: {op['reason']}")

    hp = base / "history.md"
    hl = files.lines(hp)
    if not hl:
        hl += ["# Change history", ""]
    hl += hist
    files.touch(hp)
    files.save()
    reindex(app)
    con.execute("UPDATE proposals SET status='applied', decided_at=?, decided_by=? WHERE id=?", (db.now(), who, pid))
    con.execute("UPDATE documents SET extracted_sha=?, extracted_at=? WHERE path=?", (row["source_sha"], db.now(), row["source_path"]))
    db.log_change(con, "KNOWLEDGE", app, src, None, row["source_sha"], None, None,
                  f"{pid} +{counts['add']} confirm {counts['confirm']} refine {counts['refine']} conflict {counts['conflict']} obsolete {counts['obsolete']} (approved by {who})", who)
    con.commit()
    print(f"applied {pid}: " + ", ".join(f"{k} {v}" for k, v in counts.items() if v))


def cmd_reject(con, pid, who, note):
    row, _ = load_proposal(con, pid)
    if row["status"] != "pending":
        sys.exit(f"proposal {pid} is {row['status']}, not pending")
    con.execute("UPDATE proposals SET status='rejected', decided_at=?, decided_by=? WHERE id=?", (db.now(), who, pid))
    con.execute("UPDATE documents SET extracted_sha=?, extracted_at=? WHERE path=?", (row["source_sha"], db.now(), row["source_path"]))
    db.log_change(con, "REJECT", row["app"], row["source_path"], None, row["source_sha"], None, None, f"{pid} rejected by {who}: {note or ''}", who)
    con.commit()
    print(f"rejected {pid}")


def cmd_resolve(con, cid, app, keep, who):
    p = kb_dir(app) / "conflicts.md"
    lines = read_text(p).splitlines()
    i = next((i for i, l in enumerate(lines) if l.startswith(f"## {cid} (open)")), None)
    if i is None:
        sys.exit(f"{cid} not found or not open")
    block = {}
    for l in lines[i + 1:]:
        if l.startswith("## "):
            break
        m = re.match(r"^- ([\w-]+): (.*)$", l)
        if m:
            block[m.group(1)] = m.group(2)
    lines[i] = f"## {cid} (resolved {today()}: kept {keep} by {who})"
    files = Files()
    files.cache[p] = lines
    files.touch(p)
    if keep == "new":
        fid = block["Existing-fact"].split()[0]
        facts = scan_facts(app)
        fp, _, _, _, srcs = facts[fid]
        ll = files.lines(fp)
        idx = next(k for k, l in enumerate(ll) if f"[{fid}]" in l and FACT_RE.match(l))
        ns = srcs + ([block["New-source"]] if block["New-source"] not in srcs else [])
        ll[idx] = fact_line(fid, block["New-text"], ns)
        files.touch(fp)
        hp = kb_dir(app) / "history.md"
        files.lines(hp).append(f"- {today()} [{cid}] resolved by {who}: {fid} replaced; was: {facts[fid][3]}")
        files.touch(hp)
    else:
        hp = kb_dir(app) / "history.md"
        files.lines(hp).append(f"- {today()} [{cid}] resolved by {who}: kept existing")
        files.touch(hp)
    files.save()
    reindex(app)
    db.log_change(con, "RESOLVE", app, None, note=f"{cid} kept {keep} by {who}", actor=who)
    con.commit()
    print(f"resolved {cid} (kept {keep})")


# ---------------------------------------------------------------- app layout
def ensure_app(app):
    base = kb_dir(app)
    if (base / "_index.md").exists():
        return
    write_text(base / "_index.md", f"---\napp: {app}\ntype: index\nupdated: {today()}\n---\n\n# {app}\n\n"
               "Short description of the application (2-4 lines). Read this file first, then only the topic files you need.\n\n"
               "<!-- BEGIN:filemap -->\n<!-- END:filemap -->\n")
    write_text(base / "conflicts.md", f"# Open and resolved conflicts for {app}\n")
    write_text(base / "history.md", "# Change history\n")


def file_stats(app):
    rows = []
    for p in kb_files(app):
        text = read_text(p)
        meta, _ = parse_frontmatter(text)
        active = obsolete = 0
        for line in text.splitlines():
            m = FACT_RE.match(line)
            if m:
                obsolete += 1 if m.group("tilde") else 0
                active += 0 if m.group("tilde") else 1
        rows.append({"path": p.relative_to(kb_dir(app)).as_posix(), "lines": len(text.splitlines()), "facts": active,
                     "obsolete": obsolete, "summary": meta.get("summary", ""),
                     "split": len(text.splitlines()) > MAX_LINES or active > MAX_FACTS})
    return rows


def open_conflicts(app):
    p = kb_dir(app) / "conflicts.md"
    return len(re.findall(r"^## C-\d+ \(open\)", read_text(p), re.M)) if p.exists() else 0


def reindex(app):
    ensure_app(app)
    p = kb_dir(app) / "_index.md"
    text = read_text(p)
    rows = file_stats(app)
    tab = ["| File | Facts | Lines | Summary |", "|---|---|---|---|"]
    for r in rows:
        flag = "  **(split suggested)**" if r["split"] else ""
        tab.append(f"| [{r['path']}]({r['path']}) | {r['facts']} | {r['lines']} | {r['summary']}{flag} |")
    tab += ["", f"Open conflicts: {open_conflicts(app)} ([conflicts.md](conflicts.md)). Change log: [history.md](history.md)."]
    block = "<!-- BEGIN:filemap -->\n" + "\n".join(tab) + "\n<!-- END:filemap -->"
    text = re.sub(r"<!-- BEGIN:filemap -->.*?<!-- END:filemap -->", lambda m: block, text, flags=re.S)
    meta, body = parse_frontmatter(text)
    if meta:
        meta["updated"] = today()
        text = dump_frontmatter(meta) + body
    write_text(p, text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit"); s.add_argument("path")
    s = sub.add_parser("show"); s.add_argument("id")
    s = sub.add_parser("apply"); s.add_argument("id"); s.add_argument("--approved-by", required=True)
    s = sub.add_parser("reject"); s.add_argument("id"); s.add_argument("--by", required=True); s.add_argument("--note")
    s = sub.add_parser("resolve"); s.add_argument("cid"); s.add_argument("--app", required=True)
    s.add_argument("--keep", choices=["new", "existing"], required=True); s.add_argument("--by", required=True)
    s = sub.add_parser("facts"); s.add_argument("app"); s.add_argument("--grep"); s.add_argument("--all", action="store_true")
    s = sub.add_parser("stats"); s.add_argument("app")
    s = sub.add_parser("reindex"); s.add_argument("app")
    s = sub.add_parser("new-app"); s.add_argument("app")
    a = ap.parse_args()
    con = db.connect()
    try:
        if a.cmd == "submit":
            cmd_submit(con, a.path)
        elif a.cmd == "show":
            row, prop = load_proposal(con, a.id)
            print(render(prop, a.id, row["status"]))
        elif a.cmd == "apply":
            cmd_apply(con, a.id, a.approved_by)
        elif a.cmd == "reject":
            cmd_reject(con, a.id, a.by, a.note)
        elif a.cmd == "resolve":
            cmd_resolve(con, a.cid, a.app, a.keep, a.by)
        elif a.cmd == "facts":
            for fid, (p, _, active, text, srcs) in sorted(scan_facts(a.app).items()):
                if (active or a.all) and (not a.grep or a.grep.lower() in text.lower()):
                    print(f"{fid}\t{p.relative_to(kb_dir(a.app)).as_posix()}\t{'' if active else '[obsolete] '}{text}")
        elif a.cmd == "stats":
            print(json.dumps(file_stats(a.app), indent=2))
        elif a.cmd == "reindex":
            reindex(a.app)
            print(f"reindexed {a.app}")
        elif a.cmd == "new-app":
            ensure_app(a.app)
            reindex(a.app)
            print(f"created knowledge/{a.app}/")
        con.commit()
    finally:
        con.close()


if __name__ == "__main__":
    main()
