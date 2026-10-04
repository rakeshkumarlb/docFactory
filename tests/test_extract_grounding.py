"""Grounding extracted values in their chunk text (Phase 3 redesign, step 1)."""
from docfactory.entitymodels.facts.architecture import Architecture
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.extract.grounding import grounded, identity_in_text, ungrounded_values, unknown_identities

TEXT = "3.1. User Management\nFR-01. | The system SHALL provide a self‑registration process for job seekers."


def test_identities_compare_without_case_and_trailing_punctuation():
    assert identity_in_text("FR-01", TEXT) and identity_in_text("fr-01.", TEXT)
    assert not identity_in_text("FR-001", TEXT)


def test_a_value_is_grounded_verbatim_or_by_most_of_its_words():
    assert grounded("self-registration process", TEXT)
    assert grounded("The system shall provide self-registration for job seekers", TEXT)
    assert not grounded("Single sign-on with LinkedIn accounts", TEXT)


def test_unknown_identities_are_found_in_list_items():
    data = {"requirements": [{"id": "FR-01", "title": "x", "description": "y"}, {"id": "FR-001", "title": "x", "description": "y"}]}
    assert unknown_identities(FunctionalRequirements, data, TEXT) == ["requirements[1].id: 'FR-001'"]


def test_ungrounded_values_skip_identities_and_enums_and_name_their_path():
    data = {"summary": "Invented summary about payroll", "requirements": [
        {"id": "FR-99", "title": "Self-registration", "description": "provide a self-registration process", "priority": "MUST"}]}
    assert ungrounded_values(FunctionalRequirements, data, TEXT) == ["summary: 'Invented summary about payroll'"]


def test_not_applicable_reasons_are_not_checked():
    assert ungrounded_values(Architecture, {"diagram_reference": {"reason": "No diagram was drawn."}}, TEXT) == []
