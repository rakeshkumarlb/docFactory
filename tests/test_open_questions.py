"""Open questions of a fact (open_questions.py) and the <Entity>.missing.md text (missing_md.py)."""
import json
from pathlib import Path

import pytest

from docfactory.completeness import field_counts
from docfactory.entitymodels.facts.backup_recovery import BackupRecovery
from docfactory.entitymodels.facts.sop import Sop
from docfactory.missing_md import missing_md
from docfactory.models.fact_question import FactQuestion
from docfactory.open_questions import default_in_words, open_questions
from docfactory.saver_resolution import entity_saver_classes
from tests.test_samples import MODEL_BY_FOLDER

SAMPLES = sorted((Path(__file__).resolve().parents[1] / "samples" / "json").glob("*/*.json"))


def test_top_level_fields_at_their_default_are_asked_with_the_default_assumed():
    questions = open_questions(Sop())
    assert [(q.path, q.default_assumed, q.missing_in) for q in questions] == [("procedures", "empty list", None), ("notes", "empty text", None)]
    assert questions[0].question == "Which standard operating procedures exist?"


def test_fields_of_list_items_are_asked_once_with_how_many_items_lack_them():
    sop = Sop.model_validate({"procedures": [{"name": "Test-A", "purpose": "Test purpose"}, {"name": "Test-B"}], "notes": "Test notes"})
    by_path = {q.path: q for q in open_questions(sop)}
    assert (by_path["procedures[].purpose"].missing_in, by_path["procedures[].purpose"].item_count) == (1, 2)
    assert (by_path["procedures[].steps"].missing_in, by_path["procedures[].steps"].default_assumed) == (2, "empty list")
    assert "procedures[].name" not in by_path and "notes" not in by_path and "procedures" not in by_path  # mandatory and answered fields


def test_a_not_applicable_answer_is_not_a_question():
    fact = BackupRecovery.model_validate({"backup_schedule": {"reason": "Test reason"}})
    assert "backup_schedule" not in {q.path for q in open_questions(fact)}
    assert "backup_schedule" in {q.path for q in open_questions(BackupRecovery())}


@pytest.mark.parametrize("path", SAMPLES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_the_questions_explain_exactly_the_unanswered_part_of_completeness(path):
    fact = MODEL_BY_FOLDER[path.parent.name].model_validate(json.loads(path.read_text(encoding="utf-8")))
    answered, total = field_counts(fact)
    assert sum(q.missing_in or 1 for q in open_questions(fact)) == total - answered


@pytest.mark.parametrize("saver_class", [c for c in entity_saver_classes() if not any(f.is_required() for f in c.model.model_fields.values())],
                         ids=lambda c: c.model.__name__)
def test_every_empty_entity_asks_every_top_level_scored_field(saver_class):
    questions = open_questions(saver_class.model())
    assert questions and all(q.question and q.default_assumed for q in questions)
    assert len(questions) == len(saver_class.model.model_fields) - sum(
        1 for f in saver_class.model.model_fields.values() if isinstance(f.json_schema_extra, dict) and f.json_schema_extra.get("scored") is False)


def test_default_in_words():
    fields = Sop.model_fields
    assert default_in_words(fields["procedures"]) == "empty list" and default_in_words(fields["notes"]) == "empty text"


def test_missing_md_is_a_numbered_list_with_question_and_default():
    questions = [FactQuestion(path="notes", question="Test question?", default_assumed="empty text"),
                 FactQuestion(path="items[].steps", question="Test steps?", default_assumed="empty list", missing_in=2, item_count=3)]
    text = missing_md("Test.Sop", questions)
    assert text.startswith("# Open questions: Test.Sop\n\n")
    assert "1. `notes`: Test question?\n   Assumed until answered: empty text\n" in text
    assert "2. `items[].steps` (missing in 2 of 3 items): Test steps?\n   Assumed until answered: empty list\n" in text
    assert text == missing_md("Test.Sop", questions)
