"""Requirement priorities from the requirement's own keywords (Phase 3 redesign, live fixes)."""
import pytest

from docfactory.entitymodels.facts.architecture import Architecture
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.entitymodels.facts.non_functional_requirements import NonFunctionalRequirements
from docfactory.entitymodels.items.requirement_priority import RequirementPriority
from docfactory.extract.priority_keywords import fill_priorities, keyword_priority


@pytest.mark.parametrize("text, expected", [
    ("The system SHALL provide a self-registration process.", RequirementPriority.MUST),
    ("The system shall support data migration.", RequirementPriority.MUST),
    ("Users SHALL NOT see other users' data.", RequirementPriority.MUST),
    ("The tool must show a diff.", RequirementPriority.MUST),
    ("The page SHOULD load fast.", RequirementPriority.SHOULD),
    ("Admins MAY export reports.", RequirementPriority.COULD),
    ("The system SHALL log access and SHOULD alert on failures.", RequirementPriority.MUST),
])
def test_the_strongest_keyword_decides(text, expected):
    assert keyword_priority(text) == expected


def test_lowercase_may_and_text_without_keywords_give_nothing():
    assert keyword_priority("Users may want to filter by region.") is None
    assert keyword_priority("It would be good if folders could be ignored.") is None


def test_only_empty_priorities_are_filled_from_the_items_statement():
    data = {"requirements": [
        {"id": "FR-01", "title": "t", "description": "The system SHALL register users."},
        {"id": "FR-02", "title": "t", "description": "The system SHALL export.", "priority": "COULD"},
        {"id": "FR-03", "title": "t", "description": "Nice to have folders ignored."},
    ]}
    filled, count = fill_priorities(FunctionalRequirements, data)
    assert [r.get("priority") for r in filled["requirements"]] == ["MUST", "COULD", None] and count == 1
    assert "priority" not in data["requirements"][0]  # the input is not changed


def test_non_functional_requirements_use_their_statement_and_other_entities_are_untouched():
    data = {"requirements": [{"id": "NFR-01", "category": "PERFORMANCE", "statement": "Pages SHOULD load in 2 s."}]}
    assert fill_priorities(NonFunctionalRequirements, data)[0]["requirements"][0]["priority"] == "SHOULD"
    assert fill_priorities(Architecture, {"components": [{"name": "API"}]}) == ({"components": [{"name": "API"}]}, 0)
