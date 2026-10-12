"""The recognition tool package: one single-tool package per recognition call (least privilege).

- `submit_recognition` (package `recognition`): the entities one window of a document discusses, the relationships it states between them,
  and which knowledge facts each of its chunks informs.
The tool checks the answer against the window and returns feedback the model can act on. It refuses: a type outside the vocabulary (or a
badly written `proposed:` type, or an identifier type such as Requirement), a chunk number that is not in the window, an entity none of whose
names appears in the window text, a `same_as` that is not in the catalog or names an entity of another type (allowed only for a listed
promotion, e.g. a Role that is a SupportContact, see `type_vocabulary.PROMOTIONS`), two entities with the same name, a relationship whose ends are
neither entities of the answer nor of the catalog (or that relates an entity to itself), an unknown relationship kind, and a chunk topic
outside the taggable facts. An accepted answer is appended to the list the package was built with. It writes nothing.
"""
from typing import Annotated

from pydantic import BaseModel, Field, WithJsonSchema

from docfactory.bundle.fact_registry import taggable_entity_names
from docfactory.entitymodels.items.relation_kind import RelationKind
from docfactory.extract.grounding import grounded, identity_in_text, normalize
from docfactory.models.chunk_topic import ChunkTopic
from docfactory.models.entity_record import EntityRecord
from docfactory.models.recognized_entity import RecognizedEntity
from docfactory.models.recognized_relation import RecognizedRelation
from docfactory.recognize.type_vocabulary import can_promote, type_problem
from docfactory.tools.schema_slim import inline_refs
from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry

RECOGNITION_PACKAGE_NAME = "recognition"
RECOGNITION_TOOL_NAMES = ["submit_recognition"]
KINDS = {kind.value for kind in RelationKind}

Accepted = list[tuple[list[RecognizedEntity], list[RecognizedRelation], list[ChunkTopic]]]


def _array_schema(model: type[BaseModel]) -> dict:
    schema = model.model_json_schema()
    return {"type": "array", "items": inline_refs(schema, schema.get("$defs", {}))}


def _named_in(entity: RecognizedEntity, text: str) -> bool:
    return any(identity_in_text(name, text) or grounded(name, text) for name in [entity.name, *entity.aliases])


def _identities(entities: list[RecognizedEntity], catalog: list[EntityRecord]) -> dict[str, str]:
    """Normalized name -> the entity it names (an answer entity's name, or a catalog id): names, aliases and catalog ids all resolve."""
    found: dict[str, str] = {}
    for record in catalog:
        for name in [record.entity_id, record.name, *record.aliases]:
            found.setdefault(normalize(name), record.entity_id)
    for entity in entities:
        identity = entity.same_as or f"answer:{normalize(entity.name)}"
        for name in [entity.name, *entity.aliases]:
            found[normalize(name)] = identity
    return found


def recognition_errors(entities: list[RecognizedEntity], relations: list[RecognizedRelation], topics: list[ChunkTopic],
                       text: str, chunk_nos: list[int], catalog: list[EntityRecord]) -> list[str]:
    """What is wrong with one answer for a window (`text`, its `chunk_nos`, the `catalog` it was shown); empty when it can be accepted."""
    errors: list[str] = []
    window = set(chunk_nos)
    catalog_types = {e.entity_id: e.type for e in catalog}
    catalog_ids = set(catalog_types)
    seen: set[str] = set()
    for entity in entities:
        label = f"entity {entity.name!r}"
        problem = type_problem(entity.type)
        if problem:
            errors.append(f"{label}: {problem}")
        if not _named_in(entity, text):
            errors.append(f"{label}: neither its name nor an alias appears in the chunks; use the name the document writes")
        if entity.same_as is not None and entity.same_as not in catalog_ids:
            errors.append(f"{label}: same_as {entity.same_as!r} is not an entity id of the catalog; leave same_as out unless it names a catalog id")
        elif entity.same_as is not None and not problem:
            other = catalog_types[entity.same_as]
            if other != entity.type and not can_promote(other, entity.type):
                errors.append(f"{label}: same_as {entity.same_as!r} is a {other}, but you typed this a {entity.type}; if it is really the same thing "
                              f"use type {other}, otherwise it is a different entity: leave same_as out")
        outside = sorted(set(entity.chunks) - window)
        if outside:
            errors.append(f"{label}: chunks {outside} are not in this window; use only {sorted(window)}")
        if normalize(entity.name) in seen:
            errors.append(f"{label}: listed twice; give each entity once, with all its chunks and aliases")
        seen.add(normalize(entity.name))
    known = _identities(entities, catalog)
    for relation in relations:
        label = f"relation {relation.source!r} {relation.relation} {relation.target!r}"
        missing = [end for end in (relation.source, relation.target) if normalize(end) not in known]
        if missing:
            errors.append(f"{label}: {', '.join(repr(m) for m in missing)} is neither an entity of your answer nor of the catalog; add the entity or leave the relation out")
        elif known[normalize(relation.source)] == known[normalize(relation.target)]:
            errors.append(f"{label}: an entity cannot relate to itself")
        if relation.kind and relation.kind not in KINDS:
            errors.append(f"{label}: kind {relation.kind!r} is not one of {sorted(KINDS)}; leave kind empty when none fits")
        outside = sorted(set(relation.chunks) - window)
        if outside:
            errors.append(f"{label}: chunks {outside} are not in this window")
    facts = set(taggable_entity_names())
    for topic in topics:
        if topic.chunk_no not in window:
            errors.append(f"topic of chunk {topic.chunk_no}: that chunk is not in this window")
        unknown = sorted(set(topic.facts) - facts)
        if unknown:
            errors.append(f"topic of chunk {topic.chunk_no}: {unknown} are not knowledge facts; use only {sorted(facts)}")
    return errors


def _submit_tool(text: str, chunk_nos: list[int], catalog: list[EntityRecord], accepted: Accepted):
    entities_type = Annotated[list[RecognizedEntity], WithJsonSchema(_array_schema(RecognizedEntity)),
                              Field(description="Every entity the chunks discuss, once each, with its type, canonical name, aliases and chunks. [] when none.")]
    relations_type = Annotated[list[RecognizedRelation], WithJsonSchema(_array_schema(RecognizedRelation)),
                               Field(description="Every relationship the chunks state between two entities, as a verb phrase. [] when none.")]
    topics_type = Annotated[list[ChunkTopic], WithJsonSchema(_array_schema(ChunkTopic)),
                            Field(description="For each chunk that informs knowledge facts, which ones. Chunks that inform none may be left out.")]

    def submit_recognition(entities: entities_type, relations: relations_type = [], topics: topics_type = []) -> dict:  # noqa: B006 (copied by pydantic)
        errors = recognition_errors(entities, relations, topics, text, chunk_nos, catalog)
        if errors:
            return {"ok": False, "errors": errors}
        accepted.append((list(entities), list(relations), list(topics)))
        return {"ok": True, "entities": len(entities), "relations": len(relations), "topics": len(topics)}

    return submit_recognition


def recognition_package(text: str, chunk_nos: list[int], catalog: list[EntityRecord], accepted: Accepted) -> ToolPackage:
    """The only tool of one recognition call over a window (`text`, its `chunk_nos`) shown with `catalog`; accepted answers go to `accepted`."""
    registry = ToolRegistry()
    registry.register(Tool(_submit_tool(text, chunk_nos, catalog, accepted),
                           "Submit the entities, relationships and chunk topics of these chunks. Call it once; if it returns errors, fix exactly what they name and call again."))
    return ToolPackage(RECOGNITION_PACKAGE_NAME, registry, RECOGNITION_TOOL_NAMES)
