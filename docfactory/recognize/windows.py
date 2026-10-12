"""Cut a document's chunks into recognition windows. Deterministic, no LLM.

A window is a run of whole sections in document order whose text stays within a word budget (`word_cap()`, env DOCFACTORY_WORD_CAP,
default 2000 words, sized for a 16k-token context with the prompt, vocabulary and catalog): usually two or three sections. A section
is a chunk together with its parts (a long section that ingestion split into 'heading (part 2)', ...); sections are never split
across windows unless one alone exceeds the budget, and then it gets windows of its own (its parts packed in order, a part over the
budget alone), so a long section takes the whole window. The window hash identifies what a window's recognition was based on, so an
unchanged window is never sent to the model again.
"""
import os
import re

from docfactory.extract.batching import chunks_hash
from docfactory.models.doc_chunk import DocChunk

WORD_CAP_ENV = "DOCFACTORY_WORD_CAP"
DEFAULT_WORD_CAP = 2000
MAX_OUTLINE_LINES = 80
_PART = re.compile(r"\s*\(part \d+\)$")


def word_cap() -> int:
    """The word budget of one window: env DOCFACTORY_WORD_CAP, else 2000."""
    return int(os.environ.get(WORD_CAP_ENV) or DEFAULT_WORD_CAP)


def words(chunk: DocChunk) -> int:
    """The number of words of a chunk (its heading trail counts too: the model reads it)."""
    return len(chunk.heading.split()) + len(chunk.text.split())


def section_of(chunk: DocChunk) -> str:
    """The section a chunk belongs to: its heading trail without ' (part n)'."""
    return _PART.sub("", chunk.heading)


def _sections(chunks: list[DocChunk]) -> list[list[DocChunk]]:
    sections: list[list[DocChunk]] = []
    for chunk in sorted(chunks, key=lambda c: c.chunk_no):
        if sections and section_of(sections[-1][-1]) == section_of(chunk) and _PART.search(chunk.heading):
            sections[-1].append(chunk)
        else:
            sections.append([chunk])
    return sections


def _pack(chunks: list[DocChunk], cap: int) -> list[list[DocChunk]]:
    """The chunks of one oversized section in consecutive windows of at most `cap` words; a chunk over the cap is a window of its own."""
    windows: list[list[DocChunk]] = []
    size = 0
    for chunk in chunks:
        if windows and size + words(chunk) <= cap:
            windows[-1].append(chunk)
            size += words(chunk)
        else:
            windows.append([chunk])
            size = words(chunk)
    return windows


def build_windows(chunks: list[DocChunk], cap: int | None = None) -> list[list[DocChunk]]:
    """The chunks (any order) as windows of whole sections in document order, each within `cap` words (see the module docstring)."""
    cap = cap or word_cap()
    windows: list[list[DocChunk]] = []
    current: list[DocChunk] = []
    size = 0
    for section in _sections(chunks):
        length = sum(words(c) for c in section)
        if length > cap:
            if current:
                windows.append(current)
                current, size = [], 0
            windows += _pack(section, cap)
        elif current and size + length > cap:
            windows.append(current)
            current, size = list(section), length
        else:
            current += section
            size += length
    if current:
        windows.append(current)
    return windows


def window_hash(window: list[DocChunk]) -> str:
    """SHA-256 over the window's chunk headings and texts: changes exactly when what the window shows the model changes."""
    return chunks_hash(window)


def outline_text(chunks: list[DocChunk]) -> str:
    """The document's outline for the prompt: each section's heading trail once, in order (at most 80 lines, then '...')."""
    seen: list[str] = []
    for chunk in sorted(chunks, key=lambda c: c.chunk_no):
        if section_of(chunk) not in seen:
            seen.append(section_of(chunk))
    lines = [f"- {heading}" for heading in seen[:MAX_OUTLINE_LINES]]
    return "\n".join(lines + (["- ..."] if len(seen) > MAX_OUTLINE_LINES else []))
