"""The gaps of a configuration-based document: the same rule as generation/gaps.py, over the template's fields in template order."""
from docfactory.configrender.bindings import field_name, question_for
from docfactory.documentmodels.shared.document_gap import DocumentGap
from docfactory.generation.gaps import gaps_of_bindings
from docfactory.models.document_template import DocumentTemplate


def configured_gaps(template: DocumentTemplate, app_id: str) -> list[DocumentGap]:
    """Every gap of `app_id`'s `template` document, numbered 1..n; a gap's field is '<section id>.<entity field>'."""
    bindings = ((f"{section.id}.{field_name(field.binding)}", question_for(field), field.binding)
                for section in template.sections for field in section.fields)
    return gaps_of_bindings(bindings, app_id)
