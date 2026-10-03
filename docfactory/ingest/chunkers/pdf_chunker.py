"""PDF -> element stream (see ingest/chunking.py), read with pdfplumber from the original file.

- Tables are found per page and read row by row, so an identifier stays with its statement (`FR-85. | The system SHALL ...`); empty
  cells are dropped and the first row of every table is marked as a header row.
- Text outside tables is read line by line with its font size. The body size is the most common size; a line clearly larger is a
  heading. A numbered heading (`3.1.1. Title`, `2.Overall Description`) gets its level from the numbering. When the document has
  numbered headings, larger unnumbered lines are never headings (the cover title block, words inside diagrams): they stay text.
- Table-of-contents lines (dot leaders), lone page numbers and lines repeated on most pages (running headers/footers) are dropped.
- Consecutive lines with a small vertical gap and the same size are joined into one paragraph.
- Symbol-font bullets (private-use characters such as U+F0B7) become '-'.
"""
import collections
import re
from pathlib import Path

import pdfplumber

HEADING_DELTA = 0.75  # points above the body size that make a line a heading
_NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)(?:\.\s*|\s+)([A-Za-z].*)$")  # "3.1.1. Title", "2.Overall"; not "3rd-Party"
_TOC = re.compile(r"\.{5,}\s*\d+\s*$")
_PAGE_NUMBER = re.compile(r"^\d{1,4}$")
_PRIVATE_USE = re.compile(r"[\uf000-\uf8ff]")


def _mode(values: list[float]) -> float:
    return collections.Counter(values).most_common(1)[0][0] if values else 0.0


def _inside(line: dict, boxes: list[tuple]) -> bool:
    x, y = (line["x0"] + line["x1"]) / 2, (line["top"] + line["bottom"]) / 2
    return any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in boxes)


def _read_pages(path: Path) -> list[list[tuple]]:
    """Per page, in top-to-bottom order: ("line", top, bottom, size, text) and ("table", top, rows)."""
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.find_tables()
            boxes = [t.bbox for t in tables]
            items = []
            for line in page.extract_text_lines(return_chars=True):
                text = _PRIVATE_USE.sub("-", line["text"]).strip()
                if not text or _inside(line, boxes):
                    continue
                size = _mode([round(c["size"], 1) for c in line["chars"] if c["text"].strip()])
                items.append(("line", line["top"], line["bottom"], size, text))
            for table in tables:
                rows = [[" ".join(_PRIVATE_USE.sub("-", cell or "").split()) for cell in row] for row in table.extract()]
                items.append(("table", table.bbox[1], [[cell for cell in row if cell] for row in rows]))
            pages.append(sorted(items, key=lambda item: item[1]))
    return pages


def pdf_elements(path: Path) -> list[tuple]:
    pages = _read_pages(path)
    lines = [item for page in pages for item in page if item[0] == "line"]
    repeated = collections.Counter(re.sub(r"\d+", "#", item[4]) for item in lines)
    running = {text for text, count in repeated.items() if len(pages) >= 4 and count >= len(pages) * 0.6}

    def kept(item) -> bool:
        text = item[4]
        return not (_TOC.search(text) or _PAGE_NUMBER.match(text) or re.sub(r"\d+", "#", text) in running)

    # body size: weighted by characters over paragraph-like lines (headings are short; in a short document they could outweigh the body)
    candidates = [item for item in lines if kept(item) and len(item[4]) >= 40] or [item for item in lines if kept(item)]
    body_size = _mode([item[3] for item in candidates for _ in range(len(item[4]))])
    is_heading = lambda item: item[3] >= body_size + HEADING_DELTA  # noqa: E731
    has_numbered = any(is_heading(item) and _NUMBERED.match(item[4]) for item in lines if kept(item))

    elements: list[tuple] = []
    paragraph: list[str] = []
    last = None  # (page, bottom, size) of the previous text line

    def flush(page_no: int) -> None:
        if paragraph:
            elements.append(("text", " ".join(paragraph), page_no))
            paragraph.clear()

    for page_no, items in enumerate(pages, start=1):
        for item in items:
            if item[0] == "table":
                flush(page_no)
                last = None
                for index, row in enumerate(item[2]):
                    if row:
                        elements.append(("header" if index == 0 else "row", " | ".join(row), page_no))
                continue
            if not kept(item):
                continue
            _, top, bottom, size, text = item
            numbered = _NUMBERED.match(text)
            if is_heading(item) and (numbered or not has_numbered):
                flush(page_no)
                last = None
                if numbered:
                    level = numbered.group(1).count(".") + 1
                    elements.append(("heading", level, f"{numbered.group(1)}. {numbered.group(2).strip()}", page_no))
                else:
                    elements.append(("heading", 1, text, page_no))
                continue
            close = last is not None and last[0] == page_no and last[2] == size and top - last[1] < (bottom - top) * 0.9
            if not close:
                flush(page_no)
            paragraph.append(text)
            last = (page_no, bottom, size)
        flush(page_no)
    return elements
