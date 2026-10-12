"""Merge the recognitions of a scope's originals into its entity graph. Pure functions, deterministic, no LLM.

Recognitions are given oldest ingested original first. Per window, in order:
- an entity is matched to an entity already merged by its `same_as` id, else by its name or an alias within the same type; a match gains
  the new name (as an alias), aliases and evidence. The canonical name comes from the first (oldest) mention, so ids stay stable as new
  documents arrive; the summary comes from the newest mention that gives one. A `same_as` match with a more specific type (an item type over a
  graph-only type, e.g. a Role that a support guide calls a SupportContact) gives the entity that type.
- an unmatched entity is new.
- a leading document identifier of a name is an alias too: 'ADR-001 Use RabbitMQ' gets the alias 'ADR-001', 'RB-01 High API Error Rate' 'RB-01'.
Ids are given at the end, in order of first mention: '<Type folder>/<slug of the name>' ('-2', '-3', ... on a clash). Then every relationship
is resolved by id, name or alias across all types (both ends must resolve, else it is reported) and kept once per (target, verb phrase), with
every original that states it. Evidence carries the chunk's heading and text hash from the Source outline.
"""
import re

from docfactory.extract.grounding import normalize
from docfactory.models.entity_evidence import EntityEvidence
from docfactory.models.entity_link import EntityLink
from docfactory.models.entity_record import EntityRecord
from docfactory.models.file_recognition import FileRecognition
from docfactory.models.recognized_entity import RecognizedEntity
from docfactory.models.source_chunk import SourceChunk
from docfactory.recognize.entity_resolver import EntityResolver, name_key
from docfactory.recognize.type_vocabulary import PROPOSED_PREFIX, type_rank

MAX_SLUG = 60
Outlines = dict[str, dict[int, SourceChunk]]  # resource -> chunk number -> its outline entry
_LEADING_ID = re.compile(r"^((?:[A-Z][A-Za-z]*[-_ ]?)?\d+(?:\.\d+)*)[\s:.)\-–]+[A-Za-z]")  # an identifier, then a title starting with a letter


def type_folder(type_name: str) -> str:
    """The folder of a type under entities/: the type itself, or 'Proposed-<Name>' for 'proposed:<Name>'."""
    return "Proposed-" + type_name[len(PROPOSED_PREFIX):] if type_name.startswith(PROPOSED_PREFIX) else type_name


def slug(name: str) -> str:
    """A lower-case file-safe slug: 'Matching Engine (v2)' -> 'matching-engine-v2'."""
    return re.sub(r"[^a-z0-9]+", "-", normalize(name)).strip("-")[:MAX_SLUG].strip("-") or "entity"


def leading_identifier(name: str) -> str | None:
    """The document identifier a name starts with, if any: 'ADR-001 Use RabbitMQ' -> 'ADR-001', 'SOP 1.4 Restore' -> 'SOP 1.4', '1.3.0' -> None."""
    match = _LEADING_ID.match(name.strip())
    if not match or not re.search(r"[A-Za-z]", match.group(1)):
        return None
    return match.group(1)


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
        if name and name_key(name) not in known:
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


def _match(found: RecognizedEntity, resolver: EntityResolver) -> EntityRecord | None:
    if found.same_as and (same := resolver.find(found.same_as)) is not None:
        return same
    return resolver.find(found.name, found.type) or next((r for a in found.aliases if (r := resolver.find(a, found.type))), None)


def _merge_one(found: RecognizedEntity, record: EntityRecord | None, scope: str, provisional: str, evidence: list[EntityEvidence]) -> EntityRecord:
    names = [found.name, *found.aliases]
    names += [i for n in names if (i := leading_identifier(n))]
    if record is None:
        record = EntityRecord(entity_id=provisional, scope=scope, type=found.type, name=found.name)
    elif found.type != record.type and type_rank(found.type) > type_rank(record.type):
        record = record.model_copy(update={"type": found.type})
    return record.model_copy(update={"aliases": _add_aliases(record, names), "evidence": _union_evidence(record.evidence, evidence)})


def merge_entities(scope: str, recognitions: list[FileRecognition], outlines: Outlines) -> tuple[list[EntityRecord], list[str]]:
    """(the entity graph of `scope`, notes on what could not be merged) from its recognitions, oldest original first."""
    resolver = EntityResolver()
    order: list[str] = []  # provisional ids in order of first mention
    records: dict[str, EntityRecord] = {}
    summaries: dict[str, str] = {}
    for recognition in recognitions:
        for window in recognition.windows:
            for found in window.entities:
                match = _match(found, resolver)
                provisional = match.entity_id if match else _new_id(found.type, found.name, set(records))
                record = _merge_one(found, match, scope, provisional, _evidence(recognition.resource, found.chunks, outlines))
                if match is None:
                    order.append(provisional)
                records[provisional] = record
                resolver.register(record)
                if found.summary.strip():
                    summaries[provisional] = found.summary.strip()  # later (newer) originals overwrite
    final: dict[str, str] = {}
    for provisional in order:
        final[provisional] = _new_id(records[provisional].type, records[provisional].name, set(final.values()))
    links: dict[str, dict[tuple[str, str], EntityLink]] = {}
    notes: list[str] = []
    for recognition in recognitions:
        for window in recognition.windows:
            for relation in window.relations:
                source, target = resolver.find(relation.source), resolver.find(relation.target)
                if source is None or target is None:
                    missing = relation.source if source is None else relation.target
                    notes.append(f"{recognition.resource}: relation {relation.source!r} {relation.relation} {relation.target!r} skipped: {missing!r} is no entity")
                    continue
                source_id, target_id = final[source.entity_id], final[target.entity_id]
                if source_id == target_id:
                    continue
                key = (target_id, normalize(relation.relation))
                known = links.setdefault(source_id, {})
                if key in known:
                    link = known[key]
                    resources = link.resources + ([recognition.resource] if recognition.resource not in link.resources else [])
                    known[key] = link.model_copy(update={"resources": resources, "kind": link.kind or relation.kind})
                else:
                    known[key] = EntityLink(target=target_id, relation=relation.relation.strip(), kind=relation.kind, resources=[recognition.resource])
    merged = [records[p].model_copy(update={"entity_id": final[p], "summary": summaries.get(p, ""), "links": list(links.get(final[p], {}).values())})
              for p in order]
    return sorted(merged, key=lambda r: r.entity_id), notes
