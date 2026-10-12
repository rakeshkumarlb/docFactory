"""The text an entity-centric extraction call sees for one entity: its own chunks in every original that discusses it, then the chunks of
the entities it is directly related to (one hop, both directions), within a word budget. Deterministic, no LLM.

A component's owner is often stated in the teams document, an alert's condition in the monitoring plan: gathering every place that discusses
the entity, from every original, is what lets one call fill the whole item. Own chunks come first (originals in the order given, chunks in
document order), neighbour chunks after them, each chunk once; chunks that no longer match their recorded hash are still used (the text
is re-derived from the original) but the entity is recognized again on the next recognition run anyway.
"""
from typing import Callable

from docfactory.models.doc_chunk import DocChunk
from docfactory.models.entity_record import EntityRecord
from docfactory.recognize.windows import word_cap, words

Chunks = Callable[[str], dict[int, DocChunk]]  # resource -> its chunks by number


def neighbours(entity: EntityRecord, graph: list[EntityRecord]) -> list[EntityRecord]:
    """The entities `entity` links to, then those linking to it, each once, in link order then id order."""
    by_id = {e.entity_id: e for e in graph}
    out = [by_id[link.target] for link in entity.links if link.target in by_id]
    out += [e for e in graph if any(link.target == entity.entity_id for link in e.links)]
    seen: set[str] = {entity.entity_id}
    return [e for e in out if e.entity_id not in seen and not seen.add(e.entity_id)]


def gather(entity: EntityRecord, graph: list[EntityRecord], chunks_of: Chunks, cap: int | None = None) -> list[tuple[str, DocChunk]]:
    """(resource, chunk) pairs for `entity`: its own evidence, then its neighbours' evidence, within `cap` words (own chunks always kept)."""
    cap = cap or word_cap()
    picked: list[tuple[str, DocChunk]] = []
    seen: set[tuple[str, int]] = set()
    size = 0
    for owner in [entity, *neighbours(entity, graph)]:
        for evidence in owner.evidence:
            key = (evidence.resource, evidence.chunk_no)
            chunk = chunks_of(evidence.resource).get(evidence.chunk_no)
            if chunk is None or key in seen:
                continue
            if owner is not entity and size + words(chunk) > cap:
                continue
            seen.add(key)
            picked.append((evidence.resource, chunk))
            size += words(chunk)
    return picked


def evidence_text(picked: list[tuple[str, DocChunk]]) -> str:
    """The text the model sees: each chunk as '[<file name>, chunk N] <heading trail>' followed by its text."""
    return "\n\n".join(f"[{resource.rsplit('/', 1)[-1]}, chunk {chunk.chunk_no}] {chunk.heading}\n{chunk.text}" for resource, chunk in picked)


def evidence_lines(picked: list[tuple[str, DocChunk]], own: EntityRecord) -> list[str]:
    """The item's `evidence` entries: '<file name>: <heading trail> (chunk N)' for the entity's own chunks, in order."""
    mine = {(e.resource, e.chunk_no) for e in own.evidence}
    return [f"{r.rsplit('/', 1)[-1]}: {c.heading} (chunk {c.chunk_no})" for r, c in picked if (r, c.chunk_no) in mine]
