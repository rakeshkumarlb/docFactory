"""Plain text and markdown -> element stream (see ingest/chunking.py).

Markdown headings (`#`..`######`) and short numbered lines (`3.1 Title`) are headings; blank lines separate paragraphs; markdown table
rows (`| a | b |`) are rows, the first of a table a header row (the `---` separator line is dropped). A file without headings is cut
into smaller paragraph-sized chunks by the assembler.
"""
import re
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".text", ".csv", ".log"}
_MARKDOWN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
_NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+([A-Z][^.]{1,80})$")
_TABLE_ROW = re.compile(r"^\|(.+)\|$")
_SEPARATOR = re.compile(r"^\|?\s*:?-{3,}")


def text_elements(path: Path) -> list[tuple]:
    elements: list[tuple] = []
    paragraph: list[str] = []
    in_table = False

    def flush() -> None:
        if paragraph:
            elements.append(("text", " ".join(paragraph), None))
            paragraph.clear()

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            flush()
            in_table = False
            continue
        if _SEPARATOR.match(line):
            continue
        markdown, numbered, row = _MARKDOWN.match(line), _NUMBERED.match(line), _TABLE_ROW.match(line)
        if markdown:
            flush()
            elements.append(("heading", len(markdown.group(1)), markdown.group(2), None))
        elif numbered:
            flush()
            elements.append(("heading", numbered.group(1).count(".") + 1, f"{numbered.group(1)}. {numbered.group(2)}", None))
        elif row:
            flush()
            cells = [cell.strip() for cell in row.group(1).split("|") if cell.strip()]
            elements.append(("row" if in_table else "header", " | ".join(cells), None))
            in_table = True
        else:
            paragraph.append(line)
    flush()
    return elements
