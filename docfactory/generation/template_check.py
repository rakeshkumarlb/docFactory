"""Checks that a document template is wired right: every binding resolves, section ids and bindings are unique."""
from docfactory.generation.bindings import source_field
from docfactory.generation.template_error import TemplateError
from docfactory.models.document_template import DocumentTemplate


def check_template(template: DocumentTemplate) -> DocumentTemplate:
    """Return `template` unchanged, or raise TemplateError naming the first problem."""
    ids = [section.id for section in template.sections]
    for section_id in dict.fromkeys(ids):
        if ids.count(section_id) > 1:
            raise TemplateError(f"{template.doc_type}: section id {section_id!r} is used more than once")
    for section in template.sections:
        bindings = [field.binding for field in section.fields]
        for field in section.fields:
            if bindings.count(field.binding) > 1:
                raise TemplateError(f"{template.doc_type}.{section.id}: binding {field.binding!r} is used more than once")
            try:
                source_field(field.binding)
            except TemplateError as error:
                raise TemplateError(f"{template.doc_type}.{section.id}: {error}") from error
    return template
