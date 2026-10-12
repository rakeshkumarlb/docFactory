"""The bundle's index files (OKF section 8): the root index.md lists the facts by scope (its only frontmatter is okf_version); each scope folder has its own
index.md (no frontmatter) for progressive disclosure: its facts with their items, the relationship graph and the Sources of its originals."""
from pathlib import Path

from docfactory.bundle.file_io import put_text
from docfactory.bundle.paths import GRAPH_DIR, SOURCES_DIR, SUFFIX, fact_relpath
from docfactory.models.fact_record import FactRecord

INDEX_FILE = "index.md"
OKF_VERSION = "0.2"


def index_text(records: list[FactRecord]) -> str:
    """The index for `records`: facts grouped by scope (application or Shared), each as a link with its description."""
    lines = ["---", f'okf_version: "{OKF_VERSION}"', "---"]
    scope = None
    for record in sorted(records, key=lambda r: r.key):
        if record.key.split(".")[0] != scope:
            scope = record.key.split(".")[0]
            lines += ["", f"# {scope}", ""]
        entry = f"* [{record.title or record.key}](/{fact_relpath(record.key)})"
        lines.append(entry + (f" - {record.description}" if record.description else ""))
    return "\n".join(lines) + "\n"


def scope_index_text(root: Path, scope: str, records: list[FactRecord]) -> str:
    """The index of one scope folder: its facts (with the folder of their items when they have one), its relationship graph and its Sources."""
    lines = [f"# {scope}", "", "## Facts", ""]
    for record in sorted((r for r in records if r.key.split(".")[0] == scope), key=lambda r: r.key):
        path = fact_relpath(record.key)
        entry = f"* [{record.title or record.key}](/{path})" + (f" - {record.description}" if record.description else "")
        if (root / path.removesuffix(SUFFIX) / INDEX_FILE).is_file():
            entry += f" ([items](/{path.removesuffix(SUFFIX)}/))"
        lines.append(entry)
    graph = f"{scope}/{GRAPH_DIR}/relationships{SUFFIX}"
    if (root / graph).is_file():
        lines += ["", "## Relationships", "", f"* [Relationship graph](/{graph}) - how the concepts of {scope} relate to each other"]
    sources = sorted((root / scope / SOURCES_DIR).glob("*" + SUFFIX)) if (root / scope / SOURCES_DIR).is_dir() else []
    if sources:
        lines += ["", "## Sources", ""] + [f"* [{p.name.removesuffix(SUFFIX)}](/{scope}/{SOURCES_DIR}/{p.name.replace(' ', '%20')})" for p in sources]
    return "\n".join(lines) + "\n"


def write_index(root: Path, records: list[FactRecord]) -> None:
    """(Re)write the root index.md and the index.md of every scope folder that has facts from `records`; a file already current is untouched."""
    put_text(root / INDEX_FILE, index_text(records))
    for scope in sorted({r.key.split(".")[0] for r in records}):
        put_text(root / scope / INDEX_FILE, scope_index_text(root, scope, records))
