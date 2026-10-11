"""The bundle's root index.md (OKF section 8): the only frontmatter an index may carry is okf_version; one section per scope."""
from pathlib import Path

from docfactory.bundle.file_io import put_text
from docfactory.bundle.paths import fact_relpath
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


def write_index(root: Path, records: list[FactRecord]) -> None:
    """(Re)write index.md from `records`; untouched when it is already current."""
    put_text(root / INDEX_FILE, index_text(records))
