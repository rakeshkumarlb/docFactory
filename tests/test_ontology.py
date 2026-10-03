"""The ingestion ontology: every entity has signals, signals name only real entities, and docs/ontology.md is up to date."""
import json

import pytest

from docfactory.ontology import ontology_render
from docfactory.ontology.signals import SIGNALS_FILE, entity_names, load_signals


def test_every_entity_has_exactly_one_signals_entry_in_entity_order():
    assert [entry.entity for entry in load_signals()] == entity_names()


def test_every_entity_has_at_least_one_heading_term():
    assert all(entry.heading_terms for entry in load_signals())


def test_heading_terms_and_keywords_are_lower_case():
    for entry in load_signals():
        assert all(term == term.lower() for term in entry.heading_terms + entry.keywords), entry.entity


def _write(tmp_path, entries):
    path = tmp_path / "signals.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_an_unknown_entity_is_rejected(tmp_path):
    entries = json.loads(SIGNALS_FILE.read_text(encoding="utf-8")) + [{"entity": "Made Up", "heading_terms": ["x"]}]
    with pytest.raises(ValueError, match="unknown entity"):
        load_signals(_write(tmp_path, entries))


def test_a_missing_entity_is_rejected(tmp_path):
    entries = [e for e in json.loads(SIGNALS_FILE.read_text(encoding="utf-8")) if e["entity"] != "Sop"]
    with pytest.raises(ValueError, match="without signals: \\['Sop'\\]"):
        load_signals(_write(tmp_path, entries))


def test_a_duplicate_entity_is_rejected(tmp_path):
    entries = json.loads(SIGNALS_FILE.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="more than one"):
        load_signals(_write(tmp_path, entries + entries[:1]))


def test_id_patterns_do_not_cross_match_functional_and_non_functional_ids():
    import re
    signals = {entry.entity: entry for entry in load_signals()}
    fr = [re.compile(p) for p in signals["FunctionalRequirements"].id_patterns]
    nfr = [re.compile(p) for p in signals["NonFunctionalRequirements"].id_patterns]
    assert any(p.search("FR-12.") for p in fr) and not any(p.search("NFR-12.") for p in fr)
    assert any(p.search("NFR-126.") for p in nfr) and not any(p.search("FR-12.") for p in nfr)


def test_the_ontology_document_is_generated_and_up_to_date():
    text = ontology_render.render_ontology()
    assert text == ontology_render.render_ontology()
    for name in entity_names():
        assert f"## {name}" in text
    assert "`requirements`" in text and "`priority`" in text  # nested item facts are listed
    assert ontology_render.OUTPUT.read_text(encoding="utf-8") == text, "run python -m docfactory.ontology.ontology_render"
