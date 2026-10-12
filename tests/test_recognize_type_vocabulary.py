"""The entity type vocabulary of recognition: derived from the fact registry, plus graph-only types."""
from docfactory.recognize.type_vocabulary import (GRAPH_TYPES, entity_types, identifier_types, item_types, type_problem, types_of_fact,
                                                  vocabulary_text)


def test_item_types_map_to_their_fact_and_list_field():
    mapping = {name: (fact, field) for name, (fact, field, _) in item_types().items()}
    assert mapping["Component"] == ("Architecture", "components")
    assert mapping["DataStore"] == ("Architecture", "data_stores")
    assert mapping["Integration"] == ("Architecture", "integrations")
    assert mapping["Environment"] == ("Environments", "environments")
    assert mapping["Alert"] == ("Monitoring", "alerts")
    assert mapping["SopProcedure"] == ("Sop", "procedures")
    assert mapping["SupportContact"] == ("Support", "contacts")
    assert mapping["KnownError"] == ("KnownErrors", "known_errors")
    assert "NoteEntry" not in mapping  # notes are written by discovery, never recognized


def test_identifier_types_are_left_to_the_rules():
    assert identifier_types() == {"Requirement", "NonFunctionalRequirement"}
    assert not identifier_types() & set(entity_types())


def test_the_vocabulary_is_item_types_then_graph_types_each_with_a_definition():
    names = list(entity_types())
    assert names[: len(names) - len(GRAPH_TYPES)] == [n for n in item_types() if n not in identifier_types()]
    assert set(GRAPH_TYPES) <= set(names)
    assert all(text.strip() for text in entity_types().values())
    assert "- Component: " in vocabulary_text()


def test_types_of_fact():
    assert types_of_fact("Architecture") == ["Component", "DataStore", "Integration"]
    assert types_of_fact("FunctionalRequirements") == []  # identifier types only
    assert types_of_fact("Deployment") == []


def test_type_problems():
    assert type_problem("Component") is None
    assert type_problem("Runbook") is None
    assert type_problem("proposed:Certificate") is None
    assert "not a vocabulary type" in type_problem("Server")
    assert "extracted by rules" in type_problem("Requirement")
    assert "already a vocabulary type" in type_problem("proposed:Component")
    assert "proposed:<PascalName>" in type_problem("proposed:tls certificate")
