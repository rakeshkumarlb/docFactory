#!/usr/bin/env python
"""Generate the MissingInfo file for a document and mark missing fields in the document.

For every required field that is missing or partial:
  - assigns a stable question id  Q-<doc_id>-<nn>  (nn = the field's position in the template)
  - rewrites a still-empty body to `MISSING (see Q-...)`
  - writes <doc>-MissingInfo.md with one entry per question (default question = the field's hint)
The agent may then improve the wording of each `Question:` line, but must not change ids.
An existing MissingInfo file is never overwritten (use --force) so recorded answers are safe.

Usage: missing_info.py DOC.md [--force]
"""
import argparse
import sys
from pathlib import Path

from common import COMMENT_RE, parse_frontmatter, read_text, rel, split_sections, write_text
from completeness import field_status


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    doc = Path(a.doc)
    text = read_text(doc)
    meta, body = parse_frontmatter(text)
    doc_id = meta.get("doc_id", doc.stem)
    lines = body.splitlines()
    secs = [s for s in split_sections(lines) if s.field is not None]
    entries, edits = [], []
    for n, s in enumerate(secs, 1):
        st, issue = field_status(s.body, s.field.get("na", "no"))
        if st not in ("missing", "partial"):
            continue
        if s.field.get("required") != "yes":
            if st == "missing" and "{{FILL}}" in "\n".join(s.body):
                edits.append((s, "MISSING (optional - no question raised)"))
            continue
        qid = f"Q-{doc_id}-{n:02d}"
        entries.append((qid, s, st, issue))
        if st == "missing":
            edits.append((s, f"MISSING (see {qid})"))

    # rewrite doc bodies bottom-up so indexes stay valid
    for s, marker in sorted(edits, key=lambda e: -e[0].field_line):
        first = s.field_line + 1
        last = s.end
        lines[first:last] = [marker, ""] if last < len(lines) else [marker]
    new_body = "\n".join(lines) + "\n"
    front = text[: len(text) - len(body)]
    write_text(doc, front + new_body)

    mi_path = doc.with_name(doc.stem + "-MissingInfo.md")
    if mi_path.exists() and not a.force:
        print(f"{mi_path} exists; not overwritten ({len(entries)} open question(s) in doc)")
        return 0
    out = [f"# {doc_id} - Missing information", "",
           f"Document: {rel(doc)}",
           f"Template: {meta.get('template')} v{meta.get('template_version')}", "",
           f"To answer: fill in each `Answer:` line, then save the file into `incoming/` "
           f"starting with the line `MissingInfo-Ref: {doc_id}`. Do not change the Q- ids.", ""]
    for qid, s, st, issue in entries:
        hint = s.field.get("hint", "")
        out += [f"## {qid}  (field: {s.field['id']} - {s.title.strip()})",
                f"Status: {st.upper()}" + (f" ({issue})" if issue else ""),
                f"Hint: {hint}",
                f"Question: {hint or 'Please provide: ' + s.title.strip()}",
                f"Suggested source: {s.field.get('source') or 'ask document owner'}",
                "Answer:", ""]
    write_text(mi_path, "\n".join(out))
    print(f"wrote {mi_path} with {len(entries)} question(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
