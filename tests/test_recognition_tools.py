"""The single-tool recognition package: what it accepts and every refusal."""
from docfactory.models.entity_record import EntityRecord
from docfactory.tools.recognition_tools import RECOGNITION_TOOL_NAMES, recognition_package

TEXT = ("[chunk 3] 4. Components > 4.2 Matching Engine\nThe Matching Engine (AI Engine) depends on the Search Index (OpenSearch).\n\n"
        "[chunk 4] 5. Environments\nProduction runs on the jm-prod cluster.")
CHUNKS = [3, 4]
CATALOG = [EntityRecord(entity_id="DataStore/search-index", scope="App", type="DataStore", name="Search Index", aliases=["OpenSearch"])]
ENGINE = {"name": "Matching Engine", "type": "Component", "aliases": ["AI Engine"], "summary": "Ranks candidates.", "chunks": [3]}
INDEX = {"name": "Search Index", "type": "DataStore", "same_as": "DataStore/search-index", "chunks": [3]}


def call(arguments, catalog=CATALOG):
    accepted = []
    result = recognition_package(TEXT, CHUNKS, catalog, accepted).call("submit_recognition", arguments)
    return result, accepted


def test_the_package_holds_exactly_one_tool():
    assert RECOGNITION_TOOL_NAMES == ["submit_recognition"]
    tool = recognition_package(TEXT, CHUNKS, [], []).tools()[0]
    assert tool.name == "submit_recognition"
    schema = tool.input_schema()
    assert schema["required"] == ["entities"] and "$defs" not in str(schema)


def test_an_accepted_answer_is_appended():
    relation = {"source": "Matching Engine", "target": "Search Index", "relation": "depends on", "kind": "depends_on", "chunks": [3]}
    result, accepted = call({"entities": [ENGINE, INDEX], "relations": [relation], "topics": [{"chunk_no": 4, "facts": ["Environments"]}]})
    assert result == {"ok": True, "entities": 2, "relations": 1, "topics": 1}
    entities, relations, topics = accepted[0]
    assert [e.name for e in entities] == ["Matching Engine", "Search Index"] and relations[0].kind == "depends_on" and topics[0].facts == ["Environments"]


def test_empty_lists_are_legal():
    assert call({"entities": []}) == ({"ok": True, "entities": 0, "relations": 0, "topics": 0}, [([], [], [])])


def test_refusals():
    cases = [
        ({"entities": [{**ENGINE, "type": "Server"}]}, "not a vocabulary type"),
        ({"entities": [{**ENGINE, "type": "Requirement"}]}, "extracted by rules"),
        ({"entities": [{**ENGINE, "name": "Billing Service", "aliases": []}]}, "neither its name nor an alias appears"),
        ({"entities": [{**ENGINE, "chunks": [9]}]}, "not in this window"),
        ({"entities": [{**INDEX, "same_as": "DataStore/unknown"}]}, "not an entity id of the catalog"),
        ({"entities": [ENGINE, {**ENGINE, "name": "matching engine"}]}, "listed twice"),
        ({"entities": [ENGINE], "relations": [{"source": "Matching Engine", "target": "Billing", "relation": "uses"}]}, "neither an entity of your answer nor of the catalog"),
        ({"entities": [ENGINE], "relations": [{"source": "Matching Engine", "target": "AI Engine", "relation": "is"}]}, "cannot relate to itself"),
        ({"entities": [ENGINE], "relations": [{"source": "Matching Engine", "target": "OpenSearch", "relation": "uses", "kind": "calls"}]}, "is not one of"),
        ({"entities": [], "topics": [{"chunk_no": 4, "facts": ["Servers"]}]}, "are not knowledge facts"),
        ({"entities": [], "topics": [{"chunk_no": 7, "facts": ["Deployment"]}]}, "not in this window"),
    ]
    for arguments, expected in cases:
        result, accepted = call(arguments)
        assert result["ok"] is False and accepted == [], arguments
        assert any(expected in error for error in result["errors"]), (expected, result["errors"])


def test_a_relation_may_end_at_a_catalog_entity_by_alias():
    result, _ = call({"entities": [ENGINE], "relations": [{"source": "AI Engine", "target": "OpenSearch", "relation": "depends on"}]})
    assert result["ok"] is True


def test_a_proposed_type_is_accepted():
    result, accepted = call({"entities": [{"name": "jm-prod", "type": "proposed:Cluster", "reason": "A cluster.", "chunks": [4]}]})
    assert result["ok"] is True and accepted[0][0][0].type == "proposed:Cluster"


def test_same_as_across_types_only_along_a_listed_promotion():
    text = TEXT + "\n\n[chunk 4] Support\nThe Platform Team Lead and the Matching Team handle escalations."
    catalog = CATALOG + [EntityRecord(entity_id="Team/matching-team", scope="App", type="Team", name="Matching Team"),
                         EntityRecord(entity_id="Role/platform-team-lead", scope="App", type="Role", name="Platform Team Lead")]

    def answer(entity):
        accepted = []
        return recognition_package(text, CHUNKS, catalog, accepted).call("submit_recognition", {"entities": [entity]})

    refused = answer({"name": "Matching Team", "type": "SupportContact", "same_as": "Team/matching-team", "chunks": [4]})
    assert refused["ok"] is False and any("is a Team, but you typed this a SupportContact" in e for e in refused["errors"])
    assert answer({"name": "Platform Team Lead", "type": "SupportContact", "same_as": "Role/platform-team-lead", "chunks": [4]})["ok"] is True
    refused = answer({**ENGINE, "type": "Tool", "same_as": "DataStore/search-index"})
    assert refused["ok"] is False


def test_an_alias_that_names_another_entity_is_refused():
    store = {"name": "OpenSearch", "type": "DataStore", "aliases": ["Search Index"], "chunks": [3]}  # the catalog's Search Index is another entity
    result, _ = call({"entities": [store]})
    assert result["ok"] is False and any("name other entities" in e for e in result["errors"])
    result, _ = call({"entities": [ENGINE, {"name": "Search Index", "type": "Component", "aliases": ["Matching Engine"], "chunks": [3]}]})
    assert result["ok"] is False


def test_two_entities_cannot_claim_one_catalog_entity():
    result, _ = call({"entities": [INDEX, {"name": "OpenSearch", "type": "DataStore", "same_as": "DataStore/search-index", "chunks": [3]}]})
    assert result["ok"] is False and any("cannot both be one catalog entity" in e for e in result["errors"])
