"""Word (.docx) -> element stream (see ingest/chunking.py), read with python-docx in body order.

Paragraphs styled 'Heading N' are headings of level N ('Title' is level 1); tables are read row by row (cells merged across columns
repeat in python-docx, so consecutive identical cells are kept once); the first row of every table is a header row.
"""
import re
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

_HEADING_STYLE = re.compile(r"^Heading (\d)$")


def _row_cells(row) -> list[str]:
    cells: list[str] = []
    for cell in row.cells:
        text = " ".join(cell.text.split())
        if text and (not cells or cells[-1] != text):
            cells.append(text)
    return cells


def word_elements(path: Path) -> list[tuple]:
    document = Document(str(path))
    elements: list[tuple] = []
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            paragraph = Paragraph(child, document)
            text = " ".join(paragraph.text.split())
            if not text:
                continue
            style = paragraph.style.name if paragraph.style is not None else ""
            match = _HEADING_STYLE.match(style)
            if match or style == "Title":
                elements.append(("heading", int(match.group(1)) if match else 1, text, None))
            else:
                elements.append(("text", text, None))
        elif tag == "tbl":
            for index, row in enumerate(Table(child, document).rows):
                cells = _row_cells(row)
                if cells:
                    elements.append(("header" if index == 0 else "row", " | ".join(cells), None))
    return elements
