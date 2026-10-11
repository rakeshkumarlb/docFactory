"""Which key an entity extracted from an ingested file is saved under (Phase 3 redesign, step 1)."""
import pytest

from docfactory.extract.fact_keys import fact_key, is_shared_entity
from docfactory.bundle.fact_registry import FACT_SPECS, entity_names, entity_of_key


def test_an_application_folder_gives_an_application_key():
    assert fact_key("AI-Driven-Job-Matching-Platform/srs.pdf", "FunctionalRequirements") == ("AI-Driven-Job-Matching-Platform.FunctionalRequirements", "")


@pytest.mark.parametrize("entity", ["Slo", "Kpis"])
def test_shared_entities_come_only_from_the_shared_folder(entity):
    assert fact_key("shared/standards.pdf", entity) == (f"Shared.{entity}", "")
    key, reason = fact_key("ReadmeForge/srs.pdf", entity)
    assert key is None and "only from files in shared/" in reason


def test_the_shared_folder_gives_no_application_facts():
    key, reason = fact_key("shared/standards.pdf", "Architecture")
    assert key is None and "application-specific" in reason


def test_the_general_folder_gives_no_facts():
    assert fact_key("general/notes.txt", "Architecture")[0] is None


def test_unknown_entity_and_unscoped_path_give_no_key():
    assert fact_key("ReadmeForge/srs.pdf", "Nope")[0] is None
    assert fact_key("srs.pdf", "Architecture")[0] is None


def test_every_derived_key_is_accepted_by_the_fact_registry():
    for entity in entity_names():
        key, _ = fact_key(("shared" if is_shared_entity(entity) else "ReadmeForge") + "/references/doc.pdf", entity)
        assert entity_of_key(key) == entity, key


def test_the_registry_finds_the_model_by_entity_name():
    assert FACT_SPECS["Slo"]["model"].__name__ == "Slo"
    assert "Missing" not in FACT_SPECS
