"""Deterministic tagging of chunks with the entities they inform, from the ontology signals (docfactory/ontology/signals.json).

Per chunk and entity a score is added up:
- heading term in the chunk's own (deepest) heading: 4; in an ancestor heading (inherited by sub-sections): 3;
- identifier pattern found in the text (e.g. FR-01): 4;
- keywords: 1 per distinct keyword found in the text, at most 3.
An entity tags the chunk when it scores at least THRESHOLD **and** has a strong signal (a heading or an identifier): keywords alone
never tag, they only add to the score, so a chunk with nothing but loose vocabulary goes to the LLM fallback instead of a guess. A
chunk can carry several entities. Matching is case-insensitive on word boundaries, a heading term also matches its plural ('service
level agreement' matches 'Service Level Agreements'), and the longest match wins: in 'Non-Functional Requirements' the term 'non-functional requirements' matches and the
shorter 'functional requirements' inside it does not. A chunk no entity reaches is unmapped (the LLM fallback looks at those).
"""
import re

from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.entity_signals import EntitySignals

THRESHOLD = 3
OWN_HEADING, ANCESTOR_HEADING, IDENTIFIER, KEYWORD, KEYWORD_CAP = 4, 3, 4, 1, 3
ORIGIN = "rule"
_PART = re.compile(r"\s*\(part \d+\)$")


def _term(term: str, plural: bool = False) -> re.Pattern:
    body = re.escape(term).replace(r"\ ", r"[\s-]+") + ("s?" if plural else "")
    return re.compile(r"(?<![\w-])" + body + r"(?![\w-])", re.IGNORECASE)


def _heading_matches(segment: str, signals: list[EntitySignals]) -> set[str]:
    """Entities whose heading terms match one heading segment, longest match first; a match inside a longer match does not count."""
    found = []  # (start, end, entity)
    for entry in signals:
        for term in entry.heading_terms:
            found += [(m.start(), m.end(), entry.entity) for m in _term(term, plural=True).finditer(segment)]
    found.sort(key=lambda f: (f[0], -(f[1] - f[0])))
    kept: list[tuple[int, int, str]] = []
    for start, end, entity in found:
        if not any(k[0] <= start and end <= k[1] and (k[1] - k[0]) > (end - start) for k in kept):
            kept.append((start, end, entity))
    return {entity for _, _, entity in kept}


def tag_chunk(chunk: DocChunk, signals: list[EntitySignals]) -> list[ChunkTag]:
    """The rule tags of one chunk, ordered by score (highest first), then entity name."""
    segments = _PART.sub("", chunk.heading).split(" > ")
    own = _heading_matches(segments[-1], signals)
    ancestors = set().union(*(_heading_matches(s, signals) for s in segments[:-1])) if len(segments) > 1 else set()
    tags = []
    for entry in signals:
        score, evidence, strong = 0, [], False
        if entry.entity in own:
            score, strong = score + OWN_HEADING, True
            evidence.append(f"heading '{segments[-1]}'")
        elif entry.entity in ancestors:
            score, strong = score + ANCESTOR_HEADING, True
            evidence.append("parent heading")
        ids = [m.group(0) for p in entry.id_patterns for m in re.finditer(p, chunk.text)]
        if ids:
            score, strong = score + IDENTIFIER, True
            evidence.append(f"ids {ids[0]}" + (f"..{ids[-1]} ({len(ids)})" if len(ids) > 1 else ""))
        words = [k for k in entry.keywords if _term(k).search(chunk.text)]
        if words:
            score += min(len(words), KEYWORD_CAP) * KEYWORD
            evidence.append("keywords " + ", ".join(words[:KEYWORD_CAP]))
        if strong and score >= THRESHOLD:
            tags.append(ChunkTag(chunk_no=chunk.chunk_no, entity=entry.entity, origin=ORIGIN, score=score, evidence="; ".join(evidence)))
    return sorted(tags, key=lambda t: (-t.score, t.entity))


def tag_chunks(chunks: list[DocChunk], signals: list[EntitySignals]) -> tuple[list[ChunkTag], list[int]]:
    """(all rule tags, numbers of the chunks no entity reached)."""
    tags, unmapped = [], []
    for chunk in chunks:
        found = tag_chunk(chunk, signals)
        tags += found
        if not found:
            unmapped.append(chunk.chunk_no)
    return tags, unmapped


def entity_map(tags: list[ChunkTag]) -> dict[str, list[int]]:
    """Entity -> the chunk numbers tagged with it, ascending; entities in first-seen order."""
    result: dict[str, list[int]] = {}
    for tag in sorted(tags, key=lambda t: t.chunk_no):
        result.setdefault(tag.entity, [])
        if tag.chunk_no not in result[tag.entity]:
            result[tag.entity].append(tag.chunk_no)
    return result
