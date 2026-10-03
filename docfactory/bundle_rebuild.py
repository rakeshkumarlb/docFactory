"""Regenerates every OKF bundle file from the database (the files are views; this restores deleted or stale ones).

    python -m docfactory.bundle_rebuild

Each file is the stored YmlFrontmatter plus the body rendered from the stored Value (in model field order, found through the key's saver). Facts saved before Phase 3 have no frontmatter yet
and are skipped: save them again with metadata (the seed scripts do).
"""
import json
import sys

from docfactory import db
from docfactory.bundle import file_text, write_file
from docfactory.okf_body import render_body
from docfactory.saver_resolution import ordered_value


def rebuild() -> tuple[int, int, list[str]]:
    """(files written, files already current, keys skipped for lack of frontmatter)."""
    written = current = 0
    skipped = []
    for row in db.list_rows("KnowledgeFacts"):
        if not row["YmlFrontmatter"] or not row["FilePath"]:
            skipped.append(row["FactKey"])
            continue
        title = _title(row["YmlFrontmatter"]) or row["FactKey"]
        if write_file(row["FilePath"], file_text(row["YmlFrontmatter"], render_body(title, ordered_value(row["FactKey"], row["Value"])))):
            written += 1
        else:
            current += 1
    return written, current, skipped


def _title(frontmatter: str) -> str | None:
    """The `title` line of our own frontmatter (a JSON-quoted scalar)."""
    for line in frontmatter.splitlines():
        if line.startswith("title: "):
            return json.loads(line[len("title: "):])
    return None


def main() -> int:
    written, current, skipped = rebuild()
    print(f"{written} written, {current} already current, {len(skipped)} skipped (no frontmatter)")
    for key in skipped:
        print(f"  skipped {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
