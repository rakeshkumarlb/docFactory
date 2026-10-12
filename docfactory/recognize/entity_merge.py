"""Merge the recognitions of a scope's originals into its entity graph. Pure functions, deterministic, no LLM.

Recognitions are given oldest ingested original first. Per window, in order:
- an entity is matched to an entity already merged by its `same_as` id, else by its name or an alias within the same type; a match gains
  the new name (as an alias), aliases and evidence. The canonical name and id come from the first (oldest) mention, so ids stay stable as new
  documents arrive; the summary comes from the newest mention that gives one.
- an unmatched entity is new: id '<Type folder>/<slug of the name>' ('-2', '-3', ... on a clash).
Then every relationship is resolved by id, name or alias across all types (both ends must resolve, else it is reported) and kept once per
(target, verb phrase), with every original that states it. Evidence carries the chunk's heading and text hash from the Source outline.
"""
import re

from docfactory.extract.grounding import normalize
from docfactory.models.entity_evidence import EntityEvidence
from docfactory.models.entity_link import EntityLink
from docfactory.models.entity_record import EntityRecord
from docfactory.models.file_recognition import FileRecognition
from docfactory.models.source_chunk import SourceChunk
from docfactory.recognize.entity_resolver import EntityResolver, name_key
from docfactory.recognize.type_vocabulary import PROPOSED_PREFIX

MAX_SLUG = 60
Outlines = dict[str, dict[int, SourceChunk]]  # resource -> chunk number -> its outline entry


def type_folder(type_name: str) -> str:
    """The folder of a type under entities/: the type itself, or 'Proposed-<Name>' for 'proposed:<Name>'."""
    return "Proposed-" + type_name[len(PROPOSED_PREFIX):] if type_name.startswith(PROPOSED_PREFIX) else type_name


def slug(name: str) -> str:
    """A lower-case file-safe slug: 'Matching Engine (v2)' -> 'matching-engine-v2'."""
    return re.sub(r"[^a-z0-9]+", "-", normalize(name)).strip("-")[:MAX_SLUG].strip("-") or "entity"


def _new_id(type_name: str, name: str, taken: set[str]) -> str:
    base = f"{type_folder(type_name)}/{slug(name)}"
    candidate, n = base, 1
    while candidate in taken:
        n += 1
        candidate = f"{base}-{n}"
    return candidate


def _add_aliases(record: EntityRecord, names: list[str]) -> list[str]:
    known = {name_key(n) for n in [record.name, *record.aliases]}
    out = list(record.aliases)
    for name in names:
        if name_key(name) not in known:
            out.append(name)
            known.add(name_key(name))
    return out


def _evidence(resource: str, chunk_nos: list[int], outlines: Outlines) -> list[EntityEvidence]:
    outline = outlines.get(resource, {})
    return [EntityEvidence(resource=resource, chunk_no=n, heading=outline[n].heading if n in outline else "",
                           text_hash=outline[n].text_hash if n in outline else "") for n in chunk_nos]


def _union_evidence(old: list[EntityEvidence], new: list[EntityEvidence]) -> list[EntityEvidence]:
    seen = {(e.resource, e.chunk_no) for e in old}
    return old + [e for e in new if (e.resource, e.chunk_no) not in seen and not seen.add((e.resource, e.chunk_no))]


def merge_entities(scope: str, recognitions: list[FileRecognition], outlines: Outlines) -> tuple[list[EntityRecord], list[str]]:
    """(the entity graph of `scope`, notes on what could not be merged) from its recognitions, oldest original first."""
    resolver = EntityResolver()
    records: dict[str, EntityRecord] = {}
    summaries: dict[str, str] = {}
    notes: list[str] = []
    for recognition in recognitions:
        for window in recognition.windows:
            for found in window.entities:
                record = resolver.by_id.get(found.same_as) if found.same_as else None
                record = record or resolver.find(found.name, found.type) or next(
                    (r for a in found.aliases if (r := resolver.find(a, found.type))), None)
                evidence = _evidence(recognition.resource, found.chunks, outlines)
                if record is None:
                    entity_id = _new_id(found.type, found.name, set(records))
                    record = EntityRecord(entity_id=entity_id, scope=scope, type=found.type, name=found.name, aliases=[], evidence=[])
                record = record.model_copy(update={"aliases": _add_aliases(record, [found.name, *found.aliases]),
                                                   "evidence": _union_evidence(record.evidence, evidence)})
                records[record.entity_id] = record
                resolver.register(record)
                if found.summary.strip():
                    summaries[record.entity_id] = found.summary.strip()  # later (newer) originals overwrite
    links: dict[str, dict[tuple[str, str], EntityLink]] = {}
    for recognition in recognitions:
        for window in recognition.windows:
            for relation in window.relations:
                source, target = resolver.find(relation.source), resolver.find(relation.target)
                if source is None or target is None:
                    missing = relation.source if source is None else relation.target
                    notes.append(f"{recognition.resource}: relation {relation.source!r} {relation.relation} {relation.target!r} skipped: {missing!r} is no entity")
                    continue
                if source.entity_id == target.entity_id:
                    continue
                key = (target.entity_id, normalize(relation.relation))
                known = links.setdefault(source.entity_id, {})
                if key in known:
                    link = known[key]
                    resources = link.resources + ([recognition.resource] if recognition.resource not in link.resources else [])
                    known[key] = link.model_copy(update={"resources": resources, "kind": link.kind or relation.kind})
                else:
                    known[key] = EntityLink(target=target.entity_id, relation=relation.relation.strip(), kind=relation.kind, resources=[recognition.resource])
    merged = [record.model_copy(update={"summary": summaries.get(entity_id, ""), "links": list(links.get(entity_id, {}).values())})
              for entity_id, record in sorted(records.items())]
    return merged, notes
