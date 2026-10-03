"""HTML -> element stream (see ingest/chunking.py), read with BeautifulSoup in document order.

h1-h6 are headings of that level; p, li, pre, dt, dd and blockquote are paragraphs; table rows are rows (the first row of a table is
a header row). An element nested inside another collected element (a p inside an li or a table cell) is not read twice. Script, style
and the head are ignored.
"""
from pathlib import Path

from bs4 import BeautifulSoup

_HEADINGS = {f"h{n}": n for n in range(1, 7)}
_BLOCKS = {"p", "li", "pre", "dt", "dd", "blockquote", "tr"}


def html_elements(path: Path) -> list[tuple]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    elements: list[tuple] = []
    collected = []
    for tag in soup.find_all([*_HEADINGS, *_BLOCKS]):
        if any(parent in collected for parent in tag.parents):
            continue
        collected.append(tag)
        if tag.name in _HEADINGS:
            elements.append(("heading", _HEADINGS[tag.name], " ".join(tag.get_text(" ").split()), None))
        elif tag.name == "tr":
            cells = [" ".join(cell.get_text(" ").split()) for cell in tag.find_all(["th", "td"])]
            cells = [cell for cell in cells if cell]
            if cells:
                table = tag.find_parent("table")
                first = table is not None and table.find("tr") is tag
                elements.append(("header" if first else "row", " | ".join(cells), None))
        else:
            elements.append(("text", " ".join(tag.get_text(" ").split()), None))
    return elements
