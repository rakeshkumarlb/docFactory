"""The gaps of a generated document, found by code: what its template binds that the facts do not answer.

Walks the template's fact-bound fields in template order. A bound field whose fact is absent, or whose source
field is still unanswered, is one gap. A bound field that is answered and holds a nested model or list of items adds the fact's open
questions under that field (open_questions.py: the same rule as completeness), re-pathed to the document field, 'missing in k of n'
kept and at most three example items. Only bound fields count: a fact's fields the template does not use are not this document's gaps.
Deterministic, numbered 1..n; `gaps_hash` is what lets generate skip the needs-list call when nothing changed.
"""
from docfactory.build import is_answered, load_fact
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.documentmodels.document_gap import DocumentGap
from docfactory.models.not_applicable import NotApplicable
from docfactory.open_questions import open_questions

EXAMPLE_ITEMS = 3
EXAMPLE_CHARS = 120


def _example(label: str) -> str:
    return label if len(label) <= EXAMPLE_CHARS else label[:EXAMPLE_CHARS - 3].rstrip() + "..."


def gaps_of_bindings(bindings, app_id: str) -> list[DocumentGap]:
    """Every gap of a template given as (document path, question, '<Fact>.<field>') triples in template order, numbered 1..n.
    """
    facts: dict = {}
    questions: dict = {}
    found: list[dict] = []
    for path, question_text, binding in bindings:
        fact_name, _, source = binding.partition(".")
        fact = load_fact(app_id, fact_name, facts)
        source_field = type(fact).model_fields.get(source) if fact is not None else None
        value = getattr(fact, source) if source_field is not None else None
        if source_field is None or not is_answered(source_field, value):
            found.append({"field": path, "question": question_text, "expected_source": binding})
            continue
        if isinstance(value, NotApplicable):
            continue
        if fact_name not in questions:
            questions[fact_name] = open_questions(fact)
        for question in questions[fact_name]:
            if not question.path.startswith((f"{source}.", f"{source}[].")):
                continue
            rest = question.path[len(source):]
            found.append({"field": f"{path}{rest}", "question": question.question, "expected_source": f"{fact_name}.{question.path}",
                          "missing_in": question.missing_in, "item_count": question.item_count,
                          "example_items": [_example(label) for label in question.missing_items[:EXAMPLE_ITEMS]]})
    return [DocumentGap(number=number, **gap) for number, gap in enumerate(found, start=1)]


def gaps_hash(gaps: list[DocumentGap]) -> str:
    """SHA-256 of the canonical JSON of the gaps: unchanged gaps, unchanged hash."""
    return sha256_hex(canonical_json([gap.model_dump(mode="json") for gap in gaps]))
