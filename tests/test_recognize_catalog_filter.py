"""The catalog a recognition call sees: entities named in the window, then entities of the hinted types."""
from docfactory.models.entity_record import EntityRecord
from docfactory.recognize.catalog_filter import catalog_for, catalog_text, mentioned


def entity(entity_id, type_, name, aliases=()):
    return EntityRecord(entity_id=entity_id, scope="App", type=type_, name=name, aliases=list(aliases))


ENGINE = entity("Component/matching-engine", "Component", "Matching Engine", ["AI Engine"])
PROD = entity("Environment/production", "Environment", "Production")
DB = entity("DataStore/primary-database", "DataStore", "Primary Database", ["PostgreSQL"])


def test_mentioned_matches_whole_words_only():
    assert mentioned("Production", "Deploy to production on Fridays.")
    assert not mentioned("Prod", "Deploy to production.")
    assert mentioned("jobs.ps", "Sync with jobs.ps nightly")


def test_named_entities_come_first_then_hinted_types():
    found = catalog_for("The AI Engine reads PostgreSQL.", [PROD, ENGINE, DB], {"Environment"})
    assert [e.entity_id for e in found] == ["Component/matching-engine", "DataStore/primary-database", "Environment/production"]


def test_the_rest_follows_item_types_first_and_the_cap_cuts_from_the_end():
    team = entity("Team/matching-team", "Team", "Matching Team")
    found = catalog_for("Nothing relevant here.", [team, PROD, ENGINE], set())
    assert [e.entity_id for e in found] == ["Component/matching-engine", "Environment/production", "Team/matching-team"]
    assert [e.entity_id for e in catalog_for("The Matching Team.", [team, PROD, ENGINE], set(), cap=2)] == ["Team/matching-team", "Component/matching-engine"]


def test_the_cap_comes_from_the_environment(monkeypatch):
    many = [entity(f"Component/c{n}", "Component", f"C{n}") for n in range(30)]
    monkeypatch.setenv("DOCFACTORY_CATALOG_MAX", "7")
    assert len(catalog_for("", many, set())) == 7


def test_catalog_text():
    assert catalog_text([]) == "(none yet)"
    assert catalog_text([ENGINE]) == "Component/matching-engine | Component | Matching Engine | aka AI Engine"
