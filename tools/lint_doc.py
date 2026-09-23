#!/usr/bin/env python
"""Verify a generated document still matches its template exactly.

Checks: same headings (ignoring numbering) and same field ids in the same order as the template
recomposed from the doc's `template:` front matter; template drift (hash); no leftover {{FILL}};
no invalid N/A; every link in the doc's Sources section resolves to a real file.

Usage: lint_doc.py DOC.md      exit 0 = clean, 1 = errors (warnings never fail)
"""
import re
import sys
from pathlib import Path

import compose
from common import ROOT, parse_frontmatter, read_text, split_sections, strip_number
from completeness import analyze

LINK_RE = re.compile(r"\]\(([^)#\s]+)")


def structure(body_text):
    return [(s.level, strip_number(s.title), (s.field or {}).get("id")) for s in split_sections(body_text.splitlines())
            if s.level > 0]


def main():
    doc = Path(sys.argv[1])
    text = read_text(doc)
    meta, body = parse_frontmatter(text)
    errors, warnings = [], []
    ttype = meta.get("template")
    if not ttype:
        print("ERROR: no template in front matter")
        return 1
    ref_text, man, thash = compose.compose(ttype, {})
    _, ref_body = parse_frontmatter(ref_text)
    if str(man["version"]) != meta.get("template_version"):
        warnings.append(f"template version changed: doc v{meta.get('template_version')} -> current v{man['version']}")
    elif thash != meta.get("template_hash"):
        warnings.append("template content changed since generation (same version, different hash)")

    ref, got = structure(ref_body), structure(body)
    # the doc's own '# Title' line is not part of the template
    got = [g for g in got if g[0] > 1 or g[2]]
    ref = [r for r in ref if r[0] > 1 or r[2]]
    if ref != got:
        ref_set, got_set = set(ref), set(got)
        for r in ref:
            if r not in got_set:
                errors.append(f"missing/changed section: {'#' * r[0]} {r[1]}" + (f" (field {r[2]})" if r[2] else ""))
        for g in got:
            if g not in ref_set:
                errors.append(f"unexpected/changed section: {'#' * g[0]} {g[1]}" + (f" (field {g[2]})" if g[2] else ""))
        if not errors:
            errors.append("sections are present but in a different order than the template")

    _, fields = analyze(text)
    for f in fields:
        if f["issue"]:
            errors.append(f"{f['id']}: {f['issue']}")
    left = text.count("{{FILL}}")
    if left:
        warnings.append(f"{left} unfilled {{{{FILL}}}} marker(s) - run missing_info.py")

    for s in split_sections(body.splitlines()):
        if s.field and s.field.get("id", "").endswith(".sources"):
            for link in LINK_RE.findall("\n".join(s.body)):
                if re.match(r"^[a-z]+://", link):
                    continue
                if not ((doc.parent / link).exists() or (ROOT / link).exists()):
                    errors.append(f"Sources link not found: {link}")

    for w in warnings:
        print("WARN:", w)
    for e in errors:
        print("ERROR:", e)
    print("LINT OK" if not errors else f"LINT FAILED ({len(errors)} error(s))")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
