#!/usr/bin/env python
"""Compose a document skeleton from a template's manifest + fragment files.

Generic: knows nothing about SRS/BRD/etc. A template is a folder templates/<TYPE>/ with
template.json listing section fragments. Fragments may pull in other fragments with
    <!-- include: relative/path.md shift=1 -->        (path relative to the including file;
                                                       '@/x' is relative to templates/)
and declare fillable fields with, directly under a heading:
    <!-- field id=srs.purpose required=yes na=allowed source=overview hint="..." -->

Usage:
  compose.py --list
  compose.py TYPE --check
  compose.py TYPE --out output/app/DOC-Title.md --app app --doc-id DOC1 --title "Title"
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

from common import (COMMENT_RE, FIELD_RE, HEADING_RE, INCLUDE_RE, ROOT, TEMPLATES, dump_frontmatter,
                    load_json, read_text, sha256_text, split_sections, write_text)

FIELD_KEYS_REQUIRED = ("id", "required", "na")


class TemplateError(Exception):
    pass


def _resolve(base_file, target):
    if target.startswith("@/"):
        return (TEMPLATES / target[2:]).resolve()
    return (base_file.parent / target).resolve()


def _shift_heading(line, shift):
    m = HEADING_RE.match(line)
    if not m or shift == 0:
        return line
    level = len(m.group(1)) + shift
    if not 1 <= level <= 6:
        raise TemplateError(f"heading level out of range after shift: {line!r}")
    return "#" * level + " " + m.group(2)


def expand(path, shift=0, stack=()):
    """Return the fragment's lines with includes expanded and headings shifted."""
    path = path.resolve()
    if path in stack:
        raise TemplateError("include cycle: " + " -> ".join(p.name for p in (*stack, path)))
    if not path.exists():
        raise TemplateError(f"missing fragment: {path}")
    out, fence = [], None
    for line in read_text(path).splitlines():
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            fence = None if fence == s[:3] else (fence or s[:3])
        m = None if fence else INCLUDE_RE.search(line)
        if m:
            child_shift = shift + int(m.group(2) or 0)
            out.extend(expand(_resolve(path, m.group(1)), child_shift, (*stack, path)))
        else:
            out.append(_shift_heading(line, shift) if not fence else line)
    return out


def load_manifest(ttype):
    mp = TEMPLATES / ttype / "template.json"
    if not mp.exists():
        raise TemplateError(f"unknown template {ttype!r} (no {mp})")
    man = load_json(mp)
    for k in ("type", "title", "version", "sections"):
        if k not in man:
            raise TemplateError(f"{mp}: missing key {k!r}")
    return man


def number_headings(lines):
    counters = [0] * 7
    out, fence = [], None
    for line in lines:
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            fence = None if fence == s[:3] else (fence or s[:3])
        m = None if fence else HEADING_RE.match(line)
        if m and len(m.group(1)) >= 2:
            lvl = len(m.group(1))
            counters[lvl] += 1
            for j in range(lvl + 1, 7):
                counters[j] = 0
            num = ".".join(str(c) for c in counters[2:lvl + 1])
            out.append(f"{m.group(1)} {num} {m.group(2)}")
        else:
            out.append(line)
    return out


def build_body(man):
    lines = []
    for entry in man["sections"]:
        if isinstance(entry, str):
            entry = {"path": entry}
        frag = _resolve(TEMPLATES / man["type"] / "template.json", entry["path"])
        lines.extend(expand(frag, int(entry.get("shift", 0))))
        lines.append("")
    if man.get("numbering"):
        lines = number_headings(lines)
    return lines


def validate(lines):
    """Template-level checks. Returns list of problems."""
    problems, seen = [], {}
    for s in split_sections(lines):
        if s.level == 0:
            continue
        if s.field is not None:
            missing = [k for k in FIELD_KEYS_REQUIRED if k not in s.field]
            if missing:
                problems.append(f"field under {s.title!r} lacks {missing}")
            fid = s.field.get("id")
            if fid in seen:
                problems.append(f"duplicate field id {fid!r} ({seen[fid]!r} and {s.title!r})")
            seen[fid] = s.title
            if s.field.get("required") not in ("yes", "no"):
                problems.append(f"{fid}: required must be yes|no")
            if s.field.get("na") not in ("allowed", "no"):
                problems.append(f"{fid}: na must be allowed|no")
            text = COMMENT_RE.sub("", "\n".join(s.body)).strip()
            if text:
                problems.append(f"{fid}: field sections must have no body text, found {text[:40]!r}")
    if not seen:
        problems.append("template defines no fields")
    return problems


def add_fill_markers(lines):
    """Insert {{FILL}} after each field directive."""
    out = []
    for line in lines:
        out.append(line)
        if FIELD_RE.search(line):
            out.append("{{FILL}}")
    return out


def compose(ttype, meta):
    man = load_manifest(ttype)
    lines = build_body(man)
    problems = validate(lines)
    if problems:
        raise TemplateError("; ".join(problems))
    body = "\n".join(add_fill_markers(lines)).rstrip() + "\n"
    thash = sha256_text(body)[:12]
    header = {
        "doc_id": meta.get("doc_id", "{{DOC_ID}}"),
        "title": meta.get("title", man["title"]),
        "app": meta.get("app", "{{APP}}"),
        "template": man["type"],
        "template_version": man["version"],
        "template_hash": thash,
        "generated": datetime.date.today().isoformat(),
        "status": "draft",
        "completeness": "0%",
    }
    return dump_frontmatter(header) + f"\n# {header['title']}\n\n" + body, man, thash


def list_templates():
    out = []
    for p in sorted(TEMPLATES.glob("*/template.json")):
        m = load_json(p)
        out.append((m["type"], m["version"], m["title"]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("type", nargs="?")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true", help="validate template only")
    ap.add_argument("--out")
    ap.add_argument("--app")
    ap.add_argument("--doc-id")
    ap.add_argument("--title")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    try:
        if a.list:
            for t, v, title in list_templates():
                print(f"{t}\tv{v}\t{title}")
            return 0
        if not a.type:
            ap.error("template type required")
        text, man, thash = compose(a.type, {"app": a.app, "doc_id": a.doc_id, "title": a.title})
        n_fields = len(re.findall(r"<!-- field ", text))
        if a.check or not a.out:
            if a.check:
                print(f"OK {man['type']} v{man['version']} hash={thash} fields={n_fields}")
            else:
                sys.stdout.write(text)
            return 0
        out = Path(a.out)
        out = out if out.is_absolute() else ROOT / out
        if out.exists() and not a.force:
            print(f"refusing to overwrite {out} (use --force)", file=sys.stderr)
            return 2
        write_text(out, text)
        print(json.dumps({"out": str(out), "template": man["type"], "version": man["version"],
                          "template_hash": thash, "fields": n_fields}))
        return 0
    except TemplateError as e:
        print(f"TEMPLATE ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
