"""Merging recognitions into the entity graph, and resolving names to entities."""
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.entity_record import EntityRecord
from docfactory.models.file_recognition import FileRecognition
from docfactory.models.recognized_entity import RecognizedEntity
from docfactory.models.recognized_relation import RecognizedRelation
from docfactory.models.source_chunk import SourceChunk
from docfactory.models.window_recognition import WindowRecognition
from docfactory.recognize.entity_merge import merge_entities, slug, type_folder
from docfactory.recognize.entity_resolver import EntityResolver, name_key

A, B = "App/references/a.md", "App/references/b.md"


def recognition(resource, entities, relations=()):
    window = WindowRecognition(window_hash="0" * 64, chunk_nos=[1, 2], entities=entities, relations=list(relations))
    data = [window.model_dump(mode="json")]
    return FileRecognition(resource=resource, windows=[window], hashcode=sha256_hex(canonical_json(data)), generated_by="t/1", timestamp="2026-01-01T00:00:00Z")


def ent(name, type_="Component", **kw):
    return RecognizedEntity(name=name, type=type_, chunks=kw.pop("chunks", [1]), **kw)


OUTLINES = {A: {1: SourceChunk(chunk_no=1, heading="4. Components", text_hash="a" * 64)}}


def test_name_key():
    assert name_key("The Matching-Engine") == name_key("matching engine")
    assert name_key("Environments") == name_key("environment")
    assert name_key("RB-01") == "rb 01"


def test_resolver_finds_by_id_name_and_alias_within_a_type():
    record = EntityRecord(entity_id="Component/identity-service", scope="App", type="Component", name="Identity Service", aliases=["Keycloak"])
    resolver = EntityResolver([record])
    assert resolver.find("Component/identity-service") is record
    assert resolver.find("keycloak", "Component") is record
    assert resolver.find("Keycloak", "Tool") is None
    assert resolver.find("Keycloak") is record


def test_slug_and_type_folder():
    assert slug("Matching Engine (v2)") == "matching-engine-v2"
    assert type_folder("proposed:Certificate") == "Proposed-Certificate"
    assert type_folder("Component") == "Component"


def test_mentions_in_several_originals_become_one_entity():
    graph, notes = merge_entities("App", [
        recognition(A, [ent("Identity Service", aliases=["Keycloak"], summary="Old summary.")]),
        recognition(B, [ent("Keycloak", summary="Issues tokens.", chunks=[2])]),
    ], OUTLINES)
    assert notes == [] and len(graph) == 1
    record = graph[0]
    assert record.entity_id == "Component/identity-service" and record.name == "Identity Service"  # the oldest mention names it
    assert record.aliases == ["Keycloak"] and record.summary == "Issues tokens."  # the newest summary wins
    assert [(e.resource, e.chunk_no, e.heading) for e in record.evidence] == [(A, 1, "4. Components"), (B, 2, "")]


def test_same_name_different_type_stays_separate_and_ids_do_not_clash():
    graph, _ = merge_entities("App", [recognition(A, [ent("Service Desk", "Team"), ent("Service Desk", "SupportContact")])], {})
    assert sorted(r.entity_id for r in graph) == ["SupportContact/service-desk", "Team/service-desk"]


def test_same_as_overrides_name_matching():
    first = recognition(A, [ent("Primary Database", "DataStore")])
    second = recognition(B, [ent("PostgreSQL 16", "DataStore", same_as="DataStore/primary-database")])
    graph, _ = merge_entities("App", [first, second], {})
    assert [(r.entity_id, r.aliases) for r in graph] == [("DataStore/primary-database", ["PostgreSQL 16"])]


def test_relations_resolve_across_originals_and_are_kept_once_with_every_source():
    first = recognition(A, [ent("Matching Engine"), ent("Search Index", "DataStore")],
                       [RecognizedRelation(source="Matching Engine", target="Search Index", relation="depends on", kind="depends_on")])
    second = recognition(B, [ent("Matching Engine")],
                        [RecognizedRelation(source="matching engine", target="Search Index", relation="Depends on"),
                         RecognizedRelation(source="Matching Engine", target="Billing", relation="uses")])
    graph, notes = merge_entities("App", [first, second], {})
    engine = next(r for r in graph if r.name == "Matching Engine")
    assert [(l.target, l.relation, l.kind, l.resources) for l in engine.links] == [("DataStore/search-index", "depends on", "depends_on", [A, B])]
    assert len(notes) == 1 and "'Billing' is no entity" in notes[0]


def test_merge_is_deterministic():
    recs = [recognition(A, [ent("X"), ent("Y", "DataStore")]), recognition(B, [ent("Z")])]
    assert merge_entities("App", recs, {}) == merge_entities("App", recs, {})
