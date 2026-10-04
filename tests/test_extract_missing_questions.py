"""Missing-info questions of a merged fact (Phase 3 redesign, step 1)."""
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.extract.missing_questions import missing_questions


def test_unanswered_fields_and_item_fields_give_their_questions_once():
    data = {"requirements": [{"id": "FR-01", "title": "t", "description": "d", "priority": "MUST"},
                             {"id": "FR-02", "title": "t", "description": "d"}]}
    lines = missing_questions(FunctionalRequirements, data)
    assert "summary: How would you summarise the functional requirements?" in lines
    assert "requirements[].priority: What is the priority (MUST, SHOULD, COULD or WONT) of this requirement? (missing in 1 of 2)" in lines
    assert any(line.startswith("requirements[].acceptance_criteria:") and "(missing in 2 of 2)" in line for line in lines)
    assert not any(line.startswith("requirements[].id") for line in lines)


def test_a_not_applicable_answer_is_not_missing():
    lines = missing_questions(FunctionalRequirements, {"out_of_scope": {"reason": "None."}})
    assert not any(line.startswith("out_of_scope") for line in lines)
