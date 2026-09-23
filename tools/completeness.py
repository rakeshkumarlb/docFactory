#!/usr/bin/env python
"""Compute completeness of a generated document from its field directives.

Field status (from the text under each `<!-- field ... -->` directive):
  missing  empty, {{FILL}}, or starts with MISSING
  na       starts with "N/A" followed by a reason  (only where the field says na=allowed)
  partial  starts with PARTIAL   (counts 0.5)
  filled   anything else
Completeness % = (filled + 0.5*partial) / (required fields - required N/A fields).
Optional fields are reported separately and never lower the percentage.

Usage: completeness.py DOC.md [--json] [--write] [--min N]
"""
import argparse
import json
import re
import sys

from common import COMMENT_RE, dump_frontmatter, parse_frontmatter, read_text, split_sections, write_text

NA_RE = re.compile(r"^[*_\s]*N/?A\b[\s*_:—–-]*(.*)", re.I | re.S)


def field_status(body_lines, na_mode):
    text = COMMENT_RE.sub("", "\n".join(body_lines)).strip()
    if not text or "{{FILL}}" in text or re.match(r"^[*_\s]*MISSING\b", text, re.I):
        return "missing", None
    m = NA_RE.match(text)
    if m:
        if na_mode != "allowed":
            return "missing", "N/A used but this field does not allow N/A"
        if not m.group(1).strip():
            return "missing", "N/A given without a reason"
        return "na", None
    if re.match(r"^[*_\s]*PARTIAL\b", text, re.I):
        return "partial", None
    return "filled", None


def analyze(text):
    meta, body = parse_frontmatter(text)
    fields = []
    for s in split_sections(body.splitlines()):
        if s.field is None:
            continue
        st, issue = field_status(s.body, s.field.get("na", "no"))
        fields.append({"id": s.field["id"], "title": s.title, "required": s.field.get("required") == "yes",
                       "na": s.field.get("na", "no"), "hint": s.field.get("hint", ""),
                       "source": s.field.get("source", ""), "status": st, "issue": issue})
    return meta, fields


def summarize(fields):
    req = [f for f in fields if f["required"]]
    cnt = {k: sum(1 for f in req if f["status"] == k) for k in ("filled", "partial", "na", "missing")}
    denom = len(req) - cnt["na"]
    pct = 100 if denom == 0 else round(100 * (cnt["filled"] + 0.5 * cnt["partial"]) / denom)
    opt = [f for f in fields if not f["required"]]
    return {"percent": pct, "required_total": len(req), **cnt,
            "optional_total": len(opt), "optional_filled": sum(1 for f in opt if f["status"] == "filled")}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true", help="update completeness in the document front matter")
    ap.add_argument("--min", type=int)
    a = ap.parse_args()
    text = read_text(a.doc)
    meta, fields = analyze(text)
    summ = summarize(fields)
    if a.write:
        meta["completeness"] = f"{summ['percent']}%"
        meta["completeness_detail"] = (f"filled={summ['filled']} partial={summ['partial']} "
                                       f"na={summ['na']} missing={summ['missing']} of {summ['required_total']} required")
        _, body = parse_frontmatter(text)
        write_text(a.doc, dump_frontmatter(meta) + body)
    if a.json:
        print(json.dumps({"summary": summ, "fields": fields}, indent=2))
    else:
        print(f"Completeness: {summ['percent']}%  (filled {summ['filled']}, partial {summ['partial']}, "
              f"N/A {summ['na']}, missing {summ['missing']} of {summ['required_total']} required; "
              f"optional filled {summ['optional_filled']}/{summ['optional_total']})")
        for f in fields:
            if f["required"] and f["status"] in ("missing", "partial") or f["issue"]:
                print(f"  {f['status'].upper():8} {f['id']}  {f['title']}" + (f"  [{f['issue']}]" if f["issue"] else ""))
    return 1 if a.min is not None and summ["percent"] < a.min else 0


if __name__ == "__main__":
    sys.exit(main())
