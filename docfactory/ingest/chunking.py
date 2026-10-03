"""Deterministic chunking of an original document into sections: `chunk_file(path)` picks the reader by file type.

Every reader turns its format into the same stream of elements, in document order:
  ("heading", level, title, page)  a section heading; level 1 is outermost
  ("text", text, page)             a paragraph
  ("header", text, page)           the first row of a table (column labels)
  ("row", text, page)              a table row, cells joined with ' | '
`assemble_chunks` turns the stream into DocChunks: one per section with a body, never splitting a section's element, with the heading
trail of the section. A table header row is kept once per section (repeats at page breaks are dropped). A section longer than
`max_chars` is split at element boundaries into parts. Same file in, same chunks out.
"""
import hashlib
from pathlib import Path

from docfactory.models.doc_chunk import DocChunk

MAX_CHARS = 4000
UNSTRUCTURED_MAX_CHARS = 1500  # a document without any heading is cut into smaller pieces
FRONT_MATTER = "Front matter"


def _chunk(chunk_no: int, heading: str, lines: list[str], pages: list[int]) -> DocChunk:
    text = "\n".join(lines)
    return DocChunk(chunk_no=chunk_no, heading=heading, page_from=min(pages) if pages else None, page_to=max(pages) if pages else None,
                    text=text, text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest())


def _split(lines: list[tuple[str, int | None]], max_chars: int) -> list[list[tuple[str, int | None]]]:
    """The body lines cut into parts of at most `max_chars` (a single longer line stays whole)."""
    parts, current, size = [], [], 0
    for line in lines:
        if current and size + len(line[0]) + 1 > max_chars:
            parts.append(current)
            current, size = [], 0
        current.append(line)
        size += len(line[0]) + 1
    if current:
        parts.append(current)
    return parts


def _title_block(elements: list[tuple]) -> list[tuple]:
    """Leading headings with no body and no sub-sections (a document title styled as a heading, followed by a heading of the same
    level) become front-matter text, so the title is kept in a chunk instead of vanishing with an empty section."""
    elements = list(elements)
    index = 0
    while (index + 1 < len(elements) and elements[index][0] == "heading" and elements[index + 1][0] == "heading"
           and elements[index + 1][1] <= elements[index][1]):
        _, _, title, page = elements[index]
        elements[index] = ("text", title, page)
        index += 1
    return elements


def assemble_chunks(elements: list[tuple], max_chars: int | None = None) -> list[DocChunk]:
    """DocChunks from an element stream (see the module docstring)."""
    elements = _title_block(elements)
    if max_chars is None:
        max_chars = MAX_CHARS if any(e[0] == "heading" for e in elements) else UNSTRUCTURED_MAX_CHARS
    sections: list[tuple[str, list[tuple[str, int | None]]]] = []
    trail: list[tuple[int, str]] = []
    body: list[tuple[str, int | None]] = []
    headers: set[str] = set()

    def close() -> None:
        if body:
            sections.append((" > ".join(title for _, title in trail) or FRONT_MATTER, list(body)))

    for element in elements:
        kind = element[0]
        if kind == "heading":
            close()
            body.clear()
            headers.clear()
            _, level, title, _ = element
            while trail and trail[-1][0] >= level:
                trail.pop()
            trail.append((level, title))
            continue
        _, text, page = element
        text = " ".join(text.split())
        if not text:
            continue
        if kind == "header":
            if text in headers:
                continue
            headers.add(text)
        body.append((text, page))
    close()

    chunks: list[DocChunk] = []
    for heading, lines in sections:
        parts = _split(lines, max_chars)
        for index, part in enumerate(parts, start=1):
            name = heading if len(parts) == 1 else f"{heading} (part {index})"
            chunks.append(_chunk(len(chunks) + 1, name, [t for t, _ in part], [p for _, p in part if p is not None]))
    return chunks


def chunk_file(path: Path) -> list[DocChunk]:
    """The chunks of an original file. An empty list means the file has no extractable text (e.g. a scanned PDF).

    Raises ValueError for a file type no reader handles.
    """
    from docfactory.ingest.chunkers import html_chunker, pdf_chunker, text_chunker, word_chunker

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return assemble_chunks(pdf_chunker.pdf_elements(path))
    if suffix == ".docx":
        return assemble_chunks(word_chunker.word_elements(path))
    if suffix in (".html", ".htm"):
        return assemble_chunks(html_chunker.html_elements(path))
    if suffix in text_chunker.TEXT_SUFFIXES:
        return assemble_chunks(text_chunker.text_elements(path))
    raise ValueError(f"no chunker for {suffix or 'files without an extension'}: {path.name}")
